# Day 7 · Week 1 周复盘

## 🎯 目标

- 10 道面试题(装饰器 / 生成器 / 迭代器 / 上下文管理器 / 魔法方法 / 类型注解)检验 Week 1 掌握度
- 综合作业:把装饰器 + 生成器 + 上下文管理器**三种机制组合**起来,写一个迷你日志工具 `tinylog`,不依赖任何第三方库

## 🧠 思考过程

三个组件的职责拆开想:

- **装饰器 `@log_calls`**:给任意函数加"入参 / 返回值 / 耗时 / 异常"日志 → 对应 Week 1 的 Day 1 装饰器 + Day 6 `__name__` / `__doc__`
- **上下文管理器 `log_block(label)`**:给一段代码加"开始 / 结束 / 异常 + 耗时"日志 → 对应 Day 5 `@contextmanager` 用法
- **生成器 `tail(path)`**:流式读文件逐行 yield(不一次性 readlines)→ 对应 Day 3 yield

demo.py 把三个串起来:用 `tail` 读日志文件,每行丢给 `@log_calls` 装饰的 `process_line`,整个过程套在 `log_block` 里,遇到 ERROR 行抛 `ValueError` 并被外层 `try/except` 吞掉继续循环。**一套下来 Week 1 全部知识点都被串起来了**。

## 🔧 最终方案

`tinylog.py`:

- `log_calls(func)`:`start = perf_counter()` 放 func 调用**前**,func 调用进 `try`,`except` 里打异常日志再 `raise` 不吞,正常路径打成功日志再 `return result`。`@functools.wraps(func)` 保住 `__name__` / `__doc__`。
- `log_block(label)`:`@contextmanager` 版本,`try / except / else` 分两路各算一次 `elapsed`,`except` 里必须 `raise` 不吞异常。
- `tail(path)`:`with open(path) as f: for line in f:` 逐行读,`line.rstrip()` 去换行符,空行 `continue`,`yield line`。

`demo.py`:`@log_calls` 装 `process_line`,`with log_block("scan log"): for line in tail(LOG_PATH):` 驱动;`LOG_PATH = Path(__file__).parent / "test.log"` 保证脚本位置无关。

## 🚨 踩坑

装饰器第一版完全结构错(接近全部推翻重写):

1. **`start = time.perf_counter()` 放 `log_calls(func)` 里**(只在装饰那一刻执行一次)→ 应该放 `wrapper` 里,每次调用重新记
2. **把日志 `return` 出去没 `print`** → 调用者拿到的是日志字符串,原函数返回值全丢
3. **`finally: return str + ...`** → `finally` 里 `return` 会压制异常,违反"异常要抛"要求;而且 `str` 是 Python 内建类型,当变量名会炸
4. **`func.__name__(*args, **kwargs)`** → `__name__` 是字符串属性不是函数,不能用括号调
5. **`func._name__`(少一个下划线)** → AttributeError
6. **`finally` 里又调了一次 `func(*args, **kwargs)`** → 原函数被执行两次,有副作用就惨了
7. **最后没 `return result`** → 装饰完的 `add(1, 2)` 永远返回 `None`

上下文管理器踩的坑:

- `except Exception: raise` 本身没用(抓了又立刻重抛 = 没写一样);正确套路是 `try / finally`,或者 `try / except: 打日志 + raise`
- 第一版 `except` 里**漏写 `raise`** → 异常被悄悄吞掉(Week 1 面试题 Q8 的考点)
- 拼写错 `filed` → `failed`、`after{X}` 缺空格、`{X:.4f}` 缺 `s` 单位

面试题 10 道里两处认知漏洞:

- **`yield from` 能接收子生成器 `return` 的值**(作为 `StopIteration.value`):`result = yield from inner()` 中 `result = "done"`。for 循环看不到 `return` 的值,只有委托它的 `yield from` 能拿到。
- **`__eq__` 重写后 `__hash__` 自动变 `None`**:因为"相等的对象 hash 必须相等"是 Python 要求的不变量,Python 为了防你写出不一致的 `__eq__` / `__hash__`,强制失效后者。这时 `{u1, u2}` 会直接抛 `TypeError: unhashable type`。要自定义 `__hash__` 和 `__eq__` 用同一组字段。

## ✨ `/simplify` 改动

agent 报了 7 处,都应用了:

1. `log_calls` 里 `result = func(...)` 缩进 3 空格 → 4 空格(PEP 8 强制)
2. 异常日志带上异常类型:`raised {e}` → `raised {type(e).__name__}: {e}`(调试能立刻看清异常类)
3. `tail` 的 `with open(path) as lines` → `as f`(`lines` 读起来像 list 实则是文件对象,惯例 `f`)
4. `tail` 加类型注解:`def tail(path: str | Path) -> Iterator[str]:`
5. `log_block` 从 `try / yield / except` 改成 `try / yield / except / else`,`elapsed` 每条分支只算一次,可读性↑
6. `demo.py` 里 `tail("test.log")` → `tail(LOG_PATH)`,`LOG_PATH = Path(__file__).parent / "test.log"` 做到脚本位置无关(之前跑 demo 因为 cwd 不对已经踩过一次)
7. `log_calls` 的 args 格式化换成自然函数调用样式:`add(args = (1, 2), kwargs = {}) called` → `add(1, 2) called`,用 `[repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]` 拼

**被 agent 标记但没应用的 1 条(教学笔记)**:`tail` 里 `with open(...)` 放在生成器里,**文件什么时候关**不是由 caller 决定,而是生成器耗尽 / GC / 显式 `.close()` 才关。这是"生成器 + 上下文管理器"的经典陷阱。规避写法:把 `open` 交给调用者,`tail` 只接收一个 file-like 对象。**知道这个坑的名字就够了**,本次不改。
