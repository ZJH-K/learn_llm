"""Day 9 作业:用 asyncio.Queue 模拟告警流处理。

场景:
- 1 个生产者,每 0.2s 产生一个告警(共 10 个)
- 3 个消费者,每个处理告警要 1s
- Queue(maxsize=2) 触发背压
- 所有告警处理完后优雅关闭消费者

目标:打印每个告警被哪个消费者处理,对比总耗时。
"""
import asyncio

async def producer(queue):
    for i in range(10):
        await queue.put(f"alert-{i}")
        await asyncio.sleep(0.2)

async def consumer(name, queue):
    while True:
        item = await queue.get()
        print(f"{name} 消费了 {item}")
        await asyncio.sleep(1)
        queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=2)
    cons1 = asyncio.create_task(consumer("C1", queue))
    cons2 = asyncio.create_task(consumer("C2", queue))
    cons3 = asyncio.create_task(consumer("C3", queue))

    await producer(queue)
    await queue.join()
    
    for c in (cons1, cons2, cons3):
        c.cancel()
    await asyncio.gather(cons1, cons2, cons3, return_exceptions=True)

asyncio.run(main())