from pydantic import BaseModel, Field
from datetime import datetime
import httpx
import time
import asyncio
import functools
import argparse
from loguru import logger

class CheckResult(BaseModel):
    url: str
    is_healthy: bool = False
    status_code: int | None = None
    elapsed_ms: float
    error: str | None = None
    checked_at: datetime = Field(default_factory=datetime.now)

def retry(times: int = 2, delay: float = 1.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(times + 1):
                result = await func(*args, **kwargs)
                if result.is_healthy:
                    return result
                if attempt < times:
                    logger.warning(f"[retry] {result.url} 第 {attempt + 1} 次重试...")
                    await asyncio.sleep(delay)
            return result
        return wrapper
    return decorator

@retry(times=2, delay=1.0)
async def check_url(client: httpx.AsyncClient, url: str, timeout: float = 5.0) -> CheckResult:
    start = time.perf_counter()
    status_code = None
    error = None
    try:
        r = await client.get(url, timeout=timeout)
        status_code = r.status_code
    except httpx.RequestError as e:
        error = str(e) or e.__class__.__name__
    is_healthy = (error is None) and (200 <= status_code < 300)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return CheckResult(url=url, is_healthy=is_healthy, status_code=status_code, elapsed_ms=elapsed_ms, error=error)

async def check_all(urls: list[str], max_concurrent: int = 5, timeout: float = 5.0,) -> list[CheckResult]:
    sem = asyncio.Semaphore(max_concurrent)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def _bounded(url):
            async with sem:
                return await check_url(client, url, timeout=timeout)
        results = await asyncio.gather(*(_bounded(url) for url in urls))
        return results
    
def parse_args():
    parser = argparse.ArgumentParser(description="URL 健康检查器")

    parser.add_argument("--file", type=str, help="URL 列表文件路径(每行一个)")
    parser.add_argument("--urls", nargs="+", help="直接传 URL 列表(空格分隔)")
    parser.add_argument("--concurrency", type=int, default=5, help="并发上限")
    parser.add_argument("--timeout", type=float, default=5.0, help="超时秒数")

    return parser.parse_args()

def load_urls(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        return urls
    elif args.urls:
        return args.urls
    else:
        raise ValueError("必须指定 --file 或 --urls 之一")

def main():
    args = parse_args()
    logger.add("check.log", rotation="10 MB", level="INFO", encoding="utf-8")
    urls = load_urls(args)
    asyncio.run(_async_main(urls, args.concurrency, args.timeout))

async def _async_main(urls, concurrency, timeout):
    logger.info(f"开始检查 {len(urls)} 个 URL,并发上限 {concurrency},超时 {timeout}s")
    start = time.perf_counter()
    results = await check_all(urls, max_concurrent=concurrency, timeout=timeout)
    elapsed = time.perf_counter() - start

    healthy_count = sum(1 for r in results if r.is_healthy)
    logger.info(f"检查完成:总耗时 {elapsed:.2f}s,健康 {healthy_count}/{len(results)}")

    for r in results:
        print(r.model_dump_json(indent=2))

if __name__ == "__main__":
    main()