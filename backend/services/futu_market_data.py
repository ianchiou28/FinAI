"""
富途OpenAPI市场数据服务
"""
import logging
from typing import Dict, List, Any, Optional
from futu import *
import pandas as pd

logger = logging.getLogger(__name__)

# 全局富途连接实例
_quote_ctx = None
_trd_ctx = None

def get_quote_context():
    """获取或创建行情连接"""
    global _quote_ctx
    if _quote_ctx is None:
        _quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        logger.info("富途行情连接已创建")
    return _quote_ctx

def get_trade_context():
    """获取或创建交易连接"""
    global _trd_ctx
    if _trd_ctx is None:
        _trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host='127.0.0.1', port=11111)
        logger.info("富途交易连接已创建")
    return _trd_ctx

def close_connections():
    """关闭所有连接"""
    global _quote_ctx, _trd_ctx
    if _quote_ctx:
        _quote_ctx.close()
        _quote_ctx = None
    if _trd_ctx:
        _trd_ctx.close()
        _trd_ctx = None
    logger.info("富途连接已关闭")

def unlock_trade(password: str) -> bool:
    """解锁交易"""
    try:
        trd_ctx = get_trade_context()
        ret, data = trd_ctx.unlock_trade(password=password)
        if ret == RET_OK:
            logger.info("富途交易解锁成功")
            return True
        else:
            logger.error(f"富途交易解锁失败: {data}")
            return False
    except Exception as e:
        logger.error(f"富途交易解锁异常: {e}")
        return False

def get_account_info() -> Dict[str, Any]:
    """获取账户信息"""
    try:
        trd_ctx = get_trade_context()
        ret, data = trd_ctx.accinfo_query(trd_env=TrdEnv.SIMULATE)
        if ret == RET_OK and not data.empty:
            account_data = data.iloc[0].to_dict()
            return {
                'total_assets': float(account_data.get('total_assets', 0)),
                'cash': float(account_data.get('cash', 0)),
                'market_val': float(account_data.get('market_val', 0)),
                'power': float(account_data.get('power', 0)),
                'currency': account_data.get('currency', 'HKD')
            }
        else:
            logger.error(f"获取账户信息失败: {data}")
            return {}
    except Exception as e:
        logger.error(f"获取账户信息异常: {e}")
        return {}

def get_positions() -> List[Dict[str, Any]]:
    """获取持仓信息"""
    try:
        trd_ctx = get_trade_context()
        ret, data = trd_ctx.position_list_query(trd_env=TrdEnv.SIMULATE)
        if ret == RET_OK and not data.empty:
            positions = []
            for _, row in data.iterrows():
                positions.append({
                    'code': row['code'],
                    'stock_name': row['stock_name'],
                    'qty': float(row['qty']),
                    'can_sell_qty': float(row['can_sell_qty']),
                    'cost_price': float(row['cost_price']),
                    'cur_price': float(row['cur_price']),
                    'market_val': float(row['market_val']),
                    'pl_ratio': float(row['pl_ratio']),
                    'pl_val': float(row['pl_val'])
                })
            return positions
        else:
            logger.info("当前无持仓")
            return []
    except Exception as e:
        logger.error(f"获取持仓信息异常: {e}")
        return []

def get_stock_quote(stock_codes: List[str]) -> Dict[str, Any]:
    """获取股票报价"""
    try:
        quote_ctx = get_quote_context()
        ret, data = quote_ctx.get_stock_quote(stock_codes)
        if ret == RET_OK and not data.empty:
            quotes = {}
            for _, row in data.iterrows():
                quotes[row['code']] = {
                    'code': row['code'],
                    'stock_name': row['stock_name'],
                    'cur_price': float(row['cur_price']),
                    'change_rate': float(row['change_rate']),
                    'change_val': float(row['change_val']),
                    'volume': float(row['volume']),
                    'turnover': float(row['turnover'])
                }
            return quotes
        else:
            logger.error(f"获取股票报价失败: {data}")
            return {}
    except Exception as e:
        logger.error(f"获取股票报价异常: {e}")
        return {}

def get_last_price(symbol: str) -> Optional[float]:
    """获取最新价格"""
    try:
        quotes = get_stock_quote([symbol])
        if symbol in quotes:
            return quotes[symbol]['cur_price']
        return None
    except Exception as e:
        logger.error(f"获取{symbol}最新价格失败: {e}")
        return None

def get_kline_data(symbol: str, ktype: str = "K_DAY", num: int = 100) -> List[Dict[str, Any]]:
    """获取K线数据"""
    try:
        quote_ctx = get_quote_context()
        
        # 映射K线类型
        ktype_map = {
            "1m": KLType.K_1M,
            "5m": KLType.K_5M,
            "15m": KLType.K_15M,
            "30m": KLType.K_30M,
            "1h": KLType.K_60M,
            "daily": KLType.K_DAY,
            "1d": KLType.K_DAY,
            "K_DAY": KLType.K_DAY
        }
        
        futu_ktype = ktype_map.get(ktype, KLType.K_DAY)
        ret, data = quote_ctx.get_cur_kline(symbol, num=num, ktype=futu_ktype)
        
        if ret == RET_OK and not data.empty:
            klines = []
            for _, row in data.iterrows():
                klines.append({
                    'timestamp': int(pd.Timestamp(row['time_key']).timestamp()),
                    'datetime': str(row['time_key']),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                })
            logger.info(f"获取到{len(klines)}条K线数据: {symbol}")
            return klines
        else:
            logger.error(f"获取K线数据失败: {data}")
            return []
    except Exception as e:
        logger.error(f"获取K线数据异常: {e}")
        return []

def search_stock(keyword: str) -> List[Dict[str, Any]]:
    """搜索股票"""
    try:
        quote_ctx = get_quote_context()
        # 富途API没有直接的搜索功能，这里返回一些常用股票作为示例
        common_stocks = [
            {'code': 'HK.00700', 'name': '腾讯控股'},
            {'code': 'HK.00941', 'name': '中国移动'},
            {'code': 'HK.00388', 'name': '香港交易所'},
            {'code': 'HK.01299', 'name': '友邦保险'},
            {'code': 'HK.02318', 'name': '中国平安'},
            {'code': 'US.AAPL', 'name': '苹果'},
            {'code': 'US.TSLA', 'name': '特斯拉'},
            {'code': 'US.MSFT', 'name': '微软'}
        ]
        
        # 简单的关键词匹配
        results = []
        for stock in common_stocks:
            if keyword.lower() in stock['name'].lower() or keyword.upper() in stock['code']:
                results.append(stock)
        
        return results[:10]  # 返回前10个结果
    except Exception as e:
        logger.error(f"搜索股票异常: {e}")
        return []