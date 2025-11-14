"""
MT5 AI交易API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from services.mt5_ai_trader import run_mt5_ai_trading, get_astock_portfolio
from database.models import Account

router = APIRouter(prefix="/api/mt5/ai", tags=["MT5 AI"])

@router.post("/trade")
async def trigger_ai_trade(db: Session = Depends(get_db)):
    """手动触发AI交易"""
    try:
        run_mt5_ai_trading(db)
        return {"success": True, "message": "AI交易已执行"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    """获取AI账户投资组合"""
    try:
        account = db.query(Account).filter(
            Account.name == "MT5 A股账户"
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="未找到账户")
        
        from services.mt5_ai_trader import get_astock_portfolio
        portfolio = get_astock_portfolio(db, account)
        
        return {"success": True, "data": portfolio}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
