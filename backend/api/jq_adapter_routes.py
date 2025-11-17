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
import akshare as ak

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
        
        result = {}
        count = req.count or 100
        
        for symbol in securities:
            try:
                if req.frequency == "daily":
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                else:
                    df = ak.stock_zh_a_hist_min_em(symbol=symbol, period="1", adjust="qfq")
                
                df = df.tail(count)
                klines = df.to_dict('records')
                if not df.empty:
                    result[symbol] = {
                        "open": df['开盘'].tolist(),
                        "high": df['最高'].tolist(),
                        "low": df['最低'].tolist(),
                        "close": df['收盘'].tolist(),
                        "volume": df['成交量'].tolist(),
                        "datetime": df['日期'].astype(str).tolist()
                    }
            except:
                pass
        
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
        period_map = {"1m": "1", "5m": "5", "1d": "daily"}
        period = period_map.get(unit, "daily")
        
        if period == "daily":
            df = ak.stock_zh_a_hist(symbol=security, period="daily", adjust="qfq")
        else:
            df = ak.stock_zh_a_hist_min_em(symbol=security, period=period, adjust="qfq")
        
        df = df.tail(count)
        
        field_list = fields.split(",")
        result = {}
        
        for field in field_list:
            if field == "close" and '收盘' in df.columns:
                result["close"] = df['收盘'].tolist()
            elif field == "open" and '开盘' in df.columns:
                result["open"] = df['开盘'].tolist()
            elif field == "high" and '最高' in df.columns:
                result["high"] = df['最高'].tolist()
            elif field == "low" and '最低' in df.columns:
                result["low"] = df['最低'].tolist()
            elif field == "volume" and '成交量' in df.columns:
                result["volume"] = df['成交量'].tolist()
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current_price/{security}")
async def get_current_price(security: str):
    """获取当前价格"""
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df['代码'] == security]
        if row.empty:
            raise HTTPException(status_code=404, detail=f"未找到{security}")
        price = float(row.iloc[0]['最新价'])
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
            try:
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == pos.symbol]
                current_price = float(row.iloc[0]['最新价']) if not row.empty else float(pos.avg_cost)
            except:
                current_price = float(pos.avg_cost)
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
            try:
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == pos.symbol]
                current_price = float(row.iloc[0]['最新价']) if not row.empty else float(pos.avg_cost)
            except:
                current_price = float(pos.avg_cost)
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
        if req.style == "LimitOrder":
            price = req.price
        else:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == req.security]
            price = float(row.iloc[0]['最新价']) if not row.empty else 0.0
        
        from services.order_executor_astock import place_and_execute_astock_order
        order = place_and_execute_astock_order(
            db=db,
            account=account,
            symbol=req.security,
            name=req.security,
            side=side,
            order_type="LIMIT" if req.style == "LimitOrder" else "MARKET",
            price=price or 0.0,
            quantity=quantity
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
        
        df = ak.stock_zh_a_spot_em()
        row = df[df['代码'] == security]
        price = float(row.iloc[0]['最新价']) if not row.empty else 0.0
        
        from services.order_executor_astock import place_and_execute_astock_order
        order = place_and_execute_astock_order(
            db=db,
            account=account,
            symbol=security,
            name=security,
            side=side,
            order_type="MARKET",
            price=price or 0.0,
            quantity=quantity
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
        
        df = ak.stock_zh_a_spot_em()
        row = df[df['代码'] == security]
        if row.empty:
            raise HTTPException(status_code=404, detail=f"无法获取{security}价格")
        
        price = float(row.iloc[0]['最新价'])
        
        # 计算数量
        quantity = int(value / price / 100) * 100
        
        if quantity == 0:
            raise HTTPException(status_code=400, detail="金额不足购买100股")
        
        from services.order_executor_astock import place_and_execute_astock_order
        order = place_and_execute_astock_order(
            db=db,
            account=account,
            symbol=security,
            name=security,
            side="BUY",
            order_type="MARKET",
            price=price,
            quantity=quantity
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
