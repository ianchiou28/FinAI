"""
MT5 AI自动交易服务 - 集成AI决策系统
"""
import logging
from typing import Dict, List
from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import Account, Position, AIDecisionLog
from services.mt5_market_data import get_stock_quote, get_last_price
from services.mt5_order_executor import place_and_execute_mt5_order
import requests
import json

logger = logging.getLogger(__name__)

def save_ai_decision(db: Session, account: Account, decision: Dict, portfolio: Dict, executed: bool = False, order_id: int = None):
    """保存AI决策"""
    try:
        operation = decision.get("operation", "").lower()
        symbol = decision.get("symbol", "")
        target_portion = float(decision.get("target_portion", 0))
        reason = decision.get("reason", "AI决策")
        
        log = AIDecisionLog(
            account_id=account.id,
            reason=reason,
            operation=operation,
            symbol=symbol if operation != "hold" else None,
            prev_portion=Decimal("0"),
            target_portion=Decimal(str(target_portion)),
            total_balance=Decimal(str(portfolio.get("total_assets", 0))),
            executed="true" if executed else "false",
            order_id=order_id,
            leverage=1
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"保存AI决策失败: {e}")

# A股常用股票映射
ASTOCK_SYMBOLS = {
    "浦发银行": "600000",
    "平安银行": "000001", 
    "招商银行": "600036",
    "贵州茅台": "600519",
    "中国平安": "601318",
    "万科A": "000002"
}

def get_astock_portfolio(db: Session, account: Account) -> Dict:
    """获取A股投资组合数据"""
    positions = db.query(Position).filter(
        Position.account_id == account.id
    ).all()
    
    portfolio = {}
    total_market_value = 0
    
    for pos in positions:
        if float(pos.quantity) > 0:
            current_price = get_last_price(pos.symbol) or float(pos.avg_cost)
            market_value = float(pos.quantity) * current_price
            total_market_value += market_value
            
            portfolio[pos.symbol] = {
                "quantity": float(pos.quantity),
                "avg_cost": float(pos.avg_cost),
                "current_price": current_price,
                "market_value": market_value,
                "name": pos.name
            }
    
    return {
        "cash": float(account.current_cash),
        "positions": portfolio,
        "total_assets": float(account.current_cash) + total_market_value
    }

def get_astock_prices() -> Dict[str, float]:
    """获取A股实时价格"""
    prices = {}
    symbols = list(ASTOCK_SYMBOLS.values())
    
    for symbol in symbols:
        price = get_last_price(symbol)
        if price:
            prices[symbol] = price
    
    return prices

def call_ai_for_astock_decision(account: Account, portfolio: Dict, prices: Dict[str, float]) -> Dict:
    """调用AI进行A股交易决策"""
    try:
        # 获取A股新闻
        news_summary = fetch_astock_news()
        
        prompt = f"""你是专业的A股交易AI。当前投资组合:
- 可用资金: ¥{portfolio['cash']:.2f}
- 总资产: ¥{portfolio['total_assets']:.2f}
- 持仓: {portfolio['positions']}

实时价格: {prices}

最新A股新闻: {news_summary}

可交易股票:
{ASTOCK_SYMBOLS}

请分析并返回JSON决策(仅JSON):
{{
  "operation": "open" or "close" or "hold",
  "symbol": "股票代码(如600000)",
  "name": "股票名称",
  "target_portion": 0.3,
  "reason": "详细分析"
}}

注意:
- A股最小100股
- T+1交易
- 考虑涨跌停限制
- 控制仓位风险"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {account.api_key}"
        }
        
        payload = {
            "model": account.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        api_endpoint = f"{account.base_url.rstrip('/')}/chat/completions"
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # 提取JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                import json
                decision = json.loads(content)
                logger.info(f"AI A股决策: {decision}")
                return decision
        
        return None
    except Exception as e:
        logger.error(f"AI决策失败: {e}")
        return None

def fetch_astock_news() -> str:
    """获取A股新闻摘要"""
    try:
        # 简化版新闻获取
        return "A股市场保持稳定，科技板块表现活跃。"
    except:
        return "暂无新闻"

def execute_astock_ai_decision(db: Session, account: Account, decision: Dict, portfolio: Dict) -> bool:
    """执行A股AI交易决策"""
    try:
        operation = decision.get("operation", "").lower()
        symbol = decision.get("symbol")
        name = decision.get("name", "")
        target_portion = float(decision.get("target_portion", 0))
        
        if operation == "hold":
            logger.info(f"AI决策: 观望")
            save_ai_decision(db, account, decision, portfolio, executed=False)
            return True
        
        if operation == "open":
            # 开仓买入
            available_cash = portfolio["cash"]
            target_amount = portfolio["total_assets"] * target_portion
            buy_amount = min(target_amount, available_cash * 0.95)
            
            if buy_amount < 1000:
                logger.warning(f"资金不足，需要至少¥1000")
                return False
            
            price = get_last_price(symbol)
            if not price:
                logger.error(f"无法获取{symbol}价格")
                return False
            
            quantity = int(buy_amount / price / 100) * 100
            
            if quantity < 100:
                logger.warning(f"数量不足100股")
                return False
            
            order = place_and_execute_mt5_order(
                db=db,
                account=account,
                symbol=symbol,
                name=name,
                side="BUY",
                order_type="MARKET",
                price=price,
                quantity=quantity,
                use_mt5_platform=False
            )
            
            save_ai_decision(db, account, decision, portfolio, executed=True, order_id=order.id)
            logger.info(f"AI买入成功: {symbol} {quantity}股 @ ¥{price:.2f}")
            return True
        
        elif operation == "close":
            # 平仓卖出
            pos = db.query(Position).filter(
                Position.account_id == account.id,
                Position.symbol == symbol
            ).first()
            
            if not pos or pos.quantity <= 0:
                logger.warning(f"无持仓: {symbol}")
                return False
            
            sell_quantity = int(float(pos.quantity) * target_portion / 100) * 100
            
            if sell_quantity < 100:
                logger.warning(f"卖出数量不足100股")
                return False
            
            price = get_last_price(symbol)
            if not price:
                logger.error(f"无法获取{symbol}价格")
                return False
            
            order = place_and_execute_mt5_order(
                db=db,
                account=account,
                symbol=symbol,
                name=name,
                side="SELL",
                order_type="MARKET",
                price=price,
                quantity=sell_quantity,
                use_mt5_platform=False
            )
            
            save_ai_decision(db, account, decision, portfolio, executed=True, order_id=order.id)
            logger.info(f"AI卖出成功: {symbol} {sell_quantity}股 @ ¥{price:.2f}")
            return True
        
        return False
    except Exception as e:
        logger.error(f"执行AI决策失败: {e}")
        return False

def run_mt5_ai_trading(db: Session):
    """运行MT5 AI自动交易"""
    try:
        # 获取AI账户
        accounts = db.query(Account).filter(
            Account.is_active == "true",
            Account.account_type == "AI",
            Account.name.like("%MT5%")
        ).all()
        
        if not accounts:
            logger.info("无MT5 AI账户")
            return
        
        for account in accounts:
            logger.info(f"执行AI交易: {account.name}")
            
            # 获取投资组合
            portfolio = get_astock_portfolio(db, account)
            
            # 获取价格
            prices = get_astock_prices()
            
            # AI决策
            decision = call_ai_for_astock_decision(account, portfolio, prices)
            
            if decision:
                # 执行决策
                execute_astock_ai_decision(db, account, decision, portfolio)
            
            db.commit()
    
    except Exception as e:
        logger.error(f"AI交易异常: {e}")
        db.rollback()
