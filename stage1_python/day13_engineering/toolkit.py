from loguru import logger


def clamp(value: float, min_val: float, max_val: float) -> float:
    result = max(min_val, min(value, max_val))
    logger.debug("clamp({}, {}, {}) -> {}", value, min_val, max_val, result)
    return result

