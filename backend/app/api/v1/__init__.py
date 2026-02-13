from fastapi import APIRouter
from app.api.v1 import cases, executions, chat, diagnostics, devices, settings

api_router = APIRouter(prefix="/v1")

api_router.include_router(cases.router)
api_router.include_router(executions.router)
api_router.include_router(chat.router)
api_router.include_router(diagnostics.router)
api_router.include_router(devices.router)
api_router.include_router(settings.router)
