#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途模拟交易示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Account, User
from services.futu_order_executor import place_and_execute_futu_order
from services.futu_market_data import get_stock_quote, get_positions, get_account_info, unlock_trade
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
    
    stocks = ['HK.00700', 'HK.00941', 'US.AAPL', 'US.TSLA']
    quotes = get_stock_quote(stocks)
    
    for code, quote in quotes.items():
        print(f"{quote['stock_name']} ({code}): {quote['cur_price']} ({quote['change_rate']:+.2f}%)")

def demo_account_info():
    """演示获取账户信息"""
    print("\n=== 富途账户信息 ===")
    
    account_info = get_account_info()
    if account_info:
        print(f"总资产: {account_info['total_assets']} {account_info['currency']}")
        print(f"现金: {account_info['cash']} {account_info['currency']}")
        print(f"市值: {account_info['market_val']} {account_info['currency']}")
        print(f"购买力: {account_info['power']} {account_info['currency']}")
    else:
        print("获取账户信息失败")

def demo_positions():
    """演示获取持仓信息"""
    print("\n=== 富途持仓信息 ===")
    
    positions = get_positions()
    if positions:
        for pos in positions:
            print(f"{pos['stock_name']} ({pos['code']}): {pos['qty']} 股")
            print(f"  成本价: {pos['cost_price']}, 现价: {pos['cur_price']}")
            print(f"  盈亏: {pos['pl_val']} ({pos['pl_ratio']:+.2f}%)")
    else:
        print("当前无持仓")

def demo_trading():
    """演示模拟交易"""
    print("\n=== 富途模拟交易 ===")
    
    # 获取默认账户
    account = get_default_account()
    if not account:
        print("无法获取交易账户")
        return
    
    db = SessionLocal()
    try:
        # 刷新账户信息
        db.refresh(account)
        print(f"账户现金: {account.current_cash}")
        
        # 示例：买入腾讯股票
        symbol = "HK.00700"
        name = "腾讯控股"
        
        # 获取当前价格
        quotes = get_stock_quote([symbol])
        if symbol not in quotes:
            print(f"无法获取{symbol}价格")
            return
        
        current_price = quotes[symbol]['cur_price']
        print(f"{name}当前价格: {current_price}")
        
        # 下买单
        try:
            order = place_and_execute_futu_order(
                db=db,
                account=account,
                symbol=symbol,
                name=name,
                side="BUY",
                order_type="LIMIT",
                price=current_price,
                quantity=100,  # 港股最小单位100股
                use_futu_platform=True
            )
            
            print(f"✓ 买单成功: {order.order_no}")
            print(f"  {order.side} {order.quantity} 股 {order.symbol} @ {order.price}")
            
            # 刷新账户信息
            db.refresh(account)
            print(f"交易后现金: {account.current_cash}")
            
        except Exception as e:
            print(f"✗ 买单失败: {e}")
        
        # 等待一下，然后尝试卖出
        input("\n按回车键继续卖出操作...")
        
        try:
            # 卖出一半
            sell_order = place_and_execute_futu_order(
                db=db,
                account=account,
                symbol=symbol,
                name=name,
                side="SELL",
                order_type="LIMIT",
                price=current_price,
                quantity=100,
                use_futu_platform=True
            )
            
            print(f"✓ 卖单成功: {sell_order.order_no}")
            print(f"  {sell_order.side} {sell_order.quantity} 股 {sell_order.symbol} @ {sell_order.price}")
            
            # 刷新账户信息
            db.refresh(account)
            print(f"交易后现金: {account.current_cash}")
            
        except Exception as e:
            print(f"✗ 卖单失败: {e}")
            
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 50)
    print("富途模拟交易演示")
    print("=" * 50)
    
    # 检查交易密码并解锁
    from database.models import SystemConfig
    db = SessionLocal()
    try:
        pwd_config = db.query(SystemConfig).filter(SystemConfig.key == "futu_password").first()
        if pwd_config and pwd_config.value:
            if unlock_trade(pwd_config.value):
                print("✓ 富途交易已解锁")
            else:
                print("✗ 富途交易解锁失败")
                return
        else:
            print("未设置富途交易密码，请先运行 setup_futu.py")
            return
    finally:
        db.close()
    
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
        from services.futu_market_data import close_connections
        close_connections()

if __name__ == "__main__":
    main()