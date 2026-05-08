# Day 18 - SSE 流式响应 ⭐

## 目标

模拟 LLM 逐字输出的 SSE 接口,把 SSE 协议 / `StreamingResponse` 异步生成器 / 心跳保活 / 客户端断开清理 4 件事一起练到。**关键验收点**(Day 18 ⭐):必须能独立讲清 SSE 协议帧格式、为什么 LLM 流式选 SSE 不选 WebSocket、Queue 三角色协作模式。

## 思考过程

分 3 步走,每步独立跑通再叠下一层:

**Step 1 — 单生成器跑通基础流**:`async def event_generator(prompt)` 反转 `prompt`、逐字 `yield event: token / data: <字>`,字间 `await asyncio.sleep(0.1~0.3)`,完事 `yield event: done`。验证 SSE 协议帧格式 + `StreamingResponse` 接入 + curl `-N` 看流式效果。

**Step 2 — Queue 三角色让心跳并行**:发现单生成器没法同时吐 token 和发心跳(yield 只属于本函数)→ 引入 `asyncio.Queue` 漏斗,producer / heartbeat 后台 task `put` 消息,consumer 主循环 `get` 后 yield。Queue 协议约定 `("token", 字)` / `("ping", None)` / `("done", None)` 三种消息;`finally` 块 `cancel + gather(..., return_exceptions=True)` 兜底清理悬空 task。

**Step 3 — 客户端断开清理**:Starlette 在 `yield`/`queue.get()` 任一处 await 让出时注入 `CancelledError` → `except CancelledError: logger.warning(...) + raise`(必须重抛,否则 cancel 链断 + 父 task 以为子 task 正常结束)。loguru `f"...{prompt!r}"` 用 `!r` 加引号便于识别。

## 最终方案

参见 [`main.py`](main.py)(60 行)。核心结构:

```
event_generator(prompt)
├── producer (后台 task)      ─put→ Queue
├── heartbeat (后台 task)     ─put→ Queue ─get→ consumer 主循环 ─yield→ SSE
└── try/except CancelledError + finally cancel & gather
```

启动 + 测试:

```bash
uv run uvicorn main:app --reload

# 短 prompt(< 3s,无 ping)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt":"你好"}'

# 长 prompt(中间出现 ": ping" 注释行)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt":"今天天气真好我想出去散步顺便买点东西回家做饭吃饱了好睡觉"}'
```

## 踩坑

1. **import 写成 `fastapi.response`**(单数,正确 `responses`)+ 装饰器 `@aap.get`(typo)—— 边写边过 IDE 红线的习惯没养成,生产里 import 错 = 服务起不来
2. **关键字参数 `media_type = "..."`**:等号两边加空格违反 PEP 8,关键字参数 `=` 两边不留空
3. **SSE 事件末尾少 `\n\n`**:Q5 答对的同款坑写代码时再次踩,没有空行结束符浏览器永不触发 `onmessage`(curl 看似正常,真前端 EventSource 完全收不到)
4. **字段格式里多空格**:`event: token \n data: {x}` —— `\n` 前后多空格,行首 `data:` 带空格解析不对
5. **`done` 分支没 `break`**:致命 bug,主循环卡死等下一条消息,只有心跳还在每 3 秒触发,服务"看着活实则死"
6. **嵌套 `async def heartbeat(): yield`**(Q12 揭示):内部函数定义但从没被调用,且即使调了 yield 也只属于本函数不会"穿透"出 `event_generator` —— `async def` 写出来 = 协程工厂,必须 `await` / `create_task` 才会跑
7. **`asyncio.create_task` 后台 task 异常静默吞**(`/simplify` 抓的真 bug):producer 抛错被 task 对象 hold 住、不向外抛,`done` 信号永远不发 → consumer 卡 `await queue.get()` 永远 hang。配套规律:**所有 `create_task` 都要考虑异常去哪儿** —— async 反直觉点(同步代码异常自动冒到上层 stack,async task 的异常被孤立在 task 自己肚子里)

## /simplify 改动

4 处全应用:

1. **`HEARTBEAT_INTERVAL` 提模块级**:`SCREAMING_SNAKE_CASE` 是模块常量约定,放函数体内是名实不符;放模块级以后调参也好找
2. **done 事件改 `b"event: done\ndata: {}\n\n"` 字面量**:对齐 ping 风格(line 41 已是 `b""`),且静态字符串每次请求重复 `.encode("utf-8")` 是浪费
3. **inline `reversed(prompt)` 替代 `prompt[::-1]` 临时变量**:`reversed()` 是 Python 内置,意图比切片技巧 `[::-1]` 更直接;省一行 `prompt_reverse =` 临时变量
4. **producer 加 `try/except Exception` + consumer 加 `error` 分支**(关键修复):
   ```python
   async def producer():
       try:
           ...
           await queue.put(("done", None))
       except Exception as exc:
           await queue.put(("error", exc))    # 异常显式入 queue
   ```
   ```python
   elif kind == "error":
       logger.exception(f"producer failed: {payload}")
       yield b"event: error\ndata: {}\n\n"; break
   ```
   `except Exception` 不抓 `CancelledError`(3.8+ 继承 `BaseException`)→ 正常 cancel 流程不受影响。这条修复让"接业务异常"和"接 cancel 信号"两条路径自然分离。
