"""
富途模拟交易订单执行器
"""
import uuid
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import Order, Position, Trade, Account
from futu import *
import logging

logger = logging.getLogger(__name__)

# 港股交易常量
HK_MIN_ORDER_QUANTITY = 100  # 最小交易单位
HK_COMMISSION_RATE = 0.0003  # 佣金费率 0.03%
HK_MIN_COMMISSION = 3.0  # 最低佣金 HKD 3
HK_PLATFORM_FEE = 15.0  # 平台费 HKD 15
HK_STAMP_DUTY_RATE = 0.001  # 印花税 0.1%

# 美股交易常量  
US_MIN_ORDER_QUANTITY = 1  # 最小交易单位
US_COMMISSION_PER_SHARE = 0.005  # 每股佣金 USD 0.005
US_MIN_COMMISSION = 1.0  # 最低佣金 USD 1

def _calc_hk_fee(notional: Decimal, is_sell: bool = False) -> tuple[Decimal, Decimal, Decimal]:
    """
    计算港股交易费用
    Returns: (commission, platform_fee, stamp_duty)
    """
    # 佣金
    commission = max(notional * Decimal(str(HK_COMMISSION_RATE)), Decimal(str(HK_MIN_COMMISSION)))
    
    # 平台费
    platform_fee = Decimal(str(HK_PLATFORM_FEE))
    
    # 印花税（买卖都收）
    stamp_duty = notional * Decimal(str(HK_STAMP_DUTY_RATE))
    
    return commission, platform_fee, stamp_duty

def _calc_us_fee(quantity: int) -> Decimal:
    """
    计算美股交易费用
    Returns: commission
    """
    commission = max(Decimal(str(quantity)) * Decimal(str(US_COMMISSION_PER_SHARE)), Decimal(str(US_MIN_COMMISSION)))
    return commission

def get_trade_context():
    """获取交易连接"""
    from .futu_market_data import get_trade_context
    return get_trade_context()

def place_futu_order(
    symbol: str,
    side: str,
    quantity: int,
    price: float,
    order_type: str = "NORMAL"
) -> bool:
    """在富途平台下单"""
    try:
        trd_ctx = get_trade_context()
        
        # 转换订单类型
        futu_order_type = OrderType.NORMAL if order_type == "LIMIT" else OrderType.MARKET
        futu_side = TrdSide.BUY if side.upper() == "BUY" else TrdSide.SELL
        
        ret, data = trd_ctx.place_order(
            price=price,
            qty=quantity,
            code=symbol,
            trd_side=futu_side,
            order_type=futu_order_type,
            trd_env=TrdEnv.SIMULATE  # 使用模拟交易环境
        )
        
        if ret == RET_OK:
            logger.info(f"富途下单成功: {side} {quantity} {symbol} @ {price}")
            return True
        else:
            logger.error(f"富途下单失败: {data}")
            return False
    except Exception as e:
        logger.error(f"富途下单异常: {e}")
        return False

