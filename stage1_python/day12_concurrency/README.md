# Day 12 · 并发对比:GIL / threading / multiprocessing / asyncio

## 🎯 目标

用**同一份 IO 任务和 CPU 任务**跑遍 4 种执行方式(串行 / threading / multiprocessing / asyncio),实测耗时,亲自验证 4 条反直觉认知:

1. GIL 让多线程跑 CPU 任务**等于串行**
2. multiprocess 跑 IO 任务**慢于** threading(进程启动开销)
3. `async def` 函数体里没 `await` **就是普通同步函数**(套 async 不等于并发)
4. multiprocess 加速比例 ≠ 1/N(进程启动 + IPC 开销摊不掉)

---

## 💭 思考过程

### 任务负载怎么定

- IO 任务:`time.sleep(0.5)` 模拟,跑 20 个(串行 = 10 秒)
- CPU 任务:`sum(i*i for i in range(5_000_000))` 单次约 0.3-0.5 秒,跑 8 次(串行 ≈ 2-4 秒)

负载要够大(不能秒级以下)否则差异都被启动开销淹没;但又不能太重(避免实验等太久)。

### asyncio 怎么跑同步函数

`time.sleep` 是同步阻塞,不能 await。所以 IO 任务的异步版**单独写一个 `io_task_async`**:`await asyncio.sleep(0.5)`。

CPU 任务故意保留 `async def cpu_task_async(n): return cpu_task(n)`,**不 await 任何东西**,目的就是验证 "async def 函数体里没 await 等于同步" 这条认知 —— 跑出来确实和串行差不多。

### 怎么测得准

`pool.map(...)` 是惰性的,**不 `list()` 强制迭代不会真的等任务完成**。如果 print 紧跟 map 没 list,会测出 0 秒(任务在 with 退出时才真跑完,但那时 print 已经打过了)。

`with timed(...), Pool() as pool` 多 `with` 链式语法,**让 pool 创建和销毁都被计时** —— 这才是用户感受到的"用多进程跑这件事的总耗时"。

---

## 🛠 最终方案

```python
import asyncio, os, time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager

N_IO = 20
N_CPU = 8
CPU_LOAD = 5_000_000


def io_task(idx: int) -> int:
    time.sleep(0.5); return idx

def cpu_task(n: int) -> int:
    s = 0
    for i in range(n): s += i * i
    return s

async def io_task_async(idx: int) -> int:
    await asyncio.sleep(0.5); return idx

async def cpu_task_async(n: int) -> int:
    return cpu_task(n)


@contextmanager
def timed(label: str):
    start = time.perf_counter()
    yield
    print(f"{label:<14} {time.perf_counter() - start:.3f}s")


async def main():
    with timed("IO 串行"):
        for i in range(N_IO): io_task(i)
    with timed("IO 多线程"), ThreadPoolExecutor(max_workers=N_IO) as pool:
        list(pool.map(io_task, range(N_IO)))
    with timed("IO 多进程"), ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        list(pool.map(io_task, range(N_IO)))
    with timed("IO 多协程"):
        await asyncio.gather(*[io_task_async(i) for i in range(N_IO)])

    with timed("CPU 串行"):
        for _ in range(N_CPU): cpu_task(CPU_LOAD)
    with timed("CPU 多线程"), ThreadPoolExecutor(max_workers=N_CPU) as pool:
        list(pool.map(cpu_task, [CPU_LOAD] * N_CPU))
    with timed("CPU 多进程"), ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        list(pool.map(cpu_task, [CPU_LOAD] * N_CPU))
    with timed("CPU 多协程"):
        await asyncio.gather(*[cpu_task_async(CPU_LOAD) for _ in range(N_CPU)])


if __name__ == "__main__":
    asyncio.run(main())
```

### 实测耗时(Windows / 本地机)

