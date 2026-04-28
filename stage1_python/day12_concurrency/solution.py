import asyncio
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager

N_IO = 20
N_CPU = 8
CPU_LOAD = 5_000_000


def io_task(idx: int) -> int:
    time.sleep(0.5)
    return idx


def cpu_task(n: int) -> int:
    s = 0
    for i in range(n):
        s += i * i
    return s


async def io_task_async(idx: int) -> int:
    await asyncio.sleep(0.5)
    return idx


async def cpu_task_async(n: int) -> int:
    return cpu_task(n)


@contextmanager
def timed(label: str):
    start = time.perf_counter()
    yield
    print(f"{label:<14} {time.perf_counter() - start:.3f}s")


async def main():
    with timed("IO 串行"):
        for i in range(N_IO):
            io_task(i)

    with timed("IO 多线程"), ThreadPoolExecutor(max_workers=N_IO) as pool:
        list(pool.map(io_task, range(N_IO)))

    with timed("IO 多进程"), ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        list(pool.map(io_task, range(N_IO)))

    with timed("IO 多协程"):
        await asyncio.gather(*[io_task_async(i) for i in range(N_IO)])

    with timed("CPU 串行"):
        for _ in range(N_CPU):
            cpu_task(CPU_LOAD)

    with timed("CPU 多线程"), ThreadPoolExecutor(max_workers=N_CPU) as pool:
        list(pool.map(cpu_task, [CPU_LOAD] * N_CPU))

    with timed("CPU 多进程"), ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        list(pool.map(cpu_task, [CPU_LOAD] * N_CPU))

    with timed("CPU 多协程"):
        await asyncio.gather(*[cpu_task_async(CPU_LOAD) for _ in range(N_CPU)])


if __name__ == "__main__":
    asyncio.run(main())
