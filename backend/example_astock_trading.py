"""
A股交易示例脚本
演示如何使用A股交易功能
"""
from database.connection import SessionLocal
from database.models import Account, Position, Order, Trade
from services.order_executor_astock import place_and_execute_astock
from services.market_data import get_last_price, get_kline_data
from decimal import Decimal


def example_1_get_market_data():
    """示例1: 获取市场数据"""
    print("\n" + "="*60)
    print("示例1: 获取A股市场数据")
    print("="*60)
    
    # 获取浦发银行的实时价格
    symbol = "600000"
    print(f"\n获取 {symbol} (浦发银行) 的实时价格...")
    price = get_last_price(symbol, "ASTOCK")
    print(f"当前价格: ¥{price}")
    
    # 获取K线数据
    print(f"\n获取 {symbol} 的日K线数据（最近5天）...")
    klines = get_kline_data(symbol, "ASTOCK", period="daily", count=5)
    
    print(f"\n最近5天K线数据:")
    print(f"{'日期':<12} {'开盘':<8} {'最高':<8} {'最低':<8} {'收盘':<8} {'成交量':<12}")
    print("-" * 70)
    for k in klines:
        print(f"{k['datetime']:<12} {k['open']:<8.2f} {k['high']:<8.2f} "
              f"{k['low']:<8.2f} {k['close']:<8.2f} {k['volume']:<12.0f}")


def example_2_simple_buy():
    """示例2: 简单买入操作"""
    print("\n" + "="*60)
    print("示例2: 买入A股")
    print("="*60)
    
    db = SessionLocal()
    try:
        # 获取账户
        account = db.query(Account).first()
        if not account:
            print("错误: 未找到账户")
            return
        
        print(f"\n账户信息:")
        print(f"  账户名: {account.name}")
        print(f"  可用资金: ¥{account.current_cash:,.2f}")
        
        # 买入参数
        symbol = "600000"
        name = "浦发银行"
        quantity = 100  # 1手
        
        # 获取当前价格
        price = get_last_price(symbol, "ASTOCK")
        
        print(f"\n准备买入:")
        print(f"  股票: {name} ({symbol})")
        print(f"  数量: {quantity} 股")
        print(f"  价格: ¥{price}")
        
        # 计算成本
        notional = price * quantity
        commission = max(notional * 0.0003, 5.0)
        total_cost = notional + commission
        
        print(f"\n成本计算:")
        print(f"  交易金额: ¥{notional:,.2f}")
        print(f"  佣金: ¥{commission:.2f}")
        print(f"  总成本: ¥{total_cost:,.2f}")
        
        if account.current_cash < total_cost:
            print(f"\n资金不足! 需要 ¥{total_cost:,.2f}，当前 ¥{account.current_cash:,.2f}")
            return
        
        # 确认
        confirm = input("\n确认买入? (y/n): ")
        if confirm.lower() != 'y':
            print("已取消")
            return
        
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
            use_ths=False  # 本地模拟
        )
        
        print(f"\n✓ 买入成功!")
        print(f"  订单号: {order.order_no}")
        print(f"  成交价: ¥{order.price}")
        print(f"  成交量: {order.filled_quantity} 股")
        
        # 刷新账户
        db.refresh(account)
        print(f"  剩余资金: ¥{account.current_cash:,.2f}")
        
    finally:
        db.close()


def example_3_view_positions():
    """示例3: 查看持仓"""
    print("\n" + "="*60)
    print("示例3: 查看A股持仓")
    print("="*60)
    
    db = SessionLocal()
    try:
        account = db.query(Account).first()
        if not account:
            print("错误: 未找到账户")
            return
        
        # 查询A股持仓
        positions = db.query(Position).filter(
            Position.account_id == account.id,
            Position.market == "ASTOCK",
            Position.quantity > 0
        ).all()
        
        if not positions:
            print("\n当前无A股持仓")
            return
        
        print(f"\n当前A股持仓:")
        print(f"{'股票代码':<10} {'股票名称':<12} {'数量':<8} {'成本价':<10} "
              f"{'当前价':<10} {'市值':<12} {'盈亏':<12} {'盈亏率':<10}")
        print("-" * 100)
        
        total_cost = Decimal(0)
        total_value = Decimal(0)
        
        for pos in positions:
            try:
                current_price = Decimal(str(get_last_price(pos.symbol, "ASTOCK")))
                quantity = Decimal(str(pos.quantity))
                avg_cost = Decimal(str(pos.avg_cost))
                
                cost = quantity * avg_cost
                value = quantity * current_price
                pnl = value - cost
                pnl_rate = (pnl / cost * 100) if cost > 0 else Decimal(0)
                
                total_cost += cost
                total_value += value
                
                print(f"{pos.symbol:<10} {pos.name:<12} {pos.quantity:<8.0f} "
                      f"¥{pos.avg_cost:<9.2f} ¥{float(current_price):<9.2f} "
                      f"¥{float(value):<11.2f} ¥{float(pnl):<11.2f} "
                      f"{float(pnl_rate):>8.2f}%")
            except Exception as e:
                print(f"{pos.symbol:<10} {pos.name:<12} {pos.quantity:<8.0f} "
                      f"¥{pos.avg_cost:<9.2f} {'N/A':<10} {'N/A':<12} {'N/A':<12} {'N/A':<10}")
        
        print("-" * 100)
        total_pnl = total_value - total_cost
        total_pnl_rate = (total_pnl / total_cost * 100) if total_cost > 0 else Decimal(0)
        
        print(f"{'合计':<10} {'':<12} {'':<8} {'':<10} {'':<10} "
              f"¥{float(total_value):<11.2f} ¥{float(total_pnl):<11.2f} "
              f"{float(total_pnl_rate):>8.2f}%")
        
        print(f"\n账户资金: ¥{account.current_cash:,.2f}")
        print(f"持仓市值: ¥{float(total_value):,.2f}")
        print(f"总资产: ¥{float(account.current_cash) + float(total_value):,.2f}")
        
    finally:
        db.close()


