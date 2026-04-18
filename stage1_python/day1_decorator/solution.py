import functools
import time

def timing(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__}运行{(time.perf_counter() - t0)*1000:.2f}毫秒")
        return result
    return wrapper

@timing
def slow():
    time.sleep(0.5)

slow()

@timing
def add(a, b):
    return a + b

print(add(2, 3))
print(add.__name__)