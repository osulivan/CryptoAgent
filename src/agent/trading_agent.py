"""
交易Agent - ReAct风格
使用Function Calling让Agent自主决策
"""
import json
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Agent动作类型"""
    ANALYZE = "analyze"           # 分析市场
    GET_DATA = "get_data"         # 获取数据
    CHECK_POSITION = "check_position"  # 检查持仓
    OPEN_ORDER = "open_order"     # 开仓
    CLOSE_ORDER = "close_order"   # 平仓
    HOLD = "hold"                 # 观望


@dataclass
class AgentDecision:
    """Agent决策结果"""
    action: ActionType
    reason: str
    params: Dict[str, Any]
    confidence: float


class TradingAgent:
    """交易Agent - ReAct实现"""
    
    def __init__(
        self,
        llm_client,
        exchange_client,
        chart_generator,
        trading_rules: str,
        max_iterations: int = 10
    ):
        self.llm = llm_client
        self.exchange = exchange_client
        self.chart_gen = chart_generator
        self.trading_rules = trading_rules
        self.max_iterations = max_iterations
        
        # 工具函数映射
        self.tools: Dict[str, Callable] = {
            "get_market_data": self._tool_get_market_data,
            "get_positions": self._tool_get_positions,
        }
    
    async def run(self, symbol: str = "") -> Dict[str, Any]:
        """
        运行Agent执行交易分析
        
        Returns:
            执行结果报告
        """
        print(f"\n{'='*60}")
        print(f"🤖 Agent开始执行交易分析 - {symbol}")
        print(f"{'='*60}\n")
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt(symbol)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据交易规则分析行情并做出交易决策"}
        ]
        
        execution_log = []
        final_result = None
        
        for iteration in range(self.max_iterations):
            print(f"\n--- 迭代 {iteration + 1}/{self.max_iterations} ---")
            
            # 调用LLM
            response = await self._call_llm(messages)
            
            # 解析响应
            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])
            tokens = response.get("tokens", {})
            
            print(f"Agent思考: {content[:200]}...")
            print(f"Agent tokens: {tokens}")
            
            # 记录日志（包含thought、tool_calls和tokens）
            iteration_log = {
                "iteration": iteration + 1,
                "thought": content,
                "tool_calls": [],
                "tokens": tokens
            }
            
            # 添加Assistant消息
            assistant_msg = {
                "role": "assistant",
                "content": content if content else "..."
            }
            
            # 如果有工具调用，添加格式化的tool_calls
            if tool_calls:
                formatted_tool_calls = []
                for tc in tool_calls:
                    formatted_tool_calls.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("arguments", {}))
                        }
                    })
                assistant_msg["tool_calls"] = formatted_tool_calls
            
            messages.append(assistant_msg)
            
            # 如果没有工具调用，说明Agent已完成决策
            if not tool_calls:
                final_result = self._parse_final_decision(content)
                print(f"\n✅ Agent完成决策: {final_result}")
                # 记录本次迭代日志（最终决策迭代）
                execution_log.append(iteration_log)
                break
            
            # 执行工具调用
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call, symbol)
                
                # 保存工具调用和结果到日志
                iteration_log["tool_calls"].append({
                    "id": tool_call.get("id", ""),
                    "name": tool_call.get("name", ""),
                    "arguments": tool_call.get("arguments", {}),
                    "result": result
                })
                
                # 检查是否包含图表数据
                if "chart_url" in result and result.get("success"):
                    # 使用多模态格式发送图表
                    chart_url = result["chart_url"]
                    summary = result.get("data_summary", {})
                    indicator_values = result.get("indicator_values", {})
                    
                    # 构建指标数值文本
                    indicators_text = ""
                    if indicator_values:
                        indicators_text = "\n技术指标数值:\n"
                        for ind_name, values in indicator_values.items():
                            if isinstance(values, dict):
                                # 多线指标（如布林带、MACD）
                                values_str = ", ".join([f"{k}: {v:.2f}" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in values.items()])
                                indicators_text += f"  {ind_name}: {values_str}\n"
                            else:
                                # 单线指标（如SMA、RSI）
                                indicators_text += f"  {ind_name}: {values:.2f}\n"
                    
                    # 构建多模态消息内容
                    content_parts = [
                        {
                            "type": "text",
                            "text": f"K线数据获取成功。时间周期: {result.get('timeframe')}, 交易对: {result.get('symbol')}\n"
                                    f"最新价格: {summary.get('latest_price')}, 开盘: {summary.get('latest_open')}, 最高: {summary.get('latest_high')}, 最低: {summary.get('latest_low')}, 成交量: {summary.get('latest_volume', 'N/A')}\n"
                                    f"时间: {summary.get('timestamp_iso')}{indicators_text}\n"
                                    f"请分析以下图表:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": chart_url
                            }
                        }
                    ]
                    
                    # 添加用户消息（多模态格式）
                    messages.append({
                        "role": "user",
                        "content": content_parts
                    })
                    
                    # 打印构建的多模态消息文本内容
                    print(f"\n📊 多模态消息文本内容:")
                    print("-" * 70)
                    print(content_parts[0]["text"])
                    print("-" * 70)
                    print(f"工具结果: 图表已生成，正在传给模型分析...")
                else:
                    # 普通文本结果
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                    
                    print(f"工具结果: {str(result)[:150]}...")
            
            # 记录本次迭代的日志
            execution_log.append(iteration_log)
        
        return {
            "symbol": symbol,
            "final_decision": final_result,
            "execution_log": execution_log,
            "iterations": len(execution_log)
        }
    
    def _build_system_prompt(self, symbol: str) -> str:
        """构建系统提示词"""
        return f"""## 任务描述
