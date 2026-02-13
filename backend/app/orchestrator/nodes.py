from typing import Dict, Any, Optional
from app.contracts import GraphState, SubjectType, TestOperation, OutputMode
from app.core.config import settings


def build_initial_state(state: GraphState) -> GraphState:
    state.metadata["node"] = "build_initial_state"
    state.metadata["initialized"] = True
    return state


def normalize_ui_context(state: GraphState) -> GraphState:
    state.metadata["node"] = "normalize_ui_context"
    
    user_input = state.user_input.strip()
    state.normalized_input = user_input.lower()
    
    if state.device_context and state.device_context.device_id:
        state.metadata["has_device"] = True
    
    if state.test_case_context and state.test_case_context.content:
        state.metadata["has_test_case"] = True
    
    return state


def decide_output_mode(state: GraphState) -> GraphState:
    state.metadata["node"] = "decide_output_mode"
    
    if state.options and state.options.output_mode:
        return state
    
    user_input = state.normalized_input
    
    if any(word in user_input for word in ["详细", "报告", "detail", "report"]):
        state.output_mode = OutputMode.DETAILED_REPORT
    elif any(word in user_input for word in ["调试", "debug", "debug"]):
        state.output_mode = OutputMode.DEBUG
    elif any(word in user_input for word in ["步骤", "step", "一步一步"]):
        state.output_mode = OutputMode.STEP_BY_STEP
    else:
        state.output_mode = OutputMode.QUICK_RESULT
    
    return state


def resolve_subject(state: GraphState) -> GraphState:
    state.metadata["node"] = "resolve_subject"
    
    user_input = state.normalized_input
    
    if state.test_case_context and state.test_case_context.content:
        state.subject_type = SubjectType.TEST_CASE
    elif state.device_context and state.device_context.device_id:
        state.subject_type = SubjectType.DEVICE
    elif any(word in user_input for word in ["元素", "element", "按钮", "button"]):
        state.subject_type = SubjectType.ELEMENT
    elif any(word in user_input for word in ["屏幕", "screen", "截图", "screenshot"]):
        state.subject_type = SubjectType.SCREEN
    else:
        state.subject_type = SubjectType.TEST_CASE
    
    return state


def clarify(state: GraphState) -> GraphState:
    state.metadata["node"] = "clarify"
    
    if state.subject_type == SubjectType.TEST_CASE and not state.test_case_context:
        state.needs_clarification = True
        state.clarification_message = "请提供测试用例内容或选择已有用例"
        state.clarification_options = ["输入新用例", "选择已有用例", "取消"]
    elif state.subject_type == SubjectType.DEVICE and not state.device_context:
        state.needs_clarification = True
        state.clarification_message = "请选择要使用的设备"
        state.clarification_options = ["Android设备", "iOS设备", "取消"]
    else:
        state.needs_clarification = False
    
    return state


def parse_operation(state: GraphState) -> GraphState:
    state.metadata["node"] = "parse_operation"
    
    user_input = state.normalized_input
    
    if any(word in user_input for word in ["执行", "execute", "运行", "run"]):
        state.operation = TestOperation.EXECUTE
    elif any(word in user_input for word in ["验证", "validate", "检查", "check"]):
        state.operation = TestOperation.VALIDATE
    elif any(word in user_input for word in ["分析", "analyze", "分析"]):
        state.operation = TestOperation.ANALYZE
    elif any(word in user_input for word in ["录制", "record", "记录"]):
        state.operation = TestOperation.RECORD
    elif any(word in user_input for word in ["对比", "compare", "比较"]):
        state.operation = TestOperation.COMPARE
    else:
        state.operation = TestOperation.EXECUTE
    
    return state


def policy_gate(state: GraphState) -> GraphState:
    state.metadata["node"] = "policy_gate"
    
    if not state.subject_type:
        state.error = "无法确定测试主体类型"
        return state
    
    if not state.operation:
        state.operation = TestOperation.EXECUTE
    
    state.metadata["policy_checked"] = True
    return state