def example_4_sell_position():
    """示例4: 卖出持仓"""
    print("\n" + "="*60)
    print("示例4: 卖出A股")
    print("="*60)
    
    db = SessionLocal()
    try:
        account = db.query(Account).first()
        if not account:
            print("错误: 未找到账户")
            return
        
        # 查询持仓
        positions = db.query(Position).filter(
            Position.account_id == account.id,
            Position.market == "ASTOCK",
            Position.quantity > 0
        ).all()
        
        if not positions:
            print("\n当前无A股持仓可卖出")
            return
        
        # 显示持仓列表
        print("\n当前持仓:")
        for i, pos in enumerate(positions, 1):
            current_price = get_last_price(pos.symbol, "ASTOCK")
            print(f"{i}. {pos.name} ({pos.symbol}) - "
                  f"持有 {pos.quantity:.0f} 股, "
                  f"成本价 ¥{pos.avg_cost:.2f}, "
                  f"当前价 ¥{current_price:.2f}")
        
        # 选择要卖出的股票
        choice = input("\n选择要卖出的股票 (输入序号): ")
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(positions):
                print("无效的选择")
                return
        except ValueError:
            print("无效的输入")
            return
        
        pos = positions[idx]
        current_price = get_last_price(pos.symbol, "ASTOCK")
        
        # 输入卖出数量
        quantity_str = input(f"输入卖出数量 (最多 {pos.quantity:.0f} 股, 必须是100的整数倍): ")
        try:
            quantity = int(quantity_str)
            if quantity % 100 != 0:
                print("数量必须是100的整数倍")
                return
            if quantity > pos.quantity:
                print(f"数量超过持仓 ({pos.quantity:.0f} 股)")
                return
        except ValueError:
            print("无效的数量")
            return
        
        # 计算收益
        notional = current_price * quantity
        commission = max(notional * 0.0003, 5.0)
        stamp_tax = notional * 0.001
        total_fee = commission + stamp_tax
        net_proceeds = notional - total_fee
        
        cost = pos.avg_cost * quantity
        profit = net_proceeds - cost
        
        print(f"\n卖出详情:")
        print(f"  股票: {pos.name} ({pos.symbol})")
        print(f"  数量: {quantity} 股")
        print(f"  卖出价: ¥{current_price:.2f}")
        print(f"  交易金额: ¥{notional:,.2f}")
        print(f"  佣金: ¥{commission:.2f}")
        print(f"  印花税: ¥{stamp_tax:.2f}")
        print(f"  净收入: ¥{net_proceeds:,.2f}")
        print(f"  成本: ¥{cost:,.2f}")
        print(f"  盈亏: ¥{profit:,.2f}")
        
        # 确认
        confirm = input("\n确认卖出? (y/n): ")
        if confirm.lower() != 'y':
            print("已取消")
            return
        
        # 执行卖出
        order = place_and_execute_astock(
            db=db,
            account=account,
            symbol=pos.symbol,
            name=pos.name,
            side="SELL",
            order_type="MARKET",
            price=current_price,
            quantity=quantity,
            use_ths=False
        )
        
        print(f"\n✓ 卖出成功!")
        print(f"  订单号: {order.order_no}")
        print(f"  成交价: ¥{order.price}")
        print(f"  成交量: {order.filled_quantity} 股")
        
        # 刷新账户
        db.refresh(account)
        print(f"  当前资金: ¥{account.current_cash:,.2f}")
        
    finally:
        db.close()


def main():
    """主菜单"""
    while True:
        print("\n" + "="*60)
        print("A股交易示例程序")
        print("="*60)
        print("1. 获取市场数据")
        print("2. 买入股票")
        print("3. 查看持仓")
        print("4. 卖出股票")
        print("0. 退出")
        print("="*60)
        
        choice = input("\n请选择操作: ")
        
        if choice == "1":
            example_1_get_market_data()
        elif choice == "2":
            example_2_simple_buy()
        elif choice == "3":
            example_3_view_positions()
        elif choice == "4":
            example_4_sell_position()
        elif choice == "0":
            print("\n再见!")
            break
        else:
            print("\n无效的选择，请重试")
        
        input("\n按回车键继续...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
