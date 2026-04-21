# Day 8 · asyncio 基础

## 目标

并发请求 10 个网页并计时。总耗时要接近**单个请求的耗时**(~1s),而不是串行的 10 倍(~10s)。

## 思考过程

1. **先搞清动机**:同步版 10 秒慢在哪里?—— CPU 绝大部分时间在等网络,不在算。异步能把"等"重叠起来,墙上时间从 O(N) 压到 O(1),但 CPU 工作量不变。
2. **判断异步适用场景**:I/O 密集(网络、DB、磁盘)适合,CPU 密集(矩阵、加密)不适合。
3. **上语法四件套**:`async def` / `await` / `asyncio.run` / `asyncio.gather`。
4. **第一版写出来**:用 `httpx.AsyncClient` + `gather` 并发 10 个请求,跑出 2.13s。
5. **优化点识别**:每个请求都开新 `AsyncClient` 是次优,重建连接池浪费。
6. **共享 client 重构**:外层 `async with httpx.AsyncClient() as client:` 创建一次,透传给所有 `fetch`,跑出 1.25s,提速 41%。

## 最终方案

```python
import asyncio
import httpx
import time

async def fetch(client, url):
    r = await client.get(url)
    return r.status_code

async def main():
    urls = ["https://www.example.com"] * 10
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        results = await asyncio.gather(*(fetch(client, url) for url in urls))
        print(results)
        print(f"耗时 {time.perf_counter() - start:.2f}s")

asyncio.run(main())
```

## 踩坑

1. **`httpx.AsyncClient as client`**:忘了加括号实例化。类本身不是异步上下文管理器,必须 `AsyncClient()`。
2. **`gather(fetch(url) for url in urls)`**:忘了 `*` 解包。`gather` 接的是多个位置参数,传生成器等于传 1 个,行为错。
3. **漏 `asyncio.run(main())`**:定义了 `main` 没调用,等于白写 —— 就是"`async def` 调用不自动执行"的同一个坑,这次已经是第二次踩。
4. **每个请求开新 client**:第一版在 `fetch` 里 `async with httpx.AsyncClient()`,10 个请求 = 10 套连接池。外层共享后提速 41%。
5. **VS Code 默认用 conda 全局 Python 跑**:应该 `uv run python solution.py` 才是这个项目的正确姿势,能保证依赖隔离。

## 附带学到

- **`*` 解包**:调用处 `f(*lst)` 拆成位置参数,定义处 `def g(*args)` 收集成 tuple,互为逆操作。`g([1,2,3])` ≠ `g(*[1,2,3])`,前者 args 是 `([1,2,3],)` 只收了 1 个元素。
- **`**` 字典版本**:`f(**kwargs)` 拆成关键字参数;`def f(**kwargs)` 收集关键字参数成 dict。
- **`time.perf_counter()` > `time.time()`**:专门用于测时间间隔,精度更高、单调不受系统时间回拨影响。

## /simplify 改动

本次代码量小(~15 行),未跑 `/simplify`。待 Day 9 代码量起来后统一过一次。

## 未完成

- **`asyncio.Task` / `asyncio.create_task`**:选了 B 路线提前结束,明天 Day 9 开头补上再进入 Queue / Semaphore。
