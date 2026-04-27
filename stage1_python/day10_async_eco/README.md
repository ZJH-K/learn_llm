# Day 10 · 异步生态:异步下载 100 个文件

## 🎯 目标

把 Day 9 五旋钮(`gather` / `Semaphore` / `wait_for` / `cancel` / `Queue`)从 `asyncio.sleep` 假 IO 落到**真实工程场景**:

- 真发 HTTP(`httpx.AsyncClient`)
- 真写磁盘(`aiofiles`)
- 真处理失败(timeout 重试 + 统计)

需求要点:100 URL / 并发限 10 / 超时 3s / 重试 2 次 / 成功失败统计。

---

## 💭 思考过程

### 选 Semaphore 还是 max_connections 限流

两层都能限,但**颗粒度不同**:

- `Semaphore(10)` 限"任务并发"——应用层
- `max_connections=10` 限"TCP 连接"——传输层

选 Semaphore:看代码一眼看出"我要限 10 个任务";`max_connections` 是 client 内部隐式行为,读代码人看不出限流在哪。

### retry 应该在 Semaphore 内还是外

我这版是 **包 retry**:`async with sem` 在最外,for 循环重试在内。

| | 包 retry(我这版) | 包单次(retry 在外) |
|---|---|---|
| sleep(1) 期间 | 占槽 → 实际并发 < 10 | 不占槽 → 严格 10 并发 |
| 服务端压力 | 平稳 | 失败方立刻又来抢 → 同步雷暴 |

学习场景选简单(包 retry)。生产做法记住:**retry 在外 + jitter** 避免雷暴。

### 异常路线:raise vs 吞

需求是"统计成功失败",两条路:

- **路 1**(选):download 内 `raise`,main 用 `gather(return_exceptions=True)` 兜异常,事后 `isinstance(res, Exception)` 分类
- 路 2:download 吞所有异常,返回 `(url, ok)` 元组

选路 1:异常是 Python 标准失败信号,统计逻辑放 main 里更清楚。

---

## 🛠 最终方案

核心结构:

```python
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
MAX_RETRIES = 2

async def download(client, url, sem, i):
    async with sem:
        for attempt in range(MAX_RETRIES + 1):
            try:
                r = await client.get(url)
                r.raise_for_status()
                async with aiofiles.open(DOWNLOAD_DIR / f"file_{i}.bin", "wb") as f:
                    await f.write(r.content)
                return
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                else:
                    raise
```

main 用 `gather(..., return_exceptions=True)` 收所有结果,zip 后过 `isinstance` 分类统计。

---

## 🪤 踩坑

1. **`asyncio.sleep(1)` 漏 await** —— 协程对象被丢弃,根本没 sleep。Day 8 头号坑第三次踩
2. **`asyncio.run(main)` 漏括号** —— 传函数对象不是协程,`ValueError: a coroutine was expected`
3. **`f"DOWNLOAD_DIR/file_{i}.bin"` 变量没 `{}` 包** —— f-string 里裸名字是字面字符串,不是变量替换
4. **`"ab"`(append)模式 + 重试** —— 第一次写一半超时,重试 append → 半段坏数据 + 完整数据拼一起 → 文件损坏。下载场景一律 `"wb"` 覆盖
5. **`"w"` 写 bytes** —— `TypeError: write() argument must be str, not bytes`,binary 必须 `"wb"`
6. **`r` 不是 bytes 而是 Response 对象** —— 要 `r.content`(bytes)/ `r.text`(str)
7. **`for url, i in urls` 解包错** —— urls 是字符串列表,每个元素是 url 不是 (url, i) 二元组,要 `enumerate(urls)` 拿下标
8. **`httpx.Client` 写成同步版** —— `async with` + `await` 一起就崩,必须 `httpx.AsyncClient`
9. **`import loguru` 用不了** —— loguru 的入口是 `logger`,要 `from loguru import logger`

---

## 🔧 /simplify 改动

1. **加 `r.raise_for_status()`** —— 真 bug:4xx/5xx 被当成功内容写入文件,统计造假
2. **加 `if __name__ == "__main__":`** —— 文件被 import 时不该自动执行 main
3. **`DOWNLOAD_DIR` 抬到模块级** —— 不再透传成参数(uppercase 参数名不符 Python 命名规范)
4. **`MAX_RETRIES = 2` 抬到模块级** —— 函数体内不该放常量
5. **`"三次全失败"` → `f"{MAX_RETRIES + 1} 次全失败"`** —— 硬编码和常量解耦
6. **`enumerate(zip(urls, results))` → `enumerate(results)` + `urls[i]`** —— 双层冗余,简化
