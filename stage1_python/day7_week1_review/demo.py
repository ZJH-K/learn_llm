from pathlib import Path

from tinylog import log_block, log_calls, tail

LOG_PATH = Path(__file__).parent / "test.log"


@log_calls
def process_line(line: str) -> int:
    if "ERROR" in line:
        raise ValueError(f"bad line: {line!r}")
    return len(line)


with log_block("scan log"):
    for line in tail(LOG_PATH):
        try:
            process_line(line)
        except ValueError:
            pass


@log_calls
def add(a, b):
    return a + b


print(add.__name__)