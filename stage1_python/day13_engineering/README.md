# Day 13 - 工程化

## 目标

掌握现代 Python 项目三件基础设施:pyproject.toml 元数据管理、loguru 结构化日志、pytest 测试框架,最终产出可 `uv build` 的本地 wheel。

## 思考过程

先搞清楚 `pyproject.toml` 三个区块各管什么(project / dependency-groups / build-system),再动手加 loguru 日志到函数里,最后写 pytest 测试跑通,逐步串联。

`clamp` 函数作为练习载体——逻辑简单但能练到日志记录、测试边界值覆盖、类型注解三件事。

## 最终方案

- `toolkit.py`:实现 `clamp(value, min_val, max_val) -> float`,用 `max(min_val, min(value, max_val))` 一行替代 if/elif 三分支,加 `logger.debug` 记录输入输出
- `test_toolkit.py`:三个测试覆盖 value 在范围内 / 低于下限 / 高于上限三个分支
- `pyproject.toml`:加 `[build-system]` hatchling + `asyncio_mode = "auto"` + `[tool.hatch.build.targets.wheel] include`

## 踩坑

1. `uv build` 缺 `[build-system]` → 退回 setuptools,找不到包报错
2. hatchling 找不到同名目录 → 要加 `[tool.hatch.build.targets.wheel] include = ["toolkit.py"]`
3. 测试文件写成 `if __name__ == "__main__":` 格式 → pytest 不收集,必须 `def test_*()`
4. assert 期望值写成输入值而不是夹后的边界值:`clamp(2,0,1)` 应该返回 `1`
5. `asyncio_mode="auto"` 加到了子目录 pyproject.toml,pytest rootdir 是父目录的 toml,不生效

## /simplify 改动

1. `clamp` 函数体 `result = value + if/elif` → `result = max(min_val, min(value, max_val))` 一行(用内置 min/max 替代手写分支)
2. 加类型注解 `value: float, min_val: float, max_val: float -> float`
3. 测试文件缩进 6 空格 → 标准 4 空格
