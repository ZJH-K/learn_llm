# Day 16 · Pydantic + 依赖注入

在 Day 15 的 5 端点 CRUD 基础上,把"输出 schema 控制 + 依赖注入 + 文档级错误声明"全部接上。

```bash
uv run uvicorn solution:app --reload
# Swagger UI: http://127.0.0.1:8000/docs
```

---

## 🎯 目标

- 学会用 `response_model` 控制响应 schema(白名单过滤 + 文档同步)
- 用 `Depends` 把 `_get_or_404` 升级成依赖注入,端点签名干净
- 区分 `Depends(...)`(取值)和 `dependencies=[...]`(门禁)的语义场景
- 用 `responses=` 把 401 / 404 这种业务异常显式声明到 OpenAPI
- 写一个 `verify_token` 鉴权依赖,挂到 POST/PUT/DELETE 上

---

## 🧠 思考过程

### 1. 为什么需要 `response_model`(动机驱动)

Day 15 的端点直接 `return todos[id]`(dict),Swagger 文档里响应 schema 是空的,客户端**看不到**返回字段。更糟的是 dict 里塞什么就返回什么 —— 哪天偷塞 `internal_secret` 进去也会一并漏出。

**输入 vs 输出 schema 不对称**:
- `TodoCreate`(输入)严校验,有 `Field(min_length=, ge=...)`、有默认值
- `TodoOut`(输出)纯类型 + 必填,**不要写校验和默认值**(服务端可信,默认值会蒙混 bug)

```python
class TodoOut(BaseModel):
    id: int        # 必填 —— 必须有
    title: str
    done: bool
    priority: int
```

`response_model=TodoOut` 做两件事:**运行时按 schema 过滤字段**(白名单)+ **文档生成完整响应 schema**。

`GET /todos` 返回 list,写法是 `response_model=list[TodoOut]`(自动对每项过滤)。

`DELETE` 用 `status_code=204`(No Content),**不能再加 `response_model`** —— 204 协议层就是无 body。

### 2. `Depends` 取数据(替换 `_get_or_404` 直调)

Day 15 三个端点开头都手动调 `_get_or_404(todo_id)`。问题:重复 + 易漏 + 文档不可见。

`Depends` 的姿势:
```python
@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo: dict = Depends(get_todo_or_404)):
    return todo
```

端点**签名里不再写 `todo_id`** —— FastAPI 看依赖函数 `get_todo_or_404(todo_id: int)` 的签名,从 path 反推 `todo_id` 自己注入。

**关键原则**:**single source of truth**。有了 `existing = Depends(get_todo_or_404)`,端点里**只用 `existing["id"]`**,不要再写 `todo_id` —— 否则两份信息(原始 path + 依赖加工后的结果)有可能不一致(例:依赖里做 alias 解析,`existing["id"]` ≠ 原始 `todo_id`),`todos[todo_id] = ...` 写到错的 key 上。

下划线命名也跟着调整:`_get_or_404` → `get_todo_or_404`。下划线表态"私货,只在本文件用",依赖被外部装配后角色变了,该公开。

### 3. `Depends(...)` vs `dependencies=[...]` 二选一

- **要拿返回值** → 当函数参数 `existing: dict = Depends(get_todo_or_404)`
- **不要返回值,只当门禁** → 路由级 `dependencies=[Depends(verify_token)]`

混用反例(Q12):把 `get_todo_or_404` 写到 `dependencies=[]` 里 —— 404 仍能拦,但 dict 被丢了,端点没数据可用,等于白查一次。

### 4. `responses=` —— 框架不读你函数体

我一开始以为"把 `_get_or_404` 接成 Depends 就能让 404 自动出现在文档里",**错的**。FastAPI 静态生成 OpenAPI,**不可能跑你的代码** → 看不到 `raise HTTPException(404, ...)` 这种运行时控制流。

二分法记住:
- **schema 层面能看见** → 框架自动登记(成功响应、422 校验错)
- **运行时业务异常**(401 / 403 / 404 / ...) → **必须手动 `responses=` 声明**

抽常量复用:
```python
NOT_FOUND_RESPONSE = {404: {"model": ErrorDetail, "description": "Todo 不存在"}}
UNAUTHORIZED_RESPONSE = {401: {"model": ErrorDetail, "description": "操作未授权"}}

# 多响应合并:不是 list,是 ** 解包合并
responses={**NOT_FOUND_RESPONSE, **UNAUTHORIZED_RESPONSE}
```

