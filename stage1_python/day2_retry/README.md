# Day 2 作业:`@retry(times=3, delay=1)`

## 目标

手写一个**带参装饰器** `@retry`,让被装饰的函数抛异常时自动重试,直到成功或用完次数。不用第三方 retry 库(tenacity/backoff),**裸写三层嵌套**,吃透带参装饰器的结构。

## 设计决策

| 决策点 | 选择 | 为什么 |
|---|---|---|
| `times` 口径 | **总尝试次数**(含首次) | `times=3` 最多调 3 次,比"初次 + N 次重试"语义清晰 |
| 全部失败怎么办 | `raise last_exc` 向上抛 | 调用方决定要不要吞,装饰器不越权吃异常 |
| `sleep` 放哪 | 每次 except 后,但**最后一次不 sleep** | 最后一次失败后再睡白等,纯浪费 |
| `times < 1` 边界 | 入口 `raise ValueError` | 防御性校验放函数入口,失败得早 |
| 异常范围 | `except Exception`(简化版) | 学习版先这样;生产版应传 `exceptions=(...)` 白名单 |

## 三层嵌套骨架

```python
def retry(times, delay):              # 第1层:吃装饰器参数(配置)
    def decorator(func):              # 第2层:吃被装饰函数
        @functools.wraps(func)
        def wrapper(*args, **kwargs): # 第3层:真正执行重试循环
            ...
        return wrapper
    return decorator
```

等价展开:`@retry(times=3, delay=1)` → `foo = retry(times=3, delay=1)(foo)`。

## 踩过的坑(4 个)

1. **`func(*args, **kwargs)` 位置错** —— 第一次写放在 for 循环外,等于只调一次,循环体内 try 的只是已经算好的 result,except 永远走不到。调用 func **必须放在 `try:` 里**。
2. **`logger.warning = xxx`** —— 忘了加括号,把函数对象当值赋出去了。打日志是**调用**,必须 `logger.warning("...")`。
3. **`raise last_exc` 缩进错** —— 不小心缩到和 `try/except` 平级,导致第 1 次 except 结束后就抛,循环只跑一轮。Python 靠缩进定代码块,错 4 空格就是 bug。
4. **场景 B `counter = {"n": 0}` 写在函数体里** —— 每次调用重置,永远不自愈。闭包修改外层变量要么用**可变容器 + 索引修改**(`counter["n"] += 1`),要么 `nonlocal`。

## 未来改进(今天不做)

- `exceptions=(ConnectionError, TimeoutError, ...)` 白名单 —— 当前 `except Exception` 连代码 bug 型的 `TypeError/KeyError` 也重试,毫无意义,浪费时间 + 放大故障
- **指数退避** `delay * 2**i` + **jitter**(随机扰动) —— 生产级 retry 默认配置,避免惊群
- 日志加 `func.__name__`,多处装饰时方便排查

## 运行

```bash
uv run python solution.py
```

预期关键输出:

- `always_fail`:3 条 warning(间隔 1 秒)→ `always_fail 最终放弃: boom`
- `flaky`:2 条 warning → `成功`
