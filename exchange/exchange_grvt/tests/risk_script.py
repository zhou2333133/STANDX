"""风险控制脚本"""

import os
import yaml
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from src.pysdk.grvt_ccxt import GrvtCcxt
from src.pysdk.grvt_ccxt_env import GrvtEnv
from src.pysdk.grvt_ccxt_types import PRICE_MULTIPLIER


# 中国时区
CHINA_TZ = ZoneInfo('Asia/Shanghai')


def is_in_time_range(
    current_time: datetime,
    time_rules: Dict[int, List[Tuple[time, time]]]
) -> bool:
    """
    判断当前时间是否在允许的时间范围内
    Returns:
        True表示在允许的时间范围内，False表示不在
    """
    # 转换为中国时区
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=CHINA_TZ)
    else:
        current_time = current_time.astimezone(CHINA_TZ)
    
    # 获取当前是周几（0=周一, 1=周二, ..., 6=周日）
    weekday = current_time.weekday()
    
    # 获取当前时间（只取时分秒）
    current_time_only = current_time.time()
    
    # 检查是否有该周几的规则
    if weekday not in time_rules:
        return False
    
    # 检查当前时间是否在任何一个时间段内
    for start_time, end_time in time_rules[weekday]:
        if start_time <= current_time_only <= end_time:
            return True
    
    return False


def get_current_china_time() -> datetime:
    """
    获取当前中国时间
    
    Returns:
        当前中国时间的datetime对象
    """
    return datetime.now(CHINA_TZ)


def check_time_permission(time_rules: Dict[int, List[Tuple[time, time]]]) -> bool:
    """
    检查当前时间是否有交易权限
    
    Args:
        time_rules: 时间规则字典
    
    Returns:
        True表示有权限，False表示无权限
    """
    current_time = get_current_china_time()
    return is_in_time_range(current_time, time_rules)


def parse_time_range(time_str: str) -> Tuple[time, time]:
    """
    解析时间范围字符串，格式为 "HH:MM-HH:MM"
    
    Args:
        time_str: 时间范围字符串，如 "10:00-12:00"
    
    Returns:
        (开始时间, 结束时间) 元组
    """
    start_str, end_str = time_str.split("-")
    start_hour, start_min = map(int, start_str.split(":"))
    end_hour, end_min = map(int, end_str.split(":"))
    return time(start_hour, start_min), time(end_hour, end_min)


