"""
Agent任务执行器
负责实际执行Agent分析和交易
"""
import os
import aiohttp
from datetime import datetime

from ..exchange.factory import create_exchange_client
from ..llm.factory import create_llm_client
from ..agent.trading_agent import TradingAgent
from ..chart.generator import ChartGenerator
from ..shared.constants import TASKS_FILE, MODELS_FILE, ACCOUNTS_FILE
from ..shared.storage import load_json_file
from ..shared.schemas import ExecutionResult, FinalDecision, TradeOrder


class AgentExecutor:
    """Agent执行器"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    async def execute_task(self, task_id: str, execution_id: str) -> ExecutionResult:
        """
        执行单个任务
        
        Args:
            task_id: 任务ID
            execution_id: 执行记录ID
            
        Returns:
            ExecutionResult: 执行结果
        """
        # 加载配置
        tasks = load_json_file(TASKS_FILE, [])
        models = load_json_file(MODELS_FILE, [])
        accounts = load_json_file(ACCOUNTS_FILE, [])
        
        # 查找任务
        task = None
        for t in tasks:
            if t['id'] == task_id:
                task = t
                break
        
        if not task:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                task_id=task_id,
                task_name="",
                symbol="",
                start_time=datetime.now().isoformat(),
                end_time=datetime.now().isoformat(),
                error="任务不存在"
            )
        
        # 获取账户信息
        account_info = None
        account_name = ""
        for acc in accounts:
            if acc['id'] == task.get('accountId'):
                account_info = acc
                account_name = acc.get('name', '')
                break
        
        # 获取模型信息
        model_config = None
        model_name = ""
        model_provider = ""
        for m in models:
            if m['id'] == task.get('modelId'):
                model_config = m
                model_name = m.get('name', '')
                model_provider = m.get('provider', '')
                break
        
        start_time = datetime.now().isoformat()
        
        try:
            if not model_config:
                raise Exception("模型配置不存在")
            if not account_info:
                raise Exception("交易账户配置不存在")
            
            # 创建交易所客户端
            client = create_exchange_client(
                exchange=account_info['exchange'],
                api_key=account_info['apiKey'],
                api_secret=account_info['apiSecret'],
                passphrase=account_info.get('passphrase', ''),
                simulated=account_info.get('isSimulated', True),
                proxy=os.getenv("HTTP_PROXY")
            )
            
            # 创建LLM客户端
            llm = create_llm_client(
                provider=model_config['provider'],
                api_key=model_config['apiKey'],
                model=model_config['name'],
                base_url=model_config['baseUrl']
            )
            
            chart_gen = ChartGenerator()
            
            # 创建Agent
            agent = TradingAgent(
                llm_client=llm,
                exchange_client=client,
                chart_generator=chart_gen,
                trading_rules=task.get('tradingRules', ''),
                max_iterations=10
            )
            
            # 执行Agent分析
            result = await agent.run(task['symbol'])
            
            # 获取最终决策
            final_decision_data = result.get('final_decision', {})
            decision = final_decision_data.get('decision') if final_decision_data else None
            
            # 检查Agent是否成功完成分析
            if not final_decision_data or not decision or decision == 'UNKNOWN':
                await client.close()
                return ExecutionResult(
                    execution_id=execution_id,
                    status="failed",
                    task_id=task_id,
                    task_name=task.get('name', ''),
                    symbol=task.get('symbol', ''),
                    start_time=start_time,
                    end_time=datetime.now().isoformat(),
                    error="Agent执行失败：未能获取有效决策（可能因网络问题与模型服务器断开连接）"
                )
            
            decision_type = final_decision_data.get('decision', 'UNKNOWN')
            trade_order_data = final_decision_data.get('trade_order')
            
            # 执行交易
            trade_result = None
            if decision_type in ['OPEN', 'CLOSE'] and trade_order_data:
                try:
                    symbol = trade_order_data.get('symbol', task['symbol'])
                    if hasattr(client, 'normalize_inst_id'):
                        symbol = client.normalize_inst_id(symbol)
                    
                    trade_result = await client.execute_trade(
                        decision=decision_type,
                        symbol=symbol,
                        trade_order=trade_order_data
                    )
                except Exception as e:
                    trade_result = {'error': f'交易执行失败: {str(e)}', 'executed': False}
            
            # 构建FinalDecision
            final_decision = FinalDecision(
                decision=decision_type,
                reason=final_decision_data.get('reason', ''),
                confidence=final_decision_data.get('confidence', 0),
                actionTaken=trade_result is not None and trade_result.get('executed', False)
            )
            
            if trade_order_data:
                final_decision.trade_order = TradeOrder(
                    symbol=trade_order_data.get('symbol', ''),
                    side=trade_order_data.get('side', ''),
                    size=trade_order_data.get('size', ''),
                    size_calculation=trade_order_data.get('size_calculation')
                )
            
            # 转换iterations
            iterations = self._convert_iterations(result.get('execution_log', []))
            
            # 计算总token使用量
            total_tokens = {'input': 0, 'output': 0, 'total': 0}
            for iteration in iterations:
                tokens = iteration.get('tokens', {})
                total_tokens['input'] += tokens.get('input', 0)
                total_tokens['output'] += tokens.get('output', 0)
                total_tokens['total'] += tokens.get('total', 0)
            
            await client.close()
            
            return ExecutionResult(
                execution_id=execution_id,
                status="completed",
                task_id=task_id,
                task_name=task.get('name', ''),
                symbol=task.get('symbol', ''),
                start_time=start_time,
                end_time=datetime.now().isoformat(),
                final_decision=final_decision,
                trade_result=trade_result,
                iterations=iterations,
                total_tokens=total_tokens
            )
            
        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                task_id=task_id,
                task_name=task.get('name', '') if task else '',
                symbol=task.get('symbol', '') if task else '',
                start_time=start_time,
                end_time=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def execute_task_with_config(self, task: dict, execution_id: str) -> ExecutionResult:
        """
        使用传入的配置执行任务（用于API服务直接调用）

        Args:
            task: 任务配置字典
            execution_id: 执行记录ID

        Returns:
            ExecutionResult: 执行结果
        """
        # 加载账户和模型配置
        models = load_json_file(MODELS_FILE, [])
        accounts = load_json_file(ACCOUNTS_FILE, [])

        task_id = task.get('id', '')

        # 获取账户信息
        account_info = None
        account_name = ""
        for acc in accounts:
            if acc['id'] == task.get('accountId'):
                account_info = acc
                account_name = acc.get('name', '')
                break

        # 获取模型信息
        model_config = None
        model_name = ""
        model_provider = ""
        for m in models:
            if m['id'] == task.get('modelId'):
                model_config = m
                model_name = m.get('name', '')
                model_provider = m.get('provider', '')
                break

        start_time = datetime.now().isoformat()

        try:
            if not model_config:
                raise Exception("模型配置不存在")
            if not account_info:
                raise Exception("交易账户配置不存在")

            # 创建交易所客户端
            client = create_exchange_client(
                exchange=account_info['exchange'],
                api_key=account_info['apiKey'],
                api_secret=account_info['apiSecret'],
                passphrase=account_info.get('passphrase', ''),
                simulated=account_info.get('isSimulated', True),
                proxy=os.getenv("HTTP_PROXY")
            )

            # 创建LLM客户端
            llm = create_llm_client(
                provider=model_config['provider'],
                api_key=model_config['apiKey'],
                model=model_config['name'],
                base_url=model_config['baseUrl']
            )

            chart_gen = ChartGenerator()

            # 创建Agent
            agent = TradingAgent(
                llm_client=llm,
                exchange_client=client,
                chart_generator=chart_gen,
                trading_rules=task.get('tradingRules', ''),
                max_iterations=10
            )

            # 执行Agent分析
            result = await agent.run(task['symbol'])

            # 获取最终决策
            final_decision_data = result.get('final_decision', {})
            decision = final_decision_data.get('decision') if final_decision_data else None

            # 检查Agent是否成功完成分析
            if not final_decision_data or not decision or decision == 'UNKNOWN':
                await client.close()
                return ExecutionResult(
                    execution_id=execution_id,
                    status="failed",
                    task_id=task_id,
                    task_name=task.get('name', ''),
                    symbol=task.get('symbol', ''),
                    start_time=start_time,
                    end_time=datetime.now().isoformat(),
                    error="Agent执行失败：未能获取有效决策（可能因网络问题与模型服务器断开连接）"
                )

            decision_type = final_decision_data.get('decision', 'UNKNOWN')
            trade_order_data = final_decision_data.get('trade_order')

            # 执行交易
            trade_result = None
            if decision_type in ['OPEN', 'CLOSE'] and trade_order_data:
                try:
                    symbol = trade_order_data.get('symbol', task['symbol'])
                    if hasattr(client, 'normalize_inst_id'):
                        symbol = client.normalize_inst_id(symbol)

                    trade_result = await client.execute_trade(
                        decision=decision_type,
                        symbol=symbol,
                        trade_order=trade_order_data
                    )
                except Exception as e:
                    trade_result = {'error': f'交易执行失败: {str(e)}', 'executed': False}

            # 构建FinalDecision
            final_decision = FinalDecision(
                decision=decision_type,
                reason=final_decision_data.get('reason', ''),
                confidence=final_decision_data.get('confidence', 0),
                actionTaken=trade_result is not None and trade_result.get('executed', False)
            )

            if trade_order_data:
                final_decision.trade_order = TradeOrder(
                    symbol=trade_order_data.get('symbol', ''),
                    side=trade_order_data.get('side', ''),
                    size=trade_order_data.get('size', ''),
                    size_calculation=trade_order_data.get('size_calculation')
                )

            # 转换iterations
            iterations = self._convert_iterations(result.get('execution_log', []))

            # 计算总token使用量
            total_tokens = {'input': 0, 'output': 0, 'total': 0}
            for iteration in iterations:
                tokens = iteration.get('tokens', {})
                total_tokens['input'] += tokens.get('input', 0)
                total_tokens['output'] += tokens.get('output', 0)
                total_tokens['total'] += tokens.get('total', 0)

            await client.close()

            return ExecutionResult(
                execution_id=execution_id,
                status="completed",
                task_id=task_id,
                task_name=task.get('name', ''),
                symbol=task.get('symbol', ''),
                account_id=task.get('accountId'),
                model_id=task.get('modelId'),
                trading_rules=task.get('tradingRules'),
                start_time=start_time,
                end_time=datetime.now().isoformat(),
                final_decision=final_decision,
                trade_result=trade_result,
                iterations=iterations,
                total_tokens=total_tokens
            )

        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                task_id=task_id,
                task_name=task.get('name', '') if task else '',
                symbol=task.get('symbol', '') if task else '',
                account_id=task.get('accountId') if task else None,
                model_id=task.get('modelId') if task else None,
                start_time=start_time,
                end_time=datetime.now().isoformat(),
                error=str(e)
            )

    def _convert_iterations(self, execution_log: list) -> list:
        """将agent的execution_log转换为前端需要的iterations格式"""
        iterations = []
        for log in execution_log:
            tool_calls = []
            for tc in log.get("tool_calls", []):
                result = tc.get("result", None)
                # 移除chart_url以减小JSON大小，但保留chart_local_path
                if result and isinstance(result, dict) and "chart_url" in result:
                    result = {k: v for k, v in result.items() if k != "chart_url"}
                tool_call = {
                    "tool": tc.get("name", ""),
                    "params": tc.get("arguments", {}),
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                tool_calls.append(tool_call)

            tokens_data = log.get("tokens", {})
            tokens = {
                "input": tokens_data.get("input", 0),
                "output": tokens_data.get("output", 0),
                "total": tokens_data.get("total", 0)
            }

            iterations.append({
                "iteration": log.get("iteration", 0),
                "maxIterations": 10,
                "messages": [],
                "toolCalls": tool_calls,
                "tokens": tokens
            })
        return iterations
    
    async def notify_api_service(self, result: ExecutionResult) -> bool:
        """
        通知API服务执行结果

        Args:
            result: 执行结果

        Returns:
            bool: 是否通知成功
        """
        try:
            result_json = result.model_dump()
            # 处理final_decision中的None值（但trade_order保持None）
            if result_json.get('final_decision'):
                for key, value in list(result_json['final_decision'].items()):
                    if value is None and key != 'trade_order':
                        result_json['final_decision'][key] = ""

            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.api_url}/api/internal/execution-result",
                    json=result_json
                ) as response:
                    print(f"[AgentExecutor] 通知API服务: status={response.status}")
                    return response.status == 200
        except Exception as e:
            print(f"[AgentExecutor] 通知API服务失败: {e}")
            return False
