"""
任务规划器模块
支持任务分解、模式匹配、动态规划
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Pattern
from enum import Enum, auto
import re
import json
import logging

from .actions.space import Action, ActionType

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"          # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    SKIPPED = "skipped"          # 跳过


@dataclass
class PlanStep:
    """计划步骤"""
    id: str
    description: str
    action_type: Optional[ActionType] = None
    expected_result: str = ""
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "action_type": self.action_type.value if self.action_type else None,
            "expected_result": self.expected_result,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


@dataclass
class TaskPlan:
    """任务计划"""
    task: str
    steps: List[PlanStep] = field(default_factory=list)
    current_step_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_current_step(self) -> Optional[PlanStep]:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def get_next_step(self) -> Optional[PlanStep]:
        """获取下一步"""
        next_index = self.current_step_index + 1
        if next_index < len(self.steps):
            return self.steps[next_index]
        return None
    
    def advance(self) -> bool:
        """前进到下一步"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            return True
        return False
    
    def mark_step_completed(self, step_id: Optional[str] = None) -> None:
        """标记步骤完成"""
        step = self._get_step(step_id)
        if step:
            step.status = TaskStatus.COMPLETED
    
    def mark_step_failed(self, step_id: Optional[str] = None, reason: str = "") -> None:
        """标记步骤失败"""
        step = self._get_step(step_id)
        if step:
            step.status = TaskStatus.FAILED
            step.metadata["failure_reason"] = reason
    
    def _get_step(self, step_id: Optional[str]) -> Optional[PlanStep]:
        """获取指定步骤"""
        if step_id:
            for step in self.steps:
                if step.id == step_id:
                    return step
            return None
        return self.get_current_step()
    
    def is_complete(self) -> bool:
        """检查计划是否完成"""
        return all(step.status == TaskStatus.COMPLETED for step in self.steps)
    
    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == TaskStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == TaskStatus.FAILED)
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": total - completed - failed,
            "percentage": (completed / total * 100) if total > 0 else 0,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "progress": self.get_progress(),
            "metadata": self.metadata,
        }


class TaskPattern:
    """任务模式 - 用于模式匹配规划"""
    
    def __init__(
        self,
        name: str,
        patterns: List[str],
        plan_template: List[Dict[str, Any]],
        priority: int = 0
    ):
        self.name = name
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.plan_template = plan_template
        self.priority = priority
    
    def match(self, task: str) -> bool:
        """检查任务是否匹配此模式"""
        return any(p.search(task) for p in self.patterns)
    
    def generate_plan(self, task: str) -> TaskPlan:
        """生成任务计划"""
        steps = []
        for i, step_template in enumerate(self.plan_template):
            step = PlanStep(
                id=f"step_{i+1}",
                description=step_template.get("description", ""),
                action_type=ActionType(step_template["action"]) if step_template.get("action") else None,
                expected_result=step_template.get("expected", ""),
                dependencies=step_template.get("dependencies", []),
            )
            steps.append(step)
        
        return TaskPlan(task=task, steps=steps, metadata={"pattern": self.name})


