import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.stream_service import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])


@router.get("/tasks/{task_id}")
async def stream_task_events(task_id: str):
    async def event_generator() -> AsyncGenerator[str, None]:
        queue = stream_manager.subscribe(task_id)
        
        try:
            connected_data = json.dumps({"message": f"Stream connected for task {task_id}"}, ensure_ascii=False)
            yield f"event: connected\ndata: {connected_data}\n\n"
            
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Stream error for task {task_id}: {e}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"
        finally:
            stream_manager.unsubscribe(task_id, queue)
            disconnected_data = json.dumps({"message": "Stream disconnected"}, ensure_ascii=False)
            yield f"event: disconnected\ndata: {disconnected_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
