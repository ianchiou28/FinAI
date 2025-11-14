# FinAI - 多平台AI交易系统

支持多个交易平台的AI驱动交易系统，包括Interactive Brokers、MT5等，提供实时市场数据、智能交易执行和投资组合管理。

## 🚀 快速开始

### MT5版本（A股模拟交易）⭐ 新增
```bash
# 1. 安装依赖
pip install -r requirements_mt5.txt

# 2. 设置MT5连接
python backend/setup_mt5.py

# 3. 启动平台
python start_mt5.py
```

### IBKR版本（美股）
```bash
# 1. 设置IBKR连接
python backend/setup_ibkr.py

# 2. 启动平台
python start_ibkr.py
```

### 原版本（加密货币）
```bash
# 启动原版本
python backend/main.py
```

## 📋 系统要求

### MT5版本
- Python 3.10+
- MetaTrader 5 终端
- Windows 操作系统
- 模拟账户（推荐用于测试）

### IBKR版本
- Python 3.10+
- Interactive Brokers TWS或IB Gateway
- Paper Trading账户（推荐用于测试）

## 🛠️ 安装步骤

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 设置Interactive Brokers
1. 下载并安装TWS或IB Gateway
2. 登录Paper Trading账户
3. 启用API连接（配置 → API → 启用ActiveX和Socket客户端）
4. 设置可信IP：127.0.0.1

### 3. 运行设置
```bash
python backend/setup_ibkr.py
```

### 4. 启动平台
```bash
python start_ibkr.py
```

## 🔧 主要功能

### MT5版本特性
- **A股市场**: 支持沪深A股交易
- **交易规则**: 100股起、T+1、涨跌停限制
- **费用计算**: 佣金+印花税+过户费
- **实时行情**: 分钟级到月线K线数据
- **双模式**: 本地模拟 + MT5实盘对接

### 通用功能
- **实时市场数据**: 股票价格、K线图、账户信息
- **智能交易**: 市价单、限价单等多种订单类型
- **投资组合管理**: 实时持仓跟踪和风险管理
- **模拟交易**: 安全的模拟交易环境
- **Web界面**: 现代化React前端

## 📊 API端点

- `GET /api/market/price/{symbol}` - 获取股票价格
- `POST /api/orders/create` - 创建交易订单
- `GET /api/market/account` - 获取账户信息
- `GET /api/market/positions` - 获取持仓信息

## 🚨 风险提示

本平台仅供学习和测试使用。强烈建议先在Paper Trading环境中测试。投资有风险，入市需谨慎。

## 📚 文档

- [MT5 A股文档](README_MT5.md) ⭐ 新增
- [IBKR详细文档](README_IBKR_UPDATED.md)
- [原版本文档](README_FUTU.md)

---

**免责声明**: 本软件仅供教育和研究目的。使用本软件进行实际交易的风险由用户自行承担。