def load_time_rules_from_yaml(config_path: str | Path | None = None) -> Dict[int, List[Tuple[time, time]]]:
    """
    从YAML配置文件加载时间规则
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
    
    Returns:
        时间规则字典
    """
    if yaml is None:
        raise ImportError("需要安装PyYAML库: pip install pyyaml")
    
    if config_path is None:
        # 默认配置文件路径
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.yaml"
    
    config_path = Path(config_path)
    if not config_path.exists():
        # 返回默认配置
        return {
            0: [(time(10, 0), time(12, 0)), (time(15, 0), time(19, 0))],
            1: [(time(9, 0), time(12, 0)), (time(19, 0), time(23, 0))],
            5: [(time(0, 0), time(23, 59))],
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    risk_config = config.get("risk", {})
    time_rules_config = risk_config.get("time_rules", {})
    
    # 转换配置格式
    time_rules: Dict[int, List[Tuple[time, time]]] = {}
    for weekday_str, time_ranges in time_rules_config.items():
        weekday = int(weekday_str)
        time_rules[weekday] = [parse_time_range(tr) for tr in time_ranges]
    
    return time_rules


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    计算RSI（相对强弱指标）
    
    Args:
        prices: 价格列表（收盘价），从旧到新
        period: RSI周期，默认14
    
    Returns:
        RSI值（0-100），如果数据不足则返回None
    """
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [delta if delta > 0 else 0.0 for delta in deltas]
    losses = [-delta if delta < 0 else 0.0 for delta in deltas]
    
    # 使用Wilder's平滑方法
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Optional[float]:
    """
    计算ADX（平均趋向指标）
    
    Args:
        highs: 最高价列表，从旧到新
        lows: 最低价列表，从旧到新
        closes: 收盘价列表，从旧到新
        period: ADX周期，默认14
    
    Returns:
        ADX值，如果数据不足则返回None
    """
    if len(highs) < period * 3 + 1 or len(lows) < period * 3 + 1 or len(closes) < period * 3 + 1:
        return None
    
    # 计算True Range (TR)
    tr_list = []
    for i in range(1, len(highs)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr = max(tr1, tr2, tr3)
        tr_list.append(tr)
    
    # 计算+DM和-DM
    plus_dm_list = []
    minus_dm_list = []
    for i in range(1, len(highs)):
        move_up = highs[i] - highs[i - 1]
        move_down = lows[i - 1] - lows[i]
        
        if move_up > move_down and move_up > 0:
            plus_dm = move_up
        else:
            plus_dm = 0.0
        
        if move_down > move_up and move_down > 0:
            minus_dm = move_down
        else:
            minus_dm = 0.0
        
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
    
    # 使用Wilder's平滑方法计算ATR、+DM_avg、-DM_avg
    atr = sum(tr_list[:period]) / period
    plus_dm_avg = sum(plus_dm_list[:period]) / period
    minus_dm_avg = sum(minus_dm_list[:period]) / period
    
    dx_list = []
    for i in range(period, len(tr_list)):
        # Wilder's平滑：新值 = (旧值 * (period - 1) + 新值) / period
        atr = (atr * (period - 1) + tr_list[i]) / period
        plus_dm_avg = (plus_dm_avg * (period - 1) + plus_dm_list[i]) / period
        minus_dm_avg = (minus_dm_avg * (period - 1) + minus_dm_list[i]) / period
        
        if atr == 0:
            continue
        
        plus_di = (plus_dm_avg / atr) * 100
        minus_di = (minus_dm_avg / atr) * 100
        
        di_sum = plus_di + minus_di
        if di_sum == 0:
            continue
        
        dx = (abs(plus_di - minus_di) / di_sum) * 100
        dx_list.append(dx)
    
    if len(dx_list) < period:
        return None
    
    # 计算ADX（DX的Wilder's平滑）
    adx = sum(dx_list[:period]) / period
    for i in range(period, len(dx_list)):
        adx = (adx * (period - 1) + dx_list[i]) / period
    
    return adx


def get_rsi_adx(
    grvt: GrvtCcxt,
    symbol: str = "BTC_USDT_Perp",
    timeframe: str = "15m",
    rsi_period: int = 14,
    adx_period: int = 14
) -> Tuple[Optional[float], Optional[float]]:
    """
    获取指定交易对的RSI和ADX值
    
    Args:
        grvt: GrvtCcxt实例
        symbol: 交易对符号，默认BTC_USDT_Perp
        timeframe: K线时间周期，默认15m
        rsi_period: RSI计算周期，默认14
        adx_period: ADX计算周期，默认14
    
    Returns:
        (RSI值, ADX值) 元组，如果计算失败则返回 (None, None)
    """
    try:
        max_period = max(rsi_period, adx_period)
        limit = max_period * 3 + 30
        
        ohlcv_response = grvt.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            params={"candle_type": "TRADE"}
        )
        
        result = ohlcv_response.get("result", [])
        if not result:
            return None, None
        
        min_required = max_period * 3 + 1
        if len(result) < min_required:
            return None, None
        
        # 反转数据顺序，确保从旧到新
        reversed_result = list(reversed(result))
        closes = []
        highs = []
        lows = []
        
        for candle in reversed_result:
            close_str = candle.get("close", "0")
            high_str = candle.get("high", "0")
            low_str = candle.get("low", "0")
            
            try:
                close = float(close_str)
                high = float(high_str)
                low = float(low_str)
                
                if close <= 0 or high <= 0 or low <= 0:
                    continue
                
                if close > 1000000:
                    close = close / PRICE_MULTIPLIER
                    high = high / PRICE_MULTIPLIER
                    low = low / PRICE_MULTIPLIER
                
                if close < 1000 or close > 200000:
                    continue
                
                closes.append(close)
                highs.append(high)
                lows.append(low)
            except (ValueError, TypeError):
                continue
        
        if len(closes) < min_required:
            return None, None
        
        # 计算RSI和ADX
        rsi = calculate_rsi(closes, rsi_period)
        adx = calculate_adx(highs, lows, closes, adx_period)
        
        return rsi, adx
        
    except Exception as e:
        print(f"计算RSI和ADX失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


# 示例时间规则配置（保留作为备用）
EXAMPLE_TIME_RULES = {
    0: [(time(10, 0), time(12, 0)), (time(15, 0), time(19, 0))],  # 周一：10:00-12:00, 15:00-19:00
    1: [(time(9, 0), time(12, 0)), (time(19, 0), time(23, 0))],    # 周二：09:00-12:00, 19:00-23:00
    5: [(time(0, 0), time(23, 59))],                               # 周六：00:00-23:59
}


if __name__ == "__main__":
    # 测试时间区域判断
    try:
        time_rules = load_time_rules_from_yaml()
        print("从YAML配置文件加载时间规则")
    except Exception as e:
        print(f"加载YAML配置失败，使用默认配置: {e}")
        time_rules = EXAMPLE_TIME_RULES
    
    current_time = get_current_china_time()
    print(f"当前中国时间: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"当前是周{current_time.weekday() + 1}")
    
    is_allowed = check_time_permission(time_rules)
    print(f"是否在允许时间范围内: {is_allowed}")
    
    # 测试不同时间
    print("\n测试不同时间:")
    test_times = [
        datetime(2024, 1, 1, 11, 0, 0),   # 周一 11:00
        datetime(2024, 1, 1, 13, 0, 0),   # 周一 13:00
        datetime(2024, 1, 2, 10, 0, 0),   # 周二 10:00
        datetime(2024, 1, 2, 15, 0, 0),   # 周二 15:00
        datetime(2024, 1, 6, 12, 0, 0),   # 周六 12:00
    ]
    
    for test_time in test_times:
        test_time = test_time.replace(tzinfo=CHINA_TZ)
        weekday_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][test_time.weekday()]
        result = is_in_time_range(test_time, time_rules)
        print(f"{weekday_name} {test_time.strftime('%H:%M')}: {result}")

