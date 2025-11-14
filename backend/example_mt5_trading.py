"""
MT5 A股模拟交易示例
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services.mt5_market_data import (
    init_mt5,
    shutdown_mt5,
    get_account_info,
    get_positions,
    get_stock_quote,
    get_last_price,
    get_kline_data,
    search_stock
)
from services.mt5_order_executor import place_and_execute_mt5_order
from database.connection import SessionLocal
from database.models import Account
import MetaTrader5 as mt5

def example_market_data():
    """示例：获取市场数据"""
    print("\n" + "="*60)
    print("示例1: 获取市场数据")
    print("="*60)
    
    # 初始化MT5
    if not init_mt5():
        print("❌ MT5初始化失败")
        return
    
    # 1. 获取账户信息
    print("\n[账户信息]")
    account = get_account_info()
    print(f"总资产: ¥{account.get('total_assets', 0):,.2f}")
    print(f"现金: ¥{account.get('cash', 0):,.2f}")
    print(f"持仓市值: ¥{account.get('market_val', 0):,.2f}")
    
    # 2. 获取股票报价
    print("\n[股票报价]")
    symbols = ["600000", "000001", "600519"]
    quotes = get_stock_quote(symbols)
    for symbol, data in quotes.items():
        print(f"{symbol}: ¥{data['last_price']:.2f} (买:{data['bid']:.2f} 卖:{data['ask']:.2f})")
    
    # 3. 获取K线数据
    print("\n[K线数据 - 600000]")
    klines = get_kline_data("600000", mt5.TIMEFRAME_D1, 5)
    for k in klines[-5:]:
        print(f"{k['datetime']}: 开{k['open']:.2f} 高{k['high']:.2f} 低{k['low']:.2f} 收{k['close']:.2f}")
    
    # 4. 搜索股票
    print("\n[搜索股票 - '银行']")
    results = search_stock("银行")
    for r in results[:5]:
        print(f"{r['symbol']}: {r['description']}")
    
    shutdown_mt5()

def example_trading():
    """示例：模拟交易"""
    print("\n" + "="*60)
    print("示例2: 模拟交易")
    print("="*60)
    
    # 初始化MT5
    if not init_mt5():
        print("❌ MT5初始化失败")
        return
    
    db = SessionLocal()
    try:
        # 获取账户
        account = db.query(Account).filter(Account.name == "MT5 A股账户").first()
        if not account:
            print("❌ 未找到A股账户，请先运行 setup_mt5.py")
            return
        
        print(f"\n[账户状态]")
        print(f"账户ID: {account.id}")
        print(f"当前资金: ¥{account.current_cash:,.2f}")
        
        # 获取当前价格
        symbol = "600000"
        price = get_last_price(symbol)
        if not price:
            print(f"❌ 无法获取{symbol}价格")
            return
        
        print(f"\n[交易信息]")
        print(f"股票代码: {symbol}")
        print(f"当前价格: ¥{price:.2f}")
        
        # 买入100股
        print(f"\n[执行买入] 100股 @ ¥{price:.2f}")
        try:
            order = place_and_execute_mt5_order(
                db=db,
                account=account,
                symbol=symbol,
                name="浦发银行",
                side="BUY",
                order_type="MARKET",
                price=price,
                quantity=100,
                use_mt5_platform=False  # 本地模拟
            )
            
            print(f"✓ 订单成功")
            print(f"  订单号: {order.order_no}")
            print(f"  成交价: ¥{order.price:.2f}")
            print(f"  数量: {order.quantity}")
            print(f"  状态: {order.status}")
            
            # 刷新账户
            db.refresh(account)
            print(f"\n[账户更新]")
            print(f"剩余资金: ¥{account.current_cash:,.2f}")
            
        except ValueError as e:
            print(f"❌ 交易失败: {e}")
        
    finally:
        db.close()
        shutdown_mt5()

def example_positions():
    """示例：查看持仓"""
    print("\n" + "="*60)
    print("示例3: 查看持仓")
    print("="*60)
    
    if not init_mt5():
        print("❌ MT5初始化失败")
        return
    
    # MT5持仓
    print("\n[MT5持仓]")
    positions = get_positions()
    if positions:
        for pos in positions:
            print(f"{pos['symbol']}: {pos['volume']} @ ¥{pos['price_open']:.2f} (盈亏: ¥{pos['profit']:.2f})")
    else:
        print("无持仓")
    
    # 数据库持仓
    print("\n[本地持仓]")
    db = SessionLocal()
    try:
        from database.models import Position
        positions = db.query(Position).filter(Position.market.in_(["CN", "CRYPTO"])).all()
        if positions:
            for pos in positions:
                print(f"{pos.symbol} {pos.name}: {pos.quantity}股 @ ¥{pos.avg_cost:.2f}")
        else:
            print("无持仓")
    finally:
        db.close()
    
    shutdown_mt5()

def main():
    """主函数"""
    print("="*60)
    print("MT5 A股模拟交易示例")
    print("="*60)
    print("\n选择示例:")
    print("1. 获取市场数据")
    print("2. 模拟交易")
    print("3. 查看持仓")
    print("0. 退出")
    
    choice = input("\n请选择 (0-3): ").strip()
    
    if choice == "1":
        example_market_data()
    elif choice == "2":
        example_trading()
    elif choice == "3":
        example_positions()
    elif choice == "0":
        print("退出")
    else:
        print("无效选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已终止")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
