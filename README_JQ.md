# FinAI 聚宽模拟交易平台

基于聚宽API风格的A股模拟交易平台，完全兼容聚宽策略代码。

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements_mt5.txt

# 2. 启动平台
python start_jq.py
```

## 📋 功能特性

### ✅ 完全兼容聚宽API
- `initialize(context, g)` - 初始化函数
- `handle_data(context, data)` - 策略主函数
- `before_trading_start(context)` - 开盘前运行
- `after_trading_end(context)` - 收盘后运行
- `run_daily(func, time)` - 定时运行

### ✅ 数据获取函数
- `attribute_history(security, count, unit, fields)` - 获取历史数据
- `get_price(security, start_date, end_date, frequency, fields)` - 获取价格数据

### ✅ 交易函数
- `order(security, amount)` - 按股数下单
- `order_target(security, amount)` - 目标股数下单
- `order_value(security, value)` - 按金额下单
- `order_target_value(security, value)` - 目标金额下单

### ✅ 对象
- `context.portfolio` - 投资组合对象
  - `total_value` - 总资产
  - `available_cash` - 可用资金
  - `positions` - 持仓字典
- `context.current_dt` - 当前时间
- `g` - 全局变量对象
- `log.info/warn/error` - 日志函数

## 💡 使用示例

### 1. 编写策略

创建策略文件 `my_strategy.py`:

```python
def initialize(context, g):
    """初始化"""
    g.security = '600000'  # 浦发银行
    log.info("策略初始化完成")

def handle_data(context, data):
    """策略主函数"""
    security = g.security
    
    # 获取5日收盘价
    close_data = attribute_history(security, 5, '1d', ['close'])
    MA5 = sum(close_data['close']) / 5
    current_price = close_data['close'][-1]
    
    # 交易逻辑
    if current_price > MA5 * 1.01:
        if context.portfolio.available_cash > 0:
            order_value(security, context.portfolio.available_cash * 0.95)
            log.info(f"买入 {security}")
    
    elif current_price < MA5 * 0.99:
        if security in context.portfolio.positions:
            order_target(security, 0)
            log.info(f"卖出 {security}")
```

### 2. 通过API创建模拟交易

```python
import requests

# 读取策略代码
with open('my_strategy.py', 'r', encoding='utf-8') as f:
    strategy_code = f.read()

# 创建模拟交易
response = requests.post('http://localhost:8000/api/jq/simulator/create', json={
    'strategy_code': strategy_code,
    'account_name': '我的聚宽策略'
})

result = response.json()
simulator_id = result['data']['simulator_id']
print(f"模拟器ID: {simulator_id}")
```

### 3. 运行策略

```python
# 运行策略
response = requests.post('http://localhost:8000/api/jq/simulator/run', json={
    'simulator_id': simulator_id
})

print(response.json())
```

### 4. 查看状态

```python
# 查看模拟器状态
response = requests.get(f'http://localhost:8000/api/jq/simulator/status/{simulator_id}')
status = response.json()

print(f"总资产: {status['data']['total_value']}")
print(f"现金: {status['data']['cash']}")
print(f"持仓: {status['data']['positions']}")
```

## 📊 API端点

### 模拟交易管理
- `POST /api/jq/simulator/create` - 创建模拟交易
- `POST /api/jq/simulator/run` - 运行策略
- `GET /api/jq/simulator/status/{simulator_id}` - 查看状态
- `GET /api/jq/simulator/list` - 列出所有模拟器
- `DELETE /api/jq/simulator/delete/{simulator_id}` - 删除模拟器

### 聚宽API适配
- `POST /api/jq/get_price` - 获取历史数据
- `GET /api/jq/attribute_history/{security}` - 获取单标的历史数据
- `GET /api/jq/current_price/{security}` - 获取当前价格
- `GET /api/jq/portfolio` - 获取投资组合
- `GET /api/jq/positions` - 获取持仓
- `POST /api/jq/order` - 下单
- `POST /api/jq/order_target` - 目标数量下单
- `POST /api/jq/order_value` - 按金额下单
- `GET /api/jq/orders` - 获取订单列表

## 🎯 策略示例

### 示例1: 5日均线策略

```python
def initialize(context, g):
    g.security = '600000'

def handle_data(context, data):
    security = g.security
    close_data = attribute_history(security, 5, '1d', ['close'])
    MA5 = sum(close_data['close']) / 5
    current_price = close_data['close'][-1]
    
    if current_price > MA5 * 1.01:
        order_value(security, context.portfolio.available_cash * 0.95)
    elif current_price < MA5 * 0.99:
        order_target(security, 0)
```

### 示例2: 多股票轮动

```python
def initialize(context, g):
    g.stocks = ['600000', '000001', '600036']

def handle_data(context, data):
    for security in g.stocks:
        close_data = attribute_history(security, 5, '1d', ['close'])
        MA5 = sum(close_data['close']) / 5
        current_price = close_data['close'][-1]
        
        if current_price > MA5 * 1.02:
            cash_per_stock = context.portfolio.available_cash / len(g.stocks)
            order_value(security, cash_per_stock)
```

### 示例3: 定时交易

```python
def initialize(context, g):
    g.security = '600000'
    run_daily(buy_stock, '09:30')
    run_daily(sell_stock, '14:50')

def buy_stock(context):
    order_value(g.security, context.portfolio.available_cash * 0.5)

def sell_stock(context):
    order_target(g.security, 0)
```

## 🔧 与聚宽的差异

### 已支持
✅ 基本策略框架 (initialize, handle_data)  
✅ 交易函数 (order系列)  
✅ 数据获取 (attribute_history)  
✅ 投资组合对象 (context.portfolio)  
✅ 全局变量 (g对象)  
✅ 日志功能 (log)  

### 暂不支持
❌ 回测功能 (仅支持模拟交易)  
❌ 财务数据 (get_fundamentals)  
❌ 因子数据 (get_factor_values)  
❌ 指数成分股 (get_index_stocks)  

## 📝 注意事项

1. **交易规则**: 遵循A股交易规则（100股起、T+1）
2. **费用计算**: 自动计算佣金、印花税、过户费
3. **数据源**: 使用akshare获取A股实时数据
4. **运行频率**: 手动触发运行，可集成定时任务

## 🚨 风险提示

本平台仅供学习和测试使用。投资有风险，入市需谨慎。

## 📚 相关文档

- [聚宽API文档](https://www.joinquant.com/help/api/help)
- [FinAI项目文档](README.md)
- [MT5版本文档](README_MT5.md)

---

**开发团队**: FinAI  
**版本**: 1.0.0  
**更新日期**: 2024
