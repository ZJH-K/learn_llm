import time
import functools
from loguru import logger

def retry(times=3, delay=1):
    if times < 1:
          raise ValueError("times must be >= 1")
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"第{i+1}次重试,异常:{e}")
                    last_exc = e
                    if i < times - 1:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
            
if __name__ == "__main__":
    # 场景 A
    @retry(times=3, delay=1)
    def always_fail():
        raise ValueError("boom")

    # 场景 B
    counter = {"n": 0}
    @retry(times=3, delay=1)
    def flaky():
        counter["n"] += 1
        if counter["n"] < 3:
            raise ValueError("boom")
        else:
            print("成功")

    try:
      always_fail()
    except ValueError as e:
      logger.info(f"always_fail 最终放弃: {e}")

    flaky()