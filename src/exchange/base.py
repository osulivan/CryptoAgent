"""
交易所客户端抽象基类
定义永续合约交易的统一接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class ExchangeClient(ABC):
    """交易所客户端抽象基类"""

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        base_url: str = "",
        simulated: bool = True,
        proxy: Optional[str] = None
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = base_url
        self.simulated = simulated
        self.proxy = proxy

    @abstractmethod
    async def get_klines(
        self,
        inst_id: str,
        bar: str = "1H",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取K线数据"""
        pass

    @abstractmethod
    async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
        """获取实时行情"""
        pass

    @abstractmethod
    async def get_instruments(self, inst_type: str = "SWAP") -> List[Dict[str, Any]]:
        """获取合约信息"""
        pass

    @abstractmethod
    async def get_account_balance(self, ccy: Optional[str] = None) -> Dict[str, Any]:
        """获取账户余额"""
        pass

    @abstractmethod
    async def get_positions(
        self,
        inst_type: str = "SWAP",
        inst_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取当前持仓"""
        pass

    @abstractmethod
    async def place_order(
        self,
        inst_id: str,
        side: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        开仓下单
        Args:
            inst_id: 合约ID，如 BTC-USDT-SWAP
            side: 方向，buy/long (做多) 或 sell/short (做空)
            size: 数量（币的数量）
            order_type: 订单类型，market / limit
            price: 价格（限价单需要）
            reduce_only: 是否只减仓
        """
        pass

    @abstractmethod
    async def close_position(
        self,
        inst_id: str,
        side: str,
        size: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        平仓
        Args:
            inst_id: 合约ID
            side: 持仓方向，long / short
            size: 平仓数量，None 表示全部平仓
        """
        pass

    @abstractmethod
    async def get_order_info(
        self,
        inst_id: str,
        ord_id: Optional[str] = None,
        cl_ord_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询订单信息"""
        pass

    @abstractmethod
    async def close(self):
        """关闭客户端"""
        pass

    def normalize_inst_id(self, symbol: str, inst_type: str = "SWAP") -> str:
        """
        规范化合约ID
        子类可以根据交易所规则重写此方法
        """
        return symbol.upper()

    def normalize_side(self, side: str) -> str:
        """
        规范化方向
        返回: buy (做多) / sell (做空)
        """
        side = side.lower()
        if side in ["long", "buy", "多"]:
            return "buy"
        elif side in ["short", "sell", "空"]:
            return "sell"
        return side
