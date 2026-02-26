from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMConfig(BaseModel):
    baseUrl: Optional[str] = ""
    apiKey: Optional[str] = ""
    selectedModels: Optional[List[str]] = []
    defaultMaxSteps: Optional[int] = 100
    layeredMaxTurns: Optional[int] = 50
    providerApiKeys: Optional[Dict[str, str]] = {}  # 每个供应商独立的 API Key
    providerModels: Optional[Dict[str, List[str]]] = {}  # 每个供应商独立的模型列表


class ModelsRequest(BaseModel):
    baseUrl: str
    apiKey: Optional[str] = ""


class ModelInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""


CONFIG_FILE = "/Users/lisq/ai/mobileagent/mobiletest/backend/config.json"


def _load_config() -> dict:
    import json
    default = {
        "baseUrl": "",
        "apiKey": "",
        "selectedModels": [],
        "defaultMaxSteps": 100,
        "layeredMaxTurns": 50,
        "providerApiKeys": {},
        "providerModels": {},
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                # 兼容旧配置
                old_config = json.load(f)
                # 迁移旧配置到新格式
                new_config = {
                    "baseUrl": old_config.get("visionBaseUrl", old_config.get("baseUrl", "")),
                    "apiKey": old_config.get("visionApiKey", old_config.get("apiKey", "")),
                    "selectedModels": old_config.get("selectedModels", []),
                    "defaultMaxSteps": old_config.get("defaultMaxSteps", 100),
                    "layeredMaxTurns": old_config.get("layeredMaxTurns", 50),
                    "providerApiKeys": old_config.get("providerApiKeys", {}),
                    "providerModels": old_config.get("providerModels", {}),
                }
                return {**default, **new_config}
        except:
            pass
    return default


def _save_config(config: dict):
    import json
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


@router.get("/llm")
async def get_llm_config():
    config = _load_config()
    return config


@router.post("/llm")
async def save_llm_config(config: LLMConfig):
    config_dict = config.model_dump()
    _save_config(config_dict)
    
    return {"success": True, "message": "配置已保存，重启后生效"}


@router.post("/llm/test")
async def test_llm_connection():
    from app.agent.llm.llm import get_llm, LLMProvider, Message
    import traceback
    
    config = _load_config()
    
    base_url = config.get("baseUrl", "")
    selected_models = config.get("selectedModels", [])
    api_key = config.get("apiKey", "")
    
    if not base_url:
        return {"success": False, "message": "请先配置 Base URL"}
    
    if not selected_models:
        return {"success": False, "message": "请先选择至少一个模型"}
    
    if not api_key:
        return {"success": False, "message": "请先配置 API Key"}
    
    if not base_url.startswith(("http://", "https://")):
        return {"success": False, "message": "Base URL 必须以 http:// 或 https:// 开头"}
    
    # ModelScope 特殊处理（其 API 与 OpenAI 不完全兼容）
    if "modelscope.cn" in base_url:
        import httpx
        try:
            test_url = base_url.rstrip("/") + "/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(test_url, headers=headers)
                if response.status_code == 200:
                    return {"success": True, "message": "ModelScope API 连接成功"}
                else:
                    return {"success": False, "message": f"ModelScope API 返回错误: HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}
    
    try:
        provider = LLMProvider.OPENAI
        if "bigmodel.cn" in base_url:
            provider = LLMProvider.ZHIPU
        elif "modelscope.cn" in base_url:
            provider = LLMProvider.MODELSCOPE
        elif "dashscope.aliyuncs.com" in base_url:
            provider = LLMProvider.QWEN
        
        llm = get_llm(
            provider,
            selected_models[0],  # 使用第一个选中的模型测试
            api_key=api_key,
            base_url=base_url
        )
        
        test_messages = [Message(role="user", content="Hello")]
        response = await llm.chat(test_messages)
        
        return {"success": True, "message": "连接成功", "response": response.content[:100]}
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"LLM Test Error: {error_detail}")
        return {"success": False, "message": f"{str(e)}", "detail": error_detail}


@router.post("/models")
async def fetch_models(request: ModelsRequest):
    """从 LLM API 获取模型列表"""
    import httpx
    import traceback
    
    try:
        headers = {}
        if request.apiKey:
            headers["Authorization"] = f"Bearer {request.apiKey}"
        
        base_url = request.baseUrl.rstrip("/")
        
        # ModelScope 使用固定的模型列表（其 API 返回的模型列表不完整）
        if "modelscope.cn" in base_url:
            model_list = [
                # AutoGLM Phone 模型
                {"id": "ZhipuAI/AutoGLM-Phone-9B", "name": "ZhipuAI/AutoGLM-Phone-9B", "description": "多模态"},
                # Qwen VL 系列
                {"id": "Qwen/Qwen2-VL-72B-Instruct", "name": "Qwen/Qwen2-VL-72B-Instruct", "description": "多模态"},
                {"id": "Qwen/Qwen2-VL-7B-Instruct", "name": "Qwen/Qwen2-VL-7B-Instruct", "description": "多模态"},
                {"id": "Qwen/Qwen2-VL-2B-Instruct", "name": "Qwen/Qwen2-VL-2B-Instruct", "description": "多模态"},
                {"id": "Qwen/Qwen-VL-Plus", "name": "Qwen/Qwen-VL-Plus", "description": "多模态"},
                {"id": "Qwen/Qwen-VL-Max", "name": "Qwen/Qwen-VL-Max", "description": "多模态"},
                {"id": "Qwen/Qwen2.5-VL-32B-Instruct", "name": "Qwen/Qwen2.5-VL-32B-Instruct", "description": "多模态"},
                {"id": "Qwen/Qwen2.5-VL-72B-Instruct", "name": "Qwen/Qwen2.5-VL-72B-Instruct", "description": "多模态"},
                {"id": "Qwen/Qwen2.5-VL-7B-Instruct", "name": "Qwen/Qwen2.5-VL-7B-Instruct", "description": "多模态"},
                # InternVL 系列
                {"id": "OpenGVLab/InternVL2-26B", "name": "OpenGVLab/InternVL2-26B", "description": "多模态"},
                {"id": "OpenGVLab/InternVL2-8B", "name": "OpenGVLab/InternVL2-8B", "description": "多模态"},
                {"id": "OpenGVLab/InternVL2-4B", "name": "OpenGVLab/InternVL2-4B", "description": "多模态"},
                {"id": "OpenGVLab/InternVL2-Llama3-76B", "name": "OpenGVLab/InternVL2-Llama3-76B", "description": "多模态"},
                # GLM 系列
                {"id": "ZhipuAI/glm-4v-9b", "name": "ZhipuAI/glm-4v-9b", "description": "多模态"},
                {"id": "ZhipuAI/glm-4-9b-chat", "name": "ZhipuAI/glm-4-9b-chat", "description": "多模态"},
                # Yi 系列
                {"id": "01-ai/Yi-VL-6B", "name": "01-ai/Yi-VL-6B", "description": "多模态"},
                {"id": "01-ai/Yi-VL-34B", "name": "01-ai/Yi-VL-34B", "description": "多模态"},
                # DeepSeek 系列
                {"id": "deepseek-ai/deepseek-vl-7b-chat", "name": "deepseek-ai/deepseek-vl-7b-chat", "description": "多模态"},
                {"id": "deepseek-ai/deepseek-vl-1.3b-chat", "name": "deepseek-ai/deepseek-vl-1.3b-chat", "description": "多模态"},
            ]
            return {
                "code": 0,
                "message": "success",
                "data": model_list
            }
        
        # 其他供应商使用 OpenAI 兼容的 /models 接口
        models_url = base_url + "/models"
        
        print(f"[FetchModels] URL: {models_url}")
        print(f"[FetchModels] Has API Key: {bool(request.apiKey)}")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(models_url, headers=headers)
            
            print(f"[FetchModels] Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:500]
                print(f"[FetchModels] Error response: {error_text}")
                return {
                    "code": -1,
                    "message": f"获取模型列表失败: HTTP {response.status_code} - {error_text}",
                    "data": []
                }
            
            data = response.json()
            models = data.get("data", [])
            
            # 格式化模型列表
            model_list = []
            
            # 如果是智谱 BigModel，添加 autoglm-phone
            if "bigmodel.cn" in request.baseUrl:
                model_list.append({
                    "id": "autoglm-phone",
                    "name": "autoglm-phone (AutoGLM Phone 专用)",
                    "description": "多模态"
                })
            
            for model in models:
                model_id = model.get("id", "")
                model_id_lower = model_id.lower()
                # 判断多模态模型（支持图像的模型）
                is_multimodal = any(
                    keyword in model_id_lower
                    for keyword in [
                        # OpenAI / Claude 系列
                        "gpt-4", "gpt4", "claude-3", "claude3",
                        # 智谱 GLM 系列
                        "glm-4", "glm4", "glm-v", "glmv",
                        # 阿里 Qwen 系列
                        "qwen-vl", "qwen2-vl", "qwen2.5-vl", "qwen-vl-max", "qwen-vl-plus",
                        # 通用多模态关键词
                        "vision", "vl", "multimodal", "image", "visual",
                    ]
                )
                # 排除纯文本版本
                is_text_only = any(
                    keyword in model_id_lower
                    for keyword in ["-text", "text-", "embedding", "instruct-only"]
                )
                if is_text_only:
                    is_multimodal = False
                
                model_list.append({
                    "id": model_id,
                    "name": model_id,
                    "description": "多模态" if is_multimodal else "文本模型"
                })
            
            # 按名称排序
            model_list.sort(key=lambda x: x["name"])
            
            return {
                "code": 0,
                "message": "success",
                "data": model_list
            }
            
    except httpx.TimeoutException:
        return {
            "code": -1,
            "message": "请求超时，请检查 Base URL 是否正确",
            "data": []
        }
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Fetch models error: {error_detail}")
        return {
            "code": -1,
            "message": f"获取模型列表失败: {str(e)}",
            "data": []
        }
