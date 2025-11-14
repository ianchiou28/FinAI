"""
MT5模拟交易订单执行器 - A股
"""
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import Order, Position, Trade, Account
import MetaTrader5 as mt5
import logging

logger = logging.getLogger(__name__)

# A股交易常量
CN_MIN_ORDER_QUANTITY = 100  # 最小交易单位（1手=100股）
CN_COMMISSION_RATE = Decimal("0.0003")  # 佣金费率 0.03%
CN_MIN_COMMISSION = Decimal("5")  # 最低佣金 5元
CN_STAMP_TAX_RATE = Decimal("0.001")  # 印花税 0.1%（仅卖出）
CN_TRANSFER_FEE_RATE = Decimal("0.00002")  # 过户费 0.002%

def _calc_cn_fee(quantity: int, price: float, is_sell: bool) -> Decimal:
    """计算A股交易费用"""
    notional = Decimal(str(quantity)) * Decimal(str(price))
    
    # 佣金
    commission = max(notional * CN_COMMISSION_RATE, CN_MIN_COMMISSION)
    
    # 印花税（仅卖出）
    stamp_tax = notional * CN_STAMP_TAX_RATE if is_sell else Decimal("0")
    
    # 过户费
    transfer_fee = notional * CN_TRANSFER_FEE_RATE
    
    return commission + stamp_tax + transfer_fee

def init_mt5() -> bool:
    """初始化MT5"""
    from .mt5_market_data import init_mt5
    return init_mt5()

def place_mt5_order(
    symbol: str,
    action: str,
    volume: float,
    order_type: int = mt5.ORDER_TYPE_BUY,
    price: float = 0.0,
    sl: float = 0.0,
    tp: float = 0.0
) -> Optional[mt5.OrderSendResult]:
    """在MT5平台下单"""
    try:
        if not init_mt5():
            return None
        
        # 获取股票信息
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"股票{symbol}不存在")
            return None
        
        # 确保股票可见
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"无法选择股票{symbol}")
                return None
        
        # 准备交易请求
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price if price > 0 else mt5.symbol_info_tick(symbol).ask,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 234000,
            "comment": "FinAI MT5",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # 发送交易请求
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"MT5下单失败: {result.comment}")
            return None
        
        logger.info(f"MT5下单成功: {action} {volume} {symbol}")
        return result
    except Exception as e:
        logger.error(f"MT5下单异常: {e}")
        return None

def place_and_execute_mt5_order(
    db: Session,
    account: Account,
    symbol: str,
    name: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    use_mt5_platform: bool = False,
    market: str = "CN"
) -> Order:
    """
    下单并执行MT5订单（A股）
    
    Args:
        account: 交易账户
        symbol: 股票代码 (e.g., "600000", "000001")
        name: 股票名称
        side: "BUY" or "SELL"
        order_type: "LIMIT" or "MARKET"
        price: 订单价格
        quantity: 数量（必须是100的倍数）
        use_mt5_platform: 是否使用MT5平台（True）或本地模拟（False）
    """
    
    # 验证最小交易单位
    if quantity % CN_MIN_ORDER_QUANTITY != 0:
        raise ValueError(f"数量必须是{CN_MIN_ORDER_QUANTITY}的倍数")
    
    # 获取执行价格
    if order_type == "MARKET" or not price:
        from .mt5_market_data import get_last_price
        exec_price = Decimal(str(get_last_price(symbol) or price))
    else:
        exec_price = Decimal(str(price))
    
    notional = exec_price * Decimal(str(quantity))
    is_sell = side.upper() == "SELL"
    
    # 计算费用
    total_fee = _calc_cn_fee(quantity, float(exec_price), is_sell)
    
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
            raise ValueError(f"现金不足。需要 ¥{total_cost}，可用 ¥{available_cash}")
        
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
    
    # 如果使用MT5平台，在MT5下单
    mt5_result = None
    if use_mt5_platform:
        try:
            order_type_mt5 = mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else mt5.ORDER_TYPE_SELL
            volume = quantity / 100.0  # MT5使用手数
            
            mt5_result = place_mt5_order(
                symbol, 
                side, 
                volume, 
                order_type_mt5, 
                float(exec_price) if order_type == "LIMIT" else 0.0
            )
            
            if mt5_result:
                logger.info(f"订单已在MT5平台下单: {order.order_no}")
            else:
                logger.warning(f"MT5平台下单失败，继续本地模拟: {order.order_no}")
        except Exception as e:
            logger.error(f"MT5平台下单失败: {e}")
    
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

def cancel_mt5_order(ticket: int) -> bool:
    """撤销MT5订单"""
    try:
        if not init_mt5():
            return False
        
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"MT5订单撤销成功: {ticket}")
            return True
        else:
            logger.error(f"MT5订单撤销失败: {result.comment}")
            return False
    except Exception as e:
        logger.error(f"MT5订单撤销异常: {e}")
        return False

def get_mt5_orders() -> List[Dict[str, Any]]:
    """获取MT5订单列表"""
    try:
        if not init_mt5():
            return []
        
        orders = mt5.orders_get()
        if orders is None:
            return []
        
        order_list = []
        for order in orders:
            order_list.append({
                'ticket': order.ticket,
                'symbol': order.symbol,
                'type': 'BUY' if order.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': order.volume_current,
                'price_open': order.price_open,
                'price_current': order.price_current,
                'state': order.state,
                'time_setup': order.time_setup
            })
        
        return order_list
    except Exception as e:
        logger.error(f"获取MT5订单列表异常: {e}")
        return []
