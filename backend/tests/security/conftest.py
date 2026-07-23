"""
安全测试专用 fixtures

安全测试会频繁触发登录失败，容易触发 login_limiter 速率限制（5次/分钟）。
在每个测试前清理限制记录，确保测试相互独立。
"""
import pytest


@pytest.fixture(autouse=True)
def _clear_login_rate_limiter():
    """每个安全测试前清理登录速率限制记录，避免测试间相互影响"""
    try:
        from app import login_limiter
        # 清理所有记录的请求（包括 127.0.0.1）
        login_limiter.requests.clear()
    except Exception:
        pass
    yield
    # 测试后再次清理，避免影响后续测试
    try:
        from app import login_limiter
        login_limiter.requests.clear()
    except Exception:
        pass
