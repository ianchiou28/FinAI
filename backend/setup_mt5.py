"""
MT5 A股模拟交易平台设置脚本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import engine, SessionLocal
from database.models import Base, Account
import MetaTrader5 as mt5
from decimal import Decimal

def setup_mt5():
    """设置MT5连接和初始账户"""
    print("=" * 60)
    print("MT5 A股模拟交易平台设置")
    print("=" * 60)
    
    # 1. 初始化MT5
    print("\n[1/4] 初始化MT5连接...")
    if not mt5.initialize():
        print(f"❌ MT5初始化失败: {mt5.last_error()}")
        print("\n请确保:")
        print("  1. 已安装MetaTrader 5")
        print("  2. MT5已登录账户")
        print("  3. 允许自动交易（工具 -> 选项 -> EA交易）")
        return False
    
    print("✓ MT5连接成功")
    
    # 2. 获取账户信息
    print("\n[2/4] 获取MT5账户信息...")
    account_info = mt5.account_info()
    if account_info is None:
        print("❌ 无法获取账户信息")
        mt5.shutdown()
        return False
    
    print(f"✓ 账户登录: {account_info.login}")
    print(f"  服务器: {account_info.server}")
    print(f"  余额: {account_info.balance} {account_info.currency}")
    print(f"  净值: {account_info.equity} {account_info.currency}")
    
    # 3. 创建数据库表
    print("\n[3/4] 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建成功")
    
    # 4. 创建模拟账户
    print("\n[4/4] 创建A股模拟账户...")
    db = SessionLocal()
    try:
        # 创建默认用户
        from database.models import User
        user = db.query(User).filter(User.username == "mt5_user").first()
        if not user:
            user = User(username="mt5_user", email="mt5@finai.com", is_active="true")
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # 检查是否已存在A股账户
        existing = db.query(Account).filter(
            Account.user_id == user.id,
            Account.name == "MT5 A股账户"
        ).first()
        
        if existing:
            print(f"✓ A股账户已存在 (ID: {existing.id})")
            print(f"  初始资金: ¥{existing.initial_capital:,.2f}")
            print(f"  当前资金: ¥{existing.current_cash:,.2f}")
        else:
            # 创建新账户
            initial_capital = 1000000.0  # 100万初始资金
            account = Account(
                user_id=user.id,
                version="v1",
                name="MT5 A股账户",
                account_type="MANUAL",
                is_active="true",
                initial_capital=initial_capital,
                current_cash=initial_capital,
                frozen_cash=0,
                margin_used=0
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            
            print(f"✓ A股账户创建成功 (ID: {account.id})")
            print(f"  初始资金: ¥{initial_capital:,.2f}")
    finally:
        db.close()
    
    # 5. 测试连接
    print("\n[测试] 获取股票行情...")
    test_symbols = ["600000", "000001", "600519"]  # 浦发银行、平安银行、贵州茅台
    
    for symbol in test_symbols:
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"✓ {symbol}: ¥{tick.last:.2f}")
        else:
            print(f"⚠ {symbol}: 无法获取行情（可能需要在MT5中添加该股票）")
    
    mt5.shutdown()
    
    print("\n" + "=" * 60)
    print("✓ MT5 A股模拟交易平台设置完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 启动平台: python start_mt5.py")
    print("  2. 访问前端: http://localhost:5173")
    print("  3. API文档: http://localhost:8000/docs")
    print("\n注意事项:")
    print("  - 确保MT5保持运行状态")
    print("  - A股交易单位为100股（1手）")
    print("  - 包含佣金、印花税、过户费")
    print("  - 仅供学习测试，不构成投资建议")
    
    return True

if __name__ == "__main__":
    try:
        setup_mt5()
    except KeyboardInterrupt:
        print("\n\n设置已取消")
    except Exception as e:
        print(f"\n❌ 设置失败: {e}")
        import traceback
        traceback.print_exc()
