"""
FastAPI Web API for TradeBot
提供前端管理界面所需的REST API
"""
import os
import time
import httpx
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..exchange.factory import create_exchange_client
from ..llm.factory import create_llm_client
from ..shared.constants import MODELS_FILE, TASKS_FILE, EXECUTIONS_FILE, ACCOUNTS_FILE, DEFAULT_EXECUTOR_URL
from ..shared.storage import load_json_file, save_json_file, generate_id
from ..shared.schemas import ExecutionResult


# Pydantic Models
class ModelCreate(BaseModel):
    name: str
    provider: str = "openai-compatible"
    baseUrl: str
    apiKey: str


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    isDefault: Optional[bool] = None


class ModelTest(BaseModel):
    name: str
    provider: str = "openai-compatible"
    baseUrl: str
    apiKey: str


class TaskCreate(BaseModel):
    name: str
    symbol: str
    tradingRules: str
    interval: str = Field(..., pattern="^(5m|15m|1h|4h|daily)$")
    dailyTime: Optional[str] = None
    modelId: str
    accountId: str


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    tradingRules: Optional[str] = None
    interval: Optional[str] = Field(None, pattern="^(5m|15m|1h|4h|daily)$")
    dailyTime: Optional[str] = None
    modelId: Optional[str] = None
    accountId: Optional[str] = None
    isActive: Optional[bool] = None


class AccountCreate(BaseModel):
    name: str
    exchange: str
    apiKey: str
    apiSecret: str
    passphrase: Optional[str] = None
    isSimulated: bool = True


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    passphrase: Optional[str] = None
    isSimulated: Optional[bool] = None


# 全局变量
executor_url: str = DEFAULT_EXECUTOR_URL
http_client: httpx.AsyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global executor_url, http_client
    import sys
    print(f"[API] sys.executable: {sys.executable}")
    print(f"[API] os.getcwd: {os.getcwd()}")
    print(f"[API] AGENT_SERVICE_URL env: {os.getenv('AGENT_SERVICE_URL')}")
    print(f"[API] DEFAULT_EXECUTOR_URL: {DEFAULT_EXECUTOR_URL}")
    executor_url = os.getenv("AGENT_SERVICE_URL", DEFAULT_EXECUTOR_URL)
    http_client = httpx.AsyncClient(timeout=30.0)
    print(f"✅ API服务已启动，Agent服务地址: {executor_url}")
    
    yield
    
    await http_client.aclose()
    print("⏹️ API服务已关闭")


