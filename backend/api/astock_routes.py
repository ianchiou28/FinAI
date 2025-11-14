"""
IBKR trading API routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database.connection import get_db
from database.models import Account
from services.ibkr_order_executor import place_and_execute_ibkr_order, get_ibkr_orders
from services.ibkr_market_data import get_account_info, get_positions
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ibkr", tags=["IBKR Trading"])


class IBKROrderRequest(BaseModel):
    account_id: int
    symbol: str
    name: str
    side: str  # "BUY" or "SELL"
    order_type: str = "LIMIT"
    price: Optional[float] = None
    quantity: int
    use_ibkr_platform: bool = True  # Whether to use IBKR platform


class IBKRConnectRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1


@router.post("/order")
def place_ibkr_order(req: IBKROrderRequest, db: Session = Depends(get_db)):
    """Place IBKR order"""
    try:
        account = db.query(Account).filter(Account.id == req.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        order = place_and_execute_ibkr_order(
            db=db,
            account=account,
            symbol=req.symbol,
            name=req.name,
            side=req.side,
            order_type=req.order_type,
            price=req.price,
            quantity=req.quantity,
            use_ibkr_platform=req.use_ibkr_platform
        )
        
        return {
            "success": True,
            "order_no": order.order_no,
            "status": order.status,
            "message": f"IBKR order placed: {req.side} {req.quantity} shares of {req.symbol}"
        }
    except Exception as e:
        logger.error(f"Failed to place IBKR order: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ibkr/connect")
def ibkr_connect(req: IBKRConnectRequest, db: Session = Depends(get_db)):
    """Connect to IBKR TWS/Gateway"""
    try:
        from services.ibkr_market_data import get_ib_connection
        ib = get_ib_connection()
        
        if ib.isConnected():
            # Save connection config
            from database.models import SystemConfig
            host_config = db.query(SystemConfig).filter(SystemConfig.key == "ibkr_host").first()
            if host_config:
                host_config.value = req.host
            else:
                host_config = SystemConfig(key="ibkr_host", value=req.host, description="IBKR host")
                db.add(host_config)
            
            port_config = db.query(SystemConfig).filter(SystemConfig.key == "ibkr_port").first()
            if port_config:
                port_config.value = str(req.port)
            else:
                port_config = SystemConfig(key="ibkr_port", value=str(req.port), description="IBKR port")
                db.add(port_config)
            
            db.commit()
            
            return {
                "success": True,
                "message": "IBKR连接成功！"
            }
        else:
            raise HTTPException(status_code=400, detail="IBKR连接失败")
    except Exception as e:
        logger.error(f"IBKR connect failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ibkr/account")
def get_ibkr_account():
    """Get IBKR account information"""
    try:
        account_info = get_account_info()
        return {
            "success": True,
            "data": account_info
        }
    except Exception as e:
        logger.error(f"Failed to get IBKR account info: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ibkr/positions")
def get_ibkr_positions():
    """Get IBKR position information"""
    try:
        positions = get_positions()
        return {
            "success": True,
            "data": positions
        }
    except Exception as e:
        logger.error(f"Failed to get IBKR positions: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ibkr/orders")
def get_ibkr_orders_list():
    """Get IBKR orders list"""
    try:
        orders = get_ibkr_orders()
        return {
            "success": True,
            "data": orders
        }
    except Exception as e:
        logger.error(f"Failed to get IBKR orders: {e}")
        raise HTTPException(status_code=400, detail=str(e))