| 方式 | IO(20 × 0.5s) | CPU(8 × 5M 循环) |
|---|---|---|
| 串行 | 10.01 s | 2.46 s |
| threading | **0.51 s** ✅ | 2.42 s ❌ GIL 卡死 |
| multiprocess | 1.87 s ⚠️ 进程启动 | **1.21 s** ✅ 真并行 |
| asyncio | **0.51 s** ✅ | 2.58 s ❌ 没 await |

跑命令(Windows GBK 终端):
```bash
PYTHONIOENCODING=utf-8 uv run python day12_concurrency/solution.py
```

---

## 🪤 踩坑

1. **函数调用没传参** —— `io_task()` / `cpu_task()` TypeError(签名要 idx / n)
2. **`return SyntaxError`** —— 把内置异常类当占位符,实际返回了 SyntaxError 类对象
3. **`pool.map(...)` 不阻塞,print 在 with 内** —— 测出来全是 0 秒,with 退出才真跑
4. **CPU 任务传 `[2] * 8`** —— 单次循环 2 次几乎无耗时,根本测不出 CPU 负载差异
5. **`with httpx.AsyncClient():` 跑 asyncio.gather** —— 完全用错(httpx 是 HTTP 客户端,根本不需要),且要 `async with`
6. **`asyncio.gather(*(io_task2(2) * 20))`** —— coroutine 不能 `*20`,要列表推导 `[func(i) for i in range(20)]`
7. **`asyncio.gather(...)` 在同步顶层裸调** —— gather 返回 coroutine 必须被 await,要写 `async def main` + `asyncio.run(main())`
8. **`asyncio.to_thread(requests.get())`** —— 加括号导致 `requests.get` 先在主线程同步调,等于没异步;应 `asyncio.to_thread(func, *args)`(传**函数对象** + 参数)
9. **8 个 print 标签 IO/CPU copy-paste 错** —— CPU 段标签写成 "IO 多线程耗时"
10. **Windows GBK 编码不认 ✅** —— `UnicodeEncodeError: 'gbk' codec can't encode character '✅'`,`PYTHONIOENCODING=utf-8` 临时解,系统环境变量永久解
11. **multiprocess 必须 `if __name__ == "__main__":` 守卫** —— Windows spawn 模式无限递归 fork

---

## 🔧 /simplify 改动

1. **抽 `@contextmanager def timed(label)` —— 干掉 8 段计时 copy-paste**
   ```python
   @contextmanager
   def timed(label: str):
       start = time.perf_counter()
       yield
       print(f"{label:<14} {time.perf_counter() - start:.3f}s")
   ```
   8 段 `start = perf_counter() / 跑 / print(...)` → 8 个 `with timed(...)` 一行
2. **`cpu_task_async = async def cpu_task_async(n): return cpu_task(n)`** —— 消除字节级重复(async 壳套同步实现)
3. **所有测试归到一个 `async def main()`** —— sync/async 流程不再割裂(`with ProcessPoolExecutor(...)` 是同步 context,在 async 函数里用 `with` 完全合法)
4. **常量提取** —— `N_IO = 20` / `N_CPU = 8` / `CPU_LOAD = 5_000_000` 改一处生效
5. **`[2] * 20` → `range(N_IO)`** —— 不同 idx 比傻 2 语义清晰
6. **多 with 链式** —— `with timed(...), Pool() as pool:` 让 pool 创建销毁也算入计时(对比更真实)
7. **imports 合并** —— `from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor`
8. **`pool1 / pool2` → `pool`** —— with 块 scope 隔离,无需编号
9. **`io_task2 / cpu_task2` → `io_task_async / cpu_task_async`** —— 后缀语义化
10. **删 8 处 `# IO 串行` 这种 WHAT 注释** —— `timed("IO 串行")` 标签自己就是注释
11. **label 格式化对齐** —— `{label:<14}` 输出整齐一栏

代码量从 78 行 → 70 行,但更关键的是**复杂度断崖式下降**:每个测试 1 行,8 个测试线性堆叠,对比一目了然。
