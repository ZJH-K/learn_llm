# Day 6 - 配置对象类(支持属性点取)

## 作业目标

写一个 `Config` 类,把一个普通 dict 包成"可以点取访问"的配置对象。综合用上今天学的 4 个魔法方法(`__init__` / `__repr__` / `__eq__` / `__getattr__`)。

## 行为契约

```python
data = {
    "app": "demo",
    "version": 1,
    "database": {
        "host": "localhost",
        "port": 5432,
    },
}

cfg = Config(data)
```

必须满足:

| 用法 | 期望 |
|---|---|
| `cfg.app` | `"demo"` |
| `cfg.version` | `1` |
| `cfg.database.host` | `"localhost"`(嵌套点取,关键!) |
| `cfg.database.port` | `5432` |
| `print(cfg)` | `Config(app='demo', version=1, database=Config(host='localhost', port=5432))` |
| `Config({"a": 1}) == Config({"a": 1})` | `True` |
| `Config({"a": 1}) == Config({"a": 2})` | `False` |
| `Config({"a": 1}) == {"a": 1}` | `False`(类型不同) |
| `cfg.nonexistent` | 抛 `AttributeError`(不能默默返回 None) |

## 跑法

```bash
uv run python main.py
```

对照 `main.py` 顶部 docstring 里的期望输出,**逐行一致**才算通过。

## 思考题

### Q1 · `__getattr__` 和 `__getattribute__` 的区别?

| 维度 | `__getattr__` | `__getattribute__` |
|---|---|---|
| **触发时机** | 正常属性查找**失败后**的兜底 | 属性访问的**第一入口**,每次都调 |
| **安全性** | 只要不在方法里访问未初始化的属性,就不会死循环 | 极易死循环(方法里随便访问 `self.x` 就再次触发) |
| **常用程度** | 日常工具类,Proxy/配置对象都用这个 | 极少用,只在需要拦截**所有**属性访问时 |

日常选 `__getattr__`,写代理/点取式 dict 都够用。

### Q2 · 嵌套 dict 在哪一步被包装成 Config?为什么不是在 `__getattr__` 里现包?

**答:在 `__init__` 里一次性递归包装**。

如果在 `__getattr__` 里现包,有三个问题:

1. **身份不稳定**:`cfg.database` 连续访问两次会得到**两个不同的 Config 实例**(每次现场 new 一个),`cfg.database is cfg.database` 是 False
2. **`__repr__` 变慢**:`__repr__` 里遍历 `_data.items()` 时,每个嵌套 value 都要重新包一遍
3. **一致性坏**:外部对 `cfg.database` 做任何修改不会回写到原 `_data`(因为是临时包装)

在 `__init__` 里一次性包好,`_data` 存的直接是"已经 Config 化"的嵌套结构,后面所有操作都对同一份对象。

### Q3 · 如果 `__eq__` 写成 `return self._data == other._data`,但 `_data` 里嵌套着 Config 对象,这个比较会无限递归吗?为什么?

**答:不会**。

dict 的 `==` 会对每一对 value 调 `==`,遇到嵌套 Config 就走 Config 自己的 `__eq__` → 比较里层 `_data` → 再遇到更深的 Config → ... 但**每一层嵌套层级是递减的**(dict 嵌套深度有限),最终触底到基本类型(int/str),递归自然收敛。

这是**结构归纳**(越下越浅),不是 `__getattr__` 那种"自己一直调自己"的**无限递归**(一直在同一层原地踏步)。两者要分清楚。
