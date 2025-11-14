"""
Market data API routes
Provides RESTful API interfaces for crypto market data
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from services.ibkr_market_data import get_last_price, get_kline_data, get_stock_quote, search_stock as ibkr_search_stock, get_account_info, get_positions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market_data"])


class PriceResponse(BaseModel):
    """Price response model"""
    symbol: str
    market: str
    price: float
    timestamp: int


class KlineItem(BaseModel):
    """K-line data item model"""
    timestamp: int
    datetime: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[float]
    amount: Optional[float]
    chg: Optional[float]
    percent: Optional[float]


class KlineResponse(BaseModel):
    """K-line data response model"""
    symbol: str
    market: str
    period: str
    count: int
    data: List[KlineItem]


class MarketStatusResponse(BaseModel):
    """Market status response model"""
    symbol: str
    market: str = None
    market_status: str
    timestamp: int
    current_time: str


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_stock_price(symbol: str, market: str = "US"):
    """
    Get latest stock price via IBKR

    Args:
        symbol: Stock symbol, such as 'AAPL'
        market: Market symbol, default 'US'

    Returns:
        Response containing latest price
    """
    try:
        price = get_last_price(symbol)
        
        import time
        return PriceResponse(
            symbol=symbol,
            market=market,
            price=price,
            timestamp=int(time.time() * 1000)
        )
    except Exception as e:
        logger.error(f"Failed to get stock price: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stock price: {str(e)}")


@router.get("/prices", response_model=List[PriceResponse])
async def get_multiple_prices(symbols: str, market: str = "US"):
    """
    Get latest prices for multiple stocks in batch via IBKR

    Returns:
        Response list containing multiple stock prices
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="Stock symbol list cannot be empty")
        
        if len(symbol_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 stock symbols supported")
        
        quotes = get_stock_quote(symbol_list)
        results = []
        import time
        current_timestamp = int(time.time() * 1000)
        
        for symbol, quote in quotes.items():
            results.append(PriceResponse(
                symbol=symbol,
                market=market,
                price=quote['last_price'],
                timestamp=current_timestamp
            ))
                
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch get stock prices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch get stock prices: {str(e)}")


@router.get("/kline/{symbol}", response_model=KlineResponse)
async def get_stock_kline(
    symbol: str, 
    market: str = "US",
    period: str = "1 hour",
    count: int = 100
):
    """
    Get stock K-line data via IBKR

    Args:
        symbol: Stock symbol, such as 'AAPL'
        market: Market symbol, default 'US'
        period: Time period, supports '1 min', '5 mins', '15 mins', '30 mins', '1 hour', '1 day'
        count: Number of data points, default 100, max 500

    Returns:
        Response containing K-line data
    """
    try:
        # Parameter validation - IBKR supported time periods
        valid_periods = ['1 min', '5 mins', '15 mins', '30 mins', '1 hour', '1 day']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported time period, IBKR supported periods: {', '.join(valid_periods)}"
            )
            
        if count <= 0 or count > 500:
            raise HTTPException(status_code=400, detail="Data count must be between 1-500")
        
        # Get K-line data
        kline_data = get_kline_data(symbol, period=period, count=count)
        
        # Convert data format
        kline_items = []
        for item in kline_data:
            kline_items.append(KlineItem(
                timestamp=item.get('timestamp'),
                datetime=item.get('datetime'),
                open=item.get('open'),
                high=item.get('high'),
                low=item.get('low'),
                close=item.get('close'),
                volume=item.get('volume'),
                amount=None,
                chg=None,
                percent=None
            ))
        
        return KlineResponse(
            symbol=symbol,
            market=market,
            period=period,
            count=len(kline_items),
            data=kline_items
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get K-line data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get K-line data: {str(e)}")


@router.get("/account")
async def get_ibkr_account():
    """
    Get IBKR account information

    Returns:
        Response containing account info
    """
    try:
        account_info = get_account_info()
        return {
            "success": True,
            "data": account_info
        }
    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")

@router.get("/positions")
async def get_ibkr_positions():
    """
    Get IBKR positions

    Returns:
        Response containing positions
    """
    try:
        positions = get_positions()
        return {
            "success": True,
            "data": positions
        }
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@router.get("/search/{keyword}")
async def search_stocks(keyword: str):
    """
    Search stocks by keyword
    
    Args:
        keyword: Search keyword
        
    Returns:
        List of matching stocks
    """
    try:
        results = ibkr_search_stock(keyword)
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        logger.error(f"Failed to search stocks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search stocks: {str(e)}")

@router.get("/health")
async def market_data_health():
    """
    Market data service health check

    Returns:
        Service status information
    """
    try:
        # Test getting a price to check if service is running normally
        test_price = get_last_price("AAPL")
        
        import time
        return {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "test_price": {
                "symbol": "AAPL",
                "price": test_price
            },
            "message": "Market data service is running normally"
        }
    except Exception as e:
        logger.error(f"Market data service health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": int(time.time() * 1000),
            "error": str(e),
            "message": "Market data service abnormal"
        }