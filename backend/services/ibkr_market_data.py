"""
Interactive Brokers API市场数据服务
"""
import logging
from typing import Dict, List, Any, Optional
from ib_insync import *
import pandas as pd
import asyncio

logger = logging.getLogger(__name__)

# 全局IBKR连接实例
_ib = None

def get_ib_connection():
    """获取或创建IBKR连接"""
    global _ib
    if _ib is None or not _ib.isConnected():
        _ib = IB()
        try:
            # 连接到TWS Paper Trading (端口7497) 或 IB Gateway Paper (端口4002)
            _ib.connect('127.0.0.1', 7497, clientId=1)
            logger.info("IBKR连接已建立")
        except Exception as e:
            logger.error(f"IBKR连接失败: {e}")
            raise
    return _ib

def close_connection():
    """关闭IBKR连接"""
    global _ib
    if _ib and _ib.isConnected():
        _ib.disconnect()
        _ib = None
        logger.info("IBKR连接已关闭")

def get_account_info() -> Dict[str, Any]:
    """获取账户信息"""
    try:
        ib = get_ib_connection()
        account_values = ib.accountValues()
        
        account_data = {}
        for av in account_values:
            if av.tag in ['NetLiquidation', 'TotalCashValue', 'GrossPositionValue', 'BuyingPower']:
                account_data[av.tag] = float(av.value)
        
        return {
            'total_assets': account_data.get('NetLiquidation', 0),
            'cash': account_data.get('TotalCashValue', 0),
            'market_val': account_data.get('GrossPositionValue', 0),
            'power': account_data.get('BuyingPower', 0),
            'currency': 'USD'
        }
    except Exception as e:
        logger.error(f"获取账户信息异常: {e}")
        return {}

def get_positions() -> List[Dict[str, Any]]:
    """获取持仓信息"""
    try:
        ib = get_ib_connection()
        positions = ib.positions()
        
        position_list = []
        for pos in positions:
            if pos.position != 0:  # 只返回非零持仓
                position_list.append({
                    'symbol': pos.contract.symbol,
                    'exchange': pos.contract.exchange,
                    'position': float(pos.position),
                    'avg_cost': float(pos.avgCost),
                    'market_price': 0,  # 需要单独获取
                    'market_value': float(pos.position * pos.avgCost),
                    'unrealized_pnl': 0
                })
        
        return position_list
    except Exception as e:
        logger.error(f"获取持仓信息异常: {e}")
        return []

def get_stock_quote(symbols: List[str]) -> Dict[str, Any]:
    """获取股票报价"""
    try:
        ib = get_ib_connection()
        quotes = {}
        
        for symbol in symbols:
            # 创建合约
            contract = Stock(symbol, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # 获取市场数据
            ticker = ib.reqMktData(contract, '', False, False)
            ib.sleep(1)  # 等待数据
            
            if ticker.last and ticker.last > 0:
                quotes[symbol] = {
                    'symbol': symbol,
                    'last_price': float(ticker.last),
                    'bid': float(ticker.bid) if ticker.bid else 0,
                    'ask': float(ticker.ask) if ticker.ask else 0,
                    'volume': int(ticker.volume) if ticker.volume else 0,
                    'change': float(ticker.last - ticker.close) if ticker.close else 0
                }
            
            # 取消订阅
            ib.cancelMktData(contract)
        
        return quotes
    except Exception as e:
        logger.error(f"获取股票报价异常: {e}")
        return {}

def get_last_price(symbol: str) -> Optional[float]:
    """获取最新价格"""
    try:
        quotes = get_stock_quote([symbol])
        if symbol in quotes:
            return quotes[symbol]['last_price']
        return None
    except Exception as e:
        logger.error(f"获取{symbol}最新价格失败: {e}")
        return None

def get_kline_data(symbol: str, duration: str = "1 day", bar_size: str = "1 hour", count: int = 100) -> List[Dict[str, Any]]:
    """获取K线数据"""
    try:
        ib = get_ib_connection()
        
        # 创建合约
        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)
        
        # 获取历史数据
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f"{count} D",
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        klines = []
        for bar in bars:
            klines.append({
                'timestamp': int(bar.date.timestamp()),
                'datetime': str(bar.date),
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume)
            })
        
        logger.info(f"获取到{len(klines)}条K线数据: {symbol}")
        return klines
    except Exception as e:
        logger.error(f"获取K线数据异常: {e}")
        return []

def search_stock(keyword: str) -> List[Dict[str, Any]]:
    """搜索股票"""
    try:
        # IBKR没有直接的搜索API，返回一些常用股票
        common_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc'}
        ]
        
        # 简单的关键词匹配
        results = []
        for stock in common_stocks:
            if keyword.lower() in stock['name'].lower() or keyword.upper() in stock['symbol']:
                results.append(stock)
        
        return results[:10]
    except Exception as e:
        logger.error(f"搜索股票异常: {e}")
        return []

def get_contract_details(symbol: str, sec_type: str = 'STK') -> Optional[Contract]:
    """获取合约详情"""
    try:
        ib = get_ib_connection()
        
        if sec_type == 'STK':
            contract = Stock(symbol, 'SMART', 'USD')
        elif sec_type == 'OPT':
            # 期权合约需要更多参数
            contract = Option(symbol, '20241220', 150, 'C', 'SMART', '100', 'USD')
        elif sec_type == 'FUT':
            # 期货合约
            contract = Future(symbol, '202412', 'NYMEX')
        else:
            contract = Stock(symbol, 'SMART', 'USD')
        
        ib.qualifyContracts(contract)
        return contract
    except Exception as e:
        logger.error(f"获取合约详情失败: {e}")
        return None