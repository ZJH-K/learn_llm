import functools
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        parts = [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
        call_str = f"{func.__name__}({', '.join(parts)})"
        print(f">>> {call_str} called")
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"!!! {func.__name__} raised {type(e).__name__}: {e} after {elapsed:.4f}s")
            raise
        elapsed = time.perf_counter() - start
        print(f"<<< {func.__name__} returned {result!r} in {elapsed:.4f}s")
        return result
    return wrapper


@contextmanager
def log_block(label):
    print(f"[{label}] start")
    start = time.perf_counter()
    try:
        yield
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"[{label}] failed: {type(e).__name__}: {e} after {elapsed:.4f}s")
        raise
    else:
        elapsed = time.perf_counter() - start
        print(f"[{label}] end in {elapsed:.4f}s")


def tail(path: str | Path) -> Iterator[str]:
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            yield line

 