app = FastAPI(
    title="TradeBot API",
    description="交易机器人管理API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "api"}


@app.get("/api/test-agent")
async def test_agent_connection():
    """测试Agent服务连接"""
    import aiohttp
    try:
        timeout = aiohttp.ClientTimeout(total=10.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "http://127.0.0.1:8001/execute",
                json={"task": {"id": "test"}, "execution_id": "test-aiohttp"}
            ) as response:
                text = await response.text()
                return {
                    "status": "ok",
                    "status_code": response.status,
                    "response": text[:500]
                }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ==================== Model APIs ====================

@app.get("/api/models")
async def get_models():
    """获取所有模型"""
    return load_json_file(MODELS_FILE, [])


@app.post("/api/models")
async def create_model(model: ModelCreate):
    """创建模型"""
    models = load_json_file(MODELS_FILE, [])

    # 如果是第一个模型，设为默认
    is_default = len(models) == 0

    new_model = {
        "id": generate_id(),
        "name": model.name,
        "provider": model.provider,
        "baseUrl": model.baseUrl,
        "apiKey": model.apiKey,
        "isDefault": is_default,
        "createdAt": datetime.now().isoformat()
    }

    models.append(new_model)
    save_json_file(MODELS_FILE, models)

    return new_model


@app.put("/api/models/{model_id}")
async def update_model(model_id: str, model: ModelUpdate):
    """更新模型"""
    models = load_json_file(MODELS_FILE, [])

    for i, m in enumerate(models):
        if m['id'] == model_id:
            if model.name is not None:
                m['name'] = model.name
            if model.provider is not None:
                m['provider'] = model.provider
            if model.baseUrl is not None:
                m['baseUrl'] = model.baseUrl
            if model.apiKey is not None:
                m['apiKey'] = model.apiKey
            if model.isDefault is not None:
                if model.isDefault:
                    for other in models:
                        other['isDefault'] = False
                m['isDefault'] = model.isDefault

            save_json_file(MODELS_FILE, models)
            return m

    raise HTTPException(status_code=404, detail="模型不存在")


@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    """删除模型"""
    models = load_json_file(MODELS_FILE, [])
    models = [m for m in models if m['id'] != model_id]
    save_json_file(MODELS_FILE, models)
    return {"success": True}


@app.post("/api/models/test")
async def test_model(config: ModelTest):
    """测试模型连通性"""
    try:
        start_time = time.time()

        llm = create_llm_client(
            provider=config.provider,
            api_key=config.apiKey,
            model=config.name,
            base_url=config.baseUrl
        )

        response = await llm.chat_completion(
            messages=[
                {"role": "user", "content": "你好，请回复'连接测试成功'"}
            ],
            temperature=0.1,
            max_tokens=50
        )

        latency = int((time.time() - start_time) * 1000)

        if response.get("content"):
            content = response["content"]
            return {
                "success": True,
                "message": f"连接成功 - 模型响应: {content[:50]}",
                "latency": latency
            }
        else:
            return {
                "success": False,
                "message": "连接成功但响应格式异常"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }


# ==================== Account APIs ====================

@app.get("/api/accounts")
async def get_accounts():
    """获取所有账户"""
    accounts = load_json_file(ACCOUNTS_FILE, [])
    # 隐藏敏感信息
    for acc in accounts:
        acc['apiKey'] = acc.get('apiKey', '')[:8] + '****'
        acc['apiSecret'] = '****'
        if 'passphrase' in acc:
            acc['passphrase'] = '****'
    return accounts


@app.post("/api/accounts")
async def create_account(account: AccountCreate):
    """创建账户"""
    accounts = load_json_file(ACCOUNTS_FILE, [])

    new_account = {
        "id": generate_id(),
        "name": account.name,
        "exchange": account.exchange,
        "apiKey": account.apiKey,
        "apiSecret": account.apiSecret,
        "passphrase": account.passphrase or "",
        "isSimulated": account.isSimulated,
        "createdAt": datetime.now().isoformat()
    }

    accounts.append(new_account)
    save_json_file(ACCOUNTS_FILE, accounts)

    # 隐藏敏感信息
    new_account['apiKey'] = new_account['apiKey'][:8] + '****'
    new_account['apiSecret'] = '****'
    if 'passphrase' in new_account:
        new_account['passphrase'] = '****'

    return new_account


@app.put("/api/accounts/{account_id}")
async def update_account(account_id: str, account: AccountUpdate):
    """更新账户"""
    accounts = load_json_file(ACCOUNTS_FILE, [])

    for i, acc in enumerate(accounts):
        if acc['id'] == account_id:
            if account.name is not None:
                acc['name'] = account.name
            if account.apiKey is not None:
                acc['apiKey'] = account.apiKey
            if account.apiSecret is not None:
                acc['apiSecret'] = account.apiSecret
            if account.passphrase is not None:
                acc['passphrase'] = account.passphrase
            if account.isSimulated is not None:
                acc['isSimulated'] = account.isSimulated

            save_json_file(ACCOUNTS_FILE, accounts)

            # 隐藏敏感信息
            acc['apiKey'] = acc['apiKey'][:8] + '****'
            acc['apiSecret'] = '****'
            if 'passphrase' in acc:
                acc['passphrase'] = '****'

            return acc

    raise HTTPException(status_code=404, detail="账户不存在")


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str):
    """删除账户"""
    accounts = load_json_file(ACCOUNTS_FILE, [])
    accounts = [acc for acc in accounts if acc['id'] != account_id]
    save_json_file(ACCOUNTS_FILE, accounts)
    return {"success": True}


@app.post("/api/accounts/test")
async def test_account_config(data: dict):
    """测试账户配置连通性（不保存）"""
    try:
        client = create_exchange_client(
            exchange=data.get('exchange', ''),
            api_key=data.get('apiKey', ''),
            api_secret=data.get('apiSecret', ''),
            passphrase=data.get('passphrase', ''),
            simulated=data.get('isSimulated', True),
            proxy=os.getenv("HTTP_PROXY")
        )

        await client.get_account_balance()
        await client.close()

        return {
            "success": True,
            "message": "连接成功"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }


