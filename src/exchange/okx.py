"""
OKX API客户端
封装OKX V5 API的调用
"""
import base64
import hmac
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import httpx

from .base import ExchangeClient


class OKXClient(ExchangeClient):
    """OKX API客户端"""

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        base_url: str = "https://www.okx.com",
        simulated: bool = True,
        proxy: Optional[str] = None
    ):
        super().__init__(api_key, api_secret, passphrase, base_url, simulated, proxy)
        self.base_url = base_url.rstrip("/")

        # 代理设置：优先使用传入的参数，其次环境变量
        self.proxy = proxy or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

        # 创建httpx客户端，配置代理
        client_kwargs = {"timeout": 30}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
            print(f"🌐 使用代理: {self.proxy}")

        self.client = httpx.AsyncClient(**client_kwargs)

    def normalize_inst_id(self, symbol: str, inst_type: str = "SWAP") -> str:
        """规范化合约ID (OKX格式)"""
        symbol = symbol.upper()
        if "-" not in symbol:
            # BTC-USDT -> BTC-USDT-SWAP
            return f"{symbol}-USDT-{inst_type}"
        return symbol

    def normalize_side(self, side: str) -> str:
        """规范化方向"""
        side = side.lower()
        if side in ["long", "buy", "多"]:
            return "buy"
        elif side in ["short", "sell", "空"]:
            return "sell"
        return side

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """生成API签名"""
        message = timestamp + method.upper() + request_path + body
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _get_headers(self, method: str, request_path: str, body: str = "", need_auth: bool = True) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json"
        }

        if need_auth and self.api_key:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            headers.update({
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": self._generate_signature(timestamp, method, request_path, body),
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
            })

            if self.simulated:
                headers["x-simulated-trading"] = "1"

        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
        need_auth: bool = True
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        body_str = json.dumps(body) if body else ""

        request_path = endpoint
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            request_path = f"{endpoint}?{query_string}"

        headers = self._get_headers(method, request_path, body_str, need_auth)

        response = await self.client.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            content=body_str if body_str else None
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") != "0":
            print(f"[OKX ERROR] 完整响应: {data}")
            raise Exception(f"OKX API错误: {data.get('msg')} (code: {data.get('code')})")

        return data

    async def get_klines(
        self,
        inst_id: str,
        bar: str = "1H",
        limit: int = 100,
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取K线数据"""
        params = {
            "instId": inst_id,
            "bar": bar,
            "limit": str(limit)
        }

        if after:
            params["after"] = after
        if before:
            params["before"] = before

        data = await self._request("GET", "/api/v5/market/candles", params=params, need_auth=False)
        return data.get("data", [])

    async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
        """获取实时行情"""
        params = {"instId": inst_id}
        data = await self._request("GET", "/api/v5/market/ticker", params=params, need_auth=False)
        return data.get("data", [{}])[0]

    async def get_instruments(self, inst_type: str = "SWAP") -> List[Dict[str, Any]]:
        """获取合约信息"""
        params = {"instType": inst_type}
        data = await self._request("GET", "/api/v5/public/instruments", params=params, need_auth=False)
        return data.get("data", [])

    async def get_instrument(self, inst_id: str) -> Optional[Dict[str, Any]]:
        """获取单个交易产品信息"""
        if "-SWAP" in inst_id:
            inst_type = "SWAP"
        elif "-FUTURES" in inst_id:
            inst_type = "FUTURES"
        else:
            inst_type = "SPOT"

        params = {"instType": inst_type, "instId": inst_id}
        data = await self._request("GET", "/api/v5/public/instruments", params=params, need_auth=False)
        instruments = data.get("data", [])
        return instruments[0] if instruments else None

    async def get_account_balance(self, ccy: Optional[str] = None) -> Dict[str, Any]:
        """获取账户余额"""
        params = {}
        if ccy:
            params["ccy"] = ccy

        data = await self._request("GET", "/api/v5/account/balance", params=params, need_auth=True)
        return data.get("data", [])

    async def get_positions(
        self,
        inst_type: str = "SWAP",
        inst_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取当前持仓"""
        params = {"instType": inst_type}
        if inst_id:
            params["instId"] = inst_id

        data = await self._request("GET", "/api/v5/account/positions", params=params, need_auth=True)
        positions = data.get("data", [])
        
        # 添加单位标识（OKX使用张数）
        for pos in positions:
            pos["posUnit"] = "contract"  # 张数
        
        return positions

    async def place_order(
        self,
        inst_id: str,
        side: str = "",
        size: float = 0,
        order_type: str = "market",
        price: Optional[float] = None,
        reduce_only: bool = False,
        # 兼容web/api.py调用风格
        td_mode: str = "",
        ord_type: str = "",
        sz: str = "",
        pos_side: str = ""
    ) -> Dict[str, Any]:
        """开仓下单"""
        # 优先使用web/api.py风格的参数
        if sz:
            size = float(sz)
        if ord_type:
            order_type = ord_type
        
        # 只有在没有传入side时才根据pos_side计算side
        if not side:
            if pos_side:
                # pos_side: long/short -> side: buy/sell
                side = "buy" if pos_side == "long" else "sell"
            else:
                side = self.normalize_side(side)

        ord_type_okx = "market" if order_type == "market" else "limit"
        sz_str = str(size)

        body = {
            "instId": inst_id,
            "tdMode": td_mode if td_mode else "cross",
            "side": side,
            "ordType": ord_type_okx,
            "sz": sz_str
        }

        # 添加 posSide 参数（开空仓时需要）
        if pos_side:
            body["posSide"] = pos_side

        if price:
            body["px"] = str(price)

        if reduce_only:
            body["reduceOnly"] = "true"

        data = await self._request("POST", "/api/v5/trade/order", body=body, need_auth=True)
        return data.get("data", [{}])[0]

    async def close_position(
        self,
        inst_id: str,
        side: str = "",
        size: Optional[float] = None,
        # 兼容web/api.py调用风格
        pos_side: str = "",
        mgn_mode: str = ""
    ) -> Dict[str, Any]:
        """平仓"""
        # 优先使用pos_side
        if pos_side:
            side = "buy" if pos_side == "long" else "sell"
        else:
            side = self.normalize_side(side)

        mgn_mode = mgn_mode if mgn_mode else "cross"

        if size:
            body = {
                "instId": inst_id,
                "tdMode": mgn_mode,
                "side": side,
                "ordType": "market",
                "sz": str(size),
                "reduceOnly": "true"
            }
            data = await self._request("POST", "/api/v5/trade/order", body=body, need_auth=True)
        else:
            body = {
                "instId": inst_id,
                "posSide": pos_side if pos_side else ("long" if side == "buy" else "short"),
                "mgnMode": mgn_mode
            }
            data = await self._request("POST", "/api/v5/trade/close-position", body=body, need_auth=True)

        return data.get("data", [{}])[0]

    async def execute_trade(
        self,
        decision: str,
        symbol: str,
        trade_order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行交易（统一接口）"""
        if decision == 'OPEN':
            # 开仓
            order_side = trade_order.get('side')
            if not order_side:
                raise Exception("trade_order 缺少 side 字段，无法确定开仓方向")
            pos_side = 'long' if order_side == 'LONG' else 'short'
            size = trade_order.get('size')
            if not size or size == '0':
                raise Exception("trade_order 缺少 size 字段或大小为0，无法确定开仓数量")

            # 获取交易产品信息
            instrument = await self.get_instrument(symbol)
            if not instrument:
                raise Exception(f"无法获取交易产品信息: {symbol}")

            # 获取下单精度
            lot_sz = str(instrument.get('lotSz', '1'))
            lot_sz_decimal = 0 if '.' not in lot_sz else len(lot_sz.split('.')[1])

            # OKX使用张数（1张 = 0.01币）
            coin_size = float(size)
            order_size = coin_size / 0.01
            order_size = round(order_size, lot_sz_decimal)

            if order_size <= 0:
                raise Exception(f"计算后的下单数量必须大于0: {order_size}")

            result = await self.place_order(
                inst_id=symbol,
                td_mode='cross',
                side='buy' if order_side == 'LONG' else 'sell',
                ord_type='market',
                sz=str(order_size),
                pos_side=pos_side
            )
            result['executed'] = True
            result['message'] = f"成功开仓 {order_side} {coin_size}个币 (张数: {order_size})"
            return result

        else:  # CLOSE
            close_side = trade_order.get('side')
            if not close_side:
                raise Exception("trade_order 缺少 side 字段，无法确定平仓方向")
            pos_side = 'long' if close_side == 'LONG' else 'short'
            size = trade_order.get('size', 'ALL')

            if size == 'ALL':
                # 全部平仓
                result = await self.close_position(
                    inst_id=symbol,
                    pos_side=pos_side,
                    mgn_mode='cross'
                )
                result['executed'] = True
                result['message'] = f"成功全部平仓 {close_side} 仓位"
                return result
            else:
                # 部分平仓
                instrument = await self.get_instrument(symbol)
                if not instrument:
                    raise Exception(f"无法获取交易产品信息: {symbol}")

                lot_sz = str(instrument.get('lotSz', '1'))
                lot_sz_decimal = 0 if '.' not in lot_sz else len(lot_sz.split('.')[1])

                coin_size = float(size)
                order_size = coin_size / 0.01
                order_size = round(order_size, lot_sz_decimal)

                if order_size <= 0:
                    raise Exception(f"计算后的下单数量必须大于0: {order_size}")

                result = await self.place_order(
                    inst_id=symbol,
                    td_mode='cross',
                    side='sell' if close_side == 'LONG' else 'buy',
                    ord_type='market',
                    sz=str(order_size),
                    pos_side=pos_side
                )
                result['executed'] = True
                result['message'] = f"成功部分平仓 {close_side} {coin_size}个币 (张数: {order_size})"
                return result

    async def get_order_info(
        self,
        inst_id: str,
        ord_id: Optional[str] = None,
        cl_ord_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询订单信息"""
        params = {"instId": inst_id}

        if ord_id:
            params["ordId"] = ord_id
        if cl_ord_id:
            params["clOrdId"] = cl_ord_id

        data = await self._request("GET", "/api/v5/trade/order", params=params, need_auth=True)
        return data.get("data", [{}])[0]

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