`ErrorDetail(BaseModel)` 不是必须 —— 只写 description 也能让 404 出现,但客户端看不到 `{"detail": "..."}` 的形状。**字段名 `detail` 是 FastAPI HTTPException 写死的**,不能自定义(除非自己写 exception handler)。

### 5. 嵌套依赖(`Depends → Depends`)

`get_current_user` 自己里面 `Depends(verify_token)` —— FastAPI 拓扑解析整张依赖图。**同一次请求里同一个依赖只跑一次**(默认 cache),所以多个端点共享 `current_user` 不会重复校验 token。

**反直觉**:互相独立的依赖**不保证按声明顺序执行**。需要顺序就用嵌套表达,不要靠"我把 A 写在 B 前面"。

---

## ✅ 最终方案

```
solution.py (~85 行)
├─ Schema
│  ├─ TodoCreate(BaseModel)         # 输入,严校验
│  ├─ TodoOut(BaseModel)            # 输出,纯类型必填
│  └─ ErrorDetail(BaseModel)        # 错误响应 schema
├─ 响应常量
│  ├─ NOT_FOUND_RESPONSE
│  └─ UNAUTHORIZED_RESPONSE
├─ 依赖
│  ├─ get_todo_or_404(todo_id)      # 取数据型(返回 dict)
│  └─ verify_token(x_token: Header) # 门禁型(无返回值)
└─ 5 端点
   ├─ POST   /todos        201 + verify_token + UNAUTHORIZED_RESPONSE
   ├─ GET    /todos        list[TodoOut]
   ├─ GET    /todos/{id}   Depends(get_todo_or_404) + NOT_FOUND_RESPONSE
   ├─ PUT    /todos/{id}   双依赖 + 双响应
   └─ DELETE /todos/{id}   204 + 双依赖 + 双响应(无 body)
```

---

## 🪤 踩坑

1. **IDE 自动补全把 `int` 补成 `InterruptedError`** —— `priority: InterruptedError` 启动崩。Pydantic / FastAPI 是"靠类型注解吃饭"的库,类型错了不会立刻像普通代码那样炸,而是延迟到 schema 生成那一刻才报。**Schema 启动错误第一眼先扫所有字段类型**。
2. **`responses=[a, b]` 不是 dict** —— 我误把它当 list 写了,FastAPI 拿不到状态码 key,文档里 401/404 全没出现。Python 合并多个 dict 是 `{**a, **b}`,不是 list。
3. **`vertify_token` 拼写** —— 应该是 `verify`(校验/验证),拼成 `vertify` 没这个词。前后一致代码不会报错,但 OpenAPI 自动生成的 operation summary 显示 "Vertify Token",对外暴露低级错误。`receive` / `occurred` / `separate` 同类高频陷阱。
4. **DELETE + `response_model` 自相矛盾** —— `status_code=204` 协议层就是"无 body",再加 `response_model=TodoOut` 互相打架。要么 204 不带 body(标准),要么改 200 + 返回被删的项。**不能同时用 204 + body**。
5. **404 不会自动出现在文档** —— 一开始以为 Depends 能让框架"看穿"404,实际框架静态生成 OpenAPI,看不到运行时 `raise`。**业务异常必须手动 `responses=` 声明**。

---

## 🔑 一句话原则

| 主题 | 原则 |
|---|---|
| 输入输出 schema | **输入严校验,输出纯类型** |
| Depends 选用 | **要返回值当参数,不要返回值进 dependencies** |
| 错误文档 | **schema 层自动登记,业务异常手动声明** |
| 数据来源 | **single source of truth — 用依赖结果,不要再用原始 path** |
| 命名 | **`_` 前缀看的不是重要性,是"打算被多远的代码调用"** |

---

## 📊 关键数字

- **代码行数**:~85 行(从 Day 15 的 50 行 +35 行)
- **新增端点级响应**:401(POST/PUT/DELETE)+ 404(GET-single/PUT/DELETE)
- **测试通过**:401(错 token)/ 404(对 token 但 todo 不存在)/ 200(对 token + 存在)三档手测全过
- **Swagger 锁头**:写操作端点(POST/PUT/DELETE)显示锁,读操作(GET)公开
