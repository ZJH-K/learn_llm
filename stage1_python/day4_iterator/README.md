# Day 4 - 无限斐波那契迭代器

## 作业做了什么

两种方式实现"永远吐下一个斐波那契数"的迭代器,放同一文件对比:

- `class Fib` — 用迭代器协议实现(`__iter__` / `__next__`),状态存在实例属性里
- `fib_gen()` — 用 generator 实现,`while True: yield` 无限循环

两版输出必须完全一致:`0 1 1 2 3 5 8 13 21 34`。

## 思考题

### Q1 · 两版行数差多少?哪个更好写?

class 版 11 行,generator 版 5 行,差一倍以上。**generator 明显更好写** —— `while True: yield a; a, b = b, a+b` 三行搞定,不用手写 `__iter__` / `__next__` 骨架,状态由 Python 自动冻结/恢复,完全不用管。

### Q2 · 加一个 `.reset()` 方法(数列从头开始),哪种更容易?

**class 版秒杀 generator**。class 只要加一个方法:

```python
def reset(self):
    self.a, self.b = 0, 1
```

generator 版几乎做不到 —— generator 对象一旦创建,内部状态对外部是黑盒,没有重置入口。想"重头开始"只能重新调 `fib_gen()` 造一个新对象,那就不是 reset 了。

## 本次作业最关键的认知

**class Iterator 和 generator 里的"循环"位置正好相反**:

| | class | generator |
|---|---|---|
| 循环写在哪 | **不写**——Python 反复调 `__next__` | **函数里** `while True` 包 yield |

这是今天最容易踩的误区 —— 学会了 class 版"`__next__` 不能 while True"之后,回头写 generator 很容易把这个教训也带过去,结果只 yield 一次就抛 StopIteration 了。

## 选型原则(Day 4 第 3 节对照表坐实)

- 简单吐一串值 → generator
- 需要暴露 `.reset()` / `.progress()` / `.current()` 这种方法 → class Iterator
- 需要"集合对象可多次遍历" → class Iterable(`__iter__` 返回新 Iterator)
