"""
聚宽策略示例 - 5日均线策略
可直接在FinAI平台运行
"""

def initialize(context, g):
    """初始化函数"""
    # 定义要操作的股票
    g.security = '600000'  # 浦发银行
    log.info(f"初始化完成，操作股票: {g.security}")

def handle_data(context, data):
    """策略主函数 - 每次运行时调用"""
    security = g.security
    
    # 获取过去5天的收盘价
    close_data = attribute_history(security, 5, '1d', ['close'])
    
    if not close_data or 'close' not in close_data:
        log.warn("无法获取历史数据")
        return
    
    # 计算5日均价
    close_prices = close_data['close']
    MA5 = sum(close_prices) / len(close_prices)
    current_price = close_prices[-1]
    
    log.info(f"当前价格: {current_price:.2f}, 5日均价: {MA5:.2f}")
    
    # 获取当前持仓和现金
    cash = context.portfolio.available_cash
    positions = context.portfolio.positions
    
    # 交易逻辑
    if current_price > MA5 * 1.01:
        # 价格高于均线1%，买入
        if cash > 0 and security not in positions:
            order_value(security, cash * 0.95)
            log.info(f"买入 {security}")
    
    elif current_price < MA5 * 0.99:
        # 价格低于均线1%，卖出
        if security in positions and positions[security].closeable_amount > 0:
            order_target(security, 0)
            log.info(f"卖出 {security}")
    
    else:
        log.info("持仓观望")
