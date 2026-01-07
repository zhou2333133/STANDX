# GRVT和Variational交易所页面打开工具

这个工具可以同时打开GRVT和Variational两个交易所的交易对页面，使用morelogin管理浏览器环境。

## 功能

- 使用YAML配置文件管理环境ID和交易对
- 同时打开GRVT和Variational交易所页面
- 自动复用已打开的页面，避免重复打开
- 支持通过命令行参数指定配置文件

## 使用方法

### 1. 安装依赖

```bash
pip install playwright pyyaml requests
playwright install chromium
```

### 2. 配置环境ID

编辑 `config.yaml` 文件，填写你的morelogin环境ID：

```yaml
grvt_env_id: "your_grvt_env_id_here"
var_env_id: "your_var_env_id_here"
symbol: "BTC"
```

### 3. 运行脚本

```bash
# 使用默认配置文件 config.yaml
python open_exchanges.py

# 或指定自定义配置文件
python open_exchanges.py -c my_config.yaml
```

## 配置文件说明

- `grvt_env_id`: GRVT交易所的morelogin环境ID
- `var_env_id`: Variational交易所的morelogin环境ID
- `symbol`: 交易对符号（如BTC、ETH等）

## URL格式

- GRVT: `https://grvt.io/exchange/perpetual/{SYMBOL}-USDT`
- Variational: `https://omni.variational.io/perpetual/{SYMBOL}`

## 注意事项

- 确保morelogin客户端正在运行（默认端口40000）
- 确保环境ID正确且有效
- 程序会保持运行状态，按Ctrl+C退出