@app.post("/api/accounts/{account_id}/test")
async def test_account(account_id: str):
    """测试账户连通性"""
    accounts = load_json_file(ACCOUNTS_FILE, [])

    account = None
    for acc in accounts:
        if acc['id'] == account_id:
            account = acc
            break

    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    try:
        client = create_exchange_client(
            exchange=account['exchange'],
            api_key=account['apiKey'],
            api_secret=account['apiSecret'],
            passphrase=account.get('passphrase', ''),
            simulated=account.get('isSimulated', True),
            proxy=os.getenv("HTTP_PROXY")
        )

        balance = await client.get_account_balance()
        await client.close()

        return {
            "success": True,
            "message": f"连接成功 - 账户余额: {balance.get('total_equity', 'N/A')} USDT"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }


@app.get("/api/exchanges")
async def get_exchanges():
    """获取支持的交易所列表"""
    return [
        {"id": "okx", "name": "OKX", "description": "OKX交易所"},
        {"id": "binance", "name": "Binance", "description": "币安交易所"},
    ]


@app.get("/api/exchanges/{exchange}/trading-pairs")
async def get_trading_pairs(exchange: str, simulated: bool = True):
    """获取交易所支持的交易对列表
    
    Args:
        exchange: 交易所名称 (okx/binance)
        simulated: 是否获取模拟盘/测试网的交易对，默认为True
    """
    try:
        # 创建临时客户端获取交易对，根据simulated参数决定使用实盘还是测试网
        client = create_exchange_client(
            exchange=exchange,
            api_key="",
            api_secret="",
            simulated=simulated
        )

        # 根据交易所获取对应类型的合约
        inst_type = "SWAP" if exchange == "okx" else "PERPETUAL"
        pairs = await client.get_instruments(inst_type=inst_type)
        await client.close()

        # 统一数据格式，转换为前端期望的格式
        unified_pairs = []
        for pair in pairs:
            if exchange == "okx":
                # OKX格式处理 - 从instId解析baseCcy和quoteCcy
                inst_id = pair.get("instId", "")
                # instId格式: BTC-USD-SWAP 或 BTC-USDT-SWAP
                parts = inst_id.split("-")
                base_ccy = parts[0] if len(parts) > 0 else ""
                quote_ccy = parts[1] if len(parts) > 1 else ""

                unified_pairs.append({
                    "instId": inst_id,
                    "baseCcy": base_ccy,
                    "quoteCcy": quote_ccy,
                    "instType": pair.get("instType", ""),
                    "lotSz": pair.get("lotSz", ""),
                    "minSz": pair.get("minSz", ""),
                    "tickSz": pair.get("tickSz", "")
                })
            elif exchange == "binance":
                # Binance格式需要转换
                unified_pairs.append({
                    "instId": pair.get("symbol", ""),
                    "baseCcy": pair.get("baseAsset", ""),
                    "quoteCcy": pair.get("quoteAsset", ""),
                    "instType": "SWAP",
                    "lotSz": str(pair.get("quantityPrecision", 3)),
                    "minSz": str(pair.get("filters", [{}])[2].get("minQty", "0.001") if len(pair.get("filters", [])) > 2 else "0.001"),
                    "tickSz": str(pair.get("pricePrecision", 2))
                })

        return unified_pairs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易对失败: {str(e)}")


# ==================== Task APIs ====================

