from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import random
from loguru import logger


HEARTBEAT_INTERVAL = 3

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str


async def event_generator(prompt: str):
    queue: asyncio.Queue = asyncio.Queue()

    async def producer():
        try:
            for token in reversed(prompt):
                await queue.put(("token", token))
                await asyncio.sleep(random.uniform(0.1, 0.3))
            await queue.put(("done", None))
        except Exception as exc:
            await queue.put(("error", exc))

    async def heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await queue.put(("ping", None))

    prod_task = asyncio.create_task(producer())
    hb_task = asyncio.create_task(heartbeat())

    try:
        while True:
            kind, payload = await queue.get()
            if kind == "token":
                yield f"event: token\ndata: {payload}\n\n".encode("utf-8")
            elif kind == "ping":
                yield b":ping\n\n"
            elif kind == "done":
                yield b"event: done\ndata: {}\n\n"
                break
            elif kind == "error":
                logger.exception(f"producer failed: {payload}")
                yield b"event: error\ndata: {}\n\n"
                break
    except asyncio.CancelledError:
        logger.warning(f"client disconnected, prompt={prompt!r}")
        raise
    finally:
        prod_task.cancel()
        hb_task.cancel()
        await asyncio.gather(prod_task, hb_task, return_exceptions=True)


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        event_generator(req.prompt),
        media_type="text/event-stream",
    )