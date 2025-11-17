"""
聚宽风格模拟交易引擎
"""
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, time
from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import Account, Position, Order, Trade
from services.mt5_market_data import get_last_price, get_kline_data
from services.mt5_order_executor import place_and_execute_mt5_order
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class G:
    """全局变量对象"""
    pass

class Portfolio:
    """投资组合对象"""
    def __init__(self, db: Session, account: Account):
        self.db = db
        self.account = account
        self._update()
    
    def _update(self):
        """更新投资组合数据"""
        self.db.refresh(self.account)
        self.available_cash = float(self.account.current_cash)
        self.total_value = self.available_cash
        self.positions = {}
        
        positions = self.db.query(Position).filter(
            Position.account_id == self.account.id,
            Position.quantity > 0
        ).all()
        
        for pos in positions:
            current_price = get_last_price(pos.symbol) or float(pos.avg_cost)
            market_value = float(pos.quantity) * current_price
            self.total_value += market_value
            
            self.positions[pos.symbol] = PositionData(
                security=pos.symbol,
                total_amount=float(pos.quantity),
                closeable_amount=float(pos.available_quantity),
                avg_cost=float(pos.avg_cost),
                price=current_price,
                value=market_value
            )

class PositionData:
    """持仓数据"""
    def __init__(self, security, total_amount, closeable_amount, avg_cost, price, value):
        self.security = security
        self.total_amount = total_amount
        self.closeable_amount = closeable_amount
        self.avg_cost = avg_cost
        self.price = price
        self.value = value

class Context:
    """策略上下文"""
    def __init__(self, db: Session, account: Account):
        self.db = db
        self.account = account
        self.portfolio = Portfolio(db, account)
        self.current_dt = datetime.now()
        self.previous_date = None

class JQSimulator:
    """聚宽模拟交易引擎"""
    def __init__(self, db: Session, account: Account):
        self.db = db
        self.account = account
        self.context = Context(db, account)
        self.g = G()
        
        # 策略函数
        self.initialize_func = None
        self.handle_data_func = None
        self.before_trading_start_func = None
        self.after_trading_end_func = None
        self.scheduled_funcs = []
        
        # 运行状态
        self.is_initialized = False
    
    def set_initialize(self, func: Callable):
        """设置初始化函数"""
        self.initialize_func = func
    
    def set_handle_data(self, func: Callable):
        """设置主策略函数"""
        self.handle_data_func = func
    
    def set_before_trading_start(self, func: Callable):
        """设置开盘前函数"""
        self.before_trading_start_func = func
    
    def set_after_trading_end(self, func: Callable):
        """设置收盘后函数"""
        self.after_trading_end_func = func
    
    def run_daily(self, func: Callable, time_str: str):
        """定时运行函数"""
        self.scheduled_funcs.append({
            'func': func,
            'time': time_str,
            'type': 'daily'
        })
    
    def initialize(self):
        """初始化策略"""
        if not self.is_initialized and self.initialize_func:
            logger.info("初始化策略...")
            self.initialize_func(self.context, self.g)
            self.is_initialized = True
    
    def run_strategy(self):
        """运行策略"""
        try:
            # 初始化
            if not self.is_initialized:
                self.initialize()
            
            # 更新上下文
            self.context.current_dt = datetime.now()
            self.context.portfolio._update()
            
            # 开盘前
            if self.before_trading_start_func:
                self.before_trading_start_func(self.context)
            
            # 主策略
            if self.handle_data_func:
                self.handle_data_func(self.context, None)
            
            # 定时任务
            for scheduled in self.scheduled_funcs:
                if scheduled['time'] == 'every_bar':
                    scheduled['func'](self.context)
            
            # 收盘后
            if self.after_trading_end_func:
                self.after_trading_end_func(self.context)
            
            logger.info("策略运行完成")
            
        except Exception as e:
            logger.error(f"策略运行失败: {e}")
            raise

# ==================== 策略API函数 ====================
_current_simulator = None

def set_current_simulator(simulator: JQSimulator):
    """设置当前模拟器"""
    global _current_simulator
    _current_simulator = simulator

def get_current_simulator() -> JQSimulator:
    """获取当前模拟器"""
    return _current_simulator

def attribute_history(security: str, count: int, unit: str, fields: List[str]) -> Dict:
    """获取历史数据"""
    timeframe_map = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "1d": mt5.TIMEFRAME_D1
    }
    timeframe = timeframe_map.get(unit, mt5.TIMEFRAME_D1)
    
    klines = get_kline_data(security, timeframe, count)
    
    result = {}
    for field in fields:
        if field == "close":
            result["close"] = [k["close"] for k in klines]
        elif field == "open":
            result["open"] = [k["open"] for k in klines]
        elif field == "high":
            result["high"] = [k["high"] for k in klines]
        elif field == "low":
            result["low"] = [k["low"] for k in klines]
        elif field == "volume":
            result["volume"] = [k["volume"] for k in klines]
    
    return result

def order(security: str, amount: int) -> Optional[Order]:
    """按股数下单"""
    simulator = get_current_simulator()
    if not simulator:
        return None
    
    side = "BUY" if amount > 0 else "SELL"
    quantity = abs(amount)
    
    # 确保是100的倍数
    quantity = (quantity // 100) * 100
    if quantity == 0:
        return None
    
    price = get_last_price(security)
    
    try:
        order_obj = place_and_execute_mt5_order(
            db=simulator.db,
            account=simulator.account,
            symbol=security,
            name=security,
            side=side,
            order_type="MARKET",
            price=price or 0.0,
            quantity=quantity,
            use_mt5_platform=False
        )
        simulator.context.portfolio._update()
        return order_obj
    except Exception as e:
        logger.error(f"下单失败: {e}")
        return None

def order_target(security: str, amount: int) -> Optional[Order]:
    """目标股数下单"""
    simulator = get_current_simulator()
    if not simulator:
        return None
    
    # 获取当前持仓
    current_amount = 0
    if security in simulator.context.portfolio.positions:
        current_amount = int(simulator.context.portfolio.positions[security].total_amount)
    
    delta = amount - current_amount
    
    if delta == 0:
        return None
    
    return order(security, delta)

def order_value(security: str, value: float) -> Optional[Order]:
    """按金额下单"""
    price = get_last_price(security)
    if not price:
        return None
    
    quantity = int(value / price / 100) * 100
    
    if quantity == 0:
        return None
    
    return order(security, quantity)

def order_target_value(security: str, value: float) -> Optional[Order]:
    """目标金额下单"""
    simulator = get_current_simulator()
    if not simulator:
        return None
    
    # 获取当前持仓市值
    current_value = 0
    if security in simulator.context.portfolio.positions:
        current_value = simulator.context.portfolio.positions[security].value
    
    delta_value = value - current_value
    
    if abs(delta_value) < 100:
        return None
    
    return order_value(security, delta_value)

class Log:
    """日志对象"""
    @staticmethod
    def info(msg):
        logger.info(msg)
        print(f"[INFO] {msg}")
    
    @staticmethod
    def warn(msg):
        logger.warning(msg)
        print(f"[WARN] {msg}")
    
    @staticmethod
    def error(msg):
        logger.error(msg)
        print(f"[ERROR] {msg}")

log = Log()