def planner_stub(state: GraphState) -> GraphState:
    state.metadata["node"] = "planner_stub"
    
    if state.operation == TestOperation.EXECUTE:
        state.plan = [
            {"step": 1, "action": "connect_device", "description": "连接设备"},
            {"step": 2, "action": "parse_test_case", "description": "解析测试用例"},
            {"step": 3, "action": "execute_steps", "description": "执行测试步骤"},
            {"step": 4, "action": "collect_results", "description": "收集执行结果"},
        ]
    elif state.operation == TestOperation.VALIDATE:
        state.plan = [
            {"step": 1, "action": "get_current_state", "description": "获取当前状态"},
            {"step": 2, "action": "validate_assertion", "description": "验证断言"},
        ]
    elif state.operation == TestOperation.ANALYZE:
        state.plan = [
            {"step": 1, "action": "capture_screen", "description": "截取屏幕"},
            {"step": 2, "action": "analyze_ui", "description": "分析UI元素"},
        ]
    else:
        state.plan = [
            {"step": 1, "action": "initialize", "description": "初始化"},
        ]
    
    return state


async def planner_llm(state: GraphState) -> GraphState:
    state.metadata["node"] = "planner_llm"
    
    try:
        from app.agent.llm.llm import get_llm, LLMProvider, Message
        
        llm = get_llm(LLMProvider.OPENAI)
        
        prompt = f"""作为移动测试自动化专家，请为以下任务制定执行计划：

主体类型: {state.subject_type}
操作类型: {state.operation}
用户输入: {state.user_input}
设备信息: {state.device_context.model_dump() if state.device_context else '未指定'}

请以JSON数组格式返回执行步骤，每个步骤包含:
- step: 步骤编号
- action: 动作类型
- description: 步骤描述
- params: 参数（可选）
"""
        
        messages = [Message(role="user", content=prompt)]
        response = await llm.chat(messages)
        
        import json
        state.plan = json.loads(response.content)
        
    except Exception as e:
        state.metadata["planner_llm_error"] = str(e)
        state = planner_stub(state)
    
    return state


def planner(state: GraphState) -> GraphState:
    state.metadata["node"] = "planner"
    
    if settings.langgraph_planner_mode.value == "llm":
        import asyncio
        return asyncio.run(planner_llm(state))
    else:
        return planner_stub(state)


def execute_plan(state: GraphState) -> GraphState:
    state.metadata["node"] = "execute_plan"
    
    if not state.plan:
        state.error = "没有可执行的测试计划"
        return state
    
    results = []
    for step in state.plan:
        result = {
            "step": step.get("step"),
            "action": step.get("action"),
            "description": step.get("description"),
            "status": "pending",
            "message": "",
        }
        
        if settings.langgraph_execute_live_tools:
            result["status"] = "skipped"
            result["message"] = "Live execution not enabled in stub mode"
        else:
            result["status"] = "simulated"
            result["message"] = f"模拟执行: {step.get('description')}"
        
        results.append(result)
    
    state.execution_results = results
    return state


def synthesize_stub(state: GraphState) -> GraphState:
    state.metadata["node"] = "synthesize_stub"
    
    if state.needs_clarification:
        state.final_output = state.clarification_message
        return state
    
    if state.error:
        state.final_output = f"执行失败: {state.error}"
        return state
    
    results_summary = []
    for result in state.execution_results:
        results_summary.append(
            f"步骤{result['step']}: {result['description']} - {result['status']}"
        )
    
    state.final_output = f"""测试执行完成

主体类型: {state.subject_type}
操作类型: {state.operation}
输出模式: {state.output_mode}

执行结果:
{chr(10).join(results_summary)}

状态: 成功
"""
    
    return state


async def synthesize_llm(state: GraphState) -> GraphState:
    state.metadata["node"] = "synthesize_llm"
    
    try:
        from app.agent.llm.llm import get_llm, LLMProvider, Message
        
        llm = get_llm(LLMProvider.OPENAI)
        
        prompt = f"""请根据以下测试执行结果生成总结报告：

主体类型: {state.subject_type}
操作类型: {state.operation}
输出模式: {state.output_mode}

执行步骤:
{state.execution_results}

请生成简洁的执行报告。
"""
        
        messages = [Message(role="user", content=prompt)]
        response = await llm.chat(messages)
        state.final_output = response.content
        
    except Exception as e:
        state.metadata["synthesize_llm_error"] = str(e)
        state = synthesize_stub(state)
    
    return state


def synthesize(state: GraphState) -> GraphState:
    state.metadata["node"] = "synthesize"
    
    if settings.langgraph_synthesize_mode.value == "llm":
        import asyncio
        return asyncio.run(synthesize_llm(state))
    else:
        return synthesize_stub(state)


def render(state: GraphState) -> GraphState:
    state.metadata["node"] = "render"
    
    if settings.langgraph_show_evidence and state.evidence:
        state.final_output += f"\n\n证据:\n"
        for e in state.evidence:
            state.final_output += f"- {e}\n"
    
    return state
