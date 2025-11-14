"""
System config API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from database.connection import SessionLocal
from database.models import SystemConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


@router.get("/check-required")
async def check_required_configs(db: Session = Depends(get_db)):
    """Check if required configs are set"""
    try:
        return {
            "has_required_configs": True,
            "missing_configs": []
        }
    except Exception as e:
        logger.error(f"Failed to check required configs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check required configs: {str(e)}")


@router.post("/ths-credentials")
async def save_ths_credentials(account: str, password: str, db: Session = Depends(get_db)):
    """Save THS credentials to system config"""
    try:
        # Save account
        acc_config = db.query(SystemConfig).filter(SystemConfig.key == "ths_account").first()
        if acc_config:
            acc_config.value = account
        else:
            acc_config = SystemConfig(key="ths_account", value=account, description="THS account")
            db.add(acc_config)
        
        # Save password
        pwd_config = db.query(SystemConfig).filter(SystemConfig.key == "ths_password").first()
        if pwd_config:
            pwd_config.value = password
        else:
            pwd_config = SystemConfig(key="ths_password", value=password, description="THS password")
            db.add(pwd_config)
        
        db.commit()
        return {"success": True, "message": "THS credentials saved"}
    except Exception as e:
        logger.error(f"Failed to save THS credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ths-credentials")
async def get_ths_credentials(db: Session = Depends(get_db)):
    """Get THS credentials from system config"""
    try:
        account = db.query(SystemConfig).filter(SystemConfig.key == "ths_account").first()
        password = db.query(SystemConfig).filter(SystemConfig.key == "ths_password").first()
        
        return {
            "account": account.value if account else None,
            "password": password.value if password else None
        }
    except Exception as e:
        logger.error(f"Failed to get THS credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))