"""
Agent服务调度器
负责加载任务配置并定时触发执行
"""
import asyncio
from datetime import datetime
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiohttp

from ..shared.constants import TASKS_FILE
from ..shared.storage import load_json_file
from .executor import AgentExecutor


class AgentScheduler:
    """Agent服务调度器"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.scheduler = AsyncIOScheduler()
        self.executor = AgentExecutor(api_url)
        self.jobs: Dict[str, Any] = {}
    
    def start(self):
        """启动调度器"""
        self.scheduler.start()
        print("✅ Agent调度器已启动")
        
        # 加载并启动所有启用的任务
        self.load_tasks()
    
    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        print("⏹️ Agent调度器已关闭")
    
    def load_tasks(self):
        """从JSON文件加载所有启用的任务"""
        tasks = load_json_file(TASKS_FILE, [])
        
        for task in tasks:
            if task.get('isActive', False):
                asyncio.create_task(self.add_task(task))
    
    async def add_task(self, task: dict):
        """
        添加定时任务
        
        Args:
            task: 任务配置
        """
        task_id = task['id']
        interval = task.get('interval', '15m')
        daily_time = task.get('dailyTime')
        
        print(f"[Scheduler] add_task: {task_id}, interval={interval}")
        
        # 根据interval生成cron表达式
        if interval == 'daily':
            # 每日特定时间执行
            if daily_time:
                hour, minute = daily_time.split(':')
                cron_minute = minute
                cron_hour = hour
            else:
                cron_minute = '0'
                cron_hour = '0'
        elif interval == '5m':
            cron_minute = '*/5'
            cron_hour = '*'
        elif interval == '15m':
            cron_minute = '*/15'
            cron_hour = '*'
        elif interval == '1h':
            cron_minute = '0'
            cron_hour = '*'
        elif interval == '4h':
            cron_minute = '0'
            cron_hour = '*/4'
        else:
            # 默认15分钟
            cron_minute = '*/15'
            cron_hour = '*'
        
        # 移除已存在的任务
        if task_id in self.jobs:
            self.remove_task(task_id)
        
        # 添加新任务
        job = self.scheduler.add_job(
            func=self._execute_task_wrapper,
            trigger=CronTrigger(
                minute=cron_minute,
                hour=cron_hour,
                day='*',
                month='*',
                day_of_week='*'
            ),
            id=task_id,
            args=[task_id],
            replace_existing=True
        )
        
        self.jobs[task_id] = job
        
        # 计算并通知API服务更新下次执行时间
        next_run_time = job.next_run_time
        if next_run_time:
            next_run_iso = next_run_time.strftime('%Y-%m-%dT%H:%M:%S')
            await self._update_task_next_run_time(task_id, next_run_iso)
        
        print(f"⏰ 已添加定时任务: {task.get('name', task_id)} ({interval})")
    
    def remove_task(self, task_id: str):
        """
        移除定时任务
        
        Args:
            task_id: 任务ID
        """
        if task_id in self.jobs:
            self.scheduler.remove_job(task_id)
            del self.jobs[task_id]
            print(f"⏹️ 已移除定时任务: {task_id}")
    
    def update_task(self, task: dict):
        """
        更新任务（先移除再添加）
        
        Args:
            task: 任务配置
        """
        task_id = task['id']
        print(f"[Scheduler] update_task called: {task_id}, isActive={task.get('isActive', False)}")
        
        # 如果任务已启用，重新添加
        if task.get('isActive', False):
            asyncio.create_task(self.add_task(task))
        else:
            # 如果任务被禁用，移除
            self.remove_task(task_id)
    
    async def _update_task_next_run_time(self, task_id: str, next_run_time: str) -> bool:
        """
        通知API服务更新任务的下次执行时间

        Args:
            task_id: 任务ID
            next_run_time: 下次执行时间（ISO格式）

        Returns:
            bool: 是否更新成功
        """
        try:
            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.api_url}/api/internal/task-next-run",
                    json={"taskId": task_id, "nextRunAt": next_run_time}
                ) as response:
                    print(f"[Scheduler] 更新任务下次执行时间: task_id={task_id}, next_run={next_run_time}, status={response.status}")
                    return response.status == 200
        except Exception as e:
            print(f"[Scheduler] 更新任务下次执行时间失败: {e}")
            return False
    
    async def _create_running_execution(self, task: dict, execution_id: str) -> bool:
        """
        通知API服务创建"执行中"记录

        Args:
            task: 任务配置
            execution_id: 执行记录ID

        Returns:
            bool: 是否创建成功
        """
        try:
            execution_data = {
                "id": execution_id,
                "taskId": task['id'],
                "taskName": task.get('name', ''),
                "symbol": task.get('symbol', ''),
                "accountId": task.get('accountId'),
                "modelId": task.get('modelId'),
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

            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.api_url}/api/internal/execution-running",
                    json=execution_data
                ) as response:
                    print(f"[Scheduler] 创建执行中记录: status={response.status}")
                    return response.status == 200
        except Exception as e:
            print(f"[Scheduler] 创建执行中记录失败: {e}")
            return False
    
    async def _execute_task_wrapper(self, task_id: str):
        """
        包装执行函数（用于调度器调用）
        
        Args:
            task_id: 任务ID
        """
        from ..shared.storage import generate_id
        
        execution_id = generate_id()
        print(f"[AgentScheduler] 定时触发任务执行: {task_id}, execution_id: {execution_id}")
        
        # 获取任务配置
        tasks = load_json_file(TASKS_FILE, [])
        task = None
        for t in tasks:
            if t['id'] == task_id:
                task = t
                break
        
        if not task:
            print(f"[AgentScheduler] 任务不存在: {task_id}")
            return
        
        # 先创建"执行中"记录
        await self._create_running_execution(task, execution_id)
        
        # 执行任务
        result = await self.executor.execute_task(task_id, execution_id)
        
        # 通知API服务
        notified = await self.executor.notify_api_service(result)
        if notified:
            print(f"[AgentScheduler] 任务执行完成并通知API服务: {execution_id}")
        else:
            print(f"[AgentScheduler] 任务执行完成但通知API服务失败: {execution_id}")
        
        # 更新任务的下次执行时间
        if task_id in self.jobs:
            job = self.jobs[task_id]
            next_run_time = job.next_run_time
            if next_run_time:
                next_run_iso = next_run_time.strftime('%Y-%m-%dT%H:%M:%S')
                await self._update_task_next_run_time(task_id, next_run_iso)
    
    async def execute_task_now(self, task: dict, execution_id: str = None) -> str:
        """
        立即执行一次任务（用于API服务调用）

        Args:
            task: 任务配置字典
            execution_id: 执行记录ID（可选，不传则自动生成）

        Returns:
            str: execution_id
        """
        from ..shared.storage import generate_id

        print(f"[Scheduler] execute_task_now: task_id={task.get('id')}, execution_id={execution_id}")

        if not execution_id:
            execution_id = generate_id()

        # 在后台执行
        asyncio.create_task(self._execute_and_notify_with_task(task, execution_id))

        return execution_id

    async def _execute_and_notify_with_task(self, task: dict, execution_id: str):
        """
        执行任务并通知（后台任务）- 直接传入task对象

        Args:
            task: 任务配置字典
            execution_id: 执行记录ID
        """
        print(f"[Scheduler] _execute_and_notify: 开始执行任务 {execution_id}")
        result = await self.executor.execute_task_with_config(task, execution_id)
        print(f"[Scheduler] _execute_and_notify: 任务执行完成, result.status={result.status}")
        notify_success = await self.executor.notify_api_service(result)
        print(f"[Scheduler] _execute_and_notify: 通知API服务结果: {notify_success}")
