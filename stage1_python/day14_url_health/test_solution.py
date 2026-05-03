from solution import CheckResult, load_urls, retry
import pytest
from datetime import datetime
from pydantic import ValidationError
from types import SimpleNamespace
import asyncio
import solution

def test_smoke():
    """烟雾测试 — 确保 import 能跑通"""
    assert True

def test_check_result_defaults():
    """只传必填字段时,默认值是否正确"""
    r = CheckResult(url="https://example.com", elapsed_ms=100.0)

    assert r.url == "https://example.com"
    assert r.elapsed_ms == 100.0
    assert r.is_healthy is False            # 默认 False
    assert r.status_code is None            # 默认 None
    assert r.error is None                  # 默认 None

def test_check_result_missing_url():
    """不传 url 应该抛 ValidationError"""
    with pytest.raises(ValidationError):
        CheckResult(elapsed_ms=100.0)

def test_check_result_checked_at_auto():
    """checked_at 不传也应该自动填一个 datetime"""
    r = CheckResult(url="https://x.com", elapsed_ms=100.0)

    # 断言 checked_at 是个 datetime 实例
    assert isinstance(r.checked_at, datetime)

def test_load_urls_from_file(tmp_path):
    """从文件读取 URL,空行应该被过滤"""
    # 准备:写一个临时文件,里面有 3 个 URL + 1 个空行
    p = tmp_path / "urls.txt"
    p.write_text(
        "https://a.com\n"
        "https://b.com\n"
        "\n"                          # 空行,应该被过滤
        "  https://c.com  \n",        # 行首行尾空白,应该被 strip
        encoding="utf-8",
    )

    # 模拟 args
    args = SimpleNamespace(file=str(p), urls=None)

    # 调用 + 断言
    result = load_urls(args)
    assert result == ["https://a.com", "https://b.com", "https://c.com"]

def test_load_urls_from_args():
    """命令行直接传 urls 时,直接返回该列表"""
    urls = ["https://a.com", "https://b.com", "https://c.com"]
    args = SimpleNamespace(file=None, urls=urls)
    result = load_urls(args)
    assert result == urls

def test_load_urls_neither_raises():
    """不传 file 也不传 urls 应该抛 ValueError"""
    args = SimpleNamespace(file=None, urls=None)
    with pytest.raises(ValueError):
        load_urls(args)

async def test_retry_success_no_retry():
    """第一次就健康,不应该触发重试"""
    call_count = 0

    @retry(times=2, delay=0)
    async def fake_check():
        nonlocal call_count
        call_count += 1
        return CheckResult(url="https://x.com", is_healthy=True, elapsed_ms=10.0)

    result = await fake_check()

    assert result.is_healthy is True
    assert call_count == 1                  # 只调了 1 次,没重试

async def test_retry_all_fail():
    """每次都不健康,应该总共调 times+1 次,返回最后那次的失败结果"""
    call_count = 0

    @retry(times=2, delay=0)
    async def fake_check():
        nonlocal call_count
        call_count += 1                                # nonlocal + 计数
        return CheckResult(url="https://x.com", is_healthy=False, elapsed_ms=10.0)

    result = await fake_check()

    assert result.is_healthy is False
    assert call_count == 3                # times=2,所以总共调几次?

async def test_retry_succeed_on_second():
    """第 1 次失败,第 2 次成功 → 应该只调 2 次,返回成功结果"""
    call_count = 0

    @retry(times=2, delay=0)
    async def fake_check():
        nonlocal call_count
        call_count += 1
        # 第 1 次返回不健康,第 2 次返回健康
        return CheckResult(
            url="https://x.com",
            is_healthy=(call_count == 2),               # 用 call_count 判断
            elapsed_ms=10.0,
        )

    result = await fake_check()

    assert result.is_healthy is True
    assert call_count == 2

async def test_check_all_respects_semaphore():
    """check_all 应该真的限制并发数"""
    in_flight = 0
    max_seen = 0

    # patch check_url 为一个 fake,记录同时活跃的并发数
    original = solution.check_url

    async def fake_check_url(client, url, timeout=5.0):
        nonlocal in_flight, max_seen
        in_flight += 1
        max_seen = max(max_seen, in_flight)
        await asyncio.sleep(0.1)            # 模拟网络耗时,让并发能堆起来
        in_flight -= 1
        return CheckResult(url=url, is_healthy=True, elapsed_ms=100.0)

    solution.check_url = fake_check_url
    try:
        urls = [f"https://x{i}.com" for i in range(10)]
        await solution.check_all(urls, max_concurrent=3, timeout=5.0)
        assert max_seen <= 3, f"Semaphore 失效!最多同时 {max_seen} 个,应该 ≤ 3"
    finally:
        solution.check_url = original       # 恢复原函数