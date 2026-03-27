"""
交易所客户端工厂
根据交易所类型创建对应的客户端
"""
from typing import Optional

from .base import ExchangeClient
from .okx import OKXClient
from .binance import BinanceClient
from .bybit import BybitClient


def create_exchange_client(
    exchange: str,
    api_key: str = "",
    api_secret: str = "",
    passphrase: str = "",
    base_url: str = "",
    simulated: bool = True,
    proxy: Optional[str] = None
) -> ExchangeClient:
    """
    创建交易所客户端

    Args:
        exchange: 交易所类型 (okx / binance / bybit)
        api_key: API Key
        api_secret: API Secret
        passphrase: 密码短语 (仅 OKX 需要)
        base_url: 自定义 API 地址
        simulated: 是否模拟交易
        proxy: 代理地址

    Returns:
        ExchangeClient 实例
    """
    exchange = exchange.lower()

    if exchange == "okx":
        return OKXClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            base_url=base_url or "https://www.okx.com",
            simulated=simulated,
            proxy=proxy
        )
    elif exchange == "binance":
        return BinanceClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            base_url=base_url,  # 让客户端根据 simulated 参数自动选择 URL
            simulated=simulated,
            proxy=proxy
        )
    elif exchange == "bybit":
        return BybitClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            base_url=base_url or "https://api.bybit.com",
            simulated=simulated,
            proxy=proxy
        )
    else:
        raise ValueError(f"不支持的交易所: {exchange}")


def get_exchange_list() -> list:
    """获取支持的交易所列表"""
    return [
        {"id": "okx", "name": "OKX", "description": "OKX 永续合约"},
        {"id": "binance", "name": "Binance", "description": "Binance USDT 永续合约"},
        {"id": "bybit", "name": "Bybit", "description": "Bybit USDT 永续合约"},
    ]
