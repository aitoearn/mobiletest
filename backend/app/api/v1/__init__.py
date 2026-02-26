from fastapi import APIRouter
from app.api.v1 import cases, executions, chat, diagnostics, devices, settings, engines

api_router = APIRouter(prefix="/v1")

api_router.include_router(cases.router)
api_router.include_router(executions.router)
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(diagnostics.router)
api_router.include_router(devices.router)
api_router.include_router(settings.router)
api_router.include_router(engines.router)
