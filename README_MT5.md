# FinAI MT5 - A股模拟交易平台

基于MetaTrader 5 API的A股模拟交易平台，支持实时行情、智能交易和投资组合管理。

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements_mt5.txt

# 2. 设置MT5连接
python backend/setup_mt5.py

# 3. 启动平台
python start_mt5.py
```

## 📋 系统要求

- Python 3.10+
- MetaTrader 5 终端
- Windows 操作系统（MT5官方仅支持Windows）
- 模拟账户（推荐用于测试）

## 🛠️ 安装步骤

### 1. 安装MetaTrader 5

1. 下载MT5终端：https://www.metatrader5.com/zh/download
2. 安装并启动MT5
3. 注册模拟账户或登录真实账户
4. 启用自动交易：工具 → 选项 → EA交易 → 勾选"允许自动交易"

### 2. 添加A股股票

在MT5中添加A股股票代码：
- 600000 - 浦发银行
- 000001 - 平安银行
- 600519 - 贵州茅台
- 等等...

### 3. 安装Python依赖

```bash
cd FinAI
pip install -r requirements_mt5.txt
```

### 4. 运行设置脚本

```bash
python backend/setup_mt5.py
```

### 5. 启动平台

```bash
python start_mt5.py
```

## 🔧 主要功能

### 市场数据
- ✅ 实时股票报价
- ✅ K线数据（1分钟到月线）
- ✅ 股票搜索
- ✅ 账户信息查询
- ✅ 持仓信息查询

### 交易功能
- ✅ 市价单/限价单
- ✅ 买入/卖出
- ✅ A股交易规则（100股起）
- ✅ 费用计算（佣金+印花税+过户费）
- ✅ 本地模拟交易
- ✅ MT5平台实盘对接

### 费用标准（A股）
- 佣金：0.03%（最低5元）
- 印花税：0.1%（仅卖出）
- 过户费：0.002%

## 📊 API端点

### 账户相关
- `GET /api/mt5/account` - 获取账户信息
- `GET /api/mt5/positions` - 获取持仓列表

### 行情相关
- `POST /api/mt5/quote` - 批量获取报价
- `GET /api/mt5/price/{symbol}` - 获取最新价格
- `GET /api/mt5/kline/{symbol}` - 获取K线数据
- `GET /api/mt5/search/{keyword}` - 搜索股票
- `GET /api/mt5/symbol/{symbol}` - 获取股票详情

### 交易相关
- `POST /api/mt5/order` - 创建订单

## 💡 使用示例

### Python示例

```python
import requests

# 获取账户信息
response = requests.get("http://localhost:8000/api/mt5/account")
print(response.json())

# 获取股票价格
response = requests.get("http://localhost:8000/api/mt5/price/600000")
print(response.json())

# 创建买入订单
order_data = {
    "symbol": "600000",
    "name": "浦发银行",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 100,
    "use_mt5_platform": False  # True=MT5实盘，False=本地模拟
}
response = requests.post("http://localhost:8000/api/mt5/order", json=order_data)
print(response.json())
```

### cURL示例

```bash
# 获取账户信息
curl http://localhost:8000/api/mt5/account

# 获取K线数据
curl "http://localhost:8000/api/mt5/kline/600000?timeframe=D1&count=30"

# 创建订单
curl -X POST http://localhost:8000/api/mt5/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "600000",
    "name": "浦发银行",
    "side": "BUY",
    "quantity": 100,
    "order_type": "MARKET",
    "use_mt5_platform": false
  }'
```

## 🎯 交易规则

### A股交易限制
- 最小交易单位：100股（1手）
- 涨跌幅限制：±10%（ST股票±5%）
- 交易时间：
  - 9:30-11:30（上午）
  - 13:00-15:00（下午）
- T+1交易制度（当天买入次日才能卖出）

### 订单类型
- **市价单（MARKET）**：立即以当前价格成交
- **限价单（LIMIT）**：指定价格，价格到达时成交

## 🔄 模式切换

### 本地模拟模式（默认）
```python
{
    "use_mt5_platform": false
}
```
- 纯本地数据库模拟
- 不影响MT5账户
- 适合测试和学习

### MT5实盘模式
```python
{
    "use_mt5_platform": true
}
```
- 真实连接MT5平台
- 订单会发送到MT5
- 需要MT5账户有足够资金

## 🚨 风险提示

⚠️ **重要提醒**
- 本平台仅供学习和测试使用
- 强烈建议先使用模拟账户
- 投资有风险，入市需谨慎
- 不构成任何投资建议

## 📚 技术架构

```
FinAI MT5
├── backend/
│   ├── services/
│   │   ├── mt5_market_data.py      # MT5行情服务
│   │   └── mt5_order_executor.py   # MT5订单执行
│   ├── api/
│   │   └── mt5_routes.py           # MT5 API路由
│   └── database/
│       └── models.py                # 数据模型
├── start_mt5.py                     # 启动脚本
└── setup_mt5.py                     # 设置脚本
```

## 🔧 故障排查

### MT5连接失败
1. 确认MT5已启动并登录
2. 检查"允许自动交易"是否开启
3. 重启MT5终端

### 无法获取行情
1. 在MT5中手动添加股票代码
2. 确认股票代码格式正确
3. 检查网络连接

### 订单执行失败
1. 检查账户余额是否充足
2. 确认交易数量是100的倍数
3. 查看MT5日志获取详细错误

## 📞 技术支持

- 问题反馈：GitHub Issues
- 文档：README_MT5.md
- API文档：http://localhost:8000/docs

---

**免责声明**：本软件仅供教育和研究目的。使用本软件进行实际交易的风险由用户自行承担。
