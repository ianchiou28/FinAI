"""
IBKR模拟交易订单执行器
"""
import uuid
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import Order, Position, Trade, Account
from ib_insync import *
import logging

logger = logging.getLogger(__name__)

# 美股交易常量
US_MIN_ORDER_QUANTITY = 1  # 最小交易单位
US_COMMISSION_PER_SHARE = 0.005  # 每股佣金 USD 0.005
US_MIN_COMMISSION = 1.0  # 最低佣金 USD 1

def _calc_us_fee(quantity: int, price: float) -> Decimal:
    """计算美股交易费用"""
    commission = max(Decimal(str(quantity)) * Decimal(str(US_COMMISSION_PER_SHARE)), Decimal(str(US_MIN_COMMISSION)))
    return commission

def get_ib_connection():
    """获取IBKR连接"""
    from .ibkr_market_data import get_ib_connection
    return get_ib_connection()

def place_ibkr_order(
    symbol: str,
    action: str,
    quantity: int,
    order_type: str = "MKT",
    limit_price: float = None
) -> Optional[Trade]:
    """在IBKR平台下单"""
    try:
        ib = get_ib_connection()
        
        # 创建合约
        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)
        
        # 创建订单
        if order_type == "MKT":
            order = MarketOrder(action, quantity)
        elif order_type == "LMT":
            order = LimitOrder(action, quantity, limit_price)
        else:
            order = MarketOrder(action, quantity)
        
        # 下单
        trade = ib.placeOrder(contract, order)
        
        # 等待订单状态更新
        ib.sleep(2)
        
        logger.info(f"IBKR下单成功: {action} {quantity} {symbol}")
        return trade
    except Exception as e:
        logger.error(f"IBKR下单异常: {e}")
        return None

def place_and_execute_ibkr_order(
    db: Session,
    account: Account,
    symbol: str,
    name: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    use_ibkr_platform: bool = True
) -> Order:
    """
    下单并执行IBKR订单
    
    Args:
        account: 交易账户
        symbol: 股票代码 (e.g., "AAPL", "MSFT")
        name: 股票名称
        side: "BUY" or "SELL"
        order_type: "LIMIT" or "MARKET"
        price: 订单价格
        quantity: 数量
        use_ibkr_platform: 是否使用IBKR平台（True）或本地模拟（False）
    """
    
    # 验证最小交易单位
    if quantity < US_MIN_ORDER_QUANTITY:
        raise ValueError(f"数量必须 >= {US_MIN_ORDER_QUANTITY}")
    
    # 获取执行价格
    if order_type == "MARKET" or not price:
        from .ibkr_market_data import get_last_price
        exec_price = Decimal(str(get_last_price(symbol) or price))
    else:
        exec_price = Decimal(str(price))
    
    notional = exec_price * Decimal(str(quantity))
    is_sell = side.upper() == "SELL"
    
    # 计算费用
    commission = _calc_us_fee(quantity, float(exec_price))
    total_fee = commission
    
    # 创建订单
    order = Order(
        version="v1",
        account_id=account.id,
        order_no=uuid.uuid4().hex[:16],
        symbol=symbol,
        name=name,
        market="US",
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
            raise ValueError(f"现金不足。需要 ${total_cost}，可用 ${available_cash}")
        
        account.current_cash = float(available_cash - total_cost)
        
        # 更新或创建持仓
        pos = (
            db.query(Position)
            .filter(
                Position.account_id == account.id,
                Position.symbol == symbol,
                Position.market == "US"
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
                market="US",
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
                Position.market == "US"
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
    
    # 如果使用IBKR平台，在IBKR下单
    ibkr_trade = None
    if use_ibkr_platform:
        try:
            action = "BUY" if side.upper() == "BUY" else "SELL"
            ibkr_order_type = "LMT" if order_type == "LIMIT" else "MKT"
            limit_price = float(exec_price) if order_type == "LIMIT" else None
            
            ibkr_trade = place_ibkr_order(symbol, action, quantity, ibkr_order_type, limit_price)
            if ibkr_trade:
                logger.info(f"订单已在IBKR平台下单: {order.order_no}")
            else:
                logger.warning(f"IBKR平台下单失败，继续本地模拟: {order.order_no}")
        except Exception as e:
            logger.error(f"IBKR平台下单失败: {e}")
            # 即使IBKR下单失败，也继续本地模拟
    
    # 创建成交记录
    trade = Trade(
        order_id=order.id,
        account_id=account.id,
        symbol=symbol,
        name=name,
        market="US",
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

def cancel_ibkr_order(order_id: str) -> bool:
    """撤销IBKR订单"""
    try:
        ib = get_ib_connection()
        
        # 获取所有未完成订单
        trades = ib.trades()
        for trade in trades:
            if str(trade.order.orderId) == order_id:
                ib.cancelOrder(trade.order)
                logger.info(f"IBKR订单撤销成功: {order_id}")
                return True
        
        logger.warning(f"未找到IBKR订单: {order_id}")
        return False
    except Exception as e:
        logger.error(f"IBKR订单撤销异常: {e}")
        return False

def get_ibkr_orders() -> List[Dict[str, Any]]:
    """获取IBKR订单列表"""
    try:
        ib = get_ib_connection()
        trades = ib.trades()
        
        orders = []
        for trade in trades:
            orders.append({
                'order_id': trade.order.orderId,
                'symbol': trade.contract.symbol,
                'action': trade.order.action,
                'quantity': trade.order.totalQuantity,
                'order_type': trade.order.orderType,
                'limit_price': getattr(trade.order, 'lmtPrice', 0),
                'status': trade.orderStatus.status,
                'filled': trade.orderStatus.filled,
                'remaining': trade.orderStatus.remaining
            })
        
        return orders
    except Exception as e:
        logger.error(f"获取IBKR订单列表异常: {e}")
        return []