@app.get("/api/tasks")
async def get_tasks():
    """获取所有任务"""
    tasks = load_json_file(TASKS_FILE, [])
    accounts = load_json_file(ACCOUNTS_FILE, [])
    models = load_json_file(MODELS_FILE, [])
    executions = load_json_file(EXECUTIONS_FILE, [])

    account_map = {acc['id']: acc for acc in accounts}
    model_map = {m['id']: m for m in models}

    for task in tasks:
        account = account_map.get(task.get('accountId', ''))
        model = model_map.get(task.get('modelId', ''))

        task['accountName'] = account['name'] if account else '未知账户'
        task['accountExchange'] = account['exchange'] if account else 'unknown'
        task['modelName'] = model['name'] if model else '未知模型'
        
        # 计算该任务的Token使用量
        task_executions = [e for e in executions if e.get('taskId') == task['id']]
        total_tokens = {"input": 0, "output": 0, "total": 0}
        for execution in task_executions:
            exec_tokens = execution.get("totalTokens", {})
            total_tokens["input"] += exec_tokens.get("input", 0)
            total_tokens["output"] += exec_tokens.get("output", 0)
            total_tokens["total"] += exec_tokens.get("total", 0)
        task['totalTokens'] = total_tokens

    return tasks


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    """创建任务"""
    tasks = load_json_file(TASKS_FILE, [])

    new_task = {
        "id": generate_id(),
        "name": task.name,
        "symbol": task.symbol,
        "tradingRules": task.tradingRules,
        "interval": task.interval,
        "dailyTime": task.dailyTime,
        "modelId": task.modelId,
        "accountId": task.accountId,
        "isActive": False,
        "createdAt": datetime.now().isoformat()
    }

    tasks.append(new_task)
    save_json_file(TASKS_FILE, tasks)

    return new_task


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task: TaskUpdate):
    """更新任务"""
    tasks = load_json_file(TASKS_FILE, [])

    for i, t in enumerate(tasks):
        if t['id'] == task_id:
            was_active = t.get('isActive', False)

            if task.name is not None:
                t['name'] = task.name
            if task.symbol is not None:
                t['symbol'] = task.symbol
            if task.tradingRules is not None:
                t['tradingRules'] = task.tradingRules
            if task.interval is not None:
                t['interval'] = task.interval
            if task.dailyTime is not None:
                t['dailyTime'] = task.dailyTime
            if task.modelId is not None:
                t['modelId'] = task.modelId
            if task.accountId is not None:
                t['accountId'] = task.accountId
            if task.isActive is not None:
                t['isActive'] = task.isActive

            save_json_file(TASKS_FILE, tasks)

            # 通知Agent服务任务变更
            new_active = t.get('isActive', False)
            if was_active != new_active or new_active:
                await _notify_executor_task_updated(task_id)

            return t

    raise HTTPException(status_code=404, detail="任务不存在")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    tasks = load_json_file(TASKS_FILE, [])

    for t in tasks:
        if t['id'] == task_id:
            tasks = [task for task in tasks if task['id'] != task_id]
            save_json_file(TASKS_FILE, tasks)

            # 通知Agent服务任务被删除
            await _notify_executor_task_removed(task_id)

            return {"success": True}

    raise HTTPException(status_code=404, detail="任务不存在")


@app.post("/api/tasks/{task_id}/toggle")
async def toggle_task(task_id: str):
    """切换任务启用状态 - 先更新JSON，再通知Agent"""
    tasks = load_json_file(TASKS_FILE, [])

    for t in tasks:
        if t['id'] == task_id:
            new_is_active = not t.get('isActive', False)
            
            # 1. 先更新JSON（让Agent能读取到最新状态）
            t['isActive'] = new_is_active
            save_json_file(TASKS_FILE, tasks)
            print(f"[API] 任务状态已更新: {task_id}, isActive={new_is_active}")
            
            # 2. 通知Agent服务
            if new_is_active:
                # 启用任务：通知Agent添加任务
                agent_success = await _notify_executor_task_updated(task_id)
            else:
                # 停用任务：通知Agent移除任务
                agent_success = await _notify_executor_task_removed(task_id)
            
            # 3. Agent失败时回滚
            if agent_success:
                print(f"[API] 任务状态切换成功: {task_id}, isActive={new_is_active}")
                return {"success": True, "isActive": new_is_active}
            else:
                # Agent失败，回滚JSON
                t['isActive'] = not new_is_active  # 恢复原状态
                save_json_file(TASKS_FILE, tasks)
                print(f"[API] 任务状态切换失败 - Agent服务未响应，已回滚: {task_id}")
                raise HTTPException(status_code=503, detail="Agent服务未响应，请检查Agent服务是否正常运行")

    raise HTTPException(status_code=404, detail="任务不存在")


