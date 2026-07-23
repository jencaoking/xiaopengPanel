"""
RateLimiter 速率限制器单元测试

测试范围：
- 构造函数默认值与自定义值
- is_allowed 在限额内放行、超限拒绝
- 时间窗口过期后重置
- 不同 key 互相独立
- cleanup 清理过期记录

注意：app.py 的导入会触发 api.routes → db_manager → db_backup → croniter 等
传递依赖，在缺少 croniter 等第三方包的环境下无法直接 import。
为测试 app.py 中的真实 RateLimiter 源码，这里通过 ast 从 app.py 源文件中
提取 RateLimiter 类定义并 exec 执行，确保测试的是仓库中的真实代码。
"""
import os
import ast
import time
import pytest
from unittest.mock import patch


def _load_rate_limiter_from_app_source():
    """从 app.py 源码中提取 RateLimiter 类定义并执行返回该类。

    避免触发 app 模块的完整导入链（依赖 croniter 等第三方包）。
    RateLimiter 类是自包含的，仅依赖标准库 time，可安全独立执行。
    """
    app_py = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'app.py'
    )
    with open(app_py, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'RateLimiter':
            namespace = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]),
                         app_py, 'exec'), namespace)
            return namespace['RateLimiter']
    raise ImportError('RateLimiter class not found in app.py')


RateLimiter = _load_rate_limiter_from_app_source()


# ==================== 构造函数 ====================

class TestRateLimiterConstructor:
    """RateLimiter 构造函数测试"""

    @pytest.mark.unit
    def test_default_values(self):
        """默认 max_requests=100，window_seconds=60"""
        rl = RateLimiter()
        assert rl.max_requests == 100
        assert rl.window_seconds == 60
        assert rl.requests == {}

    @pytest.mark.unit
    def test_custom_values(self):
        """应支持自定义 max_requests 与 window_seconds"""
        rl = RateLimiter(max_requests=5, window_seconds=10)
        assert rl.max_requests == 5
        assert rl.window_seconds == 10

    @pytest.mark.unit
    def test_requests_dict_independent(self):
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
    def test_allows_under_limit(self):
        """请求数未达上限时应允许"""
        rl = RateLimiter(max_requests=3, window_seconds=60)
        assert rl.is_allowed('user1') is True
        assert rl.is_allowed('user1') is True
        assert rl.is_allowed('user1') is True

    @pytest.mark.unit
    def test_blocks_over_limit(self):
        """请求数达到上限后应拒绝"""
        rl = RateLimiter(max_requests=2, window_seconds=60)
        assert rl.is_allowed('user1') is True
        assert rl.is_allowed('user1') is True
        # 第三次应被拒绝
        assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_blocks_repeatedly_after_limit(self):
        """超限后多次请求都应被拒绝"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.is_allowed('user1')
        for _ in range(5):
            assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_resets_after_window_expires(self):
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
    def test_does_not_reset_within_window(self):
        """时间窗口未过期时仍应拒绝"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.is_allowed('user1')
        # 时间前进 30 秒（仍在窗口内）
        base_time = time.time() + 30
        with patch('time.time', return_value=base_time):
            assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_different_keys_independent(self):
        """不同 key 应拥有独立的限流计数"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        assert rl.is_allowed('user1') is True
        # user1 已达上限
        assert rl.is_allowed('user1') is False
        # user2 仍可访问
        assert rl.is_allowed('user2') is True
        assert rl.is_allowed('user2') is False

    @pytest.mark.unit
    def test_records_timestamps(self):
        """每次允许的请求应记录时间戳"""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        rl.is_allowed('user1')
        rl.is_allowed('user1')
        assert len(rl.requests['user1']) == 2

    @pytest.mark.unit
    def test_new_key_starts_with_single_timestamp(self):
        """新 key 第一次请求后应仅有一个时间戳"""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        rl.is_allowed('new_user')
        assert 'new_user' in rl.requests
        assert len(rl.requests['new_user']) == 1

    @pytest.mark.unit
    def test_exactly_at_limit_blocks(self):
        """正好达到上限时下一次应被拒绝（>= 判断）"""
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert rl.is_allowed('user1') is True
        # 第 4 次达到 >= max_requests，应拒绝
        assert rl.is_allowed('user1') is False

    @pytest.mark.unit
    def test_expired_timestamps_cleaned_before_check(self):
        """is_allowed 应在判断前清理过期时间戳"""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.is_allowed('user1')  # 占用唯一名额

        # 时间前进 61 秒，过期时间戳应在下一次调用时被清理
        future = time.time() + 61
        with patch('time.time', return_value=future):
            # 清理后列表为空，应允许新请求
            assert rl.is_allowed('user1') is True
            assert len(rl.requests['user1']) == 1


# ==================== cleanup ====================

class TestCleanup:
    """cleanup 清理过期记录测试"""

    @pytest.mark.unit
    def test_cleanup_removes_expired_entries(self):
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
    def test_cleanup_keeps_active_entries(self):
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
    def test_cleanup_removes_only_expired_timestamps(self):
        """cleanup 应仅清理过期时间戳，保留未过期的"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        # 第一批请求（将过期）
        rl.is_allowed('user1')
        rl.is_allowed('user1')

        # 时间前进 50 秒，再发一次请求（仍有效）
        t1 = time.time() + 50
        with patch('time.time', return_value=t1):
            rl.is_allowed('user1')

        # 再前进 20 秒（第一批 T 已过期 70s，第三次 T+50 仅过 20s 仍有效）
        t2 = time.time() + 70
        with patch('time.time', return_value=t2):
            rl.cleanup()

        assert 'user1' in rl.requests
        # 仅保留最后一次未过期的时间戳
        assert len(rl.requests['user1']) == 1

    @pytest.mark.unit
    def test_cleanup_empty_dict_no_error(self):
        """cleanup 对空字典不应报错"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.cleanup()
        assert rl.requests == {}

    @pytest.mark.unit
    def test_cleanup_partial_expiry(self):
        """cleanup 应正确处理部分 key 过期的情况"""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.is_allowed('active_user')  # 仍活跃

        # 模拟另一个 key 的时间戳已过期
        rl.requests['expired_user'] = [time.time() - 100]

        rl.cleanup()

        assert 'active_user' in rl.requests
        assert 'expired_user' not in rl.requests

    @pytest.mark.unit
    def test_cleanup_does_not_remove_keys_with_valid_timestamps(self):
        """cleanup 不应删除仍包含有效时间戳的 key"""
        rl = RateLimiter(max_requests=10, window_seconds=100)
        rl.is_allowed('user1')

        # 时间前进 50 秒（仍在 100 秒窗口内）
        with patch('time.time', return_value=time.time() + 50):
            rl.cleanup()

        assert 'user1' in rl.requests
        assert len(rl.requests['user1']) == 1
