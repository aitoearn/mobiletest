from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import json


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStep(BaseModel):
    id: str
    name: str
    action: str
    params: Dict[str, Any] = {}
    retry_count: int = 0
    timeout: int = 30


class Workflow(BaseModel):
    id: Optional[int] = None
    name: str
    description: str = ""
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = None
    updated_at: datetime = None


class WorkflowExecution(BaseModel):
    id: Optional[int] = None
    workflow_id: int
    status: str = "pending"
    current_step: int = 0
    results: List[Dict[str, Any]] = []
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class WorkflowService:
    def __init__(self):
        self._workflows: Dict[int, Workflow] = {}
        self._executions: Dict[int, WorkflowExecution] = {}
        self._next_workflow_id = 1
        self._next_execution_id = 1
    
    def create_workflow(self, workflow: Workflow) -> Workflow:
        workflow.id = self._next_workflow_id
        workflow.created_at = datetime.utcnow()
        workflow.updated_at = datetime.utcnow()
        
        self._workflows[self._next_workflow_id] = workflow
        self._next_workflow_id += 1
        
        return workflow
    
    def get_workflow(self, workflow_id: int) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)
    
    def list_workflows(self, status: Optional[WorkflowStatus] = None) -> List[Workflow]:
        workflows = list(self._workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return sorted(workflows, key=lambda w: w.updated_at or datetime.min, reverse=True)
    
    def update_workflow(self, workflow_id: int, workflow_update: Dict[str, Any]) -> Optional[Workflow]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        if "name" in workflow_update:
            workflow.name = workflow_update["name"]
        if "description" in workflow_update:
            workflow.description = workflow_update["description"]
        if "steps" in workflow_update:
            workflow.steps = [WorkflowStep(**s) if isinstance(s, dict) else s for s in workflow_update["steps"]]
        if "status" in workflow_update:
            workflow.status = WorkflowStatus(workflow_update["status"])
        
        workflow.updated_at = datetime.utcnow()
        return workflow
    
    def delete_workflow(self, workflow_id: int) -> bool:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False
    
    def create_execution(self, workflow_id: int) -> Optional[WorkflowExecution]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        execution = WorkflowExecution(
            id=self._next_execution_id,
            workflow_id=workflow_id,
            status="pending",
            current_step=0,
            results=[],
        )
        
        self._executions[self._next_execution_id] = execution
        self._next_execution_id += 1
        
        return execution
    
    def get_execution(self, execution_id: int) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)
    
    def list_executions(self, workflow_id: Optional[int] = None) -> List[WorkflowExecution]:
        executions = list(self._executions.values())
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        return sorted(executions, key=lambda e: e.started_at or datetime.min, reverse=True)
    
    def update_execution(self, execution_id: int, update_data: Dict[str, Any]) -> Optional[WorkflowExecution]:
        execution = self._executions.get(execution_id)
        if not execution:
            return None
        
        for key, value in update_data.items():
            if hasattr(execution, key):
                setattr(execution, key, value)
        
        return execution


workflow_service = WorkflowService()


WORKFLOW_TEMPLATES = {
    "app_checkin": {
        "name": "每日签到",
        "description": "自动完成应用签到任务",
        "steps": [
            {"id": "1", "name": "打开应用", "action": "launch_app", "params": {"package_name": ""}},
            {"id": "2", "name": "等待加载", "action": "wait", "params": {"seconds": 3}},
            {"id": "3", "name": "点击签到按钮", "action": "click_text", "params": {"text": "签到"}},
            {"id": "4", "name": "等待结果", "action": "wait", "params": {"seconds": 2}},
            {"id": "5", "name": "截图保存", "action": "screenshot", "params": {}},
        ],
    },
    "news_fetch": {
        "name": "新闻获取",
        "description": "获取新闻列表并提取内容",
        "steps": [
            {"id": "1", "name": "打开新闻应用", "action": "launch_app", "params": {"package_name": ""}},
            {"id": "2", "name": "等待加载", "action": "wait", "params": {"seconds": 2}},
            {"id": "3", "name": "向上滑动", "action": "swipe_up", "params": {}},
            {"id": "4", "name": "截图", "action": "screenshot", "params": {}},
            {"id": "5", "name": "获取元素树", "action": "get_tree", "params": {}},
        ],
    },
    "screenshot_monitor": {
        "name": "屏幕监控",
        "description": "定期截取屏幕用于监控",
        "steps": [
            {"id": "1", "name": "唤醒屏幕", "action": "wake_screen", "params": {}},
            {"id": "2", "name": "截图", "action": "screenshot", "params": {}},
            {"id": "3", "name": "返回桌面", "action": "press_key", "params": {"key": "home"}},
            {"id": "4", "name": "关闭屏幕", "action": "turn_screen_off", "params": {}},
        ],
    },
}
