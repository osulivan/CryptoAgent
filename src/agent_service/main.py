"""
Agent服务主入口
FastAPI应用，提供HTTP接口供API服务调用
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..shared.constants import DEFAULT_EXECUTOR_PORT, DEFAULT_API_URL
from ..shared.schemas import ExecuteRequest, ExecuteResponse
from .scheduler import AgentScheduler

# 全局调度器实例
scheduler: AgentScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler
    
    # 启动时初始化
    api_url = os.getenv("API_SERVICE_URL", DEFAULT_API_URL)
    scheduler = AgentScheduler(api_url)
    scheduler.start()
    
    print(f"✅ Agent服务已启动，API服务地址: {api_url}")
    
    yield
    
    # 关闭时清理
    scheduler.shutdown()
    print("⏹️ Agent服务已关闭")


app = FastAPI(
    title="TradeBot Agent Service",
    description="交易Agent执行服务",
    version="1.0.0",
    lifespan=lifespan
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[Agent] 收到请求: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"[Agent] 响应: {request.method} {request.url.path} -> {response.status_code}")
    return response

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "agent",
        "scheduler_running": scheduler is not None and scheduler.scheduler.running
    }


@app.post("/execute", response_model=ExecuteResponse)
async def execute_task(request: ExecuteRequest):
    """
    执行单次任务

    Args:
        request: 执行请求

    Returns:
        ExecuteResponse: 执行响应（立即返回execution_id）
    """
    print(f"[Agent] === 收到执行请求 ===")
    print(f"[Agent] request type: {type(request)}")
    print(f"[Agent] request.task type: {type(request.task)}")
    print(f"[Agent] task_id={getattr(request.task, 'id', 'N/A')}, execution_id={request.execution_id}")
    try:
        # 在后台执行任务
        task_dict = dict(request.task) if hasattr(request.task, 'model_dump') else request.task
        print(f"[Agent] 调用 scheduler.execute_task_now... task={task_dict.get('id')}")
        execution_id = await scheduler.execute_task_now(task_dict, request.execution_id)
        print(f"[Agent] 任务已调度: execution_id={execution_id}")

        return ExecuteResponse(
            execution_id=execution_id,
            status="running",
            message="任务已启动，正在后台执行"
        )
    except Exception as e:
        import traceback
        print(f"[Agent] 执行任务异常: {type(e).__name__}: {str(e)}")
        print(f"[Agent] 异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"启动任务失败: {type(e).__name__}: {str(e)}")


@app.post("/tasks/{task_id}/reload")
async def reload_task(task_id: str):
    """
    重新加载任务（当任务配置变更时调用）
    
    Args:
        task_id: 任务ID
        
    Returns:
        dict: 操作结果
    """
    import time
    import traceback
    from ..shared.constants import TASKS_FILE
    from ..shared.storage import load_json_file
    
    start_time = time.time()
    print(f"[Agent] 开始处理任务重新加载: {task_id}")
    
    try:
        tasks = load_json_file(TASKS_FILE, [])
        task = None
        for t in tasks:
            if t['id'] == task_id:
                task = t
                break
        
        if not task:
            print(f"[Agent] 任务不存在: {task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")
        
        print(f"[Agent] 找到任务: {task_id}, isActive={task.get('isActive', False)}")
        
        # 更新调度器中的任务
        scheduler.update_task(task)
        
        elapsed = time.time() - start_time
        print(f"[Agent] 任务重新加载完成: {task_id}, elapsed={elapsed:.2f}s")
        
        return {
            "success": True,
            "message": f"任务 {task_id} 已重新加载"
        }
    except Exception as e:
        print(f"[Agent] 任务重新加载失败: {task_id}, error={type(e).__name__}: {e}")
        print(f"[Agent] 异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"任务重新加载失败: {type(e).__name__}: {e}")


@app.delete("/tasks/{task_id}")
async def remove_task(task_id: str):
    """
    移除任务（当任务被停用时调用）
    
    Args:
        task_id: 任务ID
        
    Returns:
        dict: 操作结果
    """
    scheduler.remove_task(task_id)
    
    return {
        "success": True,
        "message": f"任务 {task_id} 已移除"
    }


@app.get("/tasks")
async def list_scheduled_tasks():
    """
    获取当前调度的任务列表
    
    Returns:
        dict: 任务列表
    """
    jobs = []
    for job_id, job in scheduler.jobs.items():
        jobs.append({
            "id": job_id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "tasks": jobs,
        "total": len(jobs)
    }


def start_service():
    """启动Agent服务"""
    import uvicorn
    
    port = int(os.getenv("AGENT_SERVICE_PORT", DEFAULT_EXECUTOR_PORT))
    host = os.getenv("AGENT_SERVICE_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_service()
