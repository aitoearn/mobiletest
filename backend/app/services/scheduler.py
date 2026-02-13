import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from croniter import croniter
import logging
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    WORKFLOW = "workflow"
    TEST_CASE = "test_case"
    CUSTOM = "custom"


@dataclass
class ScheduledTask:
    id: str
    name: str
    task_type: TaskType
    cron_expression: str
    target_id: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecution:
    id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SchedulerService:
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._handlers: Dict[TaskType, Callable] = {}
    
    def register_handler(self, task_type: TaskType, handler: Callable):
        self._handlers[task_type] = handler
    
    async def start(self):
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("Scheduler started")
    
    async def stop(self):
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def _run_scheduler(self):
        while self._running:
            try:
                now = datetime.utcnow()
                
                for task_id, task in list(self._tasks.items()):
                    if not task.enabled:
                        continue
                    
                    if task.next_run and now >= task.next_run:
                        asyncio.create_task(self._execute_task(task))
                        
                        cron = croniter(task.cron_expression, now)
                        task.next_run = cron.get_next(datetime)
                        task.last_run = now
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)
    
    async def _execute_task(self, task: ScheduledTask):
        execution_id = str(uuid.uuid4())
        execution = TaskExecution(
            id=execution_id,
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self._executions[execution_id] = execution
        
        task.status = TaskStatus.RUNNING
        
        try:
            handler = self._handlers.get(task.task_type)
            if handler:
                result = await handler(task.target_id, task.params)
                execution.result = result
                execution.status = TaskStatus.COMPLETED
                task.status = TaskStatus.COMPLETED
            else:
                execution.error = f"No handler for task type {task.task_type}"
                execution.status = TaskStatus.FAILED
                task.status = TaskStatus.FAILED
                
        except Exception as e:
            execution.error = str(e)
            execution.status = TaskStatus.FAILED
            task.status = TaskStatus.FAILED
            logger.error(f"Task execution error: {e}")
        
        finally:
            execution.finished_at = datetime.utcnow()
    
    def create_task(
        self,
        name: str,
        task_type: TaskType,
        cron_expression: str,
        target_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        task_id = str(uuid.uuid4())
        
        cron = croniter(cron_expression, datetime.utcnow())
        next_run = cron.get_next(datetime)
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            cron_expression=cron_expression,
            target_id=target_id,
            params=params or {},
            next_run=next_run,
        )
        
        self._tasks[task_id] = task
        logger.info(f"Task created: {task_id} - {name}")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)
    
    def list_tasks(self, enabled: Optional[bool] = None) -> List[ScheduledTask]:
        tasks = list(self._tasks.values())
        if enabled is not None:
            tasks = [t for t in tasks if t.enabled == enabled]
        return sorted(tasks, key=lambda t: t.next_run or datetime.min)
    
    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> Optional[ScheduledTask]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        if "name" in update_data:
            task.name = update_data["name"]
        if "cron_expression" in update_data:
            task.cron_expression = update_data["cron_expression"]
            cron = croniter(task.cron_expression, datetime.utcnow())
            task.next_run = cron.get_next(datetime)
        if "enabled" in update_data:
            task.enabled = update_data["enabled"]
        if "params" in update_data:
            task.params = update_data["params"]
        
        return task
    
    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
    
    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        return self._executions.get(execution_id)
    
    def list_executions(self, task_id: Optional[str] = None) -> List[TaskExecution]:
        executions = list(self._executions.values())
        if task_id:
            executions = [e for e in executions if e.task_id == task_id]
        return sorted(executions, key=lambda e: e.started_at, reverse=True)
    
    def trigger_now(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        asyncio.create_task(self._execute_task(task))
        
        cron = croniter(task.cron_expression, datetime.utcnow())
        task.next_run = cron.get_next(datetime)
        
        return True


scheduler_service = SchedulerService()
