"""
Binance 合约客户端
支持 USDT 永续合约
"""
import hashlib
import hmac
import os
import time
from typing import Optional, List, Dict, Any

import httpx

from .base import ExchangeClient


class BinanceClient(ExchangeClient):
    """Binance USDT 永续合约客户端"""

    BASE_URL = "https://fapi.binance.com"
    TESTNET_URL = "https://demo-fapi.binance.com"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        base_url: str = "",
        simulated: bool = False,
        proxy: Optional[str] = None
    ):
        # 如果设置了 simulated=True，自动使用测试网 URL
        if simulated and not base_url:
            base_url = self.TESTNET_URL
        
        super().__init__(api_key, api_secret, passphrase, base_url or self.BASE_URL, simulated, proxy)

        self.proxy = proxy or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        self.simulated = simulated

        client_kwargs = {"timeout": 30}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        self.client = httpx.AsyncClient(**client_kwargs)

    def normalize_inst_id(self, symbol: str, inst_type: str = "PERPETUAL") -> str:
        """规范化合约ID (Binance格式: BTCUSDT)"""
        # 移除常见的后缀和分隔符
        symbol = symbol.upper()
        symbol = symbol.replace("-USDT-SWAP", "USDT")
        symbol = symbol.replace("-USDT", "USDT")
        symbol = symbol.replace("_USDT", "USDT")
        symbol = symbol.replace("USDT-SWAP", "USDT")
        return symbol

    def normalize_side(self, side: str) -> str:
        """规范化方向"""
        side = side.lower()
        if side in ["long", "buy", "多"]:
            return "BUY"
        elif side in ["short", "sell", "空"]:
            return "SELL"
        return side.upper()

    def _generate_signature(self, params: Dict) -> str:
        """生成签名"""
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        )
        return mac.hexdigest()

    def _get_headers(self, need_auth: bool = True) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        if need_auth and self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        return headers

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

        if need_auth and self.api_key:
            timestamp = str(int(1000 * time.time()))
            
            # 签名需要包含所有请求参数
            sign_params = params.copy()
            sign_params["recvWindow"] = "5000"
            sign_params["timestamp"] = timestamp
            
            signature = self._generate_signature(sign_params)
            
            params["recvWindow"] = "5000"
            params["timestamp"] = timestamp
            params["signature"] = signature

        headers = self._get_headers(need_auth)

        if method == "GET":
            response = await self.client.get(url, params=params, headers=headers)
        else:
            response = await self.client.post(url, params=params, headers=headers)

        # 调试：打印错误响应
        if response.status_code != 200:
            print(f"[Binance Error] URL: {url}")
            print(f"[Binance Error] Status: {response.status_code}")
            print(f"[Binance Error] Response: {response.text}")

        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and data.get("code"):
            raise Exception(f"Binance API错误: {data.get('msg')} (code: {data.get('code')})")

        return data

    async def get_klines(
        self,
        inst_id: str,
        bar: str = "1h",
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取K线数据"""
        bar_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1H": "1h", "4H": "4h", "1D": "1d"
        }
        interval = bar_map.get(bar, bar)

        params = {
            "symbol": inst_id,
            "interval": interval,
            "limit": limit
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self._request("GET", "/fapi/v1/klines", params=params, need_auth=False)

        # Binance返回格式: [[open_time, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_volume, taker_buy_quote_volume, ignore], ...]
        # 转换为OKX格式: [[timestamp, open, high, low, close, vol, volCcy], ...]
        # OKX格式是最新数据在第一个，所以需要反转Binance数据
        converted = []
        for k in reversed(data):  # 反转数据，使最新数据在前
            converted.append([
                k[0],           # timestamp (open_time)
                k[1],           # open
                k[2],           # high
                k[3],           # low
                k[4],           # close
                k[5],           # volume
                k[7],           # quote_volume (volCcy)
                "0",            # volCcyQuote (placeholder)
                "1"             # confirm (placeholder)
            ])
        return converted

    async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
        """获取最新行情"""
        params = {"symbol": inst_id}
        data = await self._request("GET", "/fapi/v1/ticker/24hr", params=params, need_auth=False)
        return data

    async def get_instruments(self, inst_type: str = "PERPETUAL") -> List[Dict[str, Any]]:
        """获取合约信息"""
        data = await self._request("GET", "/fapi/v1/exchangeInfo", need_auth=False)
        return [s for s in data.get("symbols", []) if s.get("contractType") == "PERPETUAL"]

    async def get_instrument(self, inst_id: str) -> Optional[Dict[str, Any]]:
        """获取单个合约信息"""
        instruments = await self.get_instruments()
        for inst in instruments:
            if inst.get("symbol") == inst_id:
                # 转换为OKX格式
                return {
                    "instId": inst.get("symbol"),
                    "lotSz": inst.get("quantityPrecision", "0"),
                    "minSz": inst.get("minQty", "0"),
                    "tickSz": inst.get("pricePrecision", "0"),
                }
        return None

    async def get_account_balance(self, ccy: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取账户余额"""
        data = await self._request("GET", "/fapi/v2/account", need_auth=True)
        assets = data.get("assets", [])
        
        # 转换为OKX格式
        converted = []
        for asset in assets:
            if float(asset.get("walletBalance", 0)) > 0:
                converted.append({
                    "ccy": asset.get("asset"),
                    "availEq": asset.get("availableBalance"),
                    "eq": asset.get("walletBalance"),
                    "upl": asset.get("unrealizedProfit"),
                })
        
        # 包装成OKX格式
        return [{"details": converted}]

    async def get_positions(
        self,
        inst_type: str = "PERPETUAL",
        inst_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取当前持仓"""
        params = {}
        if inst_id:
            params["symbol"] = inst_id

        data = await self._request("GET", "/fapi/v2/positionRisk", params=params, need_auth=True)
        
        # 转换为OKX格式
        converted = []
        for p in data:
            pos_amt = float(p.get("positionAmt", 0))
            if pos_amt == 0:
                continue
            
            # Binance: positionSide = LONG/SHORT/BOTH
            # OKX: posSide = long/short
            pos_side = "long" if p.get("positionSide") == "LONG" else "short"
            
            # Binance返回的是币数量，直接返回币数量（不转换为张数）
            coin_amt = abs(pos_amt)
            
            converted.append({
                "instId": p.get("symbol"),
                "posSide": pos_side,
                "pos": str(coin_amt),  # 币数量
                "posUnit": "coin",  # 标识单位是币数量
                "avgPx": p.get("entryPrice"),
                "upl": p.get("unRealizedProfit"),
                "lever": p.get("leverage"),
                "mgnMode": "cross" if p.get("marginType") == "CROSSED" else "isolated",
                "markPx": p.get("markPrice"),
                "liqPx": p.get("liquidationPrice")
            })
        return converted

    async def place_order(
        self,
        inst_id: str,
        side: str = "",
        size: float = 0,
        order_type: str = "market",
        price: Optional[float] = None,
        reduce_only: bool = False,
        # 兼容OKX风格参数
        td_mode: str = "",
        ord_type: str = "",
        sz: str = "",
        pos_side: str = ""
    ) -> Dict[str, Any]:
        """开仓下单"""
        # 优先使用OKX风格参数
        if sz:
            size = float(sz)
        if ord_type:
            order_type = ord_type.lower()

        # 处理pos_side（支持小写long/short和大写LONG/SHORT）
        position_side = None
        if pos_side:
            pos_side_lower = pos_side.lower()
            if pos_side_lower in ["long", "short"]:
                position_side = "LONG" if pos_side_lower == "long" else "SHORT"
                # 只有在没有传入side时才根据pos_side计算side
                if not side:
                    side = "BUY" if pos_side_lower == "long" else "SELL"

        if not side:
            side = self.normalize_side(side)

        params = {
            "symbol": inst_id,
            "side": side,
            "quantity": str(abs(size)),
            "type": "LIMIT" if price or order_type == "limit" else "MARKET"
        }

        # 双向持仓模式下需要指定positionSide
        if position_side:
            params["positionSide"] = position_side

        if price:
            params["price"] = str(price)
            params["timeInForce"] = "GTC"

        if reduce_only:
            params["reduceOnly"] = "true"

        data = await self._request("POST", "/fapi/v1/order", params=params, need_auth=True)
        return data

    async def close_position(
        self,
        inst_id: str,
        side: str = "",
        size: Optional[float] = None,
        # 兼容OKX风格参数
        pos_side: str = "",
        mgn_mode: str = ""
    ) -> Dict[str, Any]:
        """平仓"""
        # 处理pos_side（支持小写long/short）
        position_side = None
        if pos_side:
            pos_side_lower = pos_side.lower()
            if pos_side_lower in ["long", "short"]:
                position_side = "LONG" if pos_side_lower == "long" else "SHORT"
                # 只有在没有传入side时才根据pos_side计算平仓方向
                if not side:
                    # 平仓方向与持仓相反
                    side = "SELL" if pos_side_lower == "long" else "BUY"

        if not side:
            side = self.normalize_side(side)

        params = {
            "symbol": inst_id,
            "side": side,
            "type": "MARKET"
        }

        # 双向持仓模式下需要指定positionSide（不需要reduceOnly）
        if position_side:
            params["positionSide"] = position_side
        else:
            # 单向持仓模式下使用reduceOnly
            params["reduceOnly"] = "true"

        if size:
            params["quantity"] = str(abs(size))

        data = await self._request("POST", "/fapi/v1/order", params=params, need_auth=True)
        return data

    async def get_order_info(
        self,
        inst_id: str,
        ord_id: Optional[str] = None,
        cl_ord_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询订单信息"""
        params = {"symbol": inst_id}

        if ord_id:
            params["orderId"] = int(ord_id)
        if cl_ord_id:
            params["origClientOrderId"] = cl_ord_id

        data = await self._request("GET", "/fapi/v1/order", params=params, need_auth=True)
        return data

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

            # 获取下单精度（Binance返回的是整数，如3表示3位小数）
            lot_sz_decimal = int(instrument.get('lotSz', 3))

            # Binance直接使用币数量
            coin_size = float(size)
            order_size = round(coin_size, lot_sz_decimal)

            if order_size <= 0:
                raise Exception(f"计算后的下单数量必须大于0: {order_size}")

            # 开仓：多仓用BUY+LONG，空仓用SELL+SHORT
            open_order_side = 'BUY' if order_side == 'LONG' else 'SELL'
            open_pos_side = 'LONG' if order_side == 'LONG' else 'SHORT'
            result = await self.place_order(
                inst_id=symbol,
                side=open_order_side,
                size=order_size,
                order_type='market',
                pos_side=open_pos_side
            )
            result['executed'] = True
            result['message'] = f"成功开仓 {order_side} {coin_size}个币"
            return result

        else:  # CLOSE
            close_side = trade_order.get('side')
            if not close_side:
                raise Exception("trade_order 缺少 side 字段，无法确定平仓方向")
            pos_side = 'long' if close_side == 'LONG' else 'short'
            size = trade_order.get('size', 'ALL')

            if size == 'ALL':
                # 全部平仓 - 先获取持仓数量
                positions = await self.get_positions(symbol)
                position = None
                for pos in positions:
                    if float(pos.get('pos', 0)) != 0:
                        pos_side_val = pos.get('posSide', '')
                        # posSide 是小写的 long/short
                        if (close_side == 'LONG' and pos_side_val == 'long') or \
                           (close_side == 'SHORT' and pos_side_val == 'short'):
                            position = pos
                            break

                if not position:
                    return {'executed': False, 'message': f'没有找到{close_side}方向的持仓'}

                # get_positions 返回的 pos 是币数量
                coin_amt = abs(float(position.get('pos', 0)))
                if coin_amt <= 0:
                    return {'executed': False, 'message': f'{close_side}方向持仓数量为0'}

                # 获取下单精度
                instrument = await self.get_instrument(symbol)
                lot_sz_decimal = int(instrument.get('lotSz', 3)) if instrument else 3
                order_size = round(coin_amt, lot_sz_decimal)

                # 全部平仓：平空仓用BUY+SHORT，平多仓用SELL+LONG
                close_order_side = 'BUY' if close_side == 'SHORT' else 'SELL'
                close_pos_side = 'SHORT' if close_side == 'SHORT' else 'LONG'
                result = await self.place_order(
                    inst_id=symbol,
                    side=close_order_side,
                    size=order_size,
                    order_type='market',
                    pos_side=close_pos_side
                )
                result['executed'] = True
                result['message'] = f"成功全部平仓 {close_side} 仓位 ({order_size}个币)"
                return result
            else:
                # 部分平仓
                instrument = await self.get_instrument(symbol)
                if not instrument:
                    raise Exception(f"无法获取交易产品信息: {symbol}")

                lot_sz_decimal = int(instrument.get('lotSz', 3))

                coin_size = float(size)
                order_size = round(coin_size, lot_sz_decimal)

                if order_size <= 0:
                    raise Exception(f"计算后的下单数量必须大于0: {order_size}")

                # 部分平仓：平空仓用BUY+SHORT，平多仓用SELL+LONG
                # 双向持仓模式下使用positionSide即可，不需要reduceOnly
                close_order_side = 'BUY' if close_side == 'SHORT' else 'SELL'
                close_pos_side = 'SHORT' if close_side == 'SHORT' else 'LONG'
                result = await self.place_order(
                    inst_id=symbol,
                    side=close_order_side,
                    size=order_size,
                    order_type='market',
                    pos_side=close_pos_side
                )
                result['executed'] = True
                result['message'] = f"成功部分平仓 {close_side} {coin_size}个币"
                return result

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
