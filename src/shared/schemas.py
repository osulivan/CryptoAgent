"""
共享Pydantic模型
用于API服务和Agent服务之间的数据验证
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List


class ModelConfig(BaseModel):
    """模型配置"""
    id: str
    name: str
    provider: str
    baseUrl: str
    apiKey: str
    isDefault: bool = False


class AccountConfig(BaseModel):
    """账户配置"""
    id: str
    name: str
    exchange: str
    apiKey: str
    apiSecret: str
    passphrase: Optional[str] = None
    isSimulated: bool = True


class TaskConfig(BaseModel):
    """任务配置"""
    model_config = {"extra": "ignore"}
    
    id: str
    name: str
    symbol: str
    tradingRules: str
    interval: str
    dailyTime: Optional[str] = None
    modelId: str
    accountId: str
    isActive: bool = False
    lastRunAt: Optional[str] = None
    nextRunAt: Optional[str] = None
    createdAt: Optional[str] = None


class TradeOrder(BaseModel):
    """交易订单"""
    symbol: str
    side: str  # LONG or SHORT
    size: str
    size_calculation: Optional[str] = None

    @field_validator('size', mode='before')
    @classmethod
    def convert_size_to_string(cls, v):
        """将size转换为字符串"""
        if isinstance(v, (int, float)):
            return str(v)
        return v


class FinalDecision(BaseModel):
    """最终决策"""
    decision: str  # OPEN, CLOSE, HOLD
    reason: str
    confidence: float
    trade_order: Optional[TradeOrder] = None
    actionTaken: Optional[bool] = None


class ExecutionResult(BaseModel):
    """执行结果（Agent服务 -> API服务）"""
    execution_id: str
    status: str  # running, completed, failed
    task_id: str
    task_name: str
    symbol: str
    account_id: Optional[str] = None
    model_id: Optional[str] = None
    trading_rules: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    final_decision: Optional[FinalDecision] = None
    trade_result: Optional[Dict[str, Any]] = None
    iterations: List[Dict[str, Any]] = []
    total_tokens: Dict[str, int] = {"input": 0, "output": 0, "total": 0}
    error: Optional[str] = None


class ExecuteRequest(BaseModel):
    """执行任务请求（API服务 -> Agent服务）"""
    model_config = {"extra": "ignore"}
    
    task: Dict[str, Any]
    execution_id: str


class ExecuteResponse(BaseModel):
    """执行任务响应"""
    execution_id: str
    status: str
    message: str