class Planner(ABC):
    """规划器基类"""
    
    @abstractmethod
    def plan(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """生成任务计划"""
        pass


class PatternBasedPlanner(Planner):
    """基于模式的规划器"""
    
    # 预定义的任务模式
    DEFAULT_PATTERNS = [
        # 打开应用模式
        TaskPattern(
            name="open_app",
            patterns=[
                r"打开(.+?)(应用|app)",
                r"启动(.+?)(应用|app)",
                r"进入(.+?)(应用|app)",
                r"open\s+(.+?)\s+(app|application)",
                r"launch\s+(.+?)\s+(app|application)",
            ],
            plan_template=[
                {"description": "返回主页", "action": "home", "expected": "显示主屏幕"},
                {"description": "找到并点击应用图标", "action": "click", "expected": "应用启动"},
                {"description": "等待应用加载完成", "action": "wait", "expected": "应用界面显示"},
            ],
            priority=10
        ),
        
        # 搜索模式
        TaskPattern(
            name="search",
            patterns=[
                r"搜索(.+)",
                r"查找(.+)",
                r"查询(.+)",
                r"search\s+for\s+(.+)",
                r"find\s+(.+)",
            ],
            plan_template=[
                {"description": "点击搜索框", "action": "click", "expected": "搜索框获得焦点"},
                {"description": "输入搜索关键词", "action": "type", "expected": "关键词显示在搜索框"},
                {"description": "执行搜索", "action": "click", "expected": "显示搜索结果"},
            ],
            priority=10
        ),
        
        # 点击元素模式
        TaskPattern(
            name="click_element",
            patterns=[
                r"点击(.+)",
                r"打开(.+)",
                r"进入(.+)",
                r"click\s+on\s+(.+)",
                r"tap\s+(.+)",
            ],
            plan_template=[
                {"description": "定位目标元素", "action": "think", "expected": "确认元素位置"},
                {"description": "点击目标元素", "action": "click", "expected": "元素被点击"},
            ],
            priority=5
        ),
        
        # 输入文字模式
        TaskPattern(
            name="input_text",
            patterns=[
                r"输入(.+)",
                r"填写(.+)",
                r"在(.+)输入(.+)",
                r"type\s+(.+)",
                r"enter\s+(.+)",
                r"input\s+(.+)",
            ],
            plan_template=[
                {"description": "点击输入框", "action": "click", "expected": "输入框获得焦点"},
                {"description": "输入文字", "action": "type", "expected": "文字显示在输入框"},
            ],
            priority=5
        ),
        
        # 返回模式
        TaskPattern(
            name="go_back",
            patterns=[
                r"返回",
                r"后退",
                r"回到上一页",
                r"go\s+back",
                r"return",
            ],
            plan_template=[
                {"description": "点击返回按钮", "action": "back", "expected": "返回上一页"},
            ],
            priority=3
        ),
        
        # 滑动模式
        TaskPattern(
            name="swipe",
            patterns=[
                r"(向上|向下|向左|向右)滑动",
                r"滑动到(.+)",
                r"scroll\s+(up|down|left|right)",
                r"swipe\s+(up|down|left|right)",
            ],
            plan_template=[
                {"description": "执行滑动操作", "action": "swipe", "expected": "页面滚动"},
            ],
            priority=3
        ),
        
        # 登录模式
        TaskPattern(
            name="login",
            patterns=[
                r"登录(.+)",
                r"登陆(.+)",
                r"sign\s+in",
                r"log\s+in",
            ],
            plan_template=[
                {"description": "点击用户名输入框", "action": "click", "expected": "用户名框获得焦点"},
                {"description": "输入用户名", "action": "type", "expected": "用户名显示"},
                {"description": "点击密码输入框", "action": "click", "expected": "密码框获得焦点"},
                {"description": "输入密码", "action": "type", "expected": "密码显示（隐藏）"},
                {"description": "点击登录按钮", "action": "click", "expected": "登录成功或显示结果"},
            ],
            priority=8
        ),
    ]
    
    def __init__(self, patterns: Optional[List[TaskPattern]] = None):
        self.patterns = patterns or self.DEFAULT_PATTERNS.copy()
        # 按优先级排序
        self.patterns.sort(key=lambda p: -p.priority)
    
    def plan(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """基于模式匹配生成计划"""
        # 尝试匹配模式
        for pattern in self.patterns:
            if pattern.match(task):
                logger.info(f"任务匹配模式: {pattern.name}")
                return pattern.generate_plan(task)
        
        # 没有匹配到模式，返回通用计划
        return self._create_generic_plan(task)
    
    def _create_generic_plan(self, task: str) -> TaskPlan:
        """创建通用计划"""
        return TaskPlan(
            task=task,
            steps=[
                PlanStep(
                    id="step_1",
                    description=f"分析任务: {task}",
                    action_type=ActionType.THINK,
                ),
                PlanStep(
                    id="step_2",
                    description="执行必要的操作",
                ),
                PlanStep(
                    id="step_3",
                    description="验证任务完成",
                    action_type=ActionType.FINISH,
                ),
            ],
            metadata={"pattern": "generic"}
        )
    
    def add_pattern(self, pattern: TaskPattern) -> None:
        """添加自定义模式"""
        self.patterns.append(pattern)
        self.patterns.sort(key=lambda p: -p.priority)


class LLMBasedPlanner(Planner):
    """基于 LLM 的规划器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.planning_prompt = """你是一个任务规划专家。请将以下任务分解为具体的执行步骤。

任务: {task}

请按以下 JSON 格式返回执行计划：
{{
    "steps": [
        {{
            "id": "step_1",
            "description": "步骤描述",
            "action": "动作类型（可选）",
            "expected": "预期结果",
            "dependencies": []
        }}
    ],
    "reasoning": "规划思路"
}}

可用动作类型: click, long_click, swipe, type, back, home, wait, finish
"""
    
    def plan(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """使用 LLM 生成计划"""
        if not self.llm_client:
            # 没有 LLM 客户端，返回通用计划
            return self._create_fallback_plan(task)
        
        try:
            prompt = self.planning_prompt.format(task=task)
            response = self.llm_client.generate(prompt)
            
            # 解析 JSON 响应
            plan_data = self._extract_json(response)
            
            steps = []
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    id=step_data.get("id", f"step_{len(steps)+1}"),
                    description=step_data.get("description", ""),
                    action_type=ActionType(step_data["action"]) if step_data.get("action") else None,
                    expected_result=step_data.get("expected", ""),
                    dependencies=step_data.get("dependencies", []),
                )
                steps.append(step)
            
            return TaskPlan(
                task=task,
                steps=steps,
                metadata={
                    "pattern": "llm_generated",
                    "reasoning": plan_data.get("reasoning", "")
                }
            )
        
        except Exception as e:
            logger.error(f"LLM 规划失败: {e}")
            return self._create_fallback_plan(task)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON"""
        # 尝试找到 JSON 块
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        return {}
    
    def _create_fallback_plan(self, task: str) -> TaskPlan:
        """创建备用计划"""
        return TaskPlan(
            task=task,
            steps=[
                PlanStep(id="step_1", description=f"执行: {task}")
            ],
            metadata={"pattern": "fallback"}
        )


class HybridPlanner(Planner):
    """混合规划器 - 结合模式匹配和 LLM"""
    
    def __init__(
        self,
        pattern_planner: Optional[PatternBasedPlanner] = None,
        llm_planner: Optional[LLMBasedPlanner] = None,
        use_llm_for_complex: bool = True
    ):
        self.pattern_planner = pattern_planner or PatternBasedPlanner()
        self.llm_planner = llm_planner
        self.use_llm_for_complex = use_llm_for_complex
    
    def plan(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """生成计划 - 优先使用模式匹配，复杂任务使用 LLM"""
        # 首先尝试模式匹配
        plan = self.pattern_planner.plan(task, context)
        
        # 如果是通用计划且启用了 LLM，尝试使用 LLM
        if plan.metadata.get("pattern") == "generic" and self.use_llm_for_complex and self.llm_planner:
            logger.info("模式匹配失败，使用 LLM 规划")
            return self.llm_planner.plan(task, context)
        
        return plan


class PlanExecutor:
    """计划执行器"""
    
    def __init__(self, planner: Optional[Planner] = None):
        self.planner = planner or HybridPlanner()
        self.current_plan: Optional[TaskPlan] = None
    
    def create_plan(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """创建任务计划"""
        self.current_plan = self.planner.plan(task, context)
        return self.current_plan
    
    def get_next_action(self) -> Optional[Action]:
        """获取下一步动作"""
        if not self.current_plan:
            return None
        
        step = self.current_plan.get_current_step()
        if not step:
            return None
        
        # 如果步骤有预定义的动作类型，创建对应动作
        if step.action_type:
            return Action(
                action_type=step.action_type,
                params={},  # 参数需要根据实际情况填充
                reasoning=step.description
            )
        
        return None
    
    def report_step_result(
        self,
        success: bool,
        observation: str = "",
        step_id: Optional[str] = None
    ) -> None:
        """报告步骤执行结果"""
        if not self.current_plan:
            return
        
        if success:
            self.current_plan.mark_step_completed(step_id)
            self.current_plan.advance()
        else:
            self.current_plan.mark_step_failed(step_id, observation)
    
    def get_progress(self) -> Dict[str, Any]:
        """获取执行进度"""
        if self.current_plan:
            return self.current_plan.get_progress()
        return {"total": 0, "completed": 0, "failed": 0, "pending": 0, "percentage": 0}
    
    def is_complete(self) -> bool:
        """检查是否完成"""
        return self.current_plan.is_complete() if self.current_plan else True


# 便捷函数
def create_planner(planner_type: str = "hybrid", **kwargs) -> Planner:
    """创建规划器的便捷函数"""
    if planner_type == "pattern":
        return PatternBasedPlanner(**kwargs)
    elif planner_type == "llm":
        return LLMBasedPlanner(**kwargs)
    else:
        return HybridPlanner(**kwargs)


def quick_plan(task: str) -> TaskPlan:
    """快速规划的便捷函数"""
    planner = PatternBasedPlanner()
    return planner.plan(task)
