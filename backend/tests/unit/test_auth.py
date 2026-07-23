"""
认证模块单元测试

测试范围：
- 密码强度校验
- 登录逻辑（成功/失败/锁定/2FA）
- JWT 令牌刷新
- 密码修改
"""
import pytest
import time
import bcrypt
from unittest.mock import patch, MagicMock

from modules.auth import (
    check_password_strength,
    login,
    refresh_token,
    change_password,
    PASSWORD_PATTERN,
    JWT_EXPIRE_TIME,
    REFRESH_TOKEN_EXPIRE_TIME,
    MAX_LOGIN_ATTEMPTS,
    LOCKOUT_TIME,
)
from modules import auth


# ==================== 密码强度校验 ====================

class TestPasswordStrength:
    """密码强度校验测试"""

    @pytest.mark.parametrize('password', [
        'Abcdef1!',
        'StrongP@ss1',
        'MyP@ssw0rd',
        'Aa1!aaaa',
    ])
    def test_strong_passwords(self, password):
        """强密码应该通过校验"""
        is_valid, message = check_password_strength(password)
        assert is_valid is True
        assert '符合要求' in message

    @pytest.mark.parametrize('password,expected_substring', [
        ('Short1!', '长度'),          # 太短
        ('a' * 33 + 'A1!', '长度'),   # 太长
        ('ABCDEFGHI1!', '小写'),       # 无小写
        ('abcdefghi1!', '大写'),       # 无大写
        ('Abcdefgh!', '数字'),         # 无数字
        ('Abcdefgh1', '特殊字符'),     # 无特殊字符
    ])
    def test_weak_passwords(self, password, expected_substring):
        """弱密码应该被拒绝"""
        is_valid, message = check_password_strength(password)
        assert is_valid is False
        assert expected_substring in message

    def test_min_length_boundary(self):
        """最小长度边界值"""
        # 刚好8位且满足所有条件
        is_valid, _ = check_password_strength('Aa1!aaaa')
        assert is_valid is True

        # 7位，不满足
        is_valid, _ = check_password_strength('Aa1!aaa')
        assert is_valid is False

    def test_max_length_boundary(self):
        """最大长度边界值"""
        # 刚好32位且满足所有条件
        password = 'Aa1!' + 'a' * 28
        is_valid, _ = check_password_strength(password)
        assert is_valid is True

        # 33位，超出
        password = 'Aa1!' + 'a' * 29
        is_valid, _ = check_password_strength(password)
        assert is_valid is False

    def test_empty_password(self):
        """空密码"""
        is_valid, message = check_password_strength('')
        assert is_valid is False
        assert '长度' in message

    def test_special_chars_coverage(self):
        """特殊字符覆盖测试"""
        special_chars = '!@#$%^&*(),.?":{}|<>'
        for char in special_chars:
            password = f'Abcdef1{char}'
            is_valid, _ = check_password_strength(password)
            assert is_valid is True, f'特殊字符 {char} 应该被接受'


# ==================== 登录逻辑 ====================

