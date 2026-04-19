# Day 3 - 流式读大文件的生成器

## 作业做了什么

两个 generator 串管道,统计日志里含 `ERROR` 的行数:

- `read_lines(path)` — 逐行 yield 文件内容,顺手 `rstrip("\n")` 去行尾换行
- `filter_contains(lines, keyword)` — 消费上游 generator,只 yield 含 keyword 的行

```python
pipeline = filter_contains(read_lines("access.log"), "ERROR")
count = sum(1 for _ in pipeline)
```

核心价值:**全程内存里只有当前一行**,文件多大都不会 OOM。

## 思考题

### Q1 · 如果改成 `return [line for line in f]` 跑 10GB 文件会怎样?

列表推导式会**立刻**把所有行都读进内存,10GB 文件直接撑爆内存(OOM)。generator 版本内存占用恒定——同一时刻只存当前一行。这就是流式处理相对批处理的本质优势。

### Q2 · `for + if + yield` vs `yield from (x for x in lines if keyword in x)`?

两者最终效果完全一样,差别在风格:

- `for + if + yield`:过程式,一眼看懂在过滤
- `yield from (生成器表达式)`:声明式,更紧凑但初学者不易读

**选型原则**:
- 过滤 / 变换 → `for + if + yield`
- 想整批透传一个现成 iterable/generator → `yield from`

## 踩过的坑

1. **函数里只写 `print(line)` 忘了 `yield`** → 它根本不是 generator,是返回 `None` 的普通函数
2. **`yield line` 先、`line.rstrip("\n")` 后** → yield 是暂停键,rstrip 要下次 next 才跑,对已经吐出去的值无效
3. **`line.rstrip("\n")` 单独成行** → str 不可变,rstrip 返回新字符串,不接住返回值 = 白跑。必须写成 `yield line.rstrip("\n")` 合成一步

## 遗留(Day 5 回来改)

`open(path)` 没关,属资源泄漏。Day 5 学 `with` 上下文管理器后回来修。
