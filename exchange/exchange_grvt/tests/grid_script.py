import os
import sys
import time
import yaml
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

# 添加项目根目录到 Python 路径，使脚本可以从任何目录运行
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.pysdk.grvt_ccxt import GrvtCcxt
from src.pysdk.grvt_ccxt_env import GrvtEnv
from src.pysdk.grvt_ccxt_types import PRICE_MULTIPLIER
from tests.risk_script import (
    check_time_permission,
    get_current_china_time,
    get_rsi_adx,
    load_time_rules_from_yaml,
)

# ADX风控状态：记录是否因为ADX过高而触发风控
_adx_risk_triggered = False

# CSV日志文件路径（按日期命名）
_log_file_path: Optional[Path] = None


def get_log_file_path() -> Path:
    """
    获取日志文件路径（按日期命名）
    
    Returns:
        日志文件路径
    """
    global _log_file_path
    if _log_file_path is None:
        script_dir = Path(__file__).parent
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = script_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        _log_file_path = log_dir / f"order_log_{today}.csv"
    return _log_file_path


def init_order_log() -> None:
    """
    初始化订单日志CSV文件（如果不存在则创建并写入表头）
    """
    log_file = get_log_file_path()
    
    # 如果文件不存在，创建并写入表头
    if not log_file.exists():
        with open(log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "时间戳",
                "操作类型",
                "交易对",
                "方向",
                "价格",
                "数量",
                "订单ID",
                "状态",
                "错误信息",
                "备注"
            ])


def log_order_operation(
    operation_type: str,
    symbol: str,
    side: Optional[str] = None,
    price: Optional[float] = None,
    amount: Optional[float] = None,
    order_id: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    notes: Optional[str] = None
) -> None:
    """
    记录订单操作到CSV文件
    
    Args:
        operation_type: 操作类型（下单/撤单/市价平仓/限价平仓/批量撤单）
        symbol: 交易对
        side: 方向（buy/sell），可选
        price: 价格，可选
        amount: 数量，可选
        order_id: 订单ID，可选
        status: 状态（success/failed）
        error_message: 错误信息，可选
        notes: 备注，可选
    """
    try:
        # 确保日志文件已初始化
        init_order_log()
        
        log_file = get_log_file_path()
        
        # 获取当前时间戳（精确到毫秒）
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # 准备数据行
        row = [
            timestamp,
            operation_type,
            symbol,
            side or "",
            f"{price:.2f}" if price is not None else "",
            f"{amount:.6f}" if amount is not None else "",
            order_id or "",
            status,
            error_message or "",
            notes or ""
        ]
        
        # 追加写入CSV文件
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
            
    except Exception as e:
        # 记录日志失败不应该影响主程序运行
        print(f"⚠️  记录订单日志失败: {e}")


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """
    从YAML配置文件加载配置
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
    
    Returns:
        配置字典
    """
    
    if config_path is None:
        # 默认配置文件路径
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.yaml"
    
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def get_auth_params(config: Dict[str, Any] | None = None) -> dict:
    """
    从环境变量或配置文件获取认证参数（优先使用环境变量）
    
    Args:
        config: 配置字典，如果为None则从配置文件加载
    
    Returns:
        包含认证信息的字典
    """
    # 优先使用环境变量
    trading_account_id = os.getenv("GRVT_TRADING_ACCOUNT_ID")
    api_key = os.getenv("GRVT_API_KEY")
    private_key = os.getenv("GRVT_PRIVATE_KEY")
    
    # 如果环境变量不存在，从配置文件读取
    if config is None:
        try:
            config = load_config()
        except Exception:
            config = {}
    
    auth_config = config.get("auth", {})
    
    if not trading_account_id:
        trading_account_id = auth_config.get("trading_account_id", "")
    if not api_key:
        api_key = auth_config.get("api_key", "")
    if not private_key:
        private_key = auth_config.get("private_key", "")
    
    params = {
        "trading_account_id": trading_account_id,
        "api_key": api_key,
    }
    if private_key:
        params["private_key"] = private_key
    
    return params


