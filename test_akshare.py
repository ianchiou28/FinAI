"""
测试akshare获取A股数据
"""
import akshare as ak

print("测试akshare获取A股实时数据...")

try:
    # 获取A股实时行情
    df = ak.stock_zh_a_spot_em()
    print(f"✓ 成功获取 {len(df)} 只股票数据")
    
    # 测试几只股票
    test_symbols = ['600000', '600519', '000001']
    
    for symbol in test_symbols:
        stock_data = df[df['代码'] == symbol]
        if not stock_data.empty:
            name = stock_data.iloc[0]['名称']
            price = stock_data.iloc[0]['最新价']
            print(f"✓ {symbol} {name}: ¥{price}")
        else:
            print(f"❌ {symbol} 未找到")
            
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
