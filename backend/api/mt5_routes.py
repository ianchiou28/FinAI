"""
MT5 API路由 - A股模拟交易
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database.connection import get_db
from database.models import Account
from services.mt5_market_data import (
    get_account_info,
    get_positions,
    get_stock_quote,
    get_last_price,
    get_kline_data,
    search_stock,
    get_symbol_info
)
from services.mt5_order_executor import place_and_execute_mt5_order
import MetaTrader5 as mt5

router = APIRouter(prefix="/api/mt5", tags=["MT5"])

# 请求模型
class OrderRequest(BaseModel):
    symbol: str
    name: str
    side: str  # BUY or SELL
    order_type: str = "MARKET"  # MARKET or LIMIT
    price: Optional[float] = None
    quantity: int
    use_mt5_platform: bool = False

class QuoteRequest(BaseModel):
    symbols: List[str]

# 账户相关
@router.get("/account")
async def get_account():
    """获取MT5账户信息"""
    try:
        account_data = get_account_info()
        if not account_data:
            raise HTTPException(status_code=500, detail="无法获取账户信息")
        return {"success": True, "data": account_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_position_list():
    """获取持仓列表"""
    try:
        positions = get_positions()
        return {"success": True, "data": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 行情相关
@router.post("/quote")
async def get_quotes(request: QuoteRequest):
    """获取股票报价"""
    try:
        quotes = get_stock_quote(request.symbols)
        return {"success": True, "data": quotes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price/{symbol}")
async def get_price(symbol: str):
    """获取股票最新价格"""
    try:
        price = get_last_price(symbol)
        if price is None:
            raise HTTPException(status_code=404, detail=f"未找到股票{symbol}")
        return {"success": True, "data": {"symbol": symbol, "price": price}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str, 
    timeframe: str = "H1", 
    count: int = 100
):
    """
    获取K线数据
    timeframe: M1, M5, M15, M30, H1, H4, D1, W1, MN1
    """
    try:
        # 转换时间周期
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1
        }
        
        tf = timeframe_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
        klines = get_kline_data(symbol, tf, count)
        
        return {"success": True, "data": klines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/{keyword}")
async def search_stocks(keyword: str):
    """搜索股票"""
    try:
        results = search_stock(keyword)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbol/{symbol}")
async def get_symbol(symbol: str):
    """获取股票详细信息"""
    try:
        info = get_symbol_info(symbol)
        if info is None:
            raise HTTPException(status_code=404, detail=f"未找到股票{symbol}")
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 交易相关
@router.post("/order")
async def create_order(
    request: OrderRequest,
    db: Session = Depends(get_db)
):
    """创建订单"""
    try:
        # 获取默认账户
        account = db.query(Account).filter(Account.name == "MT5 A股账户").first()
        if not account:
            raise HTTPException(status_code=404, detail="未找到A股账户")
        
        # 执行订单
        order = place_and_execute_mt5_order(
            db=db,
            account=account,
            symbol=request.symbol,
            name=request.name,
            side=request.side,
            order_type=request.order_type,
            price=request.price or 0.0,
            quantity=request.quantity,
            use_mt5_platform=request.use_mt5_platform
        )
        
        return {
            "success": True,
            "data": {
                "order_no": order.order_no,
                "symbol": order.symbol,
                "side": order.side,
                "price": order.price,
                "quantity": order.quantity,
                "status": order.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