def get_btc_price(grvt: GrvtCcxt | None = None) -> float:
    """
    获取GRVT BTC当前价格
    
    Args:
        grvt: GrvtCcxt实例，如果为None则创建新实例
    
    Returns:
        BTC价格，如果获取失败返回0.0
    """
    try:
        if grvt is None:
            grvt = GrvtCcxt(env=GrvtEnv.PROD)
        
        ticker = grvt.fetch_ticker("BTC_USDT_Perp")
        
        # 处理返回的数据结构（可能是列表或字典）
        if isinstance(ticker, list) and len(ticker) > 0:
            ticker = ticker[0]
        
        # 获取价格（优先使用last_price，如果没有则使用mark_price）
        # 注意：API返回的价格已经是实际价格（字符串格式），不需要除以PRICE_MULTIPLIER
        price_str = ticker.get("last_price") or ticker.get("mark_price") or "0"
        return float(price_str) if price_str != "0" else 0.0
    except Exception as e:
        print(f"获取BTC价格失败: {e}")
        return 0.0


def round_down_to_interval(price: float, interval: float) -> float:
    """向下取整到最近的interval倍数"""
    return int(price // interval) * interval


def round_up_to_interval(price: float, interval: float) -> float:
    """向上取整到最近的interval倍数"""
    return int((price + interval - 1) // interval) * interval


def get_btc_position(grvt: GrvtCcxt) -> float:
    """
    获取账号当前BTC持仓
    
    Args:
        grvt: 已认证的GrvtCcxt实例
    
    Returns:
        BTC持仓数量，正数表示多头，负数表示空头，如果获取失败返回0.0
    """
    try:
        # 获取BTC持仓
        positions = grvt.fetch_positions(symbols=["BTC_USDT_Perp"])
        
        if positions and len(positions) > 0:
            # 获取第一个持仓的size（字符串格式）
            position = positions[0]
            size_str = position.get("size", "0")
            return float(size_str)
        
        # 如果没有持仓，返回0.0
        return 0.0
    except Exception as e:
        # 打印错误信息以便调试
        print(f"获取持仓失败: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def get_open_orders_prices(grvt: GrvtCcxt) -> tuple[list[int], list[int]]:
    """
    获取未成交订单的价格数组
    
    Args:
        grvt: 已认证的GrvtCcxt实例
    
    Returns:
        (多单未成交价格数组, 空单未成交价格数组)
    """
    try:
        # 获取BTC未成交订单
        open_orders = grvt.fetch_open_orders(
            symbol="BTC_USDT_Perp",
            params={"kind": "PERPETUAL"}
        )
        
        long_prices = []
        short_prices = []
        
        for order in open_orders:
            # 遍历订单的legs
            legs = order.get("legs", [])
            for leg in legs:
                # 检查是否是BTC_USDT_Perp订单
                instrument = leg.get("instrument", "")
                if instrument != "BTC_USDT_Perp":
                    continue
                
                # 获取限价价格
                limit_price_str = leg.get("limit_price")
                if not limit_price_str:
                    continue
                
                # 判断是多单还是空单
                is_buying = leg.get("is_buying_asset", False)
                
                # 转换价格（limit_price可能是字符串格式的实际价格，也可能需要除以PRICE_MULTIPLIER）
                try:
                    # 先尝试直接转换为float
                    price = float(limit_price_str)
                    # 如果价格很大（可能是乘以了PRICE_MULTIPLIER），则除以它
                    if price > 1000000:  # 如果价格超过100万，可能是需要除以PRICE_MULTIPLIER
                        price = price / PRICE_MULTIPLIER
                    price_int = int(price)
                    
                    if is_buying:
                        # 多单（买入）
                        if price_int not in long_prices:
                            long_prices.append(price_int)
                    else:
                        # 空单（卖出）
                        if price_int not in short_prices:
                            short_prices.append(price_int)
                except (ValueError, TypeError):
                    continue
        
        # 排序
        long_prices.sort()
        short_prices.sort()
        
        return long_prices, short_prices
    except Exception as e:
        print(f"获取未成交订单失败: {e}")
        import traceback
        traceback.print_exc()
        return [], []


def generate_grid_prices(
    current_price: float, 
    grid_count: int, 
    price_interval: float
) -> tuple[list[int], list[int]]:
    """
    生成网格价格数组（从最近到最远排序）
    
    Args:
        current_price: 当前价格
        grid_count: 网格总数（多单和空单各占一半）
        price_interval: 价格间隔
    
    Returns:
        (多单价格数组, 空单价格数组) - 都按距离当前价格从近到远排序
    """
    grid_half = grid_count // 2
    
    # 生成多单数组（买入价格，低于当前价格，从最近到最远）
    # 先找到第一个低于当前价格的网格价格
    first_long_price = round_down_to_interval(current_price, price_interval)
    if first_long_price >= current_price:
        first_long_price -= price_interval
    
    long_prices = []
    for i in range(grid_half):
        price = first_long_price - i * price_interval
        long_prices.append(int(price))
    
    # 生成空单数组（卖出价格，高于当前价格，从最近到最远）
    # 先找到第一个高于当前价格的网格价格
    first_short_price = round_up_to_interval(current_price, price_interval)
    if first_short_price <= current_price:
        first_short_price += price_interval
    
    short_prices = []
    for i in range(grid_half):
        price = first_short_price + i * price_interval
        short_prices.append(int(price))
    
    return long_prices, short_prices


def calculate_adjusted_grid_counts(
    current_position: float,
    order_size_btc: float,
    max_position_multiplier: int,
    grid_count: int
) -> tuple[int, int]:
    """
    根据当前持仓计算调整后的多空订单数量
    
    Args:
        current_position: 当前持仓（BTC）
        order_size_btc: 每个订单的开仓大小（BTC）
        max_position_multiplier: 最大持仓倍数
        grid_count: 网格总数
    
    Returns:
        (调整后的多单数量, 调整后的空单数量)
    """
    # 计算最大持仓
    max_position = max_position_multiplier * order_size_btc
    
    # 计算当前持仓与最大持仓占比
    current_pos = Decimal(str(current_position))
    max_pos = Decimal(str(max_position))
    
    ratio = (current_pos / max_pos) if max_pos > 0 else Decimal("0")
    
    # 计算偏移量（最大偏移50%）
    bias = ratio * Decimal("0.5")
    
    # 计算买/卖单数量
    base_half = Decimal(grid_count) / Decimal("2")
    buy_count = int(round(float(base_half - bias * Decimal(grid_count))))
    buy_count = max(0, min(grid_count, buy_count))
    sell_count = grid_count - buy_count
    
    return buy_count, sell_count


def calculate_order_arrays(
    grid_long_prices: list[int],
    grid_short_prices: list[int],
    open_long_prices: list[int],
    open_short_prices: list[int]
) -> tuple[list[int], list[int], list[int], list[int]]:
    """
    计算需下单和需撤单的数组

    Args:
        grid_long_prices: 网格多单价格数组
        grid_short_prices: 网格空单价格数组
        open_long_prices: 多单未成交价格数组
        open_short_prices: 空单未成交价格数组
    
    Returns:
        (需下单多单数组, 需下单空单数组, 需撤单多单数组, 需撤单空单数组)
    """
    # 转换为集合以便进行差集运算
    grid_long_set = set(grid_long_prices)
    grid_short_set = set(grid_short_prices)
    open_long_set = set(open_long_prices)
    open_short_set = set(open_short_prices)
    
    # 需下单数组：网格数组 - 未成交数组（差集）
    need_order_long = sorted(list(grid_long_set - open_long_set))
    need_order_short = sorted(list(grid_short_set - open_short_set))
    
    # 需撤单数组：未成交数组 - 网格数组（差集，即未成交数组中不在网格数组中的）
    need_cancel_long = sorted(list(open_long_set - grid_long_set))
    need_cancel_short = sorted(list(open_short_set - grid_short_set))
    
    return need_order_long, need_order_short, need_cancel_long, need_cancel_short


def load_and_parse_config() -> Tuple[Dict[str, Any], GrvtCcxt]:
    """加载配置并创建GrvtCcxt实例"""
    try:
        config = load_config()
    except Exception as e:
        print(f"加载配置文件失败: {e}，使用默认配置")
        config = {}
    
    auth_params = get_auth_params(config)
    grvt = GrvtCcxt(env=GrvtEnv.PROD, parameters=auth_params)
    return config, grvt


def close_all_positions_and_orders(grvt: GrvtCcxt, symbol: str = "BTC_USDT_Perp") -> None:
    """市价关闭所有持仓并取消所有挂单"""
    try:
        # 取消所有订单（参数格式：kind/base/quote应该是字符串，不是数组）
        cancel_params = {"kind": "PERPETUAL", "base": "BTC", "quote": "USDT"}
        if grvt.cancel_all_orders(params=cancel_params):
            print("已取消所有挂单")
            log_order_operation(
                operation_type="批量撤单",
                symbol=symbol,
                status="success",
                notes="风控触发，取消所有挂单"
            )
        
        # 获取当前持仓
        position = get_btc_position(grvt)
        if abs(position) < 0.0001:
            return
        
        # 创建reduce_only市价订单来关闭持仓（市价单不需要price参数）
        side = "sell" if position > 0 else "buy"
        amount = abs(position)
        
        try:
            order_response = grvt.create_order(
                symbol=symbol,
                order_type="market",
                side=side,
                amount=amount,
                params={"reduce_only": True}
            )
            
            # 获取订单ID
            order_id = None
            if isinstance(order_response, dict):
                order_id = order_response.get("id") or order_response.get("order_id") or \
                          order_response.get("metadata", {}).get("client_order_id")
            
            # 获取当前价格用于记录
            current_price = get_btc_price(grvt)
            
            print(f"已市价关闭持仓: {side} {amount:.6f} BTC")
            log_order_operation(
                operation_type="市价平仓",
                symbol=symbol,
                side=side,
                price=current_price,
                amount=amount,
                order_id=str(order_id) if order_id else None,
                status="success",
                notes=f"风控触发，市价平仓，原持仓: {position:.6f} BTC"
            )
        except Exception as order_err:
            error_msg = str(order_err)
            print(f"市价平仓失败: {error_msg}")
            log_order_operation(
                operation_type="市价平仓",
                symbol=symbol,
                side=side,
                amount=amount,
                status="failed",
                error_message=error_msg,
                notes=f"风控触发，市价平仓失败，原持仓: {position:.6f} BTC"
            )
            raise
        
    except Exception as e:
        print(f"关闭持仓和订单失败: {e}")
        log_order_operation(
            operation_type="市价平仓",
            symbol=symbol,
            status="failed",
            error_message=str(e),
            notes="关闭持仓和订单失败"
        )


def close_positions_with_limit_orders(grvt: GrvtCcxt, config: Dict[str, Any], symbol: str = "BTC_USDT_Perp") -> None:
    """
    使用限价单关闭持仓
    
    逻辑：
    1. 取消所有挂单
    2. 获取BTC价格和持仓
    3. 如果有持仓，挂限价单（多单用价格+offset，空单用价格-offset）
    4. 等待指定时间，检查是否成交
    5. 如果没成交，取消挂单，重新获取价格，重新挂单
    6. 循环直到持仓为0或达到最大重试次数
    """
    # 从配置中读取参数
    risk_config = config.get("risk", {})
    limit_order_config = risk_config.get("limit_order_close", {})
    price_offset = limit_order_config.get("price_offset", 5)
    wait_time = limit_order_config.get("wait_time", 30)
    max_retries = limit_order_config.get("max_retries", 10)
    
    try:
        # 取消所有订单
        cancel_params = {"kind": "PERPETUAL", "base": "BTC", "quote": "USDT"}
        grvt.cancel_all_orders(params=cancel_params)
        log_order_operation(
            operation_type="批量撤单",
            symbol=symbol,
            status="success",
            notes="时间风控触发，取消所有挂单"
        )
        
        retry_count = 0
        while retry_count < max_retries:
            # 获取当前持仓
            position = get_btc_position(grvt)
            if abs(position) < 0.0001:
                print("持仓已全部关闭")
                return
            
            # 获取当前价格
            btc_price = get_btc_price(grvt)
            if btc_price <= 0:
                print("获取BTC价格失败，无法关闭持仓")
                return
            
            # 确定方向和价格
            if position > 0:
                # 多单，需要卖出，限价单价格 = 当前价格 + offset
                side = "sell"
                limit_price = int(btc_price) + price_offset
            else:
                # 空单，需要买入，限价单价格 = 当前价格 - offset
                side = "buy"
                limit_price = int(btc_price) - price_offset
            
            amount = abs(position)
            
            # 创建限价单（reduce_only）
            try:
                order_response = grvt.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=limit_price,
                    params={"reduce_only": True}
                )
                print(f"已挂限价单关闭持仓: {side} {amount:.6f} BTC @ {limit_price}")
                
                # 获取订单ID（从metadata中获取client_order_id）
                client_order_id = None
                if isinstance(order_response, dict):
                    client_order_id = order_response.get("metadata", {}).get("client_order_id")
                    if not client_order_id:
                        # 如果没有metadata，尝试直接从response获取
                        client_order_id = order_response.get("client_order_id") or order_response.get("id")
                
                # 记录限价平仓订单
                log_order_operation(
                    operation_type="限价平仓",
                    symbol=symbol,
                    side=side,
                    price=limit_price,
                    amount=amount,
                    order_id=str(client_order_id) if client_order_id else None,
                    status="success",
                    notes=f"时间风控触发，限价平仓，原持仓: {position:.6f} BTC，重试次数: {retry_count + 1}/{max_retries}"
                )
                
                # 等待指定时间
                time.sleep(wait_time)
                
                # 检查持仓是否已关闭
                new_position = get_btc_position(grvt)
                if abs(new_position) < 0.0001:
                    print("持仓已通过限价单关闭")
                    log_order_operation(
                        operation_type="限价平仓",
                        symbol=symbol,
                        side=side,
                        price=limit_price,
                        amount=amount,
                        order_id=str(client_order_id) if client_order_id else None,
                        status="success",
                        notes="限价单已成交，持仓已全部关闭"
                    )
                    return
                
                # 如果持仓未关闭，取消刚才的订单
                if client_order_id:
                    try:
                        grvt.cancel_order(params={"client_order_id": str(client_order_id)})
                        log_order_operation(
                            operation_type="撤单",
                            symbol=symbol,
                            order_id=str(client_order_id),
                            status="success",
                            notes=f"限价单未成交，取消订单，剩余持仓: {new_position:.6f} BTC"
                        )
                    except Exception as cancel_err:
                        print(f"取消订单失败: {cancel_err}")
                        log_order_operation(
                            operation_type="撤单",
                            symbol=symbol,
                            order_id=str(client_order_id),
                            status="failed",
                            error_message=str(cancel_err),
                            notes="取消限价平仓订单失败"
                        )
                else:
                    # 如果无法获取订单ID，取消所有订单
                    try:
                        grvt.cancel_all_orders(params=cancel_params)
                    except Exception as cancel_err:
                        print(f"取消所有订单失败: {cancel_err}")
                
                print(f"限价单未成交，取消订单并重试 (剩余持仓: {new_position:.6f} BTC)")
                retry_count += 1
                
            except Exception as e:
                error_msg = str(e)
                print(f"创建限价单失败: {error_msg}")
                log_order_operation(
                    operation_type="限价平仓",
                    symbol=symbol,
                    side=side,
                    price=limit_price,
                    amount=amount,
                    status="failed",
                    error_message=error_msg,
                    notes=f"创建限价平仓订单失败，重试次数: {retry_count + 1}/{max_retries}"
                )
                retry_count += 1
                time.sleep(1)  # 短暂等待后重试
        
        print(f"达到最大重试次数 ({max_retries})，停止关闭持仓")
        log_order_operation(
            operation_type="限价平仓",
            symbol=symbol,
            status="failed",
            error_message=f"达到最大重试次数 {max_retries}",
            notes="限价平仓失败，已达到最大重试次数"
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"限价单关闭持仓失败: {error_msg}")
        log_order_operation(
            operation_type="限价平仓",
            symbol=symbol,
            status="failed",
            error_message=error_msg,
            notes="限价单关闭持仓失败"
        )


def check_risk_controls(config: Dict[str, Any], grvt: GrvtCcxt) -> bool:
    """
    执行风控检查

    Returns:
        True表示通过风控检查，False表示未通过
    """
    global _adx_risk_triggered
    
    risk_config = config.get("risk", {})
    enable_time_control = risk_config.get("enable_time_control", True)
    
    # 时间风控检查
    if enable_time_control:
        try:
            script_dir = Path(__file__).parent
            config_path = script_dir / "config.yaml"
            time_rules = load_time_rules_from_yaml(config_path)
            if not check_time_permission(time_rules):
                print("当前不在允许的交易时间内，暂停交易")
                close_positions_with_limit_orders(grvt, config)
                return False
        except Exception as e:
            print(f"⚠️  时间风控检查失败: {e}")
    
    # 指标风控检查
    indicator_control = risk_config.get("indicator_control", {})
    enable_indicator_control = indicator_control.get("enable", True)
    if enable_indicator_control:
        try:
            timeframe = indicator_control.get("timeframe", "15m")
            rsi_period = indicator_control.get("rsi_period", 14)
            adx_period = indicator_control.get("adx_period", 14)
            rsi_range = indicator_control.get("rsi_range", [30, 70])
            adx_max = indicator_control.get("adx_max", 30)
            # ADX恢复阈值，如果未配置则使用adx_max - 2作为默认值
            adx_recovery_threshold = indicator_control.get("adx_recovery_threshold", adx_max - 2)
            
            rsi, adx = get_rsi_adx(grvt, "BTC_USDT_Perp", timeframe, rsi_period, adx_period)
            if rsi is None or adx is None:
                print("无法获取RSI或ADX值，暂停交易")
                close_all_positions_and_orders(grvt)
                return False
            
            print(f"RSI: {rsi:.2f}, ADX: {adx:.2f} ({timeframe})")
            rsi_min, rsi_max = rsi_range[0], rsi_range[1]
            
            # 检查RSI
            rsi_ok = rsi_min <= rsi <= rsi_max
            
            # 检查ADX（带回撤机制）
            if _adx_risk_triggered:
                # 如果之前因为ADX触发风控，需要降到恢复阈值以下才能继续
                if adx < adx_recovery_threshold:
                    _adx_risk_triggered = False
                    print(f"ADX已恢复到{adx:.2f}，低于恢复阈值{adx_recovery_threshold}，解除风控")
                else:
                    print(f"ADX风控中: {adx:.2f} >= {adx_recovery_threshold}（恢复阈值），继续暂停交易")
                    close_all_positions_and_orders(grvt)
                    return False
            else:
                # 如果之前没有触发ADX风控，检查是否触发
                if adx >= adx_max:
                    _adx_risk_triggered = True
                    print(f"ADX触发风控: {adx:.2f} >= {adx_max}，需要降到{adx_recovery_threshold}以下才能恢复")
                    close_all_positions_and_orders(grvt)
                    return False
            
            # 如果RSI不符合条件，触发风控
            if not rsi_ok:
                print(f"指标不符合条件: RSI[{rsi_min}-{rsi_max}]={rsi:.2f}")
                close_all_positions_and_orders(grvt)
                return False
                
        except Exception as e:
            print(f"⚠️  指标风控检查失败: {e}")
    
    return True


def calculate_grid_orders(grvt: GrvtCcxt, config: Dict[str, Any]) -> Dict[str, Any]:
    """计算网格订单"""
    grid_config = config.get("grid", {})
    grid_count = grid_config.get("grid_count", 10)
    price_interval = grid_config.get("price_interval", 1500)
    order_size_btc = grid_config.get("order_size_btc", 0.001)
    max_position_multiplier = grid_config.get("max_position_multiplier", 6)
    min_price_distance = grid_config.get("min_price_distance", 10)
    
    btc_price = get_btc_price(grvt)
    btc_position = get_btc_position(grvt)
    max_position = max_position_multiplier * order_size_btc
    
    buy_count, sell_count = calculate_adjusted_grid_counts(
        btc_position, order_size_btc, max_position_multiplier, grid_count
    )
    
    # 根据实际需要的数量生成足够的网格价格
    max_needed = max(buy_count, sell_count, grid_count // 2)
    all_long_prices, all_short_prices = generate_grid_prices(btc_price, max_needed * 2, price_interval)
    
    # 取前N个（已经按距离从近到远排序）
    long_prices = all_long_prices[:buy_count]
    short_prices = all_short_prices[:sell_count]
    
    # 获取未成交订单
    open_long_prices, open_short_prices = get_open_orders_prices(grvt)
    
    # 先计算需要下单和撤单的数组（基于未过滤的网格价格）
    need_order_long, need_order_short, need_cancel_long, need_cancel_short = calculate_order_arrays(
        long_prices, short_prices, open_long_prices, open_short_prices
    )
    
    # 只对需要下单的数组进行过滤（撤单数组不过滤，因为已存在的订单即使距离太近也应该被撤掉）
    need_order_long = [p for p in need_order_long if abs(p - btc_price) >= min_price_distance]
    need_order_short = [p for p in need_order_short if abs(p - btc_price) >= min_price_distance]
    
    # 用于显示的网格价格数组（过滤后的）
    long_prices_filtered = [p for p in long_prices if abs(p - btc_price) >= min_price_distance]
    short_prices_filtered = [p for p in short_prices if abs(p - btc_price) >= min_price_distance]
    
    return {
        "btc_price": btc_price,
        "btc_position": btc_position,
        "max_position": max_position,
        "max_position_multiplier": max_position_multiplier,
        "min_price_distance": min_price_distance,
        "order_size_btc": order_size_btc,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "long_prices": long_prices_filtered,  # 使用过滤后的价格用于显示
        "short_prices": short_prices_filtered,  # 使用过滤后的价格用于显示
        "open_long_prices": open_long_prices,
        "open_short_prices": open_short_prices,
        "need_order_long": need_order_long,
        "need_order_short": need_order_short,
        "need_cancel_long": need_cancel_long,
        "need_cancel_short": need_cancel_short,
    }


def print_results(results: Dict[str, Any]) -> None:
    """打印结果"""
    print(f"最大持仓倍数：{results['max_position_multiplier']}")
    print(f"最大持仓：{results['max_position']:.3f} BTC")
    print(f"最小价格距离：{results['min_price_distance']}")
    print(f"持仓占比：{(results['btc_position'] / results['max_position'] * 100):.2f}%")
    print(f"调整后多单数量：{results['buy_count']}")
    print(f"调整后空单数量：{results['sell_count']}")
    print("")
    print(f"开仓大小：{results['order_size_btc']:.3f} BTC")
    print(f"当前BTC价格: {results['btc_price']:.2f}")
    print(f"当前持仓：{results['btc_position']:.3f} BTC")
    print("")
    print("多单数组:", results['long_prices'])
    print("空单数组:", results['short_prices'])
    print("多单未成交数组:", results['open_long_prices'])
    print("空单未成交数组:", results['open_short_prices'])
    print("需下单多单数组:", results['need_order_long'])
    print("需下单空单数组:", results['need_order_short'])
    print("需撤单多单数组:", results['need_cancel_long'])
    print("需撤单空单数组:", results['need_cancel_short'])


def cancel_orders_by_prices(grvt: GrvtCcxt, cancel_prices: list[int], is_long: bool, 
                            open_orders: list, symbol: str = "BTC_USDT_Perp") -> int:
    """根据价格取消订单"""
    if not cancel_prices:
        return 0
    
    cancel_prices_set = set(cancel_prices)
    orders_to_cancel = []  # [(order_id, price), ...]
    
    for order in open_orders:
        # 尝试多种可能的订单ID字段名
        order_id = order.get("id") or order.get("order_id") or order.get("client_order_id")
        if not order_id:
            continue
        
        legs = order.get("legs", [])
        for leg in legs:
            if leg.get("instrument", "") != symbol:
                continue
            
            is_buying = leg.get("is_buying_asset", False)
            if (is_long and not is_buying) or (not is_long and is_buying):
                continue
            
            limit_price_str = leg.get("limit_price")
            if not limit_price_str:
                continue
            
            try:
                price = float(limit_price_str)
                if price > 1000000:
                    price = price / PRICE_MULTIPLIER
                price_int = int(price)
                if price_int in cancel_prices_set:
                    orders_to_cancel.append((order_id, price_int))
                    break
            except (ValueError, TypeError):
                continue
    
    success_count = 0
    for order_id, price in orders_to_cancel:
        try:
            if grvt.cancel_order(id=order_id, symbol=symbol):
                print(f"取消挂单{price} 成功")
                log_order_operation(
                    operation_type="撤单",
                    symbol=symbol,
                    price=float(price),
                    order_id=str(order_id),
                    status="success",
                    notes=f"网格撤单，方向: {'多单' if is_long else '空单'}"
                )
                success_count += 1
            else:
                print(f"取消挂单{price} 失败: API返回False")
                log_order_operation(
                    operation_type="撤单",
                    symbol=symbol,
                    price=float(price),
                    order_id=str(order_id),
                    status="failed",
                    error_message="API返回False",
                    notes=f"网格撤单失败，方向: {'多单' if is_long else '空单'}"
                )
        except Exception as e:
            error_msg = str(e)
            print(f"取消挂单{price} 异常: {error_msg}")
            log_order_operation(
                operation_type="撤单",
                symbol=symbol,
                price=float(price),
                order_id=str(order_id),
                status="failed",
                error_message=error_msg,
                notes=f"网格撤单异常，方向: {'多单' if is_long else '空单'}"
            )
    
    return success_count


def place_orders(grvt: GrvtCcxt, results: Dict[str, Any], symbol: str = "BTC_USDT_Perp") -> tuple[int, int]:
    """下单逻辑"""
    order_size_btc = results['order_size_btc']
    need_order_long = results['need_order_long']
    need_order_short = results['need_order_short']
    
    success_long = 0
    success_short = 0
    
    for price in need_order_long:
        try:
            order_response = grvt.create_limit_order(symbol=symbol, side="buy", amount=order_size_btc, price=price)
            
            # 获取订单ID
            order_id = None
            if isinstance(order_response, dict):
                order_id = order_response.get("id") or order_response.get("order_id") or \
                          order_response.get("metadata", {}).get("client_order_id")
            
            print(f"下多单{price} 成功")
            log_order_operation(
                operation_type="下单",
                symbol=symbol,
                side="buy",
                price=float(price),
                amount=order_size_btc,
                order_id=str(order_id) if order_id else None,
                status="success",
                notes="网格多单"
            )
            success_long += 1
        except Exception as e:
            error_msg = str(e)
            print(f"下多单{price} 失败: {error_msg}")
            log_order_operation(
                operation_type="下单",
                symbol=symbol,
                side="buy",
                price=float(price),
                amount=order_size_btc,
                status="failed",
                error_message=error_msg,
                notes="网格多单失败"
            )
    
    for price in need_order_short:
        try:
            order_response = grvt.create_limit_order(symbol=symbol, side="sell", amount=order_size_btc, price=price)
            
            # 获取订单ID
            order_id = None
            if isinstance(order_response, dict):
                order_id = order_response.get("id") or order_response.get("order_id") or \
                          order_response.get("metadata", {}).get("client_order_id")
            
            print(f"下空单{price} 成功")
            log_order_operation(
                operation_type="下单",
                symbol=symbol,
                side="sell",
                price=float(price),
                amount=order_size_btc,
                order_id=str(order_id) if order_id else None,
                status="success",
                notes="网格空单"
            )
            success_short += 1
        except Exception as e:
            error_msg = str(e)
            print(f"下空单{price} 失败: {error_msg}")
            log_order_operation(
                operation_type="下单",
                symbol=symbol,
                side="sell",
                price=float(price),
                amount=order_size_btc,
                status="failed",
                error_message=error_msg,
                notes="网格空单失败"
            )
    
    return success_long, success_short


def execute_orders(grvt: GrvtCcxt, results: Dict[str, Any], symbol: str = "BTC_USDT_Perp") -> None:
    """执行下单和撤单"""
    need_order_long = results['need_order_long']
    need_order_short = results['need_order_short']
    need_cancel_long = results['need_cancel_long']
    need_cancel_short = results['need_cancel_short']
    
    # 撤单
    if need_cancel_long or need_cancel_short:
        try:
            open_orders = grvt.fetch_open_orders(symbol=symbol, params={"kind": "PERPETUAL"})
            cancel_orders_by_prices(grvt, need_cancel_long, True, open_orders, symbol)
            cancel_orders_by_prices(grvt, need_cancel_short, False, open_orders, symbol)
        except Exception as e:
            print(f"撤单失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 下单
    if need_order_long or need_order_short:
        try:
            place_orders(grvt, results, symbol)
        except Exception as e:
            print(f"下单失败: {e}")


def main():
    """主函数 - 无限循环执行网格交易逻辑"""
    config, grvt = load_and_parse_config()
    
    # 初始化订单日志
    init_order_log()
    log_file = get_log_file_path()
    print(f"订单日志文件: {log_file}")
    
    # 从配置读取循环间隔（秒），默认60秒
    loop_interval = config.get("loop_interval", 60)
    
    print(f"网格交易程序启动，循环间隔: {loop_interval}秒")
    print("=" * 50)
    
    while True:
        try:
            if not check_risk_controls(config, grvt):
                print(f"风控检查未通过，等待 {loop_interval} 秒后重试...")
                time.sleep(loop_interval)
                continue
            
            results = calculate_grid_orders(grvt, config)
            print_results(results)
            execute_orders(grvt, results)
            
            print(f"\n等待 {loop_interval} 秒后继续...")
            print("=" * 50)
            time.sleep(loop_interval)
            
        except KeyboardInterrupt:
            print("\n程序被用户中断，退出...")
            break
        except Exception as e:
            print(f"\n执行出错: {e}")
            print(f"等待 {loop_interval} 秒后重试...")
            import traceback
            traceback.print_exc()
            time.sleep(loop_interval)


if __name__ == "__main__":
    main()