@app.post("/api/tasks/{task_id}/run-once")
async def run_task_once(task_id: str):
    """立即执行一次任务"""
    tasks = load_json_file(TASKS_FILE, [])

    task = None
    for t in tasks:
        if t['id'] == task_id:
            task = t
            break

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 确保任务数据包含所有必需字段
    required_fields = ['id', 'name', 'symbol', 'tradingRules', 'interval', 'modelId', 'accountId']
    for field in required_fields:
        if field not in task:
            task[field] = ''
    
    if 'dailyTime' not in task:
        task['dailyTime'] = '09:00'
    if 'isActive' not in task:
        task['isActive'] = False

    # 调用Agent服务执行任务
    import logging
    import traceback
    import sys
    import asyncio
    logger = logging.getLogger(__name__)
    try:
        execution_id = generate_id()
        
        # 先创建"执行中"的记录
        # 查询账户和模型名称
        account_name = ""
        model_name = ""
        
        accounts = load_json_file(ACCOUNTS_FILE, [])
        for acc in accounts:
            if acc['id'] == task.get('accountId'):
                account_name = acc.get('name', '')
                break
        
        models = load_json_file(MODELS_FILE, [])
        for m in models:
            if m['id'] == task.get('modelId'):
                model_name = m.get('name', '')
                break
        
        executions = load_json_file(EXECUTIONS_FILE, [])
        running_execution = {
            "id": execution_id,
            "taskId": task['id'],
            "taskName": task.get('name', ''),
            "symbol": task.get('symbol', ''),
            "accountId": task.get('accountId'),
            "accountName": account_name,
            "modelId": task.get('modelId'),
            "modelName": model_name,
            "tradingRules": task.get('tradingRules'),
            "status": "running",
            "startTime": datetime.now().isoformat(),
            "endTime": None,
            "finalDecision": None,
            "tradeResult": None,
            "iterations": [],
            "totalTokens": {"input": 0, "output": 0, "total": 0},
            "error": None
        }
        executions.append(running_execution)
        save_json_file(EXECUTIONS_FILE, executions)
        
        import aiohttp
        import json as json_module
        
        timeout = aiohttp.ClientTimeout(total=30.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "http://127.0.0.1:8001/execute",
                json={"task": task, "execution_id": execution_id}
            ) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    response_data = json_module.loads(response_text)
                    return {
                        "success": True,
                        "message": "任务已启动",
                        "execution_id": response_data.get("execution_id")
                    }
                else:
                    # 启动失败，更新记录状态为失败
                    executions = load_json_file(EXECUTIONS_FILE, [])
                    for e in executions:
                        if e['id'] == execution_id:
                            e['status'] = 'failed'
                            e['endTime'] = datetime.now().isoformat()
                            e['error'] = f"启动任务失败: HTTP {response.status}"
                            break
                    save_json_file(EXECUTIONS_FILE, executions)
                    raise HTTPException(
                        status_code=500,
                        detail=f"启动任务失败: HTTP {response.status}"
                    )
    except Exception as e:
        print(f"[API] ERROR: 执行任务异常: {type(e).__name__}: {str(e)}", flush=True)
        print(f"[API] ERROR: 异常堆栈: {traceback.format_exc()}", flush=True)
        raise HTTPException(
            status_code=503,
            detail=f"无法连接到Agent服务: {type(e).__name__}: {str(e)}"
        )


# ==================== Execution APIs ====================

