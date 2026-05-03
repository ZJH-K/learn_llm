# Day 15 · FastAPI 路由基础

阶段二第一天。零基础起跳:从"完全没接触 web 后端"到 5 端点 CRUD 全活,12 小时。

---

## 🎯 目标

- 建立 web 后端的最小心智模型(HTTP 协议 / 请求-响应 / REST)
- 跑通 FastAPI Hello World + Swagger 自动文档
- 学 Path / Query / Body 三类参数
- 写出完整 TODO List CRUD API(5 端点)

```bash
uv run uvicorn solution:app --reload
# 浏览器开 http://127.0.0.1:8000/docs 测试
```

---

## 🧠 思考过程(从零起步的学习路径)

### 第一阶段:HTTP 基础(没碰代码,先建心智模型)

| 概念 | 抓到的核心 |
|---|---|
| 客户端-服务端 | Web 整个世界 = 一来一回的请求/响应循环 |
| HTTP 协议 | 文本协议,方法+路径+版本 / 状态码+headers+body |
| 4 大方法 | GET 查 / POST 创 / PUT 替换 / DELETE 删,对应 CRUD |
| 幂等性 | 同操作执行 N 次 = 1 次的效果。POST 不幂等所以重试要小心 |
| 5 类状态码 | 2xx 成功 / 3xx 重定向 / 4xx 客户端错 / 5xx 服务端错 |
| REST 设计 | URL 用名词不用动词;同 path 不同 method = 不同动作;嵌套表达层级关系 |

### 第二阶段:FastAPI 三关

| 关 | 学到的 |
|---|---|
| Path Parameter | URL 里 `{xxx}` 占位 → 函数参数。类型注解 `int` 自动转换 + 422 校验 |
| Query Parameter | URL `?` 后的 key=value。有默认值 = 可选,无默认 = 必填 |
| Request Body | POST/PUT 用 Pydantic Schema,Field 约束直接当 API 校验 |

**关键认知**:FastAPI 把"类型注解 + Pydantic" 当作合同,**不写一行 if/else 校验**,422 错误带 `loc: ["body", "title"]` 精确定位错误位置。

### 第三阶段:CRUD 收官

5 端点 + 内存 dict 假数据库 + `_get_or_404` 助手:

| 端点 | 行为 | 状态码 |
|---|---|---|
| POST /todos | 创建,id 自增 | 201 |
| GET /todos | 列出全部 | 200 |
| GET /todos/{id} | 单个 | 200 / 404 |
| PUT /todos/{id} | 整体替换 | 200 / 404 |
| DELETE /todos/{id} | 删除 | 204 / 404 |

跑了 10 步业务流验证全过(创建 → 列表 → 单查 → 404 → 更新 → 验证更新 → 删除 → 204 → 验证只剩 1 个 → 重复删 404)。

---

## ✅ 最终方案

```
solution.py (~50 行)
├─ 数据层
│  ├─ todos: dict[int, dict] = {}    # 内存假数据库
│  └─ next_id: int = 1                # 自增 ID 计数器
├─ Schema
│  └─ TodoCreate(BaseModel)          # title (min/max_length) + done + priority (ge/le)
├─ Helper
│  └─ _get_or_404(todo_id) -> dict   # 单查 + 不在抛 404
└─ 5 个路由
   ├─ POST   /todos        创建,201
   ├─ GET    /todos        列表
   ├─ GET    /todos/{id}   单个
   ├─ PUT    /todos/{id}   更新
   └─ DELETE /todos/{id}   删除,204
```

---

## 🪤 踩坑(教学价值最高的 5 个)

1. **`is not` ≠ `not in`** —— 前者是身份比较(`x is None`),后者是成员关系(`x not in dict`)。3 处全写错导致所有 GET/PUT/DELETE 单个永远 404。死规矩:**判 None 用 `is/is not`,判容器成员用 `in/not in`**。
2. **`.values` 漏括号** —— Day 6 同款坑复发。方法不带括号 = 拿到方法对象本身,不是返回值。`list(todos.values)` 报 TypeError;正解 `list(todos.values())`。
3. **f-string 漏 `f` 前缀** —— `detail="Todo {todo_id} 不存在"` 没 `f`,字面输出 `{todo_id}` 不替换。3 处全错。
4. **shell 含 `&` 必须引号包** —— PowerShell / bash 里 `&` 是后台运行符号,`curl http://...?q=python&limit=5` 被拆成两段。修法:URL 用引号 `curl "http://...?q=python&limit=5"`。
5. **PowerShell 的 `curl` 不是真 curl** —— 是 `Invoke-WebRequest` 别名,行为完全不同。Windows 下用 `curl.exe` 或直接在 Swagger UI 测最简单。

---

## 🔧 /simplify 改动(5 处)

1. **`{"id": ..., **todo.model_dump()}` 替代手工字段重复** —— POST/PUT 两处的 `{"title": todo.title, "done": todo.done, ...}` 用 Pydantic 解包一行搞定。Schema 加字段不动 CRUD 代码。
2. **抽 `_get_or_404` 助手** —— 3 处重复的 404 guard 收成 1 个函数。Day 16 升级成 `Depends(_get_or_404)`,自动出现在 OpenAPI 文档的 404 响应里。
3. **`.get()` 一次查替代 TOCTOU 双查询** —— 原写法先 `if not in` 再 `[key]` 查两次。改成 `todos.get(todo_id)` 一次查。dict 是 O(1) 这里影响微乎其微,但 Week 4 接 DB 后是双倍延迟 + 非原子,**养成现在习惯**。
4. **命名地道化** —— `get_todo_list` → `list_todos`(列表语义);`put_todo` → `update_todo`(HTTP 动词不该泄露到函数名)。
5. **PEP 8 nit** —— 逗号后空格 / trailing whitespace。

---

## 📋 留作教学债(明确不今天补)

| 问题 | 何时解决 |
|---|---|
| `next_id += 1` 多 worker 竞态 | 永远存在,生产用 DB autoincrement / UUID(Week 4 学) |
| `todos` 无界增长 | 持久化方案,Week 4 SQLAlchemy / Redis |
| `dict[int, dict]` 内层无 schema | **Day 16 用 `response_model=TodoResponse` 解决** |
| 路由用 `def` 不是 `async def` | **此处正确**(无真 IO);Week 4 接 asyncpg / httpx 后再换 `async def` |
| `_get_or_404` 是普通助手 | **Day 16 升级成 `Depends`** |

---

## 📊 关键数字

- **代码行数**:~50 行
- **学习时间**:12 小时(从零起跳)
- **测试通过**:10 步业务流全过(POST → GET list → GET single → 404 → PUT → GET 验证 → DELETE → 204 → GET 验证 → 重复 DELETE 404)
- **状态码实操**:200 / 201 / 204 / 404 / 422
- **踩坑数量**:5 个(`is not vs not in` / `.values` / f-string / shell `&` / PowerShell curl)
