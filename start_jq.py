"""
聚宽风格模拟交易平台启动脚本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import sys
from pathlib import Path

# 添加backend到路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# 导入路由
from api.jq_adapter_routes import router as jq_adapter_router
from api.jq_simulator_routes import router as jq_simulator_router
from database.connection import engine, Base, SessionLocal
from database.models import User, Account

# 创建FastAPI应用
app = FastAPI(
    title="FinAI 聚宽模拟交易平台",
    description="兼容聚宽API的A股模拟交易系统",
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
app.include_router(jq_adapter_router)
app.include_router(jq_simulator_router)

@app.on_event("startup")
def on_startup():
    """启动时初始化"""
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 初始化默认用户
    db: Session = SessionLocal()
    try:
        default_user = db.query(User).filter(User.username == "default").first()
        if not default_user:
            default_user = User(
                username="default",
                email=None,
                password_hash=None,
                is_active="true"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
        
        print("✓ 数据库初始化完成")
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "message": "FinAI 聚宽模拟交易平台",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    print("=" * 60)
    print("启动 FinAI 聚宽模拟交易平台")
    print("=" * 60)
    print("\n后端服务: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("\n按 Ctrl+C 停止服务\n")
    
    uvicorn.run(
        "start_jq:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
