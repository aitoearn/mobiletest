"""
动作解析器
支持多种格式的动作解析：JSON、XML、AutoGLM格式等
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union

from .space import Action, ActionType, ActionSpace


class ActionParser(ABC):
    """动作解析器基类"""
    
    @abstractmethod
    def parse(self, raw_output: str) -> Optional[Action]:
        """解析原始输出为 Action"""
        pass
    
    @abstractmethod
    def can_parse(self, raw_output: str) -> bool:
        """检查是否能解析此格式"""
        pass


class JSONActionParser(ActionParser):
    """JSON 格式动作解析器"""
    
    def can_parse(self, raw_output: str) -> bool:
        """检查是否为 JSON 格式"""
        try:
            data = json.loads(raw_output.strip())
            return isinstance(data, dict) and "action" in data
        except (json.JSONDecodeError, ValueError):
            return False
    
    def parse(self, raw_output: str) -> Optional[Action]:
        """解析 JSON 格式"""
        try:
            data = json.loads(raw_output.strip())
            
            if not isinstance(data, dict):
                return None
            
            action_type_str = data.get("action")
            if not action_type_str:
                return None
            
            # 标准化动作类型名称
            action_type = self._normalize_action_type(action_type_str)
            
            return Action(
                action_type=action_type,
                params=data.get("params", {}),
                reasoning=data.get("reasoning", data.get("thought", "")),
                confidence=data.get("confidence", 1.0),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
    
    def _normalize_action_type(self, action_str: str) -> ActionType:
        """标准化动作类型"""
        action_str = action_str.lower().strip()
        
        # 直接匹配
        try:
            return ActionType(action_str)
        except ValueError:
            pass
        
        # 别名映射
        aliases = {
            "tap": ActionType.CLICK,
            "touch": ActionType.CLICK,
            "press": ActionType.CLICK,
            "long_press": ActionType.LONG_CLICK,
            "long_tap": ActionType.LONG_CLICK,
            "input": ActionType.TYPE,
            "enter": ActionType.TYPE,
            "write": ActionType.TYPE,
            "return": ActionType.BACK,
            "exit": ActionType.BACK,
            "main": ActionType.HOME,
            "desktop": ActionType.HOME,
            "apps": ActionType.RECENT,
            "tasks": ActionType.RECENT,
            "sleep": ActionType.WAIT,
            "pause": ActionType.WAIT,
            "done": ActionType.FINISH,
            "complete": ActionType.FINISH,
            "success": ActionType.FINISH,
            "error": ActionType.FAIL,
            "failed": ActionType.FAIL,
            "open_app": ActionType.LAUNCH_APP,
            "start_app": ActionType.LAUNCH_APP,
            "launch": ActionType.LAUNCH_APP,
            "key": ActionType.PRESS_KEY,
            "capture": ActionType.SCREENSHOT,
            "reflect": ActionType.THINK,
            "reason": ActionType.THINK,
        }
        
        if action_str in aliases:
            return aliases[action_str]
        
        # 默认返回 CLICK（如果无法识别）
        return ActionType.CLICK


class XMLActionParser(ActionParser):
    """XML 格式动作解析器"""
    
    def can_parse(self, raw_output: str) -> bool:
        """检查是否为 XML 格式"""
        return "<action" in raw_output.lower() and "</action>" in raw_output.lower()
    
    def parse(self, raw_output: str) -> Optional[Action]:
        """解析 XML 格式"""
        try:
            # 提取 action 标签
            pattern = r'<action\s+type="(\w+)"[^>]*>(.*?)</action>'
            match = re.search(pattern, raw_output, re.DOTALL | re.IGNORECASE)
            
            if not match:
                return None
            
            action_type_str = match.group(1)
            content = match.group(2)
            
            # 解析参数
            params = {}
            param_pattern = r'<(\w+)>([^<]*)</\1>'
            for param_match in re.finditer(param_pattern, content):
                key = param_match.group(1)
                value = param_match.group(2).strip()
                
                # 尝试转换为数字
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
                
                params[key] = value
            
            # 标准化动作类型
            json_parser = JSONActionParser()
            action_type = json_parser._normalize_action_type(action_type_str)
            
            return Action(
                action_type=action_type,
                params=params,
                reasoning=f"Parsed from XML: {raw_output[:100]}...",
            )
        except Exception:
            return None


class AutoGLMActionParser(ActionParser):
    """AutoGLM 格式动作解析器 (action_name(param=value))"""
    
    def can_parse(self, raw_output: str) -> bool:
        """检查是否为 AutoGLM 格式"""
        # 清理文本：移除中文标点和其他干扰字符
        cleaned = self._clean_text(raw_output.strip())
        # 尝试匹配整行或行内的 action 调用
        pattern = r'\b\w+\([^)]*\)'
        return bool(re.search(pattern, cleaned))
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除干扰字符"""
        # 移除中文标点符号
        text = re.sub(r'[，。！？、；：""''（）【】]', '', text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def parse(self, raw_output: str) -> Optional[Action]:
        """解析 AutoGLM 格式"""
        try:
            # 清理文本
            print(f"Raw action: {repr(raw_output)}")
            cleaned = self._clean_text(raw_output.strip())
            print(f"Cleaned: {repr(cleaned)}")
            
            # 在多行文本中搜索 action 调用
            pattern = r'(\w+)\(([^)]*)\)'
            match = re.search(pattern, cleaned)
            print(f"Match result: {match}")
            if not match:
                return None
            
            wrapper_type = match.group(1)
            params_str = match.group(2)
            print(f"Action params: {params_str}")
            
            # 解析参数
            params = {}
            if params_str:
                # 首先尝试解析数组格式: key=[value1, value2]
                array_pattern = r'(\w+)=\[([^\]]*)\]'
                for array_match in re.finditer(array_pattern, params_str):
                    key = array_match.group(1)
                    array_content = array_match.group(2)
                    # 解析数组元素
                    elements = []
                    for elem in array_content.split(','):
                        elem = elem.strip()
                        try:
                            if '.' in elem:
                                elements.append(float(elem))
                            else:
                                elements.append(int(elem))
                        except ValueError:
                            elements.append(elem)
                    params[key] = elements
                
                # 移除已解析的数组部分
                params_str_no_arrays = re.sub(array_pattern, '', params_str)
                print(f"Remaining params: {params_str_no_arrays}")
                
                # 匹配 key=value 或 key="value"
                param_pattern = r'(\w+)=(?:"([^"]*)"|([^,\s]*))'
                for param_match in re.finditer(param_pattern, params_str_no_arrays):
                    key = param_match.group(1)
                    value = param_match.group(2) if param_match.group(2) else param_match.group(3)
                    
                    # 尝试转换为数字
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass
                    
                    params[key] = value
                    print(f"Parsed param: {key} = {value}")
                
                # 如果没有解析出任何参数，将整个内容作为默认参数
                # 例如: Launch("京东") -> params = {"app": "京东"}
                if not params and params_str.strip():
                    # 尝试提取数组参数: [value1, value2]
                    array_match = re.search(r'\[([^\]]*)\]', params_str)
                    if array_match:
                        # 解析数组元素
                        array_content = array_match.group(1)
                        elements = []
                        for elem in array_content.split(','):
                            elem = elem.strip()
                            try:
                                if '.' in elem:
                                    elements.append(float(elem))
                                else:
                                    elements.append(int(elem))
                            except ValueError:
                                elements.append(elem)
                        default_param_name = self._get_default_param_name(wrapper_type)
                        params[default_param_name] = elements
                    else:
                        # 尝试提取字符串参数
                        string_match = re.search(r'"([^"]*)"', params_str)
                        if string_match:
                            # 根据动作类型确定参数名
                            default_param_name = self._get_default_param_name(wrapper_type)
                            params[default_param_name] = string_match.group(1)
            
            # 确定实际的动作类型
            # 如果是 do() 包装格式，从参数中提取 action
            if wrapper_type.lower() == 'do' and 'action' in params:
                action_type_str = params.pop('action')  # 移除并获取 action 参数
            else:
                action_type_str = wrapper_type
            
            print(f"Action type: {action_type_str}")
            
            # 标准化动作类型
            json_parser = JSONActionParser()
            action_type = json_parser._normalize_action_type(action_type_str)
            
            return Action(
                action_type=action_type,
                params=params,
                reasoning=f"Parsed from AutoGLM: {raw_output[:100]}...",
            )
        except Exception:
            return None
    
    def _get_default_param_name(self, action_type: str) -> str:
        """根据动作类型获取默认参数名"""
        default_params = {
            'launch': 'app',
            'launch_app': 'app',
            'type': 'text',
            'tap': 'element',
            'click': 'element',
            'wait': 'duration',
            'finish': 'message',
        }
        return default_params.get(action_type.lower(), 'value')


class TextActionParser(ActionParser):
    """文本格式动作解析器（自然语言描述）"""
    
    # 动作模式匹配
    PATTERNS = [
        # 点击: "click at (500, 800)", "tap 500 800", "click x=500 y=800"
        (r'(?:click|tap)\s+(?:at\s+)?[\(\[]?(\d+)[,\s]+(\d+)[\)\]]?', ActionType.CLICK, ["x", "y"]),
        
        # 长按: "long press at (500, 800)"
        (r'long\s+(?:click|press)\s+(?:at\s+)?[\(\[]?(\d+)[,\s]+(\d+)[\)\]]?', ActionType.LONG_CLICK, ["x", "y"]),
        
        # 滑动: "swipe from (500, 800) to (500, 200)"
        (r'swipe\s+(?:from\s+)?[\(\[]?(\d+)[,\s]+(\d+)[\)\]]?\s+(?:to\s+)?[\(\[]?(\d+)[,\s]+(\d+)[\)\]]?', 
         ActionType.SWIPE, ["x1", "y1", "x2", "y2"]),
        
        # 输入: "type 'hello world'", "input: hello"
        (r'(?:type|input|enter)\s*[\'"]?([^\'"\n]+)[\'"]?', ActionType.TYPE, ["text"]),
        
        # 返回: "go back", "press back"
        (r'(?:go\s+)?back|return', ActionType.BACK, []),
        
        # 主页: "go home", "press home"
        (r'(?:go\s+)?home|main\s+screen', ActionType.HOME, []),
        
        # 等待: "wait 2 seconds", "sleep 1000ms"
        (r'(?:wait|sleep|pause)\s+(\d+)\s*(?:ms|milliseconds?)?', ActionType.WAIT, ["duration"]),
        
        # 完成: "task complete", "finished"
        (r'(?:task\s+)?(?:complete|finished|done)', ActionType.FINISH, []),
    ]
    
    def can_parse(self, raw_output: str) -> bool:
        """检查是否能解析为文本格式"""
        # 如果其他解析器能处理，就不使用文本解析
        json_parser = JSONActionParser()
        xml_parser = XMLActionParser()
        autoglm_parser = AutoGLMActionParser()
        
        if json_parser.can_parse(raw_output) or \
           xml_parser.can_parse(raw_output) or \
           autoglm_parser.can_parse(raw_output):
            return False
        
        # 检查是否有匹配的模式
        for pattern, _, _ in self.PATTERNS:
            if re.search(pattern, raw_output, re.IGNORECASE):
                return True
        
        return False
    
    def parse(self, raw_output: str) -> Optional[Action]:
        """解析文本格式"""
        text = raw_output.strip().lower()
        
        for pattern, action_type, param_names in self.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params = {}
                for i, name in enumerate(param_names):
                    value = match.group(i + 1)
                    # 尝试转换为数字
                    try:
                        params[name] = int(value)
                    except ValueError:
                        params[name] = value
                
                return Action(
                    action_type=action_type,
                    params=params,
                    reasoning=raw_output,
                )
        
        return None


class CompositeActionParser(ActionParser):
    """组合解析器 - 尝试多种解析方式"""
    
    def __init__(self):
        self.parsers: List[ActionParser] = [
            JSONActionParser(),
            XMLActionParser(),
            AutoGLMActionParser(),
            TextActionParser(),
        ]
    
    def can_parse(self, raw_output: str) -> bool:
        """检查是否有任何解析器能处理"""
        return any(parser.can_parse(raw_output) for parser in self.parsers)
    
    def parse(self, raw_output: str) -> Optional[Action]:
        """尝试所有解析器直到成功"""
        # 首先尝试直接解析
        for parser in self.parsers:
            if parser.can_parse(raw_output):
                action = parser.parse(raw_output)
                if action:
                    return action
        
        # 尝试从 <answer> 标签中提取
        answer_match = re.search(r'<answer>(.*?)</answer>', raw_output, re.DOTALL)
        if answer_match:
            answer_content = answer_match.group(1).strip()
            for parser in self.parsers:
                if parser.can_parse(answer_content):
                    action = parser.parse(answer_content)
                    if action:
                        return action
        
        # 尝试从代码块中提取
        code_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
        code_match = re.search(code_block_pattern, raw_output, re.DOTALL)
        if code_match:
            code_content = code_match.group(1).strip()
            for parser in self.parsers:
                if parser.can_parse(code_content):
                    action = parser.parse(code_content)
                    if action:
                        return action
        
        return None
    
    def add_parser(self, parser: ActionParser, index: int = -1):
        """添加自定义解析器"""
        if index < 0:
            self.parsers.append(parser)
        else:
            self.parsers.insert(index, parser)


def create_parser(format_type: str = "auto") -> ActionParser:
    """
    创建动作解析器工厂函数
    
    Args:
        format_type: 格式类型，可选 "auto", "json", "xml", "autoglm", "text"
    
    Returns:
        ActionParser 实例
    """
    format_type = format_type.lower()

    print(f"Creating parser for format: {format_type}")
    
    if format_type == "json":
        return JSONActionParser()
    elif format_type == "xml":
        return XMLActionParser()
    elif format_type == "autoglm":
        return AutoGLMActionParser()
    elif format_type == "text":
        return TextActionParser()
    else:
        return CompositeActionParser()


def parse_action(raw_output: str, format_type: str = "auto") -> Optional[Action]:
    """
    便捷函数：解析动作
    
    Args:
        raw_output: 原始输出字符串
        format_type: 格式类型
    
    Returns:
        Action 对象或 None
    """
    parser = create_parser(format_type)
    return parser.parse(raw_output)


def extract_action_from_text(text: str) -> Optional[Action]:
    """
    从文本中提取动作（尝试多种方式）
    
    Args:
        text: 可能包含动作的文本
    
    Returns:
        Action 对象或 None
    """
    # 首先尝试直接解析
    parser = CompositeActionParser()
    action = parser.parse(text)
    if action:
        return action
    
    # 尝试从代码块中提取
    code_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    for match in matches:
        action = parser.parse(match.strip())
        if action:
            return action
    
    # 尝试从 JSON 块中提取
    json_pattern = r'\{[\s\S]*?"action"[\s\S]*?\}'
    match = re.search(json_pattern, text)
    if match:
        action = parser.parse(match.group())
        if action:
            return action
    
    return None
