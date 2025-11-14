"""
测试MT5连接和A股数据
"""
import MetaTrader5 as mt5

print("=" * 60)
print("MT5连接测试")
print("=" * 60)

# 初始化MT5
if not mt5.initialize():
    print(f"❌ MT5初始化失败: {mt5.last_error()}")
    exit()

print("✓ MT5已连接")

# 获取账户信息
account_info = mt5.account_info()
if account_info:
    print(f"\n账户: {account_info.login}")
    print(f"服务器: {account_info.server}")
    print(f"余额: {account_info.balance} {account_info.currency}")

# 测试A股股票
print("\n" + "=" * 60)
print("测试A股股票数据")
print("=" * 60)

test_symbols = ["600000", "600519", "000001", "EURUSD", "BTCUSD"]

for symbol in test_symbols:
    print(f"\n测试: {symbol}")
    
    # 获取股票信息
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"  ❌ 股票不存在")
        continue
    
    print(f"  ✓ 股票存在: {symbol_info.description}")
    print(f"  可见: {symbol_info.visible}")
    
    # 尝试获取报价
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        print(f"  ✓ 最新价: {tick.last}")
        print(f"  买价: {tick.bid}")
        print(f"  卖价: {tick.ask}")
    else:
        print(f"  ❌ 无法获取报价")

# 列出所有可用股票
print("\n" + "=" * 60)
print("可用股票列表（前20个）")
print("=" * 60)

symbols = mt5.symbols_get()
if symbols:
    print(f"总共 {len(symbols)} 个股票")
    for i, s in enumerate(symbols[:20]):
        print(f"{i+1}. {s.name} - {s.description}")
else:
    print("❌ 无法获取股票列表")

mt5.shutdown()
print("\n测试完成")
