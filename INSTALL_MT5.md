# MT5 A股模拟交易平台安装指南

## 📦 环境准备

### 1. 系统要求
- Windows 10/11（MT5官方仅支持Windows）
- Python 3.10 或更高版本
- 至少 4GB RAM
- 稳定的网络连接

### 2. 安装MetaTrader 5

#### 下载MT5
1. 访问官网：https://www.metatrader5.com/zh/download
2. 下载Windows版本
3. 运行安装程序并完成安装

#### 注册模拟账户
1. 启动MT5终端
2. 点击"文件" → "开设模拟账户"
3. 选择券商服务器（建议选择支持A股的券商）
4. 填写个人信息并提交
5. 记录账号和密码

#### 配置MT5
1. 登录模拟账户
2. 点击"工具" → "选项"
3. 切换到"EA交易"选项卡
4. 勾选"允许自动交易"
5. 勾选"允许DLL导入"
6. 点击"确定"保存

### 3. 添加A股股票

#### 方法1：通过市场观察窗口
1. 在MT5中按 `Ctrl+M` 打开市场观察窗口
2. 右键点击空白处 → "显示全部"
3. 搜索A股代码（如：600000、000001）
4. 双击添加到列表

#### 方法2：通过搜索
1. 按 `Ctrl+F` 打开搜索
2. 输入股票代码或名称
3. 选择并添加

#### 常用A股代码
```
600000 - 浦发银行
600519 - 贵州茅台
000001 - 平安银行
000002 - 万科A
600036 - 招商银行
601318 - 中国平安
```

## 🐍 Python环境配置

### 1. 安装Python依赖

```bash
# 进入项目目录
cd FinAI

# 安装MT5专用依赖
pip install -r requirements_mt5.txt
```

### 2. 验证安装

```python
# 测试MT5连接
python -c "import MetaTrader5 as mt5; print('MT5版本:', mt5.__version__)"
```

## 🚀 平台设置

### 1. 运行设置脚本

```bash
python backend/setup_mt5.py
```

设置脚本会：
- ✅ 测试MT5连接
- ✅ 创建数据库表
- ✅ 初始化模拟账户（100万初始资金）
- ✅ 验证行情数据

### 2. 预期输出

```
============================================================
MT5 A股模拟交易平台设置
============================================================

[1/4] 初始化MT5连接...
✓ MT5连接成功

[2/4] 获取MT5账户信息...
✓ 账户登录: 12345678
  服务器: Demo-Server
  余额: 100000.00 USD
  净值: 100000.00 USD

[3/4] 创建数据库表...
✓ 数据库表创建成功

[4/4] 创建A股模拟账户...
✓ A股账户创建成功 (ID: 1)
  初始资金: ¥1,000,000.00

[测试] 获取股票行情...
✓ 600000: ¥8.52
✓ 000001: ¥12.34
✓ 600519: ¥1,680.00

============================================================
✓ MT5 A股模拟交易平台设置完成！
============================================================
```

## 🎯 启动平台

### 1. 启动后端服务

```bash
python start_mt5.py
```

### 2. 访问服务

- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 3. 启动前端（可选）

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

## 🧪 测试功能

### 1. 运行示例脚本

```bash
python backend/example_mt5_trading.py
```

选择示例：
1. 获取市场数据
2. 模拟交易
3. 查看持仓

### 2. API测试

#### 获取账户信息
```bash
curl http://localhost:8000/api/mt5/account
```

#### 获取股票价格
```bash
curl http://localhost:8000/api/mt5/price/600000
```

#### 创建买入订单
```bash
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

## 🔧 常见问题

### Q1: MT5初始化失败
**错误**: `MT5初始化失败: (1, 'Terminal: no IPC connection')`

**解决方案**:
1. 确认MT5终端已启动
2. 确认已登录账户
3. 重启MT5终端
4. 以管理员身份运行Python脚本

### Q2: 无法获取股票行情
**错误**: `无法获取600000价格`

**解决方案**:
1. 在MT5中手动添加该股票代码
2. 确认股票代码格式正确（6位数字）
3. 检查MT5是否连接到服务器
4. 确认市场是否开盘

### Q3: 订单执行失败
**错误**: `现金不足`

**解决方案**:
1. 检查账户余额：`GET /api/mt5/account`
2. 减少交易数量
3. 确认数量是100的倍数

### Q4: 端口被占用
**错误**: `Address already in use`

**解决方案**:
```bash
# Windows查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### Q5: Python依赖安装失败
**错误**: `Failed building wheel for MetaTrader5`

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements_mt5.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 📊 性能优化

### 1. 数据库优化
```bash
# 定期清理旧数据
sqlite3 backend/data.db "DELETE FROM trades WHERE created_at < date('now', '-30 days');"
```

### 2. MT5连接优化
- 保持MT5终端运行
- 避免频繁初始化连接
- 使用连接池管理

### 3. 内存优化
- 限制K线数据查询数量
- 定期清理缓存
- 使用分页查询

## 🔒 安全建议

1. **不要在生产环境使用模拟账户**
2. **定期备份数据库**
   ```bash
   copy backend\data.db backup\data_backup_%date%.db
   ```
3. **限制API访问**
   - 配置防火墙规则
   - 使用API密钥认证
4. **监控异常交易**
   - 设置交易限额
   - 启用交易日志

## 📚 下一步

- 阅读 [README_MT5.md](README_MT5.md) 了解详细功能
- 查看 [API文档](http://localhost:8000/docs) 学习接口使用
- 运行 [example_mt5_trading.py](backend/example_mt5_trading.py) 体验交易流程
- 开发自己的交易策略

## 💬 获取帮助

- 查看文档：README_MT5.md
- 提交问题：GitHub Issues
- 技术支持：查看API文档

---

**祝你使用愉快！** 🎉
