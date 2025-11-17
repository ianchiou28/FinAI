"""
聚宽API适配器 - 提供兼容聚宽风格的API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
from database.connection import get_db
from database.models import Account, Position, Order, Trade
from services.mt5_market_data import get_last_price, get_kline_data
from services.mt5_order_executor import place_and_execute_mt5_order
import MetaTrader5 as mt5

router = APIRouter(prefix="/api/jq", tags=["JoinQuant Adapter"])

# ==================== 请求模型 ====================
class OrderRequest(BaseModel):
    security: str
    amount: int
    style: str = "MarketOrder"  # MarketOrder or LimitOrder
    price: Optional[float] = None
    pindex: int = 0

class GetPriceRequest(BaseModel):
    security: str | List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    frequency: str = "daily"  # daily, minute
    fields: Optional[List[str]] = None
    count: Optional[int] = None

# ==================== 行情数据API ====================
@router.post("/get_price")
async def get_price(req: GetPriceRequest):
    """获取历史数据 - 兼容聚宽get_price"""
    try:
        securities = [req.security] if isinstance(req.security, str) else req.security
        
        # 转换时间周期
        timeframe = mt5.TIMEFRAME_D1 if req.frequency == "daily" else mt5.TIMEFRAME_M1
        count = req.count or 100
        
        result = {}
        for symbol in securities:
            klines = get_kline_data(symbol, timeframe, count)
            if klines:
                result[symbol] = {
                    "open": [k["open"] for k in klines],
                    "high": [k["high"] for k in klines],
                    "low": [k["low"] for k in klines],
                    "close": [k["close"] for k in klines],
                    "volume": [k["volume"] for k in klines],
                    "datetime": [k["datetime"] for k in klines]
                }
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attribute_history/{security}")
async def attribute_history(
    security: str,
    count: int = Query(5, description="获取数据条数"),
    unit: str = Query("1d", description="时间单位"),
    fields: str = Query("close", description="字段，逗号分隔")
):
    """获取单个标的历史数据 - 兼容聚宽attribute_history"""
    try:
        # 转换时间单位
        timeframe_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "1d": mt5.TIMEFRAME_D1
        }
        timeframe = timeframe_map.get(unit, mt5.TIMEFRAME_D1)
        
        klines = get_kline_data(security, timeframe, count)
        
        field_list = fields.split(",")
        result = {}
        
        for field in field_list:
            if field == "close":
                result["close"] = [k["close"] for k in klines]
            elif field == "open":
                result["open"] = [k["open"] for k in klines]
            elif field == "high":
                result["high"] = [k["high"] for k in klines]
            elif field == "low":
                result["low"] = [k["low"] for k in klines]
            elif field == "volume":
                result["volume"] = [k["volume"] for k in klines]
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current_price/{security}")
async def get_current_price(security: str):
    """获取当前价格"""
    try:
        price = get_last_price(security)
        if price is None:
            raise HTTPException(status_code=404, detail=f"未找到{security}")
        return {"success": True, "data": {"price": price}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 账户与持仓API ====================
@router.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    """获取账户信息 - 兼容聚宽context.portfolio"""
    try:
        account = db.query(Account).filter(Account.is_active == "true").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        positions = db.query(Position).filter(
            Position.account_id == account.id,
            Position.quantity > 0
        ).all()
        
        total_value = float(account.current_cash)
        positions_value = 0
        
        positions_data = {}
        for pos in positions:
            current_price = get_last_price(pos.symbol) or float(pos.avg_cost)
            market_value = float(pos.quantity) * current_price
            positions_value += market_value
            
            positions_data[pos.symbol] = {
                "total_amount": float(pos.quantity),
                "closeable_amount": float(pos.available_quantity),
                "avg_cost": float(pos.avg_cost),
                "price": current_price,
                "value": market_value
            }
        
        total_value += positions_value
        
        return {
            "success": True,
            "data": {
                "total_value": total_value,
                "available_cash": float(account.current_cash),
                "positions_value": positions_value,
                "positions": positions_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    """获取持仓列表"""
    try:
        account = db.query(Account).filter(Account.is_active == "true").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        positions = db.query(Position).filter(
            Position.account_id == account.id,
            Position.quantity > 0
        ).all()
        
        result = []
        for pos in positions:
            current_price = get_last_price(pos.symbol) or float(pos.avg_cost)
            result.append({
                "security": pos.symbol,
                "total_amount": float(pos.quantity),
                "closeable_amount": float(pos.available_quantity),
                "avg_cost": float(pos.avg_cost),
                "price": current_price,
                "value": float(pos.quantity) * current_price
            })
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 交易API ====================
@router.post("/order")
async def order(req: OrderRequest, db: Session = Depends(get_db)):
    """下单 - 兼容聚宽order函数"""
    try:
        account = db.query(Account).filter(Account.is_active == "true").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        # 判断买卖方向
        side = "BUY" if req.amount > 0 else "SELL"
        quantity = abs(req.amount)
        
        # 确保是100的倍数
        if quantity % 100 != 0:
            quantity = (quantity // 100) * 100
        
        if quantity == 0:
            raise HTTPException(status_code=400, detail="数量必须是100的倍数")
        
        # 获取价格
        price = req.price if req.style == "LimitOrder" else get_last_price(req.security)
        
        order = place_and_execute_mt5_order(
            db=db,
            account=account,
            symbol=req.security,
            name=req.security,
            side=side,
            order_type="LIMIT" if req.style == "LimitOrder" else "MARKET",
            price=price or 0.0,
            quantity=quantity,
            use_mt5_platform=False
        )
        
        return {
            "success": True,
            "data": {
                "order_id": order.id,
                "order_no": order.order_no,
                "security": order.symbol,
                "amount": order.quantity if side == "BUY" else -order.quantity,
                "price": order.price,
                "status": order.status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/order_target")
async def order_target(
    security: str,
    amount: int,
    db: Session = Depends(get_db)
):
    """目标数量下单 - 兼容聚宽order_target"""
    try:
        account = db.query(Account).filter(Account.is_active == "true").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        # 获取当前持仓
        pos = db.query(Position).filter(
            Position.account_id == account.id,
            Position.symbol == security
        ).first()
        
        current_amount = int(pos.quantity) if pos else 0
        delta = amount - current_amount
        
        if delta == 0:
            return {"success": True, "message": "无需调整"}
        
        side = "BUY" if delta > 0 else "SELL"
        quantity = abs(delta)
        
        # 确保是100的倍数
        quantity = (quantity // 100) * 100
        
        if quantity == 0:
            return {"success": True, "message": "调整量不足100股"}
        
        price = get_last_price(security)
        
        order = place_and_execute_mt5_order(
            db=db,
            account=account,
            symbol=security,
            name=security,
            side=side,
            order_type="MARKET",
            price=price or 0.0,
            quantity=quantity,
            use_mt5_platform=False
        )
        
        return {
            "success": True,
            "data": {
                "order_id": order.id,
                "order_no": order.order_no
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/order_value")
async def order_value(
    security: str,
    value: float,
    db: Session = Depends(get_db)
):
    """按金额下单 - 兼容聚宽order_value"""
    try:
        account = db.query(Account).filter(Account.is_active == "true").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        price = get_last_price(security)
        if not price:
            raise HTTPException(status_code=404, detail=f"无法获取{security}价格")
        
        # 计算数量
        quantity = int(value / price / 100) * 100
        
        if quantity == 0:
            raise HTTPException(status_code=400, detail="金额不足购买100股")
        
        order = place_and_execute_mt5_order(
            db=db,
            account=account,
            symbol=security,
            name=security,
            side="BUY",
            order_type="MARKET",
            price=price,
            quantity=quantity,
            use_mt5_platform=False
        )
        
        return {
            "success": True,
            "data": {
                "order_id": order.id,
                "order_no": order.order_no
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 订单查询API ====================
@router.get("/orders")
async def get_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取订单列表"""
    try:
        account = db.query(Account).filter(Account.is_active == "true").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        query = db.query(Order).filter(Order.account_id == account.id)
        
        if status:
            query = query.filter(Order.status == status.upper())
        
        orders = query.order_by(Order.order_time.desc()).limit(100).all()
        
        result = []
        for order in orders:
            result.append({
                "order_id": order.id,
                "order_no": order.order_no,
                "security": order.symbol,
                "amount": order.quantity if order.side == "BUY" else -order.quantity,
                "price": order.price,
                "filled": order.filled_quantity,
                "status": order.status,
                "time": order.order_time.isoformat()
            })
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 工具函数API ====================
@router.get("/normalize_code/{code}")
async def normalize_code(code: str):
    """股票代码格式转换"""
    try:
        # 简单的代码转换逻辑
        if len(code) == 6:
            if code.startswith("6"):
                return {"success": True, "data": f"{code}.XSHG"}
            else:
                return {"success": True, "data": f"{code}.XSHE"}
        return {"success": True, "data": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
