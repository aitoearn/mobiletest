from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class TestOperation(str, Enum):
    EXECUTE = "execute"
    VALIDATE = "validate"
    ANALYZE = "analyze"
    RECORD = "record"
    COMPARE = "compare"


class OutputMode(str, Enum):
    QUICK_RESULT = "quick_result"
    DETAILED_REPORT = "detailed_report"
    STEP_BY_STEP = "step_by_step"
    DEBUG = "debug"


class SubjectType(str, Enum):
    TEST_CASE = "test_case"
    TEST_SUITE = "test_suite"
    DEVICE = "device"
    ELEMENT = "element"
    SCREEN = "screen"


class DeviceContext(BaseModel):
    device_id: str
    platform: str
    screen_size: Optional[tuple[int, int]] = None
    current_activity: Optional[str] = None
    orientation: str = "portrait"


class TestCaseContext(BaseModel):
    case_id: Optional[int] = None
    name: Optional[str] = None
    content: str
    parsed_steps: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionOptions(BaseModel):
    output_mode: OutputMode = OutputMode.QUICK_RESULT
    auto_screenshot: bool = True
    continue_on_error: bool = False
    timeout: int = 300
    use_vision: bool = True
    use_llm: bool = True


class GraphState(BaseModel):
    thread_id: str
    subject_type: Optional[SubjectType] = None
    operation: Optional[TestOperation] = None
    output_mode: OutputMode = OutputMode.QUICK_RESULT
    
    user_input: str = ""
    normalized_input: str = ""
    
    device_context: Optional[DeviceContext] = None
    test_case_context: Optional[TestCaseContext] = None
    options: ExecutionOptions = Field(default_factory=ExecutionOptions)
    
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    
    plan: List[Dict[str, Any]] = Field(default_factory=list)
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    
    final_output: Optional[str] = None
    error: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ChatRequestV1(BaseModel):
    message: str
    thread_id: Optional[str] = None
    device_id: Optional[str] = None
    test_case_id: Optional[int] = None
    options: Optional[ExecutionOptions] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponseV1(BaseModel):
    thread_id: str
    message: str
    status: str
    needs_clarification: bool = False
    clarification_options: List[str] = Field(default_factory=list)
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionTraceV1(BaseModel):
    thread_id: str
    node_name: str
    timestamp: str
    input_state: Dict[str, Any]
    output_state: Dict[str, Any]
    duration_ms: int