def place_and_execute_futu_order(
    db: Session,
    account: Account,
    symbol: str,
    name: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    use_futu_platform: bool = True
) -> Order:
    """
    下单并执行富途订单
    
    Args:
        account: 交易账户
        symbol: 股票代码 (e.g., "HK.00700", "US.AAPL")
        name: 股票名称
        side: "BUY" or "SELL"
        order_type: "LIMIT" or "MARKET"
        price: 订单价格
        quantity: 数量
        use_futu_platform: 是否使用富途平台（True）或本地模拟（False）
    """
    
    # 判断市场类型
    market = "HK" if symbol.startswith("HK.") else "US" if symbol.startswith("US.") else "CN"
    
    # 验证最小交易单位
    min_qty = HK_MIN_ORDER_QUANTITY if market == "HK" else US_MIN_ORDER_QUANTITY
    if quantity < min_qty:
        raise ValueError(f"数量必须 >= {min_qty}")
    
    # 港股必须是100的倍数
    if market == "HK" and quantity % HK_MIN_ORDER_QUANTITY != 0:
        raise ValueError(f"港股数量必须是{HK_MIN_ORDER_QUANTITY}的倍数")
    
    # 获取执行价格
    if order_type == "MARKET" or not price:
        from .futu_market_data import get_last_price
        exec_price = Decimal(str(get_last_price(symbol) or price))
    else:
        exec_price = Decimal(str(price))
    
    notional = exec_price * Decimal(str(quantity))
    is_sell = side.upper() == "SELL"
    
    # 计算费用
    if market == "HK":
        commission, platform_fee, stamp_duty = _calc_hk_fee(notional, is_sell)
        total_fee = commission + platform_fee + stamp_duty
    else:  # US market
        commission = _calc_us_fee(quantity)
        total_fee = commission
    
    # 创建订单
    order = Order(
        version="v1",
        account_id=account.id,
        order_no=uuid.uuid4().hex[:16],
        symbol=symbol,
        name=name,
        market=market,
        side=side.upper(),
        order_type=order_type,
        price=float(exec_price),
        quantity=quantity,
        leverage=1,
        filled_quantity=0,
        status="PENDING",
    )
    db.add(order)
    db.flush()
    
    # 执行订单
    if side.upper() == "BUY":
        # 买入：扣除现金
        total_cost = notional + total_fee
        available_cash = Decimal(str(account.current_cash))
        
        if available_cash < total_cost:
            raise ValueError(f"现金不足。需要 {total_cost}，可用 {available_cash}")
        
        account.current_cash = float(available_cash - total_cost)
        
        # 更新或创建持仓
        pos = (
            db.query(Position)
            .filter(
                Position.account_id == account.id,
                Position.symbol == symbol,
                Position.market == market
            )
            .first()
        )
        
        if pos:
            # 更新现有持仓
            old_notional = Decimal(str(pos.quantity)) * Decimal(str(pos.avg_cost))
            new_qty = Decimal(str(pos.quantity)) + Decimal(str(quantity))
            new_cost = (old_notional + notional) / new_qty
            pos.quantity = float(new_qty)
            pos.available_quantity = float(new_qty)
            pos.avg_cost = float(new_cost)
        else:
            # 创建新持仓
            pos = Position(
                version="v1",
                account_id=account.id,
                symbol=symbol,
                name=name,
                market=market,
                quantity=quantity,
                available_quantity=quantity,
                avg_cost=float(exec_price),
                leverage=1,
            )
            db.add(pos)
            db.flush()
    
    elif side.upper() == "SELL":
        # 卖出：检查持仓并增加现金
        pos = (
            db.query(Position)
            .filter(
                Position.account_id == account.id,
                Position.symbol == symbol,
                Position.market == market
            )
            .first()
        )
        
        if not pos or Decimal(str(pos.available_quantity)) < Decimal(str(quantity)):
            available = pos.available_quantity if pos else 0
            raise ValueError(f"持仓不足。可用: {available}，尝试卖出: {quantity}")
        
        # 增加现金（成交金额 - 费用）
        cash_gain = notional - total_fee
        account.current_cash = float(Decimal(str(account.current_cash)) + cash_gain)
        
        # 更新持仓
        pos.quantity = float(Decimal(str(pos.quantity)) - Decimal(str(quantity)))
        pos.available_quantity = float(Decimal(str(pos.available_quantity)) - Decimal(str(quantity)))
    
    else:
        raise ValueError(f"无效的方向: {side}。必须是 BUY 或 SELL")
    
    # 如果使用富途平台，在富途下单
    if use_futu_platform:
        try:
            place_futu_order(symbol, side, quantity, float(exec_price), order_type)
            logger.info(f"订单已在富途平台下单: {order.order_no}")
        except Exception as e:
            logger.error(f"富途平台下单失败: {e}")
            # 即使富途下单失败，也继续本地模拟
    
    # 创建成交记录
    trade = Trade(
        order_id=order.id,
        account_id=account.id,
        symbol=symbol,
        name=name,
        market=market,
        side=side.upper(),
        price=float(exec_price),
        quantity=quantity,
        commission=float(total_fee),
        taker_fee=0,
        interest_charged=0,
    )
    db.add(trade)
    
    # 标记订单为已成交
    order.filled_quantity = quantity
    order.status = "FILLED"
    
    db.commit()
    db.refresh(order)
    db.refresh(account)
    if pos:
        db.refresh(pos)
    
    return order

def cancel_futu_order(order_id: str) -> bool:
    """撤销富途订单"""
    try:
        trd_ctx = get_trade_context()
        ret, data = trd_ctx.modify_order(ModifyOrderOp.CANCEL, order_id, 0, 0)
        if ret == RET_OK:
            logger.info(f"富途订单撤销成功: {order_id}")
            return True
        else:
            logger.error(f"富途订单撤销失败: {data}")
            return False
    except Exception as e:
        logger.error(f"富途订单撤销异常: {e}")
        return False