class TestLogin:
    """登录功能测试"""

    def test_login_success(self, mock_users):
        """正确凭证登录成功"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/', method='POST', json={
            'username': 'admin',
            'password': 'Test@123456'
        }):
            result, status = login({'username': 'admin', 'password': 'Test@123456'})
            assert status == 200
            assert result['status'] == 'success'
            assert 'token' in result
            assert 'refresh_token' in result
            assert result['user']['username'] == 'admin'
            assert result['user']['role'] == 'admin'

    def test_login_wrong_password(self, mock_users):
        """错误密码登录失败"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = login({'username': 'admin', 'password': 'wrongpassword'})
            assert status == 401
            assert result['status'] == 'error'
            assert '尝试机会' in result['message']

    def test_login_nonexistent_user(self, mock_users):
        """不存在的用户登录失败"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = login({'username': 'nobody', 'password': 'Test@123456'})
            assert status == 401
            assert result['status'] == 'error'

    def test_login_missing_username(self, mock_users):
        """缺少用户名"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = login({'password': 'Test@123456'})
            assert status == 401

    def test_login_missing_password(self, mock_users):
        """缺少密码"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = login({'username': 'admin'})
            assert status == 401

    def test_login_lockout_after_max_attempts(self, mock_users):
        """超过最大尝试次数后锁定"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            # 尝试 MAX_LOGIN_ATTEMPTS 次错误密码
            for i in range(MAX_LOGIN_ATTEMPTS):
                login({'username': 'admin', 'password': 'wrong'})

            # 第 MAX_LOGIN_ATTEMPTS + 1 次应该被锁定
            result, status = login({'username': 'admin', 'password': 'Test@123456'})
            assert status == 403
            assert '登录尝试次数过多' in result['message']

    def test_login_lockout_then_unlock(self, mock_users):
        """锁定后超时自动解锁"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            # 制造锁定
            for i in range(MAX_LOGIN_ATTEMPTS):
                login({'username': 'admin', 'password': 'wrong'})

            # 确认已锁定
            result, status = login({'username': 'admin', 'password': 'wrong'})
            assert status == 403

            # 模拟锁定时间已过
            auth.login_attempts['admin'][1] = time.time() - LOCKOUT_TIME - 1

            # 应该可以再次尝试
            result, status = login({'username': 'admin', 'password': 'Test@123456'})
            assert status == 200
            assert result['status'] == 'success'

    def test_login_resets_attempts_on_success(self, mock_users):
        """登录成功后重置尝试次数"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            # 制造几次失败
            for i in range(3):
                login({'username': 'admin', 'password': 'wrong'})

            assert auth.login_attempts['admin'][0] == 3

            # 成功登录
            login({'username': 'admin', 'password': 'Test@123456'})

            # 尝试次数应被重置
            assert auth.login_attempts['admin'][0] == 0

    def test_login_with_2fa_enabled(self, mock_users):
        """2FA 启用时返回 2fa_required"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'), \
             patch('modules.totp_manager.get_2fa_status', return_value={'enabled': True}):
            result, status = login({'username': 'admin', 'password': 'Test@123456'})
            assert status == 200
            assert result['status'] == '2fa_required'
            assert 'temp_token' in result
            assert result['temp_token']


# ==================== 令牌刷新 ====================

class TestRefreshToken:
    """刷新令牌测试"""

    def test_refresh_token_success(self, mock_users):
        """有效的刷新令牌获取新访问令牌"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            # 先登录获取刷新令牌
            login_result, _ = login({'username': 'admin', 'password': 'Test@123456'})
            refresh = login_result['refresh_token']

            # 使用刷新令牌获取新令牌
            result, status = refresh_token({'refresh_token': refresh})
            assert status == 200
            assert result['status'] == 'success'
            assert 'token' in result
            assert result['token'] != login_result['token']  # 新令牌

    def test_refresh_token_missing(self, mock_users):
        """缺少刷新令牌"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = refresh_token({})
            assert status == 400
            assert result['status'] == 'error'

    def test_refresh_token_invalid(self, mock_users):
        """无效的刷新令牌"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = refresh_token({'refresh_token': 'invalid-token-string'})
            assert status == 401
            assert result['status'] == 'error'

    def test_refresh_token_wrong_type(self, mock_users):
        """使用访问令牌而非刷新令牌"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            # 先登录获取访问令牌
            login_result, _ = login({'username': 'admin', 'password': 'Test@123456'})
            access_token = login_result['token']

            # 用访问令牌作为刷新令牌使用
            result, status = refresh_token({'refresh_token': access_token})
            assert status == 400
            assert 'Invalid refresh token type' in result['message']

    def test_refresh_token_nonexistent_user(self, mock_users):
        """刷新令牌对应的用户已被删除"""
        from flask import Flask
        import jwt
        app = Flask(__name__)
        with app.test_request_context('/'):
            # 生成一个不存在用户的刷新令牌
            from modules.auth import get_jwt_secret
            token = jwt.encode(
                {
                    'username': 'deleted_user',
                    'exp': time.time() + 3600,
                    'iat': time.time(),
                    'type': 'refresh'
                },
                get_jwt_secret(),
                algorithm='HS256'
            )
            result, status = refresh_token({'refresh_token': token})
            assert status == 404
            assert result['status'] == 'error'


# ==================== 修改密码 ====================

class TestChangePassword:
    """修改密码测试"""

    def test_change_password_success(self, mock_users):
        """成功修改密码"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = change_password(
                'admin',
                'Test@123456',
                'NewP@ss123'
            )
            assert status == 200
            assert result['status'] == 'success'

    def test_change_password_wrong_old(self, mock_users):
        """原密码错误"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = change_password(
                'admin',
                'wrongoldpass',
                'NewP@ss123'
            )
            assert status == 401
            assert result['status'] == 'error'

    def test_change_password_weak_new(self, mock_users):
        """新密码强度不足"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = change_password(
                'admin',
                'Test@123456',
                'weak'
            )
            assert status == 400
            assert result['status'] == 'error'

    def test_change_password_nonexistent_user(self, mock_users):
        """用户不存在"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = change_password(
                'nobody',
                'Test@123456',
                'NewP@ss123'
            )
            assert status == 404

    def test_change_password_empty_old(self, mock_users):
        """空原密码"""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/'):
            result, status = change_password(
                'admin',
                '',
                'NewP@ss123'
            )
            assert status == 400
