#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IBKR模拟交易示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Account, User
from services.ibkr_order_executor import place_and_execute_ibkr_order
from services.ibkr_market_data import get_stock_quote, get_positions, get_account_info, get_ib_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_default_account():
    """获取默认账户"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "default").first()
        if not user:
            logger.error("未找到默认用户")
            return None
        
        account = db.query(Account).filter(Account.user_id == user.id).first()
        if not account:
            logger.error("未找到默认账户")
            return None
        
        return account
    finally:
        db.close()

def demo_stock_quotes():
    """演示获取股票报价"""
    print("\n=== 获取股票报价 ===")
    
    stocks = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    quotes = get_stock_quote(stocks)
    
    for symbol, quote in quotes.items():
        print(f"{symbol}: ${quote['last_price']:.2f} (变动: ${quote['change']:+.2f})")

def demo_account_info():
    """演示获取账户信息"""
    print("\n=== IBKR账户信息 ===")
    
    account_info = get_account_info()
    if account_info:
        print(f"总资产: ${account_info['total_assets']:,.2f}")
        print(f"现金: ${account_info['cash']:,.2f}")
        print(f"市值: ${account_info['market_val']:,.2f}")
        print(f"购买力: ${account_info['power']:,.2f}")
    else:
        print("获取账户信息失败")

def demo_positions():
    """演示获取持仓信息"""
    print("\n=== IBKR持仓信息 ===")
    
    positions = get_positions()
    if positions:
        for pos in positions:
            print(f"{pos['symbol']}: {pos['position']} 股")
            print(f"  成本价: ${pos['avg_cost']:.2f}")
            print(f"  市值: ${pos['market_value']:,.2f}")
    else:
        print("当前无持仓")

def demo_trading():
    """演示模拟交易"""
    print("\n=== IBKR模拟交易 ===")
    
    # 获取默认账户
    account = get_default_account()
    if not account:
        print("无法获取交易账户")
        return
    
    db = SessionLocal()
    try:
        # 刷新账户信息
        db.refresh(account)
        print(f"账户现金: ${account.current_cash:,.2f}")
        
        # 示例：买入苹果股票
        symbol = "AAPL"
        name = "Apple Inc"
        
        # 获取当前价格
        quotes = get_stock_quote([symbol])
        if symbol not in quotes:
            print(f"无法获取{symbol}价格")
            return
        
        current_price = quotes[symbol]['last_price']
        print(f"{name}当前价格: ${current_price:.2f}")
        
        # 下买单
        try:
            order = place_and_execute_ibkr_order(
                db=db,
                account=account,
                symbol=symbol,
                name=name,
                side="BUY",
                order_type="LIMIT",
                price=current_price,
                quantity=10,  # 买入10股
                use_ibkr_platform=True
            )
            
            print(f"✓ 买单成功: {order.order_no}")
            print(f"  {order.side} {order.quantity} 股 {order.symbol} @ ${order.price:.2f}")
            
            # 刷新账户信息
            db.refresh(account)
            print(f"交易后现金: ${account.current_cash:,.2f}")
            
        except Exception as e:
            print(f"✗ 买单失败: {e}")
        
        # 等待一下，然后尝试卖出
        input("\n按回车键继续卖出操作...")
        
        try:
            # 卖出一半
            sell_order = place_and_execute_ibkr_order(
                db=db,
                account=account,
                symbol=symbol,
                name=name,
                side="SELL",
                order_type="LIMIT",
                price=current_price,
                quantity=5,
                use_ibkr_platform=True
            )
            
            print(f"✓ 卖单成功: {sell_order.order_no}")
            print(f"  {sell_order.side} {sell_order.quantity} 股 {sell_order.symbol} @ ${sell_order.price:.2f}")
            
            # 刷新账户信息
            db.refresh(account)
            print(f"交易后现金: ${account.current_cash:,.2f}")
            
        except Exception as e:
            print(f"✗ 卖单失败: {e}")
            
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 50)
    print("Interactive Brokers模拟交易演示")
    print("=" * 50)
    
    # 检查IBKR连接
    try:
        ib = get_ib_connection()
        if ib.isConnected():
            print("✓ IBKR连接正常")
        else:
            print("✗ IBKR连接失败，请检查TWS/Gateway是否运行")
            return
    except Exception as e:
        print(f"✗ IBKR连接异常: {e}")
        print("请确保:")
        print("1. TWS或IB Gateway已启动")
        print("2. 已登录Paper Trading账户")
        print("3. API设置已启用")
        return
    
    try:
        # 演示各种功能
        demo_stock_quotes()
        demo_account_info()
        demo_positions()
        
        # 询问是否进行交易演示
        response = input("\n是否进行模拟交易演示? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            demo_trading()
        
        print("\n演示完成!")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
    finally:
        # 清理连接
        from services.ibkr_market_data import close_connection
        close_connection()

if __name__ == "__main__":
    main()