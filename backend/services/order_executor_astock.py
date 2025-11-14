"""
A-share paper trading order executor
Supports both simulation (local) and THS platform integration
"""
import uuid
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import Order, Position, Trade, Account
import logging

logger = logging.getLogger(__name__)

# A-share trading constants
ASTOCK_MIN_COMMISSION = 5.0  # ¥5 minimum commission
ASTOCK_COMMISSION_RATE = 0.0003  # 0.03% commission rate
ASTOCK_STAMP_TAX_RATE = 0.001  # 0.1% stamp tax (only on sell)
ASTOCK_MIN_ORDER_QUANTITY = 100  # Minimum 1 lot (100 shares)
ASTOCK_LOT_SIZE = 100  # 1 lot = 100 shares


def _calc_astock_fee(notional: Decimal, is_sell: bool = False) -> tuple[Decimal, Decimal]:
    """
    Calculate A-share trading fees
    Returns: (commission, stamp_tax)
    """
    # Commission (both buy and sell)
    commission = max(notional * Decimal(str(ASTOCK_COMMISSION_RATE)), Decimal(str(ASTOCK_MIN_COMMISSION)))
    
    # Stamp tax (only on sell)
    stamp_tax = notional * Decimal(str(ASTOCK_STAMP_TAX_RATE)) if is_sell else Decimal(0)
    
    return commission, stamp_tax


def place_and_execute_astock(
    db: Session,
    account: Account,
    symbol: str,
    name: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    use_ths: bool = False
) -> Order:
    """
    Place and execute an A-share order
    
    Args:
        account: Trading account
        symbol: Stock code (e.g., "600000")
        name: Stock name
        side: "BUY" or "SELL"
        order_type: "LIMIT" or "MARKET"
        price: Order price (CNY)
        quantity: Number of shares (must be multiple of 100)
        use_ths: Whether to use THS platform (True) or local simulation (False)
    """
    # Validate quantity (must be multiple of 100)
    if quantity % ASTOCK_LOT_SIZE != 0:
        raise ValueError(f"Quantity must be multiple of {ASTOCK_LOT_SIZE} (1 lot)")
    
    if quantity < ASTOCK_MIN_ORDER_QUANTITY:
        raise ValueError(f"Quantity must be >= {ASTOCK_MIN_ORDER_QUANTITY}")
    
    # Get execution price
    if order_type == "MARKET" or not price:
        # For market orders, get current price
        from .market_data import get_last_price
        exec_price = Decimal(str(get_last_price(symbol, "ASTOCK")))
    else:
        exec_price = Decimal(str(price))
    
    notional = exec_price * Decimal(str(quantity))
    is_sell = side.upper() == "SELL"
    
    # Calculate fees
    commission, stamp_tax = _calc_astock_fee(notional, is_sell)
    total_fee = commission + stamp_tax
    
    # Create order
    order = Order(
        version="v1",
        account_id=account.id,
        order_no=uuid.uuid4().hex[:16],
        symbol=symbol,
        name=name,
        market="ASTOCK",
        side=side.upper(),
        order_type=order_type,
        price=float(exec_price),
        quantity=quantity,
        leverage=1,  # A-share doesn't support leverage
        filled_quantity=0,
        status="PENDING",
    )
    db.add(order)
    db.flush()
    
    # Execute order based on side
    if side.upper() == "BUY":
        # Buy: deduct cash
        total_cost = notional + total_fee
        available_cash = Decimal(str(account.current_cash))
        
        if available_cash < total_cost:
            raise ValueError(f"Insufficient cash. Need ¥{total_cost}, have ¥{available_cash}")
        
        account.current_cash = float(available_cash - total_cost)
        
        # Update or create position
        pos = (
            db.query(Position)
            .filter(
                Position.account_id == account.id,
                Position.symbol == symbol,
                Position.market == "ASTOCK"
            )
            .first()
        )
        
        if pos:
            # Update existing position
            old_notional = Decimal(str(pos.quantity)) * Decimal(str(pos.avg_cost))
            new_qty = Decimal(str(pos.quantity)) + Decimal(str(quantity))
            new_cost = (old_notional + notional) / new_qty
            pos.quantity = float(new_qty)
            pos.available_quantity = float(new_qty)
            pos.avg_cost = float(new_cost)
        else:
            # Create new position
            pos = Position(
                version="v1",
                account_id=account.id,
                symbol=symbol,
                name=name,
                market="ASTOCK",
                quantity=quantity,
                available_quantity=quantity,
                avg_cost=float(exec_price),
                leverage=1,
            )
            db.add(pos)
            db.flush()
    
    elif side.upper() == "SELL":
        # Sell: check position and add cash
        pos = (
            db.query(Position)
            .filter(
                Position.account_id == account.id,
                Position.symbol == symbol,
                Position.market == "ASTOCK"
            )
            .first()
        )
        
        if not pos or Decimal(str(pos.available_quantity)) < Decimal(str(quantity)):
            raise ValueError(f"Insufficient position. Have: {pos.available_quantity if pos else 0}, trying to sell: {quantity}")
        
        # Add cash (notional - fees)
        cash_gain = notional - total_fee
        account.current_cash = float(Decimal(str(account.current_cash)) + cash_gain)
        
        # Update position
        pos.quantity = float(Decimal(str(pos.quantity)) - Decimal(str(quantity)))
        pos.available_quantity = float(Decimal(str(pos.available_quantity)) - Decimal(str(quantity)))
    
    else:
        raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")
    
    # If using THS platform, place order on THS
    if use_ths:
        try:
            from .ths_market_data import place_ths_order
            direction = "buy" if side.upper() == "BUY" else "sell"
            place_ths_order(symbol, direction, quantity, float(exec_price))
            logger.info(f"Order placed on THS platform: {order.order_no}")
        except Exception as e:
            logger.error(f"Failed to place order on THS: {e}")
            # Continue with local simulation even if THS fails
    
    # Create trade record
    trade = Trade(
        order_id=order.id,
        account_id=account.id,
        symbol=symbol,
        name=name,
        market="ASTOCK",
        side=side.upper(),
        price=float(exec_price),
        quantity=quantity,
        commission=float(commission),
        taker_fee=float(stamp_tax),  # Use taker_fee field for stamp tax
        interest_charged=0,
    )
    db.add(trade)
    
    # Mark order as filled
    order.filled_quantity = quantity
    order.status = "FILLED"
    
    db.commit()
    db.refresh(order)
    db.refresh(account)
    if pos:
        db.refresh(pos)
    
    return order
