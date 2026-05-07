# Day 17 · 中间件 + 异常处理 + CORS

## 🎯 目标

在 Day 16 五端点 CRUD + Depends/response_model/dependencies 的基础上,叠加 5 件横切关注点:

1. `@app.middleware("http")` 中间件骨架 + 洋葱模型
2. 全局异常处理器(自定义业务异常 + Exception 兜底)
3. `CORSMiddleware`
4. 请求日志中间件(loguru + 状态码 + 耗时)
5. 请求 ID 中间件(贯穿 header / state / 日志,排查链路用)

最终验收:`X-Request-ID` 必须在 200 / 404 / 500 三档响应里都出现且与日志一致。

---

## 🤔 思考过程

**第一坎:中间件 vs `Depends` 怎么分?**

Day 16 学的 `Depends` 在端点之前注入参数,作用域是单端点 / 一组端点。但"每个请求都打日志""每个请求都生成 trace_id""跨域预检"这些和业务无关、要套在所有端点外面的事,`Depends` 不合适——百端点不可能各写一遍。这是中间件的天然位置。

**第二坎:中间件叠多个,谁先跑?**

后注册的是外层(LIFO 包裹)。注册顺序 = 内层 → 外层。请求进时外层先碰到,响应出时外层最后离开 —— 标准洋葱模型。
对应到本作业的**关键决策**:`request_id` 必须最后注册成最外层,这样 `log_middleware` 的 `logger.info` 在 `request_id_middleware` 的 `logger.contextualize` 块里执行,日志才能绑上 ID。

**第三坎:全局异常处理器到底该怎么写?**

业务代码里 `raise TodoNotFound(42)`,在某处统一转成 `{"error":"todo_not_found", "todo_id":42}` + 404。比 Day 16 每个端点写 `responses={...}` 更 DRY。

**第四坎(全天最反直觉的认知)**:`@app.exception_handler(Exception)` 在 FastAPI 是被特殊路由的!

源码大意:

```python
for key, value in self.exception_handlers.items():
    if key in (500, Exception):
        error_handler = value           # 单独抽给最外层 ServerErrorMiddleware
    else:
        exception_handlers[key] = value  # 其他给 ExceptionMiddleware
```

所以 `TodoNotFound` 的 handler 装在 `ExceptionMiddleware`(内层),响应能正常冒回经过用户中间件;但 `Exception` 兜底装在 `ServerErrorMiddleware`(最外层),异常**冲过所有用户中间件**才被接住——`request_id_middleware` 的"`await call_next` 之后"代码永不执行,500 case 的 `X-Request-ID` header 必须 handler 自己加。

---

## 🛠️ 最终方案

中间件栈(从外到内):

```
ServerErrorMiddleware  ← @app.exception_handler(Exception) 装在这
  └─ CORSMiddleware
       └─ request_id_middleware    (设 state.request_id + contextualize)
            └─ request_log_middleware (try/finally 单点 logger.info)
                 └─ ExceptionMiddleware  ← @app.exception_handler(TodoNotFound) 装在这
                      └─ 端点
```

关键写法:

- `TodoNotFound(Exception)` 自定义异常,带 `super().__init__(...)` 让 `str(exc)` 有内容
- 两个 handler 都用 `getattr(request.state, "request_id", "unknown")` 防御性兜底
- `Exception` handler 显式 `headers={"X-Request-ID": rid}` 因为绕过中间件
- `request_log_middleware` 用 `try/finally` 单点打 `logger.info`,traceback 让 uvicorn 兜底打,业务层一行就够
- `request_id_middleware` 优先取请求头 `X-Request-ID`(尊重上游链路),没有再 `uuid.uuid4().hex[:8]` 生成

---

## 🪤 踩过的坑

1. **`exc.id` vs `exc.todo_id`**:handler 里写错属性名,AttributeError 触发 Exception 兜底,整条 404 路径全废返 500。属性名要和类 `__init__` 里 `self.xxx = ...` 完全一致
2. **运算符优先级 bug**:`time.perf_counter() - start * 1000`,`*` 高于 `-`,实际算 `now - (start*1000)` = 巨大负数;正解 `(time.perf_counter() - start) * 1000`
3. **中间件注册顺序反**:第一版把 `request_id` 写在最先注册(内层),log middleware 的 `logger.info` 在 contextualize 块退出后执行,日志没绑 ID。修法:`request_id` 必须最后注册
4. **`request.headers.get("X-Request-ID")` 取请求 ID**:客户端没传时返 None;应该取 `request.state.request_id`(中间件 set 的)
5. **500 case `X-Request-ID` header 缺失**:因为 ServerErrorMiddleware 直接发响应,绕过用户中间件;handler 必须自加 `headers={...}`
6. **PowerShell 引号坑**:`curl -d '{"k":"v"}'` 内层 `"` 被 PS 吃掉,curl 实际收到 `{k:v}` 不是合法 JSON → 422。解决:`\"` 转义,或 `-d "@body.json"` 喂文件,或用浏览器 `/docs`
7. **`raise ValueError("test")` 测兜底时 traceback 极长**:这是 `BaseHTTPMiddleware` 用 anyio TaskGroup,异常被 `BaseExceptionGroup` 包又 `collapse_excgroups` 解开的产物;`ERROR: Exception in ASGI application` 是 ServerErrorMiddleware 设计如此 re-raise 给 uvicorn 记录,无法消除

---

## ✨ /simplify 改动(9 处全应用)

| # | 改动 | 原因 |
|---|------|------|
| A | `responses={**UNAUTHORIZED_RESPONSE}` ×2 → 直传 dict | `**` 单 dict 是死残留,合并多 dict 才需要 |
| B | `d[k] = X; return d[k]` → `record = X; d[k] = record; return record` | 避免二次查找,可读性更好 |
| C | `todo_not_captured_handler` → `internal_error_handler` | 处理所有 Exception 不止 Todo,命名不能误导 |
| D | `try/except + 各打一次 logger` → `try/finally` 单点 `logger.info` | 业务 access log 一行就够;traceback 让 uvicorn 兜底打 |
| E | `TodoNotFound.__init__` 加 `super().__init__(f"...")` | 让 `str(exc)` 有内容,debug 时受益 |
| F | PEP8 冒号后空格 `request:Request` → `request: Request` | 一致性 |
| G | `request.state.request_id` → `getattr(request.state, "request_id", "unknown")` | 防御 request_id 中间件本身崩(虽不太可能)|
| H | `logger.exception` → `logger.info`(配合 D 的 try/finally) | 三层日志各自有用途,业务层不重复打 traceback |
| I | `"secret123"` 字面量 → 模块级常量 `VALID_TOKEN = "secret123"` | 后续 Day 20 学 JWT 时一致 |

## 验收(curl 实测)

```bash
# 1. 自动生成 ID
curl -i http://localhost:8000/todos
# x-request-id: b405d9cb (随机 8 位)

# 2. 客户端传 ID 原样返回
curl -i -H "X-Request-ID: my-debug-001" http://localhost:8000/todos
# x-request-id: my-debug-001

# 3. 404(走 ExceptionMiddleware,header 由中间件自动加)
curl -i http://localhost:8000/todos/999
# 404 + body+header request_id 一致

# 4. 500(走 ServerErrorMiddleware,header 由 handler 手动加)
curl -i http://localhost:8000/todos    # 临时在 list_todos 里 raise ValueError 测试
# 500 + body+header request_id 一致(测完删掉 raise)
```
