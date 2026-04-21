"""Day 9 作业 1:并发限流爬虫。

30 个 URL 里混一个故意会超时的(httpbin.org/delay/5,响应 5 秒)。
要求:
- Semaphore(3) 限流
- wait_for timeout=3s 兜底
- 失败返回 -1,不让 gather 整个崩

结果:29×200 + 1×(-1),耗时 ~6s。
"""
import asyncio
import httpx
import time


async def fetch(client, sem, url):
    async with sem:
        try:
            r = await asyncio.wait_for(client.get(url), timeout=3.0)
            return r.status_code
        except asyncio.TimeoutError:
            return -1


async def main():
    urls = ["https://www.example.com"] * 29 + ["https://httpbin.org/delay/5"]
    sem = asyncio.Semaphore(3)
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        results = await asyncio.gather(*(fetch(client, sem, url) for url in urls))
        print(results)
        print(f"耗时 {time.perf_counter() - start:.2f}s")


asyncio.run(main())