@app.get("/api/executions")
async def get_executions(limit: int = 50, offset: int = 0, task_id: Optional[str] = None):
    """获取执行历史"""
    executions = load_json_file(EXECUTIONS_FILE, [])

    if task_id:
        executions = [e for e in executions if e.get('taskId') == task_id]

    executions.sort(key=lambda x: x.get('startTime', ''), reverse=True)

    total = len(executions)
    executions = executions[offset:offset + limit]

    return {
        "items": executions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/executions/stats")
async def get_execution_stats():
    """获取执行统计"""
    executions = load_json_file(EXECUTIONS_FILE, [])

    today = datetime.now().date()
    today_executions = [
        e for e in executions
        if datetime.fromisoformat(e.get('startTime', '1970-01-01')).date() == today
    ]

    total_tokens = {"input": 0, "output": 0, "total": 0}
    for execution in executions:
        exec_tokens = execution.get("totalTokens", {})
        total_tokens["input"] += exec_tokens.get("input", 0)
        total_tokens["output"] += exec_tokens.get("output", 0)
        total_tokens["total"] += exec_tokens.get("total", 0)

    return {
        "totalExecutions": len(today_executions),
        "completedExecutions": len([e for e in today_executions if e.get('status') == 'completed']),
        "failedExecutions": len([e for e in today_executions if e.get('status') == 'failed']),
        "buyDecisions": len([e for e in today_executions if e.get('finalDecision', {}).get('decision') == 'BUY']),
        "sellDecisions": len([e for e in today_executions if e.get('finalDecision', {}).get('decision') == 'SELL']),
        "holdDecisions": len([e for e in today_executions if e.get('finalDecision', {}).get('decision') == 'HOLD']),
        "totalTokens": total_tokens,
    }


@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    """获取单个执行记录"""
    executions = load_json_file(EXECUTIONS_FILE, [])
    for e in executions:
        if e.get('id') == execution_id:
            return e
    raise HTTPException(status_code=404, detail="执行记录不存在")


@app.delete("/api/executions/{execution_id}")
async def delete_execution(execution_id: str):
    """删除单条执行记录"""
    executions = load_json_file(EXECUTIONS_FILE, [])

    original_len = len(executions)
    executions = [e for e in executions if e.get('id') != execution_id]

    if len(executions) == original_len:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    save_json_file(EXECUTIONS_FILE, executions)
    return {"success": True}


@app.delete("/api/executions")
async def clear_executions():
    """清空所有执行记录"""
    save_json_file(EXECUTIONS_FILE, [])
    return {"success": True}


# ==================== Chart APIs ====================

@app.get("/api/charts/{filename}")
async def get_chart(filename: str):
    """
    获取K线图表图片
    """
    chart_path = os.path.join("charts", filename)
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="图表不存在")
    return FileResponse(chart_path, media_type="image/png")


# ==================== Internal APIs (Agent服务回调) ====================

@app.post("/api/internal/task-next-run")
async def update_task_next_run(request: Request):
    """
    更新任务的下次执行时间
    内部接口，由Agent服务调用
    """
    try:
        data = await request.json()
        task_id = data.get('taskId')
        next_run_at = data.get('nextRunAt')
        
        if not task_id or not next_run_at:
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 更新任务的下次执行时间
        tasks = load_json_file(TASKS_FILE, [])
        for t in tasks:
            if t['id'] == task_id:
                t['nextRunAt'] = next_run_at
                break
        
        save_json_file(TASKS_FILE, tasks)
        print(f"[API] 已更新任务下次执行时间: {task_id} -> {next_run_at}")
        return {"success": True}
    except Exception as e:
        print(f"[API] 更新任务下次执行时间失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/internal/execution-running")
async def create_running_execution(request: Request):
    """
    创建"执行中"的执行记录
    内部接口，由Agent服务调用（定时任务开始时）
    """
    try:
        data = await request.json()
        
        # 获取账户和模型名称
        account_name = ""
        model_name = ""
        
        accounts = load_json_file(ACCOUNTS_FILE, [])
        for acc in accounts:
            if acc['id'] == data.get('accountId'):
                account_name = acc.get('name', '')
                break
        
        models = load_json_file(MODELS_FILE, [])
        for m in models:
            if m['id'] == data.get('modelId'):
                model_name = m.get('name', '')
                break
        
        # 添加账户和模型名称
        data['accountName'] = account_name
        data['modelName'] = model_name
        
        # 保存执行记录
        executions = load_json_file(EXECUTIONS_FILE, [])
        executions.append(data)
        save_json_file(EXECUTIONS_FILE, executions)
        
        print(f"[API] 已创建执行中记录: {data.get('id')}")
        return {"success": True}
    except Exception as e:
        print(f"[API] 创建执行中记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/internal/execution-result")
