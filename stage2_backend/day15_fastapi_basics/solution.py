from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

todos: dict[int, dict] = {}
next_id: int = 1


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    done: bool = False
    priority: int = Field(default=1, ge=1, le=5)


app = FastAPI()


def _get_or_404(todo_id: int) -> dict:
    todo = todos.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} 不存在")
    return todo


@app.post("/todos", status_code=201)
def create_todo(todo: TodoCreate):
    global next_id
    new_id = next_id
    next_id += 1
    todos[new_id] = {"id": new_id, **todo.model_dump()}
    return todos[new_id]


@app.get("/todos")
def list_todos():
    return list(todos.values())


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    return _get_or_404(todo_id)


@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo: TodoCreate):
    _get_or_404(todo_id)
    todos[todo_id] = {"id": todo_id, **todo.model_dump()}
    return todos[todo_id]


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    _get_or_404(todo_id)
    del todos[todo_id]
