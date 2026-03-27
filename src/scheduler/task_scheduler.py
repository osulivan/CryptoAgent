"""
定时任务调度器
使用APScheduler定时触发Agent执行交易分析
"""
from typing import Callable, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger


class TradingTaskScheduler:
    """交易任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
    
    def start(self):
        """启动调度器"""
        self.scheduler.start()
        print("✅ 任务调度器已启动")
    
    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        print("⏹️ 任务调度器已关闭")
    
    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        minutes: int = 5,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None
    ):
        """
        添加定时任务（按间隔）
        
        Args:
            func: 要执行的函数
            job_id: 任务ID
            minutes: 间隔分钟数
            args: 函数位置参数
            kwargs: 函数关键字参数
        """
        job = self.scheduler.add_job(
            func=func,
            trigger=IntervalTrigger(minutes=minutes),
            id=job_id,
            args=args,
            kwargs=kwargs,
            replace_existing=True
        )
        self.jobs[job_id] = job
        print(f"⏰ 已添加定时任务: {job_id} (每 {minutes} 分钟)")
        return job
    
    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        minute: str = "*/5",
        hour: str = "*",
        day: str = "*",
        month: str = "*",
        day_of_week: str = "*",
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None
    ):
        """
        添加定时任务（Cron表达式）
        
        Args:
            func: 要执行的函数
            job_id: 任务ID
            minute: 分钟 (如 "*/5" 表示每5分钟)
            hour: 小时
            day: 日期
            month: 月份
            day_of_week: 星期
            args: 函数位置参数
            kwargs: 函数关键字参数
        """
        job = self.scheduler.add_job(
            func=func,
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            ),
            id=job_id,
            args=args,
            kwargs=kwargs,
            replace_existing=True
        )
        self.jobs[job_id] = job
        print(f"⏰ 已添加定时任务: {job_id} (Cron: {minute} {hour} {day} {month} {day_of_week})")
        return job
    
    def remove_job(self, job_id: str):
        """移除任务"""
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            print(f"🗑️ 已移除任务: {job_id}")
    
    def pause_job(self, job_id: str):
        """暂停任务"""
        if job_id in self.jobs:
            self.scheduler.pause_job(job_id)
            print(f"⏸️ 已暂停任务: {job_id}")
    
    def resume_job(self, job_id: str):
        """恢复任务"""
        if job_id in self.jobs:
            self.scheduler.resume_job(job_id)
            print(f"▶️ 已恢复任务: {job_id}")
    
    def get_jobs(self):
        """获取所有任务"""
        return self.scheduler.get_jobs()
    
    def print_jobs(self):
        """打印所有任务"""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            print("当前没有定时任务")
            return
        
        print("\n当前定时任务列表:")
        print("-" * 60)
        for job in jobs:
            print(f"  ID: {job.id}")
            print(f"  下次执行: {job.next_run_time}")
            print(f"  触发器: {job.trigger}")
            print("-" * 60)


# 全局调度器实例
scheduler = TradingTaskScheduler()


async def run_trading_agent(agent, symbol: str = "BTC-USDT-SWAP"):
    """
    包装函数：运行交易Agent
    
    Args:
        agent: TradingAgent实例
        symbol: 交易对
    """
    try:
        result = await agent.run(symbol)
        print(f"\n{'='*60}")
        print(f"📊 交易分析完成")
        print(f"决策: {result.get('final_decision', {})}")
        print(f"迭代次数: {result.get('iterations', 0)}")
        print(f"{'='*60}\n")
        return result
    except Exception as e:
        print(f"❌ 交易分析失败: {e}")
        import traceback
        traceback.print_exc()
