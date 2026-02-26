from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid

from app.models import Engine
from app.core.database import get_db

router = APIRouter(prefix="/engines", tags=["engines"])


class EngineCreate(BaseModel):
    name: str
    model: str
    prompt: str
    provider: Optional[str] = ""  # 供应商名称
    baseUrl: Optional[str] = ""
    apiKey: Optional[str] = ""


class EngineUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    provider: Optional[str] = None  # 供应商名称
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None


class EngineSchema(BaseModel):
    id: str
    name: str
    model: str
    prompt: str
    provider: str  # 供应商名称
    baseUrl: str
    apiKey: str
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class EngineResponse(BaseModel):
    code: int
    message: str
    data: Optional[EngineSchema] = None


class EnginesResponse(BaseModel):
    code: int
    message: str
    data: List[dict]


class ModelsResponse(BaseModel):
    code: int
    message: str
    data: List[dict]


# 预定义的模型列表
AVAILABLE_MODELS = [
    {"value": "autoglm-phone", "label": "AutoGLM Phone", "baseUrl": ""},
    {"value": "gpt-4o", "label": "GPT-4o", "baseUrl": "https://api.openai.com/v1"},
    {"value": "gpt-4o-mini", "label": "GPT-4o Mini", "baseUrl": "https://api.openai.com/v1"},
    {"value": "glm-4-plus", "label": "GLM-4 Plus", "baseUrl": "https://open.bigmodel.cn/api/paas/v4"},
    {"value": "qwen-max", "label": "Qwen Max", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"value": "qwen-vl-max", "label": "Qwen VL Max", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
]


@router.get("", response_model=EnginesResponse)
async def list_engines(db: Session = Depends(get_db)):
    """获取所有执行引擎，第一个引擎标记为默认"""
    result = await db.execute(select(Engine).order_by(Engine.created_at))
    engines = result.scalars().all()
    engines_list = []
    for i, e in enumerate(engines):
        engines_list.append({
            "id": e.id,
            "name": e.name,
            "model": e.model,
            "prompt": e.prompt,
            "provider": e.provider or "",
            "baseUrl": e.base_url,
            "apiKey": e.api_key,
            "createdAt": e.created_at.isoformat() if e.created_at else "",
            "updatedAt": e.updated_at.isoformat() if e.updated_at else "",
            "isDefault": i == 0,  # 第一个引擎标记为默认
        })
    return EnginesResponse(
        code=0,
        message="success",
        data=engines_list
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """获取可用的模型列表"""
    return ModelsResponse(
        code=0,
        message="success",
        data=AVAILABLE_MODELS
    )


@router.post("", response_model=EngineResponse)
async def create_engine(engine: EngineCreate, db: Session = Depends(get_db)):
    """创建新的执行引擎"""
    engine_id = str(uuid.uuid4())
    
    new_engine = Engine(
        id=engine_id,
        name=engine.name,
        model=engine.model,
        prompt=engine.prompt,
        provider=engine.provider or "",
        base_url=engine.baseUrl or "",
        api_key=engine.apiKey or "",
    )
    
    db.add(new_engine)
    await db.commit()
    await db.refresh(new_engine)
    
    return EngineResponse(
        code=0,
        message="创建成功",
        data=EngineSchema(
            id=new_engine.id,
            name=new_engine.name,
            model=new_engine.model,
            prompt=new_engine.prompt,
            provider=new_engine.provider or "",
            baseUrl=new_engine.base_url,
            apiKey=new_engine.api_key,
            createdAt=new_engine.created_at.isoformat() if new_engine.created_at else "",
            updatedAt=new_engine.updated_at.isoformat() if new_engine.updated_at else "",
        )
    )


@router.get("/{engine_id}", response_model=EngineResponse)
async def get_engine(engine_id: str, db: Session = Depends(get_db)):
    """获取单个执行引擎"""
    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="引擎不存在")
    
    return EngineResponse(
        code=0,
        message="success",
        data=EngineSchema(
            id=engine.id,
            name=engine.name,
            model=engine.model,
            prompt=engine.prompt,
            provider=engine.provider or "",
            baseUrl=engine.base_url,
            apiKey=engine.api_key,
            createdAt=engine.created_at.isoformat() if engine.created_at else "",
            updatedAt=engine.updated_at.isoformat() if engine.updated_at else "",
        )
    )


@router.put("/{engine_id}", response_model=EngineResponse)
async def update_engine(engine_id: str, engine_update: EngineUpdate, db: Session = Depends(get_db)):
    """更新执行引擎"""
    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="引擎不存在")
    
    if engine_update.name is not None:
        engine.name = engine_update.name
    if engine_update.model is not None:
        engine.model = engine_update.model
    if engine_update.prompt is not None:
        engine.prompt = engine_update.prompt
    if engine_update.provider is not None:
        engine.provider = engine_update.provider
    if engine_update.baseUrl is not None:
        engine.base_url = engine_update.baseUrl
    if engine_update.apiKey is not None:
        engine.api_key = engine_update.apiKey
    
    await db.commit()
    await db.refresh(engine)
    
    return EngineResponse(
        code=0,
        message="更新成功",
        data=EngineSchema(
            id=engine.id,
            name=engine.name,
            model=engine.model,
            prompt=engine.prompt,
            provider=engine.provider or "",
            baseUrl=engine.base_url,
            apiKey=engine.api_key,
            createdAt=engine.created_at.isoformat() if engine.created_at else "",
            updatedAt=engine.updated_at.isoformat() if engine.updated_at else "",
        )
    )


@router.delete("/{engine_id}")
async def delete_engine(engine_id: str, db: Session = Depends(get_db)):
    """删除执行引擎"""
    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="引擎不存在")
    
    db.delete(engine)
    await db.commit()
    
    return {"code": 0, "message": "删除成功"}
