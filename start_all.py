"""
一键启动FinAI MT5 A股交易平台
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def main():
    print("=" * 60)
    print("FinAI MT5 A股交易平台 - 一键启动")
    print("=" * 60)
    
    # 检查依赖
    print("\n[1/3] 检查依赖...")
    try:
        import akshare
        import fastapi
        import uvicorn
        import sqlalchemy
        print("✓ 依赖已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("\n请运行: pip install -r requirements_mt5.txt")
        return
    
    # 启动后端
    print("\n[2/3] 启动后端服务...")
    backend_dir = Path(__file__).parent / "backend"
    sys.path.insert(0, str(backend_dir))
    
    try:
        from api.mt5_routes import router as mt5_router
        from api.mt5_ai_routes import router as mt5_ai_router
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        
        app = FastAPI(
            title="FinAI MT5 A股模拟交易平台",
            description="基于akshare的A股实时数据模拟交易系统",
            version="1.0.0"
        )
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        app.include_router(mt5_router)
        app.include_router(mt5_ai_router)
        
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        
        frontend_path = Path(__file__).parent / "frontend"
        
        @app.get("/")
        async def root():
            html_file = frontend_path / "mt5-vue.html"
            if html_file.exists():
                return FileResponse(html_file)
            return {
                "message": "FinAI MT5 A股模拟交易平台",
                "version": "1.0.0",
                "docs": "/docs"
            }
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        print("✓ 后端服务已启动")
        print("\n" + "=" * 60)
        print("🚀 服务已启动")
        print("=" * 60)
        print("\n交易平台: http://localhost:8000")
        print("API文档: http://localhost:8000/docs")
        print("\n按 Ctrl+C 停止服务\n")
        
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n服务已停止")
