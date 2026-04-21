import asyncio
import httpx
import time

async def fetch(client, url):
        r = await client.get(url)
        return r.status_code

async def main():
    urls = ["https://www.example.com"] * 10
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        results = await asyncio.gather(*(fetch(client, url) for url in urls))
        print(results)
        print(f"耗时 {time.perf_counter() - start:.2f}s")

asyncio.run(main())
