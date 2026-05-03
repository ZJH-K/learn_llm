# Day 14 · URL 健康检查器 CLI

Week 1-2 阶段收官项目。把前 13 天学的全部技术栈(decorator / async / Pydantic / loguru / pytest)拼成一个 110 行的 CLI 工具。

---

## 🎯 目标

产出可在终端跑的 URL 健康检查器,**强制覆盖 5 项**:

- 装饰器(`@retry` 异步带参)
- 异步并发(`asyncio.gather` + `Semaphore` 限流)
- Pydantic 配置(`CheckResult` 数据 Schema)
- loguru 结构化日志(双 sink)
- pytest 测试(覆盖 Schema / load_urls / 装饰器 / 并发行为)

```bash
uv run python solution.py --file urls.txt --concurrency 5 --timeout 5
uv run python solution.py --urls https://a.com https://b.com --concurrency 2
uv run pytest -v
```

---

## 🧠 思考过程(7 个 Step)

| Step | 决策 | 为什么 |
|---|---|---|
| 1 | `CheckResult` 用 Pydantic `BaseModel`,字段 `url` / `is_healthy` / `status_code: int \| None` / `elapsed_ms` / `error: str \| None` / `checked_at` | 健康 / 不健康共用一个 Schema;status_code 在网络异常时是 None(对应 Schema 的 `int \| None`)|
| 2 | `check_url` 内部 `try/except httpx.RequestError` 把异常转成 `is_healthy=False` 的 result,**不向外抛** | 健康检查的语义就是"报告状态",崩了反而失去价值 |
| 3 | `@retry` 用三层嵌套带参装饰器,基于**返回值 `is_healthy`** 而非异常触发重试 | check_url 已经吞了异常,只能从返回值判定;Day 2 的 retry 是异常版,这里是返回值版 |
| 4 | `check_all` 用 `_bounded` 辅助协程把 `Semaphore` **包在每个 task 内部** | 包在 gather 外面只 acquire 一次,Semaphore 完全失效(/review 抓到过这个 bug) |
| 5 | `argparse` + `--file` 二选一,`load_urls` 用列表推导式过滤空行 + strip | 文件读取最常见;命令行直接列也支持 |
| 6 | loguru 加文件 sink + utf-8(Windows 必加),retry 用 `logger.warning`,**JSON 结果保留 `print`** | 日志和结果输出的语义不同 —— 日志走 stderr / file,结果走 stdout 才能被 `\| jq` 之类的工具消费 |
| 7 | pytest 11 测试:Schema(3) + load_urls(3,用 `tmp_path` + `SimpleNamespace`)+ retry(3,fake async function + nonlocal 计数 + `delay=0`)+ check_all 行为测试(1,守 Semaphore 语义) | 测装饰器不要测真 check_url(太重),手写 fake 函数最干净 |

---

## ✅ 最终方案

```
solution.py (95 行)
├─ CheckResult           Pydantic Schema,default_factory 给 checked_at
├─ retry(times, delay)   异步带参装饰器,基于 is_healthy 重试
├─ check_url             单 URL 检查,client 复用,异常转 result
├─ check_all             gather + Semaphore(_bounded 包 task)
├─ parse_args / load_urls   argparse + 文件读取
└─ main / _async_main    入口 + 进出日志 + 健康统计

test_solution.py (~110 行)
└─ 11 个测试,uv run pytest -v 全 PASSED

pyproject.toml           运行依赖 (httpx / loguru / pydantic) + dev (pytest 系)
urls.txt                 5 个测试 URL(健康 / 慢 / 不健康 / DNS 失败 / 500)
```

---

## 🪤 踩坑(教学价值最高的 5 个)

1. **类 vs 实例**:写过 `CheckResult.url = url` 直接给类贴属性,**不是创建实例**。后果:绕过 Pydantic 校验 + 多次调用共享同一个 url 字段污染。修法是函数内用局部变量囤数据,最后 `return CheckResult(url=url, ...)` 实例化一次。
2. **try/except 变量初始化**:`status_code` 只在 try 成功路径赋值,`error` 只在 except 路径赋值,后续 `if 200 <= status_code < 300 and error is None` **任何一条路径都会 NameError**。修法:try 前先 `status_code = None; error = None` 兜底。
3. **同步装饰器装 async 函数**:`time.perf_counter` 测出来是 0 秒(测的是协程对象创建时间,没真 await),返回值是协程对象不是 result。修法:wrapper 也要 `async def`,内部 `await func(...)`。
4. **`asyncio.sleep` 漏 `await`**:`asyncio.sleep(delay)` 返回协程对象不睡。`time.sleep(delay)` 又会阻塞整个 event loop。**正确写法只有 `await asyncio.sleep(delay)`**。
5. **Semaphore 包错位置**:`async def check_all(...): async with sem: gather(...)` —— sem 在 gather 外面只 acquire 一次,内部所有 task 不受限。**必须**用辅助协程 `async def _bounded(url): async with sem: ...`,把 sem 包在**每个 task 内部**。

---

## 🔧 /simplify + /review 改动

### /simplify 抓 5 处(细节)
1. `print((f"..."))` 多余括号删
2. `times = 2, delay = 1` 关键字参数 PEP 8 不加空格 + `1` 改 `1.0` 类型一致
3. `def retry(times=2, delay=1.0)` 加类型注解 `(times: int, delay: float)`
4. `is_healthy = ... and (status_code is not None) and ...` 中间是 dead code(`error is None` 已隐含 status_code 非 None),删
5. line 42 trailing whitespace 清

### /review 抓 2 处必修(架构)
1. **🔴 Semaphore 失效 bug**:`check_all` 里 `_bounded` 函数定义了但 `gather` 直接调裸 `check_url` —— `--concurrency` 完全没生效。修法:gather 改调 `_bounded(url)`。**同时补 `test_check_all_respects_semaphore` 测试**用 fake check_url 计数 in_flight 守住 `max_seen ≤ max_concurrent`,防止 bug 复发。
2. **🔴 README 空** —— 由本次收尾填(就是这份文档)。

### /review 工程清理
- 删 `main.py`(`uv init` 自动生成的残留入口)
- `pyproject.toml` 去重:pytest / pytest-asyncio 之前在 `[project].dependencies` 和 `[dependency-groups].dev` 都列了,只留 dev

### /review 留作 tech debt(明确不今天处理)
- `check_url` 缺 mock 测试(需要 `respx` 第三方库,Week 5 / OnCall 项目时再补)
- URL 没用 `pydantic.HttpUrl`(更严格但更挑剔,用 `str` 友好)
- `--concurrency 0` / 负数 / 文件不存在 / 空文件等边界没处理(Day 15 起手时一起补健壮性)
- `@retry` 硬编码 `result.is_healthy`(YAGNI,有第二用例再泛化)

---

## 📊 关键数字

- **代码 / 测试行数**:solution.py 95 行 + test_solution.py ~110 行
- **测试**:11 个全 PASSED(`uv run pytest -v`)
- **并发加速**:5 个 URL,串行 ~13s → max_concurrent=2 ~3.9s(节省 70%)
- **踩坑数量**:12 个(独立纠正后跑通,记得比读文档牢)
