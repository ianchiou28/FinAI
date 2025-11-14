#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinAI - Interactive Brokers Trading Platform
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import logging

from database.connection import engine, Base, SessionLocal
from database.models import TradingConfig, User, Account, SystemConfig
from config.settings import DEFAULT_TRADING_CONFIGS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinAI - IBKR Trading Platform",
    description="AI-powered trading platform using Interactive Brokers API",
    version="1.0.0"
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "IBKR Trading API is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.on_event("startup")
def on_startup():
    """Initialize application on startup"""
    logger.info("Starting FinAI IBKR Trading Platform...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize database with default data
    db: Session = SessionLocal()
    try:
        # Seed trading configs if empty
        if db.query(TradingConfig).count() == 0:
            for cfg in DEFAULT_TRADING_CONFIGS.values():
                db.add(
                    TradingConfig(
                        version="v1",
                        market=cfg.market,
                        min_commission=cfg.min_commission,
                        commission_rate=cfg.commission_rate,
                        exchange_rate=cfg.exchange_rate,
                        min_order_quantity=cfg.min_order_quantity,
                        lot_size=cfg.lot_size,
                    )
                )
            db.commit()
        
        # Ensure default user exists
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
        
        # Ensure default user has IBKR account
        default_accounts = db.query(Account).filter(Account.user_id == default_user.id).all()
        if len(default_accounts) == 0:
            default_account = Account(
                user_id=default_user.id,
                version="v1",
                name="IBKR Paper Trading",
                account_type="IBKR",
                model="paper",
                base_url="127.0.0.1:7497",
                api_key="ibkr_paper",
                initial_capital=100000.0,
                current_cash=100000.0,
                frozen_cash=0.0,
                is_active="true"
            )
            db.add(default_account)
            db.commit()
            
        logger.info("Database initialization completed")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Initialize IBKR connection
    try:
        from services.ibkr_market_data import get_ib_connection
        ib = get_ib_connection()
        if ib.isConnected():
            logger.info("✓ IBKR connection established successfully")
        else:
            logger.warning("✗ IBKR connection failed - check TWS/Gateway")
    except Exception as e:
        logger.error(f"IBKR connection error: {e}")

@app.on_event("shutdown")
def on_shutdown():
    """Cleanup on application shutdown"""
    logger.info("Shutting down FinAI IBKR Trading Platform...")
    
    # Close IBKR connection
    try:
        from services.ibkr_market_data import close_connection
        close_connection()
        logger.info("IBKR connection closed")
    except Exception as e:
        logger.error(f"Error closing IBKR connection: {e}")

# API routes
from api.market_data_routes import router as market_data_router
from api.order_routes import router as order_router
from api.account_routes import router as account_router

app.include_router(market_data_router)
app.include_router(order_router)
app.include_router(account_router)

# WebSocket endpoint
from api.ws import websocket_endpoint
app.websocket("/ws")(websocket_endpoint)

# Serve frontend
@app.get("/")
async def serve_root():
    """Serve the frontend index.html for root route"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "FinAI IBKR Trading Platform - Frontend not built yet"}

# Catch-all route for SPA routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the frontend index.html for SPA routes"""
    # Skip API and static routes
    if full_path.startswith(("api", "static", "docs", "openapi.json")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "FinAI IBKR Trading Platform - Frontend not built yet"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)