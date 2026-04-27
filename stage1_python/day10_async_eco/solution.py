# Day 10 异步生态作业:异步下载 100 个文件
#
# 需求:
#   1. 100 个 URL(自己造,推荐 https://httpbin.org/bytes/{n})
#   2. 并发限 10(Semaphore 或 max_connections 自选,理由写 README)
#   3. 每个请求超时 3s(用 httpx.Timeout,不要外层 wait_for)
#   4. aiofiles 异步写入 ./downloads/file_{i}.bin
#   5. 失败重试最多 2 次(总共最多 3 次请求),重试间 asyncio.sleep(1)
#   6. 收尾打印:总耗时 / 成功数 / 失败数 / 失败 URL 列表
#   7. loguru INFO 日志:开始 / 成功 / 失败 / 重试
#
# 提示:
#   - 主结构 gather(*[download_one(...) for ...])
#   - 只对 httpx.TimeoutException 重试,其他异常直接失败
#   - return_exceptions=True vs try/except 自己想清楚再选

import asyncio
import time
import httpx
import aiofiles
from loguru import logger
from pathlib import Path

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
                logger.info(f"file_{i} 下载成功")
                return
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    logger.warning(f"第 {attempt+1} 次超时,重试中")
                    await asyncio.sleep(1)
                else:
                    logger.warning(f"{url} {MAX_RETRIES + 1} 次全失败")
                    raise


async def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    urls = ["https://httpbin.org/bytes/1024"] * 100
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=10) as client:
        start = time.perf_counter()
        results = await asyncio.gather(
            *(download(client, url, sem, i) for i, url in enumerate(urls)),
            return_exceptions=True,
        )
        print(f"总耗时：{time.perf_counter() - start}")
    success = 0
    failed_items = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            failed_items.append((i, urls[i], type(res).__name__))
        else:
            success += 1
    print(f"成功:{success}/100")
    print(f"失败:{len(failed_items)}")
    print(f"失败 URL:{failed_items[:5]}...")


if __name__ == "__main__":
    asyncio.run(main())
