# Day 5 - 数据库连接 with 管理器

## 作业目标

写两版模拟数据库事务的上下文管理器,对比 **class 形式** 和 **`@contextmanager` 形式** 的写法差异。

## 行为契约

**共用**:一个伪 `_FakeDB` 对象,有 `.execute(sql)` 方法,累积未提交语句到 `pending` 列表。

**出块行为**(两版一致):

| 路径 | 动作序列 |
|---|---|
| 无异常 | `commit (N)` → `close` |
| 有异常 | `rollback (N)` → `close` → **异常继续向上抛(不吞)** |

## 使用方式(来自 `main.py`)

```python
# class 版
with DBConnection("orders") as conn:
    conn.execute("INSERT ...")

# generator 版
with db_connection("users") as conn:
    conn.execute("SELECT ...")
```

## 跑法

```bash
uv run python main.py
```

对照 `main.py` 顶部 docstring 里的期望输出,**逐行一致**才算通过。

## 思考题

### Q1 · 两版核心差异在哪?

四个维度对比:

| 维度 | class 版 | `@contextmanager` 版 |
|---|---|---|
| **`as xxx` 赋的值** | `__enter__` 的返回值 | yield 后面的表达式 |
| **怎么感知异常** | `__exit__` 的 `exc_type` 参数 | `try/except` 在 yield 这一行捕获 |
| **怎么保证异常向上抛** | 默认 `return None` 就会抛 | `except` 里必须**显式 `raise`** |
| **清理代码写哪** | `__exit__` 方法体 | `finally` 块 |

### Q2 · `__exit__` 要 return 什么才能保证异常向上抛?默认返回值是什么?

- 默认返回 `None`(falsy)就能保证异常向上抛
- **`return True`(truthy) 会把异常吞掉** —— 这是坑,除非明确要压制某类异常,否则永远别 return True
- `__exit__` 函数体不写 return,默认就是 None

### Q3 · `@contextmanager` 版如果 yield 不包在 try/finally 里,哪条路径会出问题?

两个隐患(都是异常路径):

1. **yield 不包 try/finally** → with 块抛异常时,异常会在 yield 这一行重抛,**后面的 commit/rollback/close 全跑不到**(清理漏做)
2. **包了 try/except 但 except 里忘了 raise** → 异常被静默吞掉,上层 `except RuntimeError as e: caught:...` 根本抓不到,看起来"一切正常"实际业务已经炸了

## 本次作业最关键的认知

**两版在行为上完全等价,但机制路径完全不同**:class 靠 `__exit__` 参数感知异常、默认 return None 透传;generator 靠 `try/except/else/finally` 四段分支感知、必须显式 `raise` 透传。记住这个对应关系,以后读 SQLAlchemy / httpx / fastapi 源码里的 context manager 就不会迷路。

另外一个从 /simplify 抓到的小点:**异常捕获范围要精确**。`except:` 和 `except Exception:` 不等价,前者会吞 Ctrl-C,业务代码里默认用 `except Exception:`(和 Day 2 @retry 里的坑同源)。
