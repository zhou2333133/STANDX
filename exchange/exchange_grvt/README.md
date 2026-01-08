# Grid Trading Script 使用教程

本文档介绍如何使用 `grid_script.py` 进行网格交易。

## 目录

- [功能概述](#功能概述)
- [系统要求](#系统要求)
- [Linux 使用教程](#linux-使用教程)
- [Windows 使用教程](#windows-使用教程)
- [配置文件说明](#配置文件说明)
- [环境变量配置](#环境变量配置)
- [运行脚本](#运行脚本)
- [常见问题](#常见问题)
- [自成交脚本使用教程](#自成交脚本使用教程)

## 功能概述

`grid_script.py` 是一个自动化网格交易脚本，具有以下功能：

- **网格交易**：自动在价格网格上挂买单和卖单
- **动态调整**：根据当前持仓自动调整多空订单比例
- **风险控制**：
  - 时间控制：只在指定时间段内交易
  - 指标控制：基于 RSI 和 ADX 指标控制交易
  - ADX 回撤机制：ADX 触发风控后需降至恢复阈值才能继续交易
- **自动下单**：自动下单和撤单，保持网格订单状态

## 系统要求

- Python 3.10 或更高版本
- 网络连接（用于访问 GRVT API）
- GRVT 交易账户和 API 凭证

---

## Linux 使用教程

### 1. 检查 Python 版本

```bash
python3 --version
# 或
python --version
```

确保版本 >= 3.10。

### 2. 创建虚拟环境（venv）

```bash
# 进入项目目录
cd /grvt-pysdk-main

# 创建虚拟环境（推荐在项目根目录）
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

激活后，命令行提示符前会显示 `(venv)`。

### 3. 安装依赖

```bash
# 确保虚拟环境已激活（看到 (venv) 前缀）
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 配置 API 凭证

有两种方式配置 API 凭证：

#### 方式一：使用环境变量（推荐）

```bash
# 在激活的虚拟环境中设置环境变量
export GRVT_TRADING_ACCOUNT_ID="your_trading_account_id"
export GRVT_API_KEY="your_api_key"
export GRVT_PRIVATE_KEY="your_private_key"
```

#### 方式二：编辑配置文件

编辑 `tests/config.yaml`，在 `auth` 部分填入你的凭证：

```yaml
auth:
  trading_account_id: "your_trading_account_id"
  api_key: "your_api_key"
  private_key: "your_private_key"
```

### 5. 配置交易参数

编辑 `tests/config.yaml`，根据你的需求调整参数：

- `loop_interval`: 循环间隔（秒）
- `grid.grid_count`: 网格数量
- `grid.price_interval`: 价格间隔
- `grid.order_size_btc`: 每个订单的开仓大小
- `grid.max_position_multiplier`: 最大持仓倍数
- `risk`: 风险控制配置

详细配置说明见 [配置文件说明](#配置文件说明)。

### 6. 运行脚本

```bash
# 确保虚拟环境已激活
cd tests
python grid_script.py
```

### 7. 停止脚本

按 `Ctrl + C` 停止脚本。

### 8. 退出虚拟环境

```bash
deactivate
```

---

## Windows 使用教程

### 1. 检查 Python 版本

打开 **命令提示符（CMD）** 或 **PowerShell**：

```cmd
python --version
```

确保版本 >= 3.10。如果提示找不到 `python`，尝试 `py --version`。

### 2. 创建虚拟环境（venv）

```cmd
# 进入项目目录（使用你的实际路径）
cd D:\Documents\GitHub\grvt-pysdk-main

# 创建虚拟环境
python -m venv venv
# 或使用 py 命令
py -m venv venv
```

### 3. 激活虚拟环境

#### 在 CMD 中：

```cmd
venv\Scripts\activate.bat
```

#### 在 PowerShell 中：

```powershell
venv\Scripts\Activate.ps1
```

如果 PowerShell 执行策略限制，需要先运行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

激活后，命令行提示符前会显示 `(venv)`。

### 4. 安装依赖

```cmd
# 确保虚拟环境已激活（看到 (venv) 前缀）
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. 配置 API 凭证

有两种方式配置 API 凭证：

#### 方式一：使用环境变量（推荐）

**在 CMD 中：**

```cmd
set GRVT_TRADING_ACCOUNT_ID=your_trading_account_id
set GRVT_API_KEY=your_api_key
set GRVT_PRIVATE_KEY=your_private_key
```

**在 PowerShell 中：**

```powershell
$env:GRVT_TRADING_ACCOUNT_ID="your_trading_account_id"
$env:GRVT_API_KEY="your_api_key"
$env:GRVT_PRIVATE_KEY="your_private_key"
```

**永久设置（推荐）：**

1. 右键点击"此电脑" → "属性"
2. 点击"高级系统设置"
3. 点击"环境变量"
4. 在"用户变量"或"系统变量"中添加：
   - `GRVT_TRADING_ACCOUNT_ID`
   - `GRVT_API_KEY`
   - `GRVT_PRIVATE_KEY`

#### 方式二：编辑配置文件

编辑 `tests\config.yaml`，在 `auth` 部分填入你的凭证：

```yaml
auth:
  trading_account_id: "your_trading_account_id"
  api_key: "your_api_key"
  private_key: "your_private_key"
```

### 6. 配置交易参数

编辑 `tests\config.yaml`，根据你的需求调整参数。详细配置说明见 [配置文件说明](#配置文件说明)。

### 7. 运行脚本

```cmd
# 确保虚拟环境已激活
cd tests
python grid_script.py
```

### 8. 停止脚本

按 `Ctrl + C` 停止脚本。

### 9. 退出虚拟环境

```cmd
deactivate
```

---

## 配置文件说明

配置文件 `tests/config.yaml` 包含以下主要配置项：

### 循环间隔

```yaml
loop_interval: 3  # 每次循环的间隔时间（秒）
```

### 网格交易配置

```yaml
grid:
  grid_count: 10              # 网格数量（多单和空单各占一半）
  price_interval: 20          # 价格间隔（USDT）
  order_size_btc: 0.001      # 每个订单的开仓大小（BTC）
  max_position_multiplier: 6  # 最大持仓倍数
  min_price_distance: 5      # 最小价格距离，过滤掉距离当前价格太近的订单
```

### 风险控制配置

#### 时间控制

```yaml
risk:
  enable_time_control: true
  time_rules:
    0:  # 周一
      - "12:00-21:00"
    1:  # 周二
      - "12:00-21:00"
    # ... 其他日期
```

#### 指标控制

```yaml
risk:
  indicator_control:
    enable: true
    timeframe: "5m"           # K线时间周期（5m, 15m, 30m, 1h, 4h, 1d等）
    rsi_period: 14            # RSI计算周期
    adx_period: 14            # ADX计算周期
    rsi_range: [30, 70]       # RSI允许范围 [min, max]
    adx_max: 30               # ADX最大阈值（ADX必须小于此值）
    adx_recovery_threshold: 28  # ADX恢复阈值（触发风控后需降到这个值以下才能继续交易）
```

**ADX 回撤机制说明：**

- 当 ADX >= `adx_max`（例如 30）时，触发风控，立即关闭所有持仓和订单
- 触发风控后，即使 ADX 降到 30 以下，也需要降到 `adx_recovery_threshold`（例如 28）以下才能恢复交易
- 这避免了在临界值附近频繁触发和解除风控

---

## 环境变量配置

脚本优先使用环境变量中的 API 凭证，如果环境变量未设置，则使用配置文件中的值。

### Linux / macOS

```bash
export GRVT_TRADING_ACCOUNT_ID="your_trading_account_id"
export GRVT_API_KEY="your_api_key"
export GRVT_PRIVATE_KEY="your_private_key"
```

### Windows CMD

```cmd
set GRVT_TRADING_ACCOUNT_ID=your_trading_account_id
set GRVT_API_KEY=your_api_key
set GRVT_PRIVATE_KEY=your_private_key
```

### Windows PowerShell

```powershell
$env:GRVT_TRADING_ACCOUNT_ID="your_trading_account_id"
$env:GRVT_API_KEY="your_api_key"
$env:GRVT_PRIVATE_KEY="your_private_key"
```

---

## 运行脚本

### 基本运行

脚本可以从项目根目录或 `tests` 目录运行：

```bash
# Linux / macOS - 方式一：从项目根目录运行（推荐）
python3 tests/grid_script.py

# Linux / macOS - 方式二：从 tests 目录运行
cd tests
python3 grid_script.py

# Windows - 方式一：从项目根目录运行（推荐）
python tests\grid_script.py

# Windows - 方式二：从 tests 目录运行
cd tests
python grid_script.py
```

### 后台运行（Linux / macOS）

使用 `nohup` 或 `screen` / `tmux`：

```bash
# 使用 nohup（从项目根目录）
nohup python3 tests/grid_script.py > grid_trading.log 2>&1 &

# 使用 screen
screen -S Grvt-MM    # 创建一个命名会话
cd /path/to/grvt-pysdk-main  # 替换为你的项目路径
python3 tests/grid_script.py
Ctrl+A, 然后按 D                # 脱离会话（后台运行）
screen -r Grvt-MM    # 重新进入会话
screen -XS  885686 quit  # 退出会话
screen -ls						# 列出所有会话
# 重新连接：screen -r Grvt-MM

# 使用 tmux
tmux new -s grid_trading
cd /path/to/grvt-pysdk-main  # 替换为你的项目路径
python3 tests/grid_script.py
# 按 Ctrl+B 然后按 D 分离会话
# 重新连接：tmux attach -t grid_trading
```

### Windows 后台运行

可以使用任务计划程序或第三方工具，或者使用 PowerShell 后台作业：

```powershell
Start-Job -ScriptBlock { cd D:\path\to\tests; python grid_script.py }
```

---

## 常见问题

### 1. 虚拟环境激活失败

**Linux / macOS：**
```bash
# 确保使用正确的激活命令
source venv/bin/activate
```

**Windows：**
```cmd
# CMD
venv\Scripts\activate.bat

# PowerShell
venv\Scripts\Activate.ps1
# 如果提示执行策略限制，运行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. 找不到模块错误

#### ModuleNotFoundError: No module named 'src'

**问题：** 如果看到 `ModuleNotFoundError: No module named 'src'` 错误

**解决方案：**
- 脚本已修复，现在可以从项目根目录或 `tests` 目录运行
- 确保虚拟环境已激活
- 确保已安装所有依赖：`pip install -r requirements.txt`
- 推荐从项目根目录运行：`python tests/grid_script.py` 或 `python3 tests/grid_script.py`

#### ZoneInfoNotFoundError: No timezone found with key 'Asia/Shanghai' (Windows)

**问题：** 在 Windows 上运行时出现时区错误

**解决方案：**
```cmd
# 安装 tzdata 包（Windows 上使用 zoneinfo 需要）
pip install tzdata
```

或者重新安装所有依赖：
```cmd
pip install -r requirements.txt
```

### 3. API 认证失败

检查：
- 环境变量或配置文件中的 API 凭证是否正确
- API 凭证是否有交易权限
- 网络连接是否正常

### 4. 配置文件找不到

确保 `config.yaml` 文件在 `tests/` 目录下。脚本会自动查找 `tests/config.yaml`，无论从哪个目录运行都可以。

### 5. 权限错误（Linux）

如果遇到权限错误，可能需要：

```bash
chmod +x grid_script.py
```

### 6. 脚本运行后立即退出

检查：
- 配置文件格式是否正确（YAML 语法）
- 是否在允许的交易时间内（如果启用了时间控制）
- 指标是否满足条件（如果启用了指标控制）

### 7. 订单未执行

检查：
- 账户余额是否充足
- 价格是否合理（不会立即成交）
- API 权限是否包含下单权限

---

## 注意事项

1. **风险提示**：网格交易存在风险，请谨慎使用，建议先用小额资金测试。

2. **API 安全**：不要将 API 凭证提交到版本控制系统（如 Git）。建议使用环境变量。

3. **网络稳定性**：确保网络连接稳定，脚本需要持续访问 API。

4. **监控运行**：建议定期检查脚本运行状态和交易情况。

5. **配置备份**：修改配置前建议备份原配置文件。

---

## 自成交前端脚本使用教程

`Example/zcj.py` 是一个自动化自成交脚本，用于在多个账户之间进行自成交操作。需要用到morelogin的API，如果还没有morelogin账号，可以先注册：
https://www.morelogin.com/register/?from=Dazmon

### 功能概述

- **多账户管理**：支持同时管理多个 MoreLogin 浏览器环境
- **自动持仓检查**：通过 UI 自动检查账户持仓情况
- **智能下单**：根据持仓情况自动下限价单和市价单
- **自动平仓**：最后一个环境自动限价平仓
- **未成交订单管理**：自动取消未成交订单

### 系统要求

- Python 3.10 或更高版本
- MoreLogin 客户端已安装并登录
- Playwright 浏览器驱动已安装
- GRVT 交易账户和 API 凭证

### 安装 Playwright

```bash
# 安装 playwright 包
pip install playwright


### 配置文件设置

配置 `Example/config.yaml` 文件：

```yaml
# 环境ID列表（MoreLogin环境ID）
env_ids:
  - "2006316431742406656"
  - "2006316431671103488"

# 交易对配置
trading_pair: "XPL-USDT"

# API配置
api:
  base_url: "http://localhost:40000"
  timeout: 10
  close_timeout: 2

# 浏览器配置
browser:
  page_load_timeout: 30000
  wait_until: "domcontentloaded"

# 等待时间配置（秒）
delays:
  after_browser_start: 1
  between_profiles: 0.5

# 交易配置
trading:
  price_offset: 0.0001      # 限价单价格偏移量
  amount: 30                # 交易数量
  position_check_interval: 3  # 持仓检查间隔（每N次循环检查一次）
```

**配置说明：**
- `env_ids`: MoreLogin 环境ID列表，至少需要2个环境ID
- `trading_pair`: 交易对，例如 "XPL-USDT", "BTC-USDT" 等
- `api.base_url`: MoreLogin API 地址（默认：`http://localhost:40000`）
- `trading.price_offset`: 限价单价格偏移量
- `trading.amount`: 交易数量
- `trading.position_check_interval`: 持仓检查间隔（每N次循环检查一次）

### 运行脚本

#### Linux / macOS

```bash
# 确保虚拟环境已激活
cd Example
python3 zcj.py
```

#### Windows

```cmd
# 确保虚拟环境已激活
cd Example
python zcj.py
```

### 脚本工作流程

1. **启动环境**：自动打开配置文件中指定的所有 MoreLogin 环境
2. **打开交易页面**：在每个环境中打开指定的交易对页面
3. **循环检查持仓**：
   - 每 N 次循环（由 `position_check_interval` 配置）检查一次持仓
   - 遍历所有环境，获取每个环境的持仓情况
4. **自动下单**：
   - **非最后环境**：如果持仓不为0，当前环境下限价单，下一个环境下市价单（方向相反）
   - **最后环境**：如果持仓不为0，先取消所有未成交订单，然后下限价单平仓
5. **持续运行**：脚本会持续运行，直到按 `Ctrl+C` 停止

### 交易逻辑示例

假设有 4 个环境，持仓情况为：`[30, 60, 0, -100]`

1. **环境1（30）**：限价空单30，环境2市价多单30 → `[0, 90, 0, -100]`
2. **环境2（90）**：限价空单90，环境3市价多单90 → `[0, 0, 90, -100]`
3. **环境3（90）**：限价空单90，环境4市价多单90 → `[0, 0, 0, -10]`
4. **环境4（-10）**：限价多单10平仓 → `[0, 0, 0, 0]`

### 注意事项

1. **MoreLogin 客户端**：确保 MoreLogin 客户端已启动并成功登录
2. **环境数量**：至少需要 2 个环境ID才能运行
3. **网络稳定性**：确保网络连接稳定，脚本需要持续访问 MoreLogin API
4. **配置安全**：不要将包含真实环境ID的 `config.yaml` 提交到版本控制系统，建议使用 `.gitignore` 忽略或使用 `config.yaml.example` 作为模板
5. **交易风险**：自成交存在风险，请谨慎使用，建议先用小额资金测试

### 常见问题

#### 1. 无法连接到 MoreLogin API

**问题：** 提示 `无法连接到 MoreLogin API`

**解决方案：**
- 确保 MoreLogin 客户端已启动
- 确保 MoreLogin 客户端已成功登录
- 检查 `config.yaml` 中的 `api.base_url` 是否正确（默认：`http://localhost:40000`）

#### 2. Playwright 相关错误

**问题：** `ModuleNotFoundError: No module named 'playwright'`

**解决方案：**
```bash
pip install playwright
playwright install
```

#### 3. 环境打开失败

**问题：** 部分环境无法打开

**解决方案：**
- 检查 MoreLogin 环境ID是否正确
- 确保环境在 MoreLogin 中可用
- 检查网络连接

#### 4. 持仓检查失败

**问题：** 持仓检查返回 None 或失败

**解决方案：**
- 确保交易对配置正确
- 检查页面是否正常加载
- 查看错误日志了解具体原因

---

## 技术支持

如有问题，请查看：
- 项目 GitHub Issues
- GRVT API 文档
- Python 官方文档

---

**祝交易顺利！** 🚀

