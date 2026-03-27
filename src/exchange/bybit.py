"""
Bybit 合约客户端
支持 USDT 永续合约
"""
import base64
import hashlib
import json
import os
import time
from typing import Optional, List, Dict, Any

import httpx

from .base import ExchangeClient


class BybitClient(ExchangeClient):
    """Bybit USDT 永续合约客户端"""

    BASE_URL = "https://api.bybit.com"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        base_url: str = "",
        simulated: bool = False,
        proxy: Optional[str] = None
    ):
        super().__init__(api_key, api_secret, passphrase, base_url or self.BASE_URL, simulated, proxy)

        self.proxy = proxy or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

        client_kwargs = {"timeout": 30}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        self.client = httpx.AsyncClient(**client_kwargs)

    def normalize_inst_id(self, symbol: str, inst_type: str = "PERPETUAL") -> str:
        """规范化合约ID (Bybit格式: BTCUSDT)"""
        symbol = symbol.upper().replace("-USDT", "USDT").replace("_USDT", "USDT")
        return symbol

    def normalize_side(self, side: str) -> str:
        """规范化方向"""
        side = side.lower()
        if side in ["long", "buy", "多"]:
            return "Buy"
        elif side in ["short", "sell", "空"]:
            return "Sell"
        return side.capitalize()

    def _generate_signature(self, params: Dict, timestamp: str) -> str:
        """生成签名"""
        param_str = json.dumps(params) if params else ""
        message = timestamp + "POST" + "/v5/order/create" + param_str
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode("utf-8")

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        need_auth: bool = True
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        headers = {"Content-Type": "application/json"}

        if need_auth and self.api_key:
            timestamp = str(int(1000 * time.time()))
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = timestamp
            headers["X-BAPI-RECV-WINDOW"] = "5000"

            param_str = json.dumps(params) if params else ""
            sign = self._generate_signature(params, timestamp)
            headers["X-BAPI-SIGN"] = sign
            headers["X-BAPI-SIGN-TYPE"] = "2"

        if method == "GET":
            response = await self.client.get(url, params=params, headers=headers)
        else:
            response = await self.client.post(url, json=params if params else {}, headers=headers)

        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise Exception(f"Bybit API错误: {data.get('retMsg')} (code: {data.get('retCode')})")

        return data.get("result", {})

    async def get_klines(
        self,
        inst_id: str,
        bar: str = "1H",
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取K线数据"""
        bar_map = {
            "1m": "1", "5m": "5", "15m": "15", "30m": "30",
            "1H": "60", "4H": "240", "1D": "D"
        }
        interval = bar_map.get(bar, "60")

        params = {
            "category": "linear",
            "symbol": inst_id,
            "interval": interval,
            "limit": limit
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self._request("GET", "/v5/market/kline", params=params, need_auth=False)
        return data.get("list", [])

    async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
        """获取最新行情"""
        params = {
            "category": "linear",
            "symbol": inst_id
        }
        data = await self._request("GET", "/v5/market/tickers", params=params, need_auth=False)
        return data.get("list", [{}])[0]

    async def get_instruments(self, inst_type: str = "PERPETUAL") -> List[Dict[str, Any]]:
        """获取合约信息"""
        params = {"category": "linear"}
        data = await self._request("GET", "/v5/market/instruments-info", params=params, need_auth=False)
        return data.get("list", [])

    async def get_account_balance(self, ccy: Optional[str] = None) -> Dict[str, Any]:
        """获取账户余额"""
        params = {"accountType": "UNIFIED"}
        data = await self._request("GET", "/v5/account/wallet-balance", params=params, need_auth=True)
        return data.get("list", [])

    async def get_positions(
        self,
        inst_type: str = "PERPETUAL",
        inst_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取当前持仓"""
        params = {"category": "linear"}
        if inst_id:
            params["symbol"] = inst_id

        data = await self._request("GET", "/v5/position/closed-pnl", params=params, need_auth=True)

        positions_params = {"category": "linear", "settleCoin": "USDT"}
        if inst_id:
            positions_params["symbol"] = inst_id

        positions_data = await self._request("GET", "/v5/position/position-info", params=positions_params, need_auth=True)
        return [p for p in positions_data.get("list", []) if float(p.get("size", 0)) != 0]

    async def place_order(
        self,
        inst_id: str,
        side: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """开仓下单"""
        side = self.normalize_side(side)

        params = {
            "category": "linear",
            "symbol": inst_id,
            "side": side,
            "orderType": "Market" if order_type == "market" else "Limit",
            "qty": str(abs(size)),
            "timeInForce": "GTC"
        }

        if price:
            params["price"] = str(price)

        if reduce_only:
            params["reduceOnly"] = "true"

        data = await self._request("POST", "/v5/order/create", params=params, need_auth=True)
        return data

    async def close_position(
        self,
        inst_id: str,
        side: str,
        size: Optional[float] = None
    ) -> Dict[str, Any]:
        """平仓"""
        side = self.normalize_side(side)

        params = {
            "category": "linear",
            "symbol": inst_id,
            "side": "Sell" if side == "Buy" else "Buy",
            "orderType": "Market",
            "timeInForce": "GTC"
        }

        if size:
            params["qty"] = str(abs(size))
        else:
            params["reduceOnly"] = "true"

        data = await self._request("POST", "/v5/order/create", params=params, need_auth=True)
        return data

    async def get_order_info(
        self,
        inst_id: str,
        ord_id: Optional[str] = None,
        cl_ord_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询订单信息"""
        params = {
            "category": "linear",
            "symbol": inst_id
        }

        if ord_id:
            params["orderId"] = ord_id
        if cl_ord_id:
            params["orderLinkId"] = cl_ord_id

        data = await self._request("GET", "/v5/order/realtime", params=params, need_auth=True)
        return data.get("list", [{}])[0]

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
