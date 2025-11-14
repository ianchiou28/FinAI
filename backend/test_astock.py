"""
A-share trading integration test script
测试A股交易集成
"""
import sys
from database.connection import SessionLocal
from database.models import Account, Position, Order
from services.order_executor_astock import place_and_execute_astock
from services.market_data import get_last_price, get_kline_data


def test_market_data():
    """测试行情数据获取"""
    print("\n=== 测试行情数据获取 ===")
    
    try:
        # 测试获取浦发银行(600000)的价格
        symbol = "600000"
        print(f"\n获取 {symbol} 最新价格...")
        price = get_last_price(symbol, "ASTOCK")
        print(f"✓ 最新价格: ¥{price}")
        
        # 测试获取K线数据
        print(f"\n获取 {symbol} K线数据...")
        klines = get_kline_data(symbol, "ASTOCK", period="daily", count=5)
        print(f"✓ 获取到 {len(klines)} 条K线数据")
        if klines:
            latest = klines[-1]
            print(f"  最新K线: 日期={latest['datetime']}, 收盘={latest['close']}")
        
        return True
    except Exception as e:
        print(f"✗ 行情数据测试失败: {e}")
        return False


def test_local_trading():
    """测试本地模拟交易"""
    print("\n=== 测试本地模拟交易 ===")
    
    db = SessionLocal()
    try:
        # 获取默认账户
        account = db.query(Account).first()
        if not account:
            print("✗ 未找到账户，请先创建账户")
            return False
        
        print(f"\n账户信息:")
        print(f"  账户ID: {account.id}")
        print(f"  账户名称: {account.name}")
        print(f"  可用资金: ¥{account.current_cash}")
        
        # 测试买入
        symbol = "600000"
        name = "浦发银行"
        quantity = 100  # 1手
        
        print(f"\n测试买入 {quantity} 股 {name} ({symbol})...")
        
        # 获取当前价格
        price = get_last_price(symbol, "ASTOCK")
        print(f"  当前价格: ¥{price}")
        
        # 计算所需资金
        notional = price * quantity
        commission = max(notional * 0.0003, 5.0)
        total_cost = notional + commission
        
        print(f"  交易金额: ¥{notional:.2f}")
        print(f"  佣金: ¥{commission:.2f}")
        print(f"  总成本: ¥{total_cost:.2f}")
        
        if account.current_cash < total_cost:
            print(f"✗ 资金不足，需要 ¥{total_cost:.2f}，当前 ¥{account.current_cash}")
            return False
        
        # 执行买入
        order = place_and_execute_astock(
            db=db,
            account=account,
            symbol=symbol,
            name=name,
            side="BUY",
            order_type="MARKET",
            price=price,
            quantity=quantity,
            use_ths=False
        )
        
        print(f"✓ 买入成功!")
        print(f"  订单号: {order.order_no}")
        print(f"  状态: {order.status}")
        print(f"  成交价: ¥{order.price}")
        print(f"  成交量: {order.filled_quantity} 股")
        
        # 刷新账户信息
        db.refresh(account)
        print(f"  剩余资金: ¥{account.current_cash}")
        
        # 查询持仓
        position = db.query(Position).filter(
            Position.account_id == account.id,
            Position.symbol == symbol,
            Position.market == "ASTOCK"
        ).first()
        
        if position:
            print(f"\n持仓信息:")
            print(f"  股票: {position.name} ({position.symbol})")
            print(f"  数量: {position.quantity} 股")
            print(f"  成本价: ¥{position.avg_cost}")
            print(f"  当前价: ¥{price}")
            pnl = (price - position.avg_cost) * position.quantity
            print(f"  浮动盈亏: ¥{pnl:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 本地交易测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_ths_connection():
    """测试同花顺连接（可选）"""
    print("\n=== 测试同花顺连接 ===")
    print("注意: 此测试需要安装 ths_trade 库并配置同花顺账户")
    
    try:
        from services.ths_market_data import get_ths_instance
        trade = get_ths_instance()
        print("✓ THS实例创建成功")
        print("  请使用 /api/astock/ths/login 接口登录")
        return True
    except ImportError:
        print("✗ ths_trade 库未安装")
        print("  安装命令: pip install ths_trade")
        return False
    except Exception as e:
        print(f"✗ THS连接测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("A股交易集成测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 行情数据
    results.append(("行情数据获取", test_market_data()))
    
    # 测试2: 本地交易
    results.append(("本地模拟交易", test_local_trading()))
    
    # 测试3: 同花顺连接（可选）
    results.append(("同花顺连接", test_ths_connection()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
