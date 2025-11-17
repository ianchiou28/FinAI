"""
聚宽模拟交易API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database.connection import get_db
from database.models import Account
from services.jq_simulator import JQSimulator, set_current_simulator
import importlib.util
import sys

router = APIRouter(prefix="/api/jq/simulator", tags=["JQ Simulator"])

# 全局模拟器实例
_simulators = {}

class CreateSimulatorRequest(BaseModel):
    strategy_code: str
    account_name: str = "JQ模拟账户"

class RunSimulatorRequest(BaseModel):
    simulator_id: str

@router.post("/create")
async def create_simulator(req: CreateSimulatorRequest, db: Session = Depends(get_db)):
    """创建模拟交易"""
    try:
        # 获取或创建账户
        account = db.query(Account).filter(
            Account.name == req.account_name
        ).first()
        
        if not account:
            # 创建新账户
            from database.models import User
            user = db.query(User).filter(User.username == "default").first()
            if not user:
                raise HTTPException(status_code=404, detail="未找到默认用户")
            
            account = Account(
                user_id=user.id,
                version="v1",
                name=req.account_name,
                account_type="AI",
                model="jq_simulator",
                initial_capital=100000.0,
                current_cash=100000.0,
                frozen_cash=0.0,
                is_active="true"
            )
            db.add(account)
            db.commit()
            db.refresh(account)
        
        # 创建模拟器
        simulator = JQSimulator(db, account)
        
        # 执行策略代码
        exec_globals = {
            'g': simulator.g,
            'log': None,
            'attribute_history': None,
            'order': None,
            'order_target': None,
            'order_value': None,
            'order_target_value': None
        }
        
        exec(req.strategy_code, exec_globals)
        
        # 设置策略函数
        if 'initialize' in exec_globals:
            simulator.set_initialize(exec_globals['initialize'])
        if 'handle_data' in exec_globals:
            simulator.set_handle_data(exec_globals['handle_data'])
        if 'before_trading_start' in exec_globals:
            simulator.set_before_trading_start(exec_globals['before_trading_start'])
        if 'after_trading_end' in exec_globals:
            simulator.set_after_trading_end(exec_globals['after_trading_end'])
        
        # 保存模拟器
        simulator_id = f"sim_{account.id}"
        _simulators[simulator_id] = simulator
        
        return {
            "success": True,
            "data": {
                "simulator_id": simulator_id,
                "account_id": account.id,
                "account_name": account.name
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def run_simulator(req: RunSimulatorRequest):
    """运行模拟交易"""
    try:
        simulator = _simulators.get(req.simulator_id)
        if not simulator:
            raise HTTPException(status_code=404, detail="模拟器不存在")
        
        # 设置当前模拟器
        set_current_simulator(simulator)
        
        # 运行策略
        simulator.run_strategy()
        
        return {
            "success": True,
            "message": "策略运行完成",
            "data": {
                "total_value": simulator.context.portfolio.total_value,
                "cash": simulator.context.portfolio.available_cash,
                "positions": len(simulator.context.portfolio.positions)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{simulator_id}")
async def get_simulator_status(simulator_id: str):
    """获取模拟器状态"""
    try:
        simulator = _simulators.get(simulator_id)
        if not simulator:
            raise HTTPException(status_code=404, detail="模拟器不存在")
        
        simulator.context.portfolio._update()
        
        positions = []
        for symbol, pos in simulator.context.portfolio.positions.items():
            positions.append({
                "security": symbol,
                "amount": pos.total_amount,
                "avg_cost": pos.avg_cost,
                "price": pos.price,
                "value": pos.value
            })
        
        return {
            "success": True,
            "data": {
                "simulator_id": simulator_id,
                "account_name": simulator.account.name,
                "total_value": simulator.context.portfolio.total_value,
                "cash": simulator.context.portfolio.available_cash,
                "positions": positions,
                "is_initialized": simulator.is_initialized
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_simulators():
    """列出所有模拟器"""
    try:
        result = []
        for sim_id, simulator in _simulators.items():
            simulator.context.portfolio._update()
            result.append({
                "simulator_id": sim_id,
                "account_name": simulator.account.name,
                "total_value": simulator.context.portfolio.total_value,
                "is_initialized": simulator.is_initialized
            })
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{simulator_id}")
async def delete_simulator(simulator_id: str):
    """删除模拟器"""
    try:
        if simulator_id in _simulators:
            del _simulators[simulator_id]
            return {"success": True, "message": "模拟器已删除"}
        else:
            raise HTTPException(status_code=404, detail="模拟器不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