async def receive_execution_result(request: Request):
    """
    接收Agent服务的执行结果
    内部接口，由Agent服务调用
    """
    try:
        import json
        body = await request.body()
        data = json.loads(body)
        print(f"[API] 收到执行结果原始数据: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
        
        # 手动转换为ExecutionResult
        result = ExecutionResult(**data)
        print(f"[API] 解析成功: execution_id={result.execution_id}, status={result.status}")
        # 获取账户和模型信息
        account_name = ""
        model_name = ""
        
        accounts = load_json_file(ACCOUNTS_FILE, [])
        for acc in accounts:
            if acc['id'] == result.account_id:
                account_name = acc.get('name', '')
                break
        
        models = load_json_file(MODELS_FILE, [])
        for m in models:
            if m['id'] == result.model_id:
                model_name = m.get('name', '')
                break
        
        # 转换为前端格式
        execution = {
            "id": result.execution_id,
            "taskId": result.task_id,
            "taskName": result.task_name,
            "symbol": result.symbol,
            "accountId": result.account_id,
            "accountName": account_name,
            "modelId": result.model_id,
            "modelName": model_name,
            "tradingRules": result.trading_rules,
            "status": result.status,
            "startTime": result.start_time,
            "endTime": result.end_time,
            "finalDecision": result.final_decision.model_dump() if result.final_decision else None,
            "tradeResult": result.trade_result,
            "iterations": result.iterations,
            "totalTokens": result.total_tokens,
            "error": result.error
        }

        # 保存执行记录
        executions = load_json_file(EXECUTIONS_FILE, [])

        # 查找是否已存在（更新）
        found = False
        for i, e in enumerate(executions):
            if e.get('id') == result.execution_id:
                # 保留原有的accountId、modelId、tradingRules（如果result中没有）
                if not execution.get('accountId') and e.get('accountId'):
                    execution['accountId'] = e.get('accountId')
                    execution['accountName'] = e.get('accountName', '')
                if not execution.get('modelId') and e.get('modelId'):
                    execution['modelId'] = e.get('modelId')
                    execution['modelName'] = e.get('modelName', '')
                if not execution.get('tradingRules') and e.get('tradingRules'):
                    execution['tradingRules'] = e.get('tradingRules')
                executions[i] = execution
                found = True
                break

        if not found:
            executions.append(execution)

        save_json_file(EXECUTIONS_FILE, executions)

        # 更新任务最后执行时间
        tasks = load_json_file(TASKS_FILE, [])
        for t in tasks:
            if t['id'] == result.task_id:
                t['lastRunAt'] = result.end_time or result.start_time
                break
        save_json_file(TASKS_FILE, tasks)

        return {"success": True}

    except Exception as e:
        import traceback
        print(f"[API] 保存执行结果失败: {e}")
        print(f"[API] 错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"保存执行结果失败: {str(e)}")


# ==================== Helper Functions ====================

async def _notify_executor_task_updated(task_id: str) -> bool:
    """通知Agent服务任务已更新（同步等待，确保Agent添加任务成功）"""
    import aiohttp
    url = f"http://127.0.0.1:8001/tasks/{task_id}/reload"
    print(f"[API] 正在通知Agent服务: {url}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print(f"[API] 发送 POST 请求到: {url}")
            async with session.post(url) as response:
                print(f"[API] 通知Agent服务任务更新: task_id={task_id}, status={response.status}")
                return response.status == 200
    except Exception as e:
        print(f"[API] 通知Agent服务任务更新失败: task_id={task_id}, error={type(e).__name__}: {e}")
        return False


async def _notify_executor_task_removed(task_id: str) -> bool:
    """通知Agent服务任务已删除（同步等待，确保Agent删除任务成功）"""
    import aiohttp
    url = f"http://127.0.0.1:8001/tasks/{task_id}"
    print(f"[API] 正在通知Agent服务: {url}")
    try:
        timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print(f"[API] 发送 DELETE 请求到: {url}")
            async with session.delete(url) as response:
                print(f"[API] 通知Agent服务任务删除: task_id={task_id}, status={response.status}")
                return response.status == 200
    except Exception as e:
        print(f"[API] 通知Agent服务任务删除失败: task_id={task_id}, error={type(e).__name__}: {e}")
        return False


# ==================== Static Files ====================

@app.get("/")
async def root():
    """根路径返回前端页面"""
    frontend_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "frontend", "dist", "index.html"
    )
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "TradeBot API is running"}


@app.get("/{path:path}")
async def static_files(path: str):
    """静态文件服务"""
    frontend_dist = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "frontend", "dist"
    )

    file_path = os.path.join(frontend_dist, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not found")
