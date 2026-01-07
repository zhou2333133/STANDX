"""
Exchange Adapters Package

统一入口：通过配置创建适配器，无需关心具体实现

使用示例:
    from adapters import create_adapter
    
    # 只需要更改配置即可切换交易所
    config = {
        "exchange_name": "standx",  # 或 "nado", "grvt" 等
        "private_key": "0x...",
        "chain": "bsc"
    }
    
    adapter = create_adapter(config)
    adapter.connect()
    balance = adapter.get_balance()
"""
from adapters.base_adapter import (
    BasePerpAdapter,
    OrderSide,
    OrderType,
    TimeInForce,
    OrderStatus,
    Position,
    Balance,
    Order,
)
from adapters.factory import (
    create_adapter,
    register_adapter,
    get_available_exchanges,
)

__all__ = [
    # 基类和接口
    "BasePerpAdapter",
    "create_adapter",
    
    # 数据模型
    "Position",
    "Balance",
    "Order",
    
    # 枚举
    "OrderSide",
    "OrderType",
    "TimeInForce",
    "OrderStatus",
    
    # 工厂函数
    "register_adapter",
    "get_available_exchanges",
]