你是一位专业的数字货币交易Agent，负责执行用户的交易策略。

## 交易对
{symbol}

## 交易规则
{self.trading_rules}

## 你的工作流程
1. **事前准备**：
- 充分理解交易规则
- 调用工具获取所需数据（如需）
2. **分析判断**: 根据获取到的数据和交易规则进行分析判断，做出交易决策
3. **输出决策指令**: 以JSON格式输出最终决策和交易指令（如需要交易）

## 开仓数量计算规则（必须严格遵守）
1. 如果交易规则中直接写了具体的交易数量（如"开仓0.1个BTC"），则直接使用该数量
2. 如果交易规则中写的是仓位百分比（如"10%仓位"），则需要自行计算：
   - 计算公式：开仓币数量 = (可用保证金 × 仓位百分比) ÷ 当前价格
   - 示例：可用保证金10万USDT，BTC现价5万，开10%仓位
     - 计算：开仓币数量 = (100000 × 0.1) ÷ (50000) = 0.2 个BTC
   - 注意：杠杆倍数不影响开仓数量计算，只影响所需保证金

## 输出要求
当你完成分析并做出决策后，请以以下JSON格式输出最终结论：

### 1. 如果决策是HOLD（观望）：
{{
    "decision": "HOLD",
    "reason": "详细说明判断依据",
    "confidence": 0.85
}}

### 2. 如果决策是开仓（OPEN）：
{{
    "decision": "OPEN",
    "reason": "详细说明判断依据",
    "confidence": 0.85,
    "trade_order": {{
        "symbol": "{symbol}",
        "side": "LONG" | "SHORT",
        "size": "开仓数量（币的数量，如 0.1 表示0.1个BTC）",
        "size_calculation": "说明数量是如何计算的"
    }}
}}

### 3. 如果决策是平仓（CLOSE）：
{{
    "decision": "CLOSE",
    "reason": "详细说明判断依据",
    "confidence": 0.85,
    "trade_order": {{
        "symbol": "{symbol}",
        "side": "LONG" | "SHORT",
        "size": "平仓数量（币的数量，如 0.1 表示平0.1个BTC，或 'ALL' 表示全部平仓）"
    }}
}}

