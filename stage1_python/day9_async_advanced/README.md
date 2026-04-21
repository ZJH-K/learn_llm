# Day 9 · async 深入(Task / Semaphore / wait_for / cancel / Queue)

## 目标

Day 8 学了并发发动机(`gather`),Day 9 学控制旋钮:怎么**限流、超时、取消、解耦**。两个作业各对应一半旋钮:

1. **并发限流爬虫**(前半部分):`Semaphore` 限流 + `wait_for` 超时 + 异常优雅兜底(代码在对话里,未单独归档)
2. **告警流 Queue**(后半部分):`Queue` + 生产者-消费者 + 背压 + `cancel` 优雅收尾 → 本目录 `solution.py`

## 思考过程

### 作业 1:并发限流爬虫

1. 昨天 `gather` 发 10 个请求 1.25s 爽,**但如果 1000 个呢?** → 对方 429 / 本地 FD 爆 / 连接池满 → 必须限流
2. `Semaphore(N)` 是"令牌桶",`async with sem:` 拿令牌,代码块结束自动还 → 和 `AsyncClient` 同样"外层创建,传进 worker"模式
3. 没超时的异步代码 = 定时炸弹(一个请求卡住 → 所有 worker 卡住 → 服务 503)→ `wait_for` 强制超时
4. 异常类型混淆踩坑:`httpx.TimeoutException` ≠ `asyncio.TimeoutError`,抓错 = 等于没抓,`gather` 会整个崩掉
5. 故意混 `https://httpbin.org/delay/5` 验证超时 → 29×200 + 1×(-1) 优雅失败

### 作业 2:告警流 Queue

1. `gather` 是"一批跑完"模型,但真实场景是"源源不断"(日志流、告警流、LLM token 流)→ `Queue` 是这种场景的标配
2. `maxsize` 不是优化,是**背压**:生产快消费慢时 `put` 阻塞,反过来逼生产者慢下来
3. 消费者死循环 `while True: await queue.get()` → 必须靠外部 `cancel()` 或"毒丸"收尾
4. 输出是完美 round-robin,验证"消费速度决定吞吐"的工程真理

## 最终方案

### 作业 2 代码(solution.py)

```python
import asyncio

async def producer(queue):
    for i in range(10):
        await queue.put(f"alert-{i}")
        await asyncio.sleep(0.2)

async def consumer(name, queue):
    while True:
        item = await queue.get()
        print(f"{name} 消费了 {item}")
        await asyncio.sleep(1)
        queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=2)
    cons1 = asyncio.create_task(consumer("C1", queue))
    cons2 = asyncio.create_task(consumer("C2", queue))
    cons3 = asyncio.create_task(consumer("C3", queue))

    await producer(queue)
    await queue.join()

    for c in (cons1, cons2, cons3):
        c.cancel()
    await asyncio.gather(cons1, cons2, cons3, return_exceptions=True)

asyncio.run(main())
```

### 作业 1 代码(限流爬虫,wait_for 版)

```python
import asyncio
import httpx
import time

async def fetch(client, sem, url):
    async with sem:
        try:
            r = await asyncio.wait_for(client.get(url), timeout=3.0)
            return r.status_code
        except asyncio.TimeoutError:
            return -1

async def main():
    urls = ["https://www.example.com"] * 29 + ["https://httpbin.org/delay/5"]
    sem = asyncio.Semaphore(3)
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        results = await asyncio.gather(*(fetch(client, sem, url) for url in urls))
        print(results)
        print(f"耗时 {time.perf_counter() - start:.2f}s")

asyncio.run(main())
```

结果:`[200×29, -1]`,耗时 ~6s(slow URL 卡住一个 sem 槽位 3s,拖累整体)。

## 踩坑

1. **漏 `await`(第三次了)**:`r = asyncio.wait_for(...)` 前忘写 `await`,r 变协程对象,下一行 `.status_code` 崩。**肌肉记忆:看到 `asyncio.*` 调用就条件反射前缀 `await`**。

2. **`time.sleep` vs `asyncio.sleep`**:异步里 `time.sleep` 同步阻塞事件循环,`await time.sleep(...)` 因为 `time.sleep` 返回 `None` 直接 `TypeError`。**所有 sleep 用 `asyncio.sleep`**,`time` 只留给 `perf_counter` 计时。

3. **`task_done` 拼错 2 次**:先写成 `taskdown`,纠正后又写成 `task_down`。API 是 `task_done`,**"done"(完成)不是"down"(下去)**。

4. **后台 task 异常静默丢失(Day 9 最毒的坑)**:consumer 里调错 API → `AttributeError` → task 死掉但 main 不知道 → `queue.join()` 等永不到来的 `task_done` → 程序打 3 行后无报错死锁。工程防护:每个后台 task 外面包一层 `try/except` 把错误显式打出来。

5. **异常类型混淆**:`httpx.TimeoutException` 和 `asyncio.TimeoutError` 是完全不同的类型,抓错 = 等于没抓。**规则:谁负责超时,抓谁的异常**。

6. **`cancel()` 后忘 await**:虽然 `asyncio.run` 会兜底帮你收,但铁律是 `cancel + await`,手动 loop 场景不兜底会看到 `Task was destroyed but it is pending!`。

## /simplify 改动

代码量和对话里手动反复纠错已相当于 `/simplify` 的迭代(异常类型、API 拼写、await 位置、time vs asyncio.sleep 四条关键改动都是对话实时纠的),未另跑 `/simplify`。

## 关键认知带走

- **Semaphore 甜点公式**:`rate × 耗时 × 0.5`(打五折保命)
- **cancel 三铁律**:cancel 后必须 await;抓 `CancelledError` 必须 raise;不用 `except Exception:` 抓异步代码
- **消费速度决定系统吞吐**:加生产者没用,加消费者才提速
- **没超时的异步 = 定时炸弹**:所有下游调用都要有 timeout
