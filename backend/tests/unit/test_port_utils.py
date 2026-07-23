"""
端口工具模块单元测试

测试范围：
- is_port_available 端口可用性检查（边界、绑定成功/失败）
- validate_port 端口有效性校验（范围、类型、占用）
- check_port_in_use 通过 psutil 检查端口监听
- get_current_process_pid 返回当前进程 PID
"""
import os
import socket
import pytest
from unittest.mock import patch, MagicMock

from modules.port_utils import (
    is_port_available,
    validate_port,
    check_port_in_use,
    get_current_process_pid,
)


# ==================== is_port_available ====================

class TestIsPortAvailable:
    """is_port_available 端口可用性检查测试"""

    @pytest.mark.unit
    def test_port_below_1024_returns_false(self):
        """小于 1024 的端口应返回 False"""
        assert is_port_available(80) is False
        assert is_port_available(1) is False
        assert is_port_available(1023) is False

    @pytest.mark.unit
    def test_port_above_65535_returns_false(self):
        """大于 65535 的端口应返回 False"""
        assert is_port_available(65536) is False
        assert is_port_available(100000) is False

    @pytest.mark.unit
    def test_non_integer_port_returns_false(self):
        """非整数类型端口应返回 False"""
        assert is_port_available('8080') is False
        assert is_port_available(None) is False
        assert is_port_available(8080.5) is False

    @pytest.mark.unit
    def test_boundary_ports_valid(self):
        """边界端口 1024 和 65535 应进入绑定流程"""
        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        with patch('modules.port_utils.socket.socket', return_value=mock_socket):
            # 1024 边界
            assert is_port_available(1024) is True
            # 65535 边界
            assert is_port_available(65535) is True
        # 验证调用了 bind
        assert mock_socket.bind.called

    @pytest.mark.unit
    def test_available_port_returns_true(self):
        """可绑定的端口应返回 True"""
        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        with patch('modules.port_utils.socket.socket', return_value=mock_socket):
            assert is_port_available(8080) is True
            mock_socket.bind.assert_called_with(('0.0.0.0', 8080))

    @pytest.mark.unit
    def test_in_use_port_returns_false(self):
        """已被占用的端口应返回 False"""
        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        mock_socket.bind.side_effect = socket.error('Address already in use')
        with patch('modules.port_utils.socket.socket', return_value=mock_socket):
            assert is_port_available(8080) is False

    @pytest.mark.unit
    def test_socket_sets_timeout(self):
        """应设置 1 秒超时"""
        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        with patch('modules.port_utils.socket.socket', return_value=mock_socket):
            is_port_available(8080)
            mock_socket.settimeout.assert_called_with(1)


# ==================== validate_port ====================

class TestValidatePort:
    """validate_port 端口校验测试"""

    @pytest.mark.unit
    def test_valid_port_returns_success(self):
        """有效端口应返回 (True, 端口有效)"""
        with patch('modules.port_utils.check_port_in_use', return_value=False):
            ok, msg = validate_port(8080)
            assert ok is True
            assert '有效' in msg

    @pytest.mark.unit
    @pytest.mark.parametrize('port', [80, 1, 1023, -1, 0])
    def test_port_out_of_range_low(self, port):
        """小于 1024 的端口应返回 (False, 范围错误)"""
        with patch('modules.port_utils.check_port_in_use', return_value=False):
            ok, msg = validate_port(port)
            assert ok is False
            assert '1024-65535' in msg

    @pytest.mark.unit
    @pytest.mark.parametrize('port', [65536, 100000, 70000])
    def test_port_out_of_range_high(self, port):
        """大于 65535 的端口应返回 (False, 范围错误)"""
        with patch('modules.port_utils.check_port_in_use', return_value=False):
            ok, msg = validate_port(port)
            assert ok is False
            assert '1024-65535' in msg

    @pytest.mark.unit
    def test_string_port_convertible(self):
        """可转换为整数的字符串端口应能通过"""
        with patch('modules.port_utils.check_port_in_use', return_value=False):
            ok, msg = validate_port('8080')
            assert ok is True
            assert '有效' in msg

    @pytest.mark.unit
    def test_non_integer_port_returns_error(self):
        """无法转换为整数的字符串应返回 (False, 必须是整数)"""
        ok, msg = validate_port('abc')
        assert ok is False
        assert '整数' in msg

    @pytest.mark.unit
    def test_port_in_use_returns_error(self):
        """已被占用的端口应返回 (False, 端口已被占用)"""
        with patch('modules.port_utils.check_port_in_use', return_value=True):
            ok, msg = validate_port(8080)
            assert ok is False
            assert '占用' in msg

    @pytest.mark.unit
    def test_validate_port_string_out_of_range(self):
        """超出范围的字符串端口应返回范围错误"""
        with patch('modules.port_utils.check_port_in_use', return_value=False):
            ok, msg = validate_port('80')
            assert ok is False
            assert '1024-65535' in msg


# ==================== check_port_in_use ====================

class TestCheckPortInUse:
    """check_port_in_use 端口监听检查测试"""

    @pytest.mark.unit
    def test_port_listened_returns_true(self):
        """端口处于 LISTEN 状态时应返回 True"""
        conn = MagicMock()
        conn.laddr.port = 8080
        conn.status = 'LISTEN'

        with patch('modules.port_utils.psutil.net_connections', return_value=[conn]):
            assert check_port_in_use(8080) is True

    @pytest.mark.unit
    def test_port_not_listened_returns_false(self):
        """端口未处于 LISTEN 状态时应返回 False"""
        conn = MagicMock()
        conn.laddr.port = 8080
        conn.status = 'ESTABLISHED'  # 非 LISTEN

        with patch('modules.port_utils.psutil.net_connections', return_value=[conn]):
            assert check_port_in_use(8080) is False

    @pytest.mark.unit
    def test_no_connections_returns_false(self):
        """无任何连接时应返回 False"""
        with patch('modules.port_utils.psutil.net_connections', return_value=[]):
            assert check_port_in_use(8080) is False

    @pytest.mark.unit
    def test_different_port_returns_false(self):
        """监听其他端口时应返回 False"""
        conn = MagicMock()
        conn.laddr.port = 9000  # 不同的端口
        conn.status = 'LISTEN'

        with patch('modules.port_utils.psutil.net_connections', return_value=[conn]):
            assert check_port_in_use(8080) is False

    @pytest.mark.unit
    def test_multiple_connections_one_matches(self):
        """多个连接中有一个匹配 LISTEN 应返回 True"""
        conn1 = MagicMock()
        conn1.laddr.port = 9000
        conn1.status = 'LISTEN'

        conn2 = MagicMock()
        conn2.laddr.port = 8080
        conn2.status = 'LISTEN'

        conn3 = MagicMock()
        conn3.laddr.port = 8080
        conn3.status = 'ESTABLISHED'

        with patch('modules.port_utils.psutil.net_connections',
                   return_value=[conn1, conn2, conn3]):
            assert check_port_in_use(8080) is True


# ==================== get_current_process_pid ====================

class TestGetCurrentProcessPid:
    """get_current_process_pid 测试"""

    @pytest.mark.unit
    def test_returns_int(self):
        """应返回整数类型的 PID"""
        pid = get_current_process_pid()
        assert isinstance(pid, int)

    @pytest.mark.unit
    def test_matches_os_getpid(self):
        """应与 os.getpid() 返回值一致"""
        assert get_current_process_pid() == os.getpid()

    @pytest.mark.unit
    def test_pid_positive(self):
        """PID 应为正数"""
        assert get_current_process_pid() > 0
