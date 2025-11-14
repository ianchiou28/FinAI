"""
MT5 API市场数据服务 - A股模拟交易
"""
import logging
from typing import Dict, List, Any, Optional
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_mt5_initialized = False

def init_mt5() -> bool:
    """初始化MT5连接"""
    global _mt5_initialized
    if not _mt5_initialized:
        if not mt5.initialize():
            logger.error(f"MT5初始化失败: {mt5.last_error()}")
            return False
        _mt5_initialized = True
        logger.info("MT5连接已建立")
    return True

def shutdown_mt5():
    """关闭MT5连接"""
    global _mt5_initialized
    if _mt5_initialized:
        mt5.shutdown()
        _mt5_initialized = False
        logger.info("MT5连接已关闭")

def get_account_info() -> Dict[str, Any]:
    """获取账户信息"""
    try:
        if not init_mt5():
            return {}
        
        account_info = mt5.account_info()
        if account_info is None:
            return {}
        
        return {
            'total_assets': account_info.balance + account_info.profit,
            'cash': account_info.balance,
            'market_val': account_info.equity - account_info.balance,
            'profit': account_info.profit,
            'margin': account_info.margin,
            'margin_free': account_info.margin_free,
            'currency': account_info.currency
        }
    except Exception as e:
        logger.error(f"获取账户信息异常: {e}")
        return {}

def get_positions() -> List[Dict[str, Any]]:
    """获取持仓信息"""
    try:
        if not init_mt5():
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        position_list = []
        for pos in positions:
            position_list.append({
                'symbol': pos.symbol,
                'ticket': pos.ticket,
                'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'swap': pos.swap,
                'commission': pos.commission
            })
        
        return position_list
    except Exception as e:
        logger.error(f"获取持仓信息异常: {e}")
        return []

def get_stock_quote(symbols: List[str]) -> Dict[str, Any]:
    """获取股票报价"""
    try:
        if not init_mt5():
            return {}
        
        quotes = {}
        for symbol in symbols:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            
            quotes[symbol] = {
                'symbol': symbol,
                'last_price': tick.last,
                'bid': tick.bid,
                'ask': tick.ask,
                'volume': tick.volume,
                'time': datetime.fromtimestamp(tick.time)
            }
        
        return quotes
    except Exception as e:
        logger.error(f"获取股票报价异常: {e}")
        return {}

_price_cache = {}
_cache_time = None

def get_last_price(symbol: str) -> Optional[float]:
    """获取最新价格 - 使用akshare获取A股实时数据"""
    global _price_cache, _cache_time
    
    try:
        import akshare as ak
        from datetime import datetime, timedelta
        
        # 缓存机制：5秒内使用缓存
        now = datetime.now()
        if _cache_time and (now - _cache_time).total_seconds() < 5:
            if symbol in _price_cache:
                return _price_cache[symbol]
        
        # 重新获取数据
        df = ak.stock_zh_a_spot_em()
        _cache_time = now
        _price_cache.clear()
        
        # 缓存所有股票价格
        for _, row in df.iterrows():
            code = row['代码']
            price = float(row['最新价'])
            _price_cache[code] = price
        
        return _price_cache.get(symbol)
        
    except Exception as e:
        logger.error(f"获取{symbol}最新价格失败: {e}")
        return _price_cache.get(symbol)

def get_kline_data(
    symbol: str, 
    timeframe: int = mt5.TIMEFRAME_H1, 
    count: int = 100
) -> List[Dict[str, Any]]:
    """
    获取K线数据
    timeframe: mt5.TIMEFRAME_M1, M5, M15, M30, H1, H4, D1, W1, MN1
    """
    try:
        if not init_mt5():
            return []
        
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            return []
        
        df = pd.DataFrame(rates)
        klines = []
        
        for _, row in df.iterrows():
            klines.append({
                'timestamp': int(row['time']),
                'datetime': datetime.fromtimestamp(row['time']).strftime('%Y-%m-%d %H:%M:%S'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['tick_volume'])
            })
        
        logger.info(f"获取到{len(klines)}条K线数据: {symbol}")
        return klines
    except Exception as e:
        logger.error(f"获取K线数据异常: {e}")
        return []

def search_stock(keyword: str) -> List[Dict[str, Any]]:
    """搜索股票"""
    try:
        if not init_mt5():
            return []
        
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
        
        results = []
        for s in symbols:
            if keyword.upper() in s.name.upper():
                results.append({
                    'symbol': s.name,
                    'description': s.description,
                    'path': s.path
                })
                if len(results) >= 20:
                    break
        
        return results
    except Exception as e:
        logger.error(f"搜索股票异常: {e}")
        return []

def get_symbol_info(symbol: str) -> Optional[Dict[str, Any]]:
    """获取股票详细信息"""
    try:
        if not init_mt5():
            return None
        
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        
        return {
            'symbol': info.name,
            'description': info.description,
            'point': info.point,
            'digits': info.digits,
            'trade_contract_size': info.trade_contract_size,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'currency_base': info.currency_base,
            'currency_profit': info.currency_profit
        }
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        return None
