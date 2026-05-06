from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

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


NOT_FOUND_RESPONSE = {404: {"model": ErrorDetail, "description": "Todo 不存在"}}
UNAUTHORIZED_RESPONSE = {401: {"model": ErrorDetail, "description": "操作未授权"}}


app = FastAPI()


def get_todo_or_404(todo_id: int) -> dict:
    todo = todos.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} 不存在")
    return todo


def verify_token(x_token: str = Header(...)) -> None:
    if x_token != "secret123":
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post(
    "/todos",
    status_code=201,
    response_model=TodoOut,
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(verify_token)],
)
def create_todo(todo: TodoCreate):
    global next_id
    new_id = next_id
    next_id += 1
    todos[new_id] = {"id": new_id, **todo.model_dump()}
    return todos[new_id]


@app.get("/todos", response_model=list[TodoOut])
def list_todos():
    return list(todos.values())


@app.get("/todos/{todo_id}", response_model=TodoOut, responses=NOT_FOUND_RESPONSE)
def get_todo(todo: dict = Depends(get_todo_or_404)):
    return todo


@app.put(
    "/todos/{todo_id}",
    response_model=TodoOut,
    responses={**NOT_FOUND_RESPONSE, **UNAUTHORIZED_RESPONSE},
    dependencies=[Depends(verify_token)],
)
def update_todo(todo_in: TodoCreate, existing: dict = Depends(get_todo_or_404)):
    todos[existing["id"]] = {"id": existing["id"], **todo_in.model_dump()}
    return todos[existing["id"]]


@app.delete(
    "/todos/{todo_id}",
    status_code=204,
    responses={**NOT_FOUND_RESPONSE, **UNAUTHORIZED_RESPONSE},
    dependencies=[Depends(verify_token)],
)
def delete_todo(existing: dict = Depends(get_todo_or_404)):
    del todos[existing["id"]]
