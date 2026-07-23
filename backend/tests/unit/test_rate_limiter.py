"""
RateLimiter 速率限制器单元测试

测试范围：
- 构造函数默认值与自定义值
- is_allowed 在限额内放行、超限拒绝
- 时间窗口过期后重置
- 不同 key 互相独立
- cleanup 清理过期记录
"""
import time
import pytest
from unittest.mock import patch


@pytest.fixture(scope='module')
def RateLimiter(app):
    """获取 app.py 中的 RateLimiter 类（依赖 app fixture 确保模块已加载）"""
    from app import RateLimiter as _RL
    return _RL


# ==================== 构造函数 ====================

class TestRateLimiterConstructor:
    """RateLimiter 构造函数测试"""

    @pytest.mark.unit
    def test_default_values(self, RateLimiter):
        """默认 max_requests=100，window_seconds=60"""
        rl = RateLimiter()
        assert rl.max_requests == 100
        assert rl.window_seconds == 60
        assert rl.requests == {}

    @pytest.mark.unit
    def test_custom_values(self, RateLimiter):
        """应支持自定义 max_requests 与 window_seconds"""
        rl = RateLimiter(max_requests=5, window_seconds=10)
        assert rl.max_requests == 5
        assert rl.window_seconds == 10

    @pytest.mark.unit
    def test_requests_dict_independent(self, RateLimiter):
        """每个实例应拥有独立的 requests 字典"""
        rl1 = RateLimiter()
        rl2 = RateLimiter()
        rl1.is_allowed('key1')
        assert 'key1' in rl1.requests
        assert 'key1' not in rl2.requests


# ==================== is_allowed ====================

class TestIsAllowed:
    """is_allowed 限流判断测试"""

    @pytest.mark.unit
    def test_allows_under_limit(self, RateLimiter):
        """请求数未达上限时应允许"""
        rl = RateLimiter(max_requests=3, window_seconds=60)
        assert rl.is_allowed('user1') is True
        assert rl.is_allowed('user1') is True
        assert rl.is_allowed('user1') is True

    @pytest.mark.unit
    def test_blocks_over_limit(self, RateLimiter):
        """请求数达到上限后应拒绝"""
        rl = RateLimiter(max_requests=2, window_seconds=60)
        assert rl.is_allowed('user1') is True
        assert rl.is_allowed('user1') is True
        # 第三次应被拒绝
        assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_blocks_repeatedly_after_limit(self, RateLimiter):
        """超限后多次请求都应被拒绝"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.is_allowed('user1')
        for _ in range(5):
            assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_resets_after_window_expires(self, RateLimiter):
        """时间窗口过期后应重新允许请求"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        # 第一次允许
        assert rl.is_allowed('user1') is True
        # 第二次被拒
        assert rl.is_allowed('user1') is False

        # 模拟时间前进 61 秒（超过窗口）
        base_time = time.time() + 61
        with patch('time.time', return_value=base_time):
            assert rl.is_allowed('user1') is True

    @pytest.mark.unit
    def test_does_not_reset_within_window(self, RateLimiter):
        """时间窗口未过期时仍应拒绝"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.is_allowed('user1')
        # 时间前进 30 秒（仍在窗口内）
        base_time = time.time() + 30
        with patch('time.time', return_value=base_time):
            assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_different_keys_independent(self, RateLimiter):
        """不同 key 应拥有独立的限流计数"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        assert rl.is_allowed('user1') is True
        # user1 已达上限
        assert rl.is_allowed('user1') is False
        # user2 仍可访问
        assert rl.is_allowed('user2') is True
        assert rl.is_allowed('user2') is False

    @pytest.mark.unit
    def test_records_timestamps(self, RateLimiter):
        """每次允许的请求应记录时间戳"""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        rl.is_allowed('user1')
        rl.is_allowed('user1')
        assert len(rl.requests['user1']) == 2

    @pytest.mark.unit
    def test_new_key_starts_with_single_timestamp(self, RateLimiter):
        """新 key 第一次请求后应仅有一个时间戳"""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        rl.is_allowed('new_user')
        assert 'new_user' in rl.requests
        assert len(rl.requests['new_user']) == 1

    @pytest.mark.unit
    def test_exactly_at_limit_blocks(self, RateLimiter):
        """正好达到上限时下一次应被拒绝（>= 判断）"""
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert rl.is_allowed('user1') is True
        # 第 4 次达到 >= max_requests，应拒绝
        assert rl.is_allowed('user1') is False


# ==================== cleanup ====================

class TestCleanup:
    """cleanup 清理过期记录测试"""

    @pytest.mark.unit
    def test_cleanup_removes_expired_entries(self, RateLimiter):
        """cleanup 应移除过期的请求记录"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.is_allowed('user1')
        rl.is_allowed('user2')

        # 时间前进 70 秒（超过窗口）
        future = time.time() + 70
        with patch('time.time', return_value=future):
            rl.cleanup()

        # 所有时间戳过期，key 应被删除
        assert 'user1' not in rl.requests
        assert 'user2' not in rl.requests

    @pytest.mark.unit
    def test_cleanup_keeps_active_entries(self, RateLimiter):
        """cleanup 应保留未过期的请求记录"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.is_allowed('user1')

        # 时间仅前进 10 秒（仍在窗口内）
        future = time.time() + 10
        with patch('time.time', return_value=future):
            rl.cleanup()

        assert 'user1' in rl.requests
        assert len(rl.requests['user1']) == 1

    @pytest.mark.unit
    def test_cleanup_removes_only_expired_timestamps(self, RateLimiter):
        """cleanup 应仅清理过期时间戳，保留未过期的"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        # 第一批请求（将过期）
        rl.is_allowed('user1')
        rl.is_allowed('user1')

        # 时间前进 50 秒
        with patch('time.time', return_value=time.time() + 50):
            rl.is_allowed('user1')  # 第三次，仍有效

        # 再前进 20 秒（第一批过期，第三次仍在窗口内）
        with patch('time.time', return_value=time.time() + 70):
            rl.cleanup()

        assert 'user1' in rl.requests
        # 仅保留最后一次未过期的时间戳
        assert len(rl.requests['user1']) == 1

    @pytest.mark.unit
    def test_cleanup_empty_dict_no_error(self, RateLimiter):
        """cleanup 对空字典不应报错"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.cleanup()
        assert rl.requests == {}

    @pytest.mark.unit
    def test_cleanup_partial_expiry(self, RateLimiter):
        """cleanup 应正确处理部分 key 过期的情况"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.is_allowed('active_user')  # 仍活跃

        # 模拟另一个 key 的时间戳已过期
        rl.requests['expired_user'] = [time.time() - 100]

        rl.cleanup()

        assert 'active_user' in rl.requests
        assert 'expired_user' not in rl.requests
