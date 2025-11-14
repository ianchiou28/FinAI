"""
Tonghuashun (同花顺) A-share market data service using easytrader
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Global THS trade instance
_ths_trade_instance = None


def get_ths_instance():
    """Get or create THS trade instance using easytrader"""
    global _ths_trade_instance
    if _ths_trade_instance is None:
        try:
            import easytrader
            _ths_trade_instance = easytrader.use('ths')
            logger.info("THS trade instance created with easytrader")
            
            # Auto-login if credentials exist
            try:
                from database.connection import SessionLocal
                from database.models import SystemConfig
                db = SessionLocal()
                try:
                    account = db.query(SystemConfig).filter(SystemConfig.key == "ths_account").first()
                    password = db.query(SystemConfig).filter(SystemConfig.key == "ths_password").first()
                    if account and password and account.value and password.value:
                        _ths_trade_instance.prepare(account.value, password.value)
                        logger.info("Auto-logged in to THS")
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Auto-login to THS failed: {e}")
        except ImportError:
            logger.error("easytrader library not installed. Run: pip install easytrader")
            raise
    return _ths_trade_instance


def login_ths(account: str, password: str) -> bool:
    """Login to Tonghuashun simulation trading system"""
    try:
        trade = get_ths_instance()
        trade.prepare(account, password)
        logger.info(f"Successfully logged in to THS with account: {account}")
        return True
    except Exception as e:
        logger.error(f"Failed to login to THS: {e}")
        raise


def get_ths_account_info() -> Dict[str, Any]:
    """Get THS account information"""
    try:
        trade = get_ths_instance()
        balance = trade.balance
        return balance if isinstance(balance, dict) else {}
    except Exception as e:
        logger.error(f"Failed to get THS account info: {e}")
        return {}


def get_ths_position_info() -> List[Dict[str, Any]]:
    """Get THS position information"""
    try:
        trade = get_ths_instance()
        position = trade.position
        return position if isinstance(position, list) else []
    except Exception as e:
        logger.error(f"Failed to get THS position info: {e}")
        return []


def place_ths_order(symbol: str, direction: str, quantity: int, price: float) -> bool:
    """
    Place order on THS simulation platform
    
    Args:
        symbol: Stock code (e.g., "600000")
        direction: "buy" or "sell"
        quantity: Number of shares (must be multiple of 100)
        price: Order price
    """
    try:
        trade = get_ths_instance()
        if direction.lower() == "buy":
            result = trade.buy(symbol, price=price, amount=quantity)
        else:
            result = trade.sell(symbol, price=price, amount=quantity)
        logger.info(f"THS order placed: {direction} {quantity} shares of {symbol} at {price}, result: {result}")
        return True
    except Exception as e:
        logger.error(f"Failed to place THS order: {e}")
        raise


def cancel_ths_order(order_no: str) -> bool:
    """Cancel THS order"""
    try:
        trade = get_ths_instance()
        result = trade.cancel_entrust(order_no)
        logger.info(f"THS order cancelled: {order_no}, result: {result}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel THS order: {e}")
        raise


def get_last_price_from_ths(symbol: str) -> Optional[float]:
    """
    Get last price for A-share stock
    Note: THS API may not provide real-time quotes directly
    This is a placeholder - implement with actual THS API or use alternative data source
    """
    try:
        # THS API doesn't provide direct quote API in basic version
        # You may need to use tushare, akshare, or other data sources
        import akshare as ak
        stock_df = ak.stock_zh_a_spot_em()
        stock_info = stock_df[stock_df['代码'] == symbol]
        if not stock_info.empty:
            price = float(stock_info.iloc[0]['最新价'])
            logger.info(f"Got price for {symbol}: {price}")
            return price
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
    return None


def get_kline_data_from_ths(symbol: str, period: str = "daily", count: int = 100) -> List[Dict[str, Any]]:
    """
    Get K-line data for A-share stock
    Uses akshare as data source
    """
    try:
        import akshare as ak
        import pandas as pd
        
        # Map period to akshare format
        period_map = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "daily": "daily",
            "1d": "daily",
        }
        ak_period = period_map.get(period, "daily")
        
        if ak_period == "daily":
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        else:
            df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=ak_period, adjust="qfq")
        
        if df is not None and not df.empty:
            df = df.tail(count)
            klines = []
            for _, row in df.iterrows():
                klines.append({
                    "timestamp": int(pd.Timestamp(row['日期']).timestamp()),
                    "datetime": str(row['日期']),
                    "open": float(row['开盘']),
                    "high": float(row['最高']),
                    "low": float(row['最低']),
                    "close": float(row['收盘']),
                    "volume": float(row['成交量']),
                })
            logger.info(f"Got {len(klines)} K-line records for {symbol}")
            return klines
    except Exception as e:
        logger.error(f"Failed to get K-line data for {symbol}: {e}")
    return []
