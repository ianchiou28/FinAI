"""
MT5 A股模拟交易平台启动脚本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入路由
from api.mt5_routes import router as mt5_router
from api.mt5_ai_routes import router as mt5_ai_router

# 创建FastAPI应用
app = FastAPI(
    title="FinAI MT5 A股模拟交易平台",
    description="基于MT5 API的A股模拟交易系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(mt5_router)
app.include_router(mt5_ai_router)

@app.get("/")
async def root():
    return {
        "message": "FinAI MT5 A股模拟交易平台",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health():
    """健康检查"""
    import MetaTrader5 as mt5
    
    mt5_status = "connected" if mt5.initialize() else "disconnected"
    if mt5_status == "connected":
        mt5.shutdown()
    
    return {
        "status": "healthy",
        "mt5": mt5_status
    }

if __name__ == "__main__":
    print("=" * 60)
    print("启动 FinAI MT5 A股模拟交易平台")
    print("=" * 60)
    print("\n后端服务: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("前端界面: http://localhost:5173")
    print("\n按 Ctrl+C 停止服务\n")
    
    uvicorn.run(
        "start_mt5:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
