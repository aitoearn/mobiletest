from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.core.config import settings
from app.api.v1 import api_router

REQUEST_COUNT = Counter(
    "mobiletest_requests_total",
    "Total request count",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "mobiletest_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"]
)

app = FastAPI(
    title=settings.app_name,
    description="Mobile AI Automation Testing Platform with LangGraph Orchestration",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.2.0",
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.on_event("startup")
async def startup_event():
    import logging
    logging.info(f"Starting {settings.app_name}")
    logging.info(f"Planner mode: {settings.langgraph_planner_mode}")
    logging.info(f"Checkpointer backend: {settings.langgraph_checkpointer_backend}")
