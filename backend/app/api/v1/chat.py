from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.contracts import ChatRequestV1, ChatResponseV1
from app.orchestrator.runner import graph_runner

router = APIRouter(prefix="/chat", tags=["对话接口"])


@router.post("/supervisor", response_model=ChatResponseV1)
async def chat_supervisor(request: ChatRequestV1):
    response = await graph_runner.run(request)
    return response


@router.post("/supervisor/stream")
async def chat_supervisor_stream(request: ChatRequestV1):
    async def event_generator():
        async for chunk in graph_runner.run_stream(request):
            yield chunk
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
