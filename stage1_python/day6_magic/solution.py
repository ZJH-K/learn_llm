# Day 6 - 配置对象类(支持属性点取)
#
# 任务:写一个 Config 类,把 dict 包装成"点取式"配置对象
#
# 必须实现的魔法方法:
#   __init__     —— 存 data,把嵌套 dict 也包成 Config
#   __getattr__  —— 点取兜底
#   __repr__     —— 友好显示
#   __eq__       —— 底层数据相等就相等
#
# 行为契约见 README.md;期望输出见 main.py 顶部 docstring。
# 写完跑:uv run python main.py


class Config:
    def __init__(self, data):
        self._data = {k: (Config(v) if isinstance(v, dict) else v) for k, v in data.items()}

    def __getattr__(self, key):
        # 坑:若 _data 未被 __init__ 设置(如 pickle/copy 绕过 __init__),
        # self._data 会再次触发本方法 → RecursionError。生产代码需加 if key == "_data": raise 守护。
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {key!r}") from None

    def __repr__(self):
        parts = ", ".join(f"{k}={v!r}" for k, v in self._data.items())
        return f"Config({parts})"
        

    def __eq__(self, other):
        if not isinstance(other, Config):
            return NotImplemented
        return self._data == other._data
