import uuid
from typing import Optional, AsyncGenerator
from datetime import datetime

from app.contracts import (
    GraphState, ChatRequestV1, ChatResponseV1,
    SubjectType, TestOperation, OutputMode,
    DeviceContext, TestCaseContext, ExecutionOptions
)
from app.orchestrator.nodes import (
    build_initial_state,
    normalize_ui_context,
    decide_output_mode,
    resolve_subject,
    clarify,
    parse_operation,
    policy_gate,
    planner,
    execute_plan,
    synthesize,
    render,
)
from app.core.config import settings


class GraphRunner:
    def __init__(self):
        self.nodes = [
            ("build_initial_state", build_initial_state),
            ("normalize_ui_context", normalize_ui_context),
            ("decide_output_mode", decide_output_mode),
            ("resolve_subject", resolve_subject),
            ("clarify", clarify),
            ("parse_operation", parse_operation),
            ("policy_gate", policy_gate),
            ("planner", planner),
            ("execute_plan", execute_plan),
            ("synthesize", synthesize),
            ("render", render),
        ]
    
    async def run(self, request: ChatRequestV1) -> ChatResponseV1:
        thread_id = request.thread_id or str(uuid.uuid4())
        
        state = GraphState(
            thread_id=thread_id,
            user_input=request.message,
        )
        
        if request.device_id:
            state.device_context = DeviceContext(
                device_id=request.device_id,
                platform="android",
            )
        
        if request.test_case_id:
            state.test_case_context = TestCaseContext(
                case_id=request.test_case_id,
                content="",
            )
        
        if request.options:
            state.options = request.options
        
        if request.context:
            state.metadata.update(request.context)
        
        for node_name, node_func in self.nodes:
            start_time = datetime.utcnow()
            
            if node_name == "clarify" and state.needs_clarification:
                state = node_func(state)
                break
            
            if node_name == "planner" and hasattr(node_func, '__call__'):
                state = node_func(state)
            else:
                state = node_func(state)
            
            if state.error:
                break
        
        return ChatResponseV1(
            thread_id=state.thread_id,
            message=state.final_output or "执行完成",
            status="error" if state.error else "success",
            needs_clarification=state.needs_clarification,
            clarification_options=state.clarification_options,
            execution_results=state.execution_results,
            evidence=state.evidence,
            metadata=state.metadata,
        )
    
    async def run_stream(self, request: ChatRequestV1) -> AsyncGenerator[str, None]:
        thread_id = request.thread_id or str(uuid.uuid4())
        
        state = GraphState(
            thread_id=thread_id,
            user_input=request.message,
        )
        
        if request.device_id:
            state.device_context = DeviceContext(
                device_id=request.device_id,
                platform="android",
            )
        
        if request.options:
            state.options = request.options
        
        yield f"data: {self._format_sse('start', {'thread_id': thread_id})}\n\n"
        
        for node_name, node_func in self.nodes:
            start_time = datetime.utcnow()
            
            if node_name == "planner":
                state = node_func(state)
            else:
                state = node_func(state)
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            yield f"data: {self._format_sse('node', {'node': node_name, 'duration_ms': duration_ms})}\n\n"
            
            if state.needs_clarification and node_name == "clarify":
                yield f"data: {self._format_sse('clarify', {'message': state.clarification_message, 'options': state.clarification_options})}\n\n"
                break
            
            if state.error:
                yield f"data: {self._format_sse('error', {'error': state.error})}\n\n"
                break
        
        yield f"data: {self._format_sse('complete', {'message': state.final_output, 'metadata': state.metadata})}\n\n"
    
    def _format_sse(self, event_type: str, data: dict) -> str:
        import json
        return json.dumps({"type": event_type, "data": data})


graph_runner = GraphRunner()