## 重要提醒
- 必须严格遵守交易规则中的所有要求
- 必须获取真实的数据进行分析判断，不要猜测，不得编造数据
- 若获取不到交易规则中所必需要的数据，不得输出交易指令（如开仓、平仓等）
- 当难以判断是否符合交易规则时，宁可选择HOLD观望
"""
    
    def _get_tools_definition(self) -> List[Dict]:
        """获取工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_market_data",
                    "description": "获取指定交易对在指定时间周期的K线数据和技术指标图表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "交易对名称"
                            },
                            "timeframe": {
                                "type": "string",
                                "enum": ["5m", "15m", "30m", "1H", "4H", "1D"],
                                "description": "K线时间周期（5m, 15m, 30m, 1H, 4H, 1D - 注意分钟用小写m，小时/天用大写）"
                            },
                            "indicators": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "需要显示的技术指标，支持动态参数格式，如: sma(20), ema(12), bollinger(20,2.0), rsi(14), macd, kdj, stoch, cci, willr, atr, adx, aroon, obv, vwap, mfi"
                            }
                        },
                        "required": ["symbol", "timeframe"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_positions",
                    "description": "获取指定交易对的当前持仓信息及可用保证金",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "交易对名称"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            }
        ]
    
    async def _call_llm(self, messages: List[Dict]) -> Dict[str, Any]:
        """调用LLM API - 使用统一适配器接口"""
        tools = self._get_tools_definition()

        try:
            # 使用统一的适配器接口（支持所有提供商）
            response = await self.llm.chat_completion(
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=32000
            )

            return response

        except Exception as e:
            print(f"LLM调用错误: {e}")
            import traceback
            traceback.print_exc()
            return {"content": f"错误: {e}", "tool_calls": [], "tokens": {}}
    
    async def _execute_tool(self, tool_call: Dict, symbol: str) -> Dict:
        """执行工具调用"""
        name = tool_call.get("name")
        args = tool_call.get("arguments", {})
        
        print(f"  执行工具: {name}({args})")
        
        if name in self.tools:
            try:
                return await self.tools[name](symbol, **args)
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": f"未知工具: {name}"}
    
    # ==================== 工具实现 ====================
    
    async def _tool_get_market_data(self, default_symbol: str, symbol: str = None, timeframe: str = None, indicators: List[str] = None) -> Dict:
        """获取市场数据工具"""
        # 使用传入的symbol或默认symbol
        inst_id = symbol or default_symbol
        
        # 规范化产品名称
        if hasattr(self.exchange, 'normalize_inst_id'):
            inst_id = self.exchange.normalize_inst_id(inst_id)
        
        if not timeframe:
            return {"error": "timeframe参数是必需的"}
        
        # 时间格式转换（交易所可能不同）
        if timeframe.lower().endswith('m'):
            exchange_timeframe = timeframe.lower()
        else:
            exchange_timeframe = timeframe.upper()
        
        try:
            # 1. 获取K线数据
            klines = await self.exchange.get_klines(
                inst_id=inst_id,
                bar=exchange_timeframe,
                limit=100
            )
            
            if not klines:
                return {"error": "未获取到K线数据"}
            
            # 2. 生成图表
            chart_result = self.chart_gen.generate_chart(
                klines=klines,
                indicators=indicators or [],
                title=f"{inst_id} {timeframe}"
            )
            
            # 3. 获取数据摘要
            summary = self.chart_gen.get_latest_data_summary(klines)
            
            return {
                "success": True,
                "timeframe": timeframe,
                "symbol": inst_id,
                "chart_url": f"data:image/png;base64,{chart_result['base64']}",
                "chart_local_path": chart_result.get('local_path'),
                "data_summary": summary,
                "indicator_values": chart_result.get('indicator_values', {})
            }
            
        except Exception as e:
            return {"error": f"获取市场数据失败: {str(e)}"}
    
    async def _tool_get_positions(self, default_symbol: str, symbol: str = None) -> Dict:
        """获取持仓工具 - 返回精简后的持仓信息"""
        inst_id = symbol or default_symbol
        
        # 规范化产品名称
        if hasattr(self.exchange, 'normalize_inst_id'):
            inst_id = self.exchange.normalize_inst_id(inst_id)
        
        if not inst_id:
            return {"error": "symbol参数是必需的"}
        
        try:
            # 1. 获取持仓数据
            positions = await self.exchange.get_positions(inst_id=inst_id)
            
            # 2. 获取账户余额（用于显示可用保证金）
            account_balance = await self.exchange.get_account_balance()
            available_margin = "获取不到"
            if account_balance and len(account_balance) > 0:
                # 在details字段中查找USDT的可用保证金
                summary = account_balance[0]
                details = summary.get('details', [])
                
                for detail in details:
                    if detail.get('ccy') == 'USDT':
                        avail_eq = detail.get('availEq')
                        if avail_eq and avail_eq != '':
                            available_margin = float(avail_eq)
                        break
            
            # 3. 过滤掉空持仓，并提取关键信息
            long_position = None
            short_position = None
            
            for pos in positions:
                # 只保留有实际持仓的
                pos_size = float(pos.get('pos', 0) or 0)
                if pos_size == 0:
                    continue
                
                # 根据单位决定是否转换（OKX: 张数->币数量, Binance: 已经是币数量）
                pos_unit = pos.get('posUnit', 'contract')  # 默认张数
                if pos_unit == 'contract':
                    # OKX: 张数转币数量（1张 = 0.01币）
                    coin_size = pos_size * 0.01
                else:
                    # Binance: 已经是币数量
                    coin_size = pos_size
                
                # 提取关键字段
                simplified_pos = {
                    "持仓方向": "多仓" if pos.get('posSide') == 'long' else "空仓",
                    "持仓数量_币": round(coin_size, 4),
                    "开仓均价": float(pos.get('avgPx', 0) or 0),
                    "浮动盈亏": float(pos.get('upl', 0) or 0),
                    "杠杆倍数": int(pos.get('lever', 1)),
                    "保证金模式": "全仓" if pos.get('mgnMode') == 'cross' else "逐仓",
                    "标记价格": float(pos.get('markPx', 0) or 0),
                }
                
                # 分别记录多仓和空仓
                if pos.get('posSide') == 'long':
                    long_position = simplified_pos
                else:
                    short_position = simplified_pos
            
            # 4. 构建简洁的返回结果
            result = {
                "success": True,
                "交易对": inst_id,
                "是否有持仓": long_position is not None or short_position is not None,
                "可用保证金_USDT": available_margin,
                "多仓信息": long_position,
                "空仓信息": short_position,
            }
            
            return result
            
        except Exception as e:
            return {"error": f"获取持仓失败: {str(e)}"}
    
    def _parse_final_decision(self, content: str) -> Dict[str, Any]:
        """解析Agent的最终决策"""
        try:
            # 尝试从内容中提取JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                # 尝试直接解析
                json_str = content[content.find("{"):content.rfind("}")+1]
            
            decision = json.loads(json_str)
            return decision
        except:
            # 如果解析失败，返回文本内容
            return {
                "decision": "UNKNOWN",
                "reason": content,
                "confidence": 0
            }
