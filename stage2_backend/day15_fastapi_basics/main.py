from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()                      # 创建一个 FastAPI 应用实例

@app.get("/")                        # 装饰器 = "GET / 这条路由,由下面的函数处理"
def root():
    return {"message": "Hello FastAPI"}   # 返回 dict,FastAPI 自动转 JSON

# 1. 单参数 path,类型 int
@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id, "name": f"商品{item_id}"}

# 2. 单参数 path,类型 str(用户名)
@app.get("/users/{username}")
def get_user(username: str):
    return {"username": username, "profile": f"{username} 的主页"}

# 3. 多参数 path(嵌套资源,REST 风格)
@app.get("/articles/{article_id}/comments/{comment_id}")
def get_comment(article_id: int, comment_id: int):
    return {"article_id": article_id, "comment_id": comment_id, "content": "评论内容..."}

# 1. 搜索:必填 q + 可选 limit/page
@app.get("/search")
def search(q: str, limit: int = 10, page: int = 1):
    return {"q": q, "limit": limit, "page": page, "results": [f"{q}-result-{i}" for i in range(limit)]}

# 2. 列出商品:全部可选(category 可为 None)
@app.get("/products")
def list_products(category: str | None = None, max_price: float | None = None, in_stock: bool = True):
    return {
        "category": category,
        "max_price": max_price,
        "in_stock": in_stock,
        "msg": "返回符合条件的商品列表",
    }

class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)   # 标题非空,最多 100 字
    done: bool = False
    priority: int = Field(default=1, ge=1, le=5)        # 优先级 1-5

@app.post("/todos", status_code=201)
def create_todo(todo: TodoCreate):
    return {
        "id": 100,
        "title": todo.title,
        "done": todo.done,
        "priority": todo.priority,
        "msg": "创建成功"
    }