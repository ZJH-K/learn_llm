from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid
from loguru import logger
import time


VALID_TOKEN = "secret123"


todos: dict[int, dict] = {}
next_id: int = 1


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    done: bool = False
    priority: int = Field(default=1, ge=1, le=5)


class TodoOut(BaseModel):
    id: int
    title: str
    done: bool
    priority: int


class ErrorDetail(BaseModel):
    detail: str


class TodoNotFound(Exception):
    def __init__(self, todo_id: int):
        super().__init__(f"todo {todo_id} not found")
        self.todo_id = todo_id


UNAUTHORIZED_RESPONSE = {401: {"model": ErrorDetail, "description": "操作未授权"}}


app = FastAPI()


@app.exception_handler(TodoNotFound)
async def todo_not_found_handler(request: Request, exc: TodoNotFound):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=404,
        content={"error": "todo_not_found", "todo_id": exc.todo_id, "request_id": request_id}
    )


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={"error": "internal", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{request.method} {request.url.path} {status} {elapsed_ms:.1f}ms")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
    request.state.request_id = request_id

    with logger.contextualize(request_id=request_id):
        response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_todo_or_404(todo_id: int) -> dict:
    todo = todos.get(todo_id)
    if todo is None:
        raise TodoNotFound(todo_id)
    return todo


def verify_token(x_token: str = Header(...)) -> None:
    if x_token != VALID_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post(
    "/todos",
    status_code=201,
    response_model=TodoOut,
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(verify_token)],
)
async def create_todo(todo: TodoCreate):
    global next_id
    new_id = next_id
    next_id += 1
    record = {"id": new_id, **todo.model_dump()}
    todos[new_id] = record
    return record


@app.get("/todos", response_model=list[TodoOut])
async def list_todos():
    return list(todos.values())


@app.get("/todos/{todo_id}", response_model=TodoOut)
async def get_todo(todo: dict = Depends(get_todo_or_404)):
    return todo


@app.put(
    "/todos/{todo_id}",
    response_model=TodoOut,
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(verify_token)],
)
async def update_todo(todo_in: TodoCreate, existing: dict = Depends(get_todo_or_404)):
    record = {"id": existing["id"], **todo_in.model_dump()}
    todos[existing["id"]] = record
    return record


@app.delete(
    "/todos/{todo_id}",
    status_code=204,
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(verify_token)],
)
async def delete_todo(existing: dict = Depends(get_todo_or_404)):
    del todos[existing["id"]]