import os
import json
import secrets
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from config.config import config_instance
from modules.log_manager import log_system

# 2FA数据文件路径
TOTP_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'totp_data.json')

# 备用验证码数量
BACKUP_CODES_COUNT = 10

# TOTP发行者名称
TOTP_ISSUER = 'xiaopengPanel'


def _load_totp_data():
    """从JSON文件加载2FA数据"""
    try:
        if os.path.exists(TOTP_DATA_FILE):
            with open(TOTP_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log_system(f'Failed to load TOTP data: {e}', 'ERROR', 'totp')
    return {}


def _save_totp_data(data):
    """保存2FA数据到JSON文件"""
    try:
        os.makedirs(os.path.dirname(TOTP_DATA_FILE), exist_ok=True)
        with open(TOTP_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_system(f'Failed to save TOTP data: {e}', 'ERROR', 'totp')
        return False


def generate_secret():
    """生成TOTP密钥"""
    return pyotp.random_base32()


def generate_backup_codes(count=BACKUP_CODES_COUNT):
    """生成备用验证码"""
    codes = []
    for _ in range(count):
        # 生成格式为 XXXX-XXXX 的8位验证码
        code = secrets.token_hex(4).upper()
        formatted = f'{code[:4]}-{code[4:]}'
        codes.append(formatted)
    return codes


def get_totp_uri(username, secret):
    """生成TOTP URI用于二维码"""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=TOTP_ISSUER)


def generate_qr_code_base64(username, secret):
    """生成QR码的Base64编码图片"""
    uri = get_totp_uri(username, secret)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def verify_totp_code(secret, code):
    """验证TOTP验证码"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def verify_backup_code(username, code):
    """验证备用验证码，验证成功后删除该备用码"""
    data = _load_totp_data()
    user_data = data.get(username, {})

    if 'backup_codes' not in user_data:
        return False

    normalized_code = code.strip().upper()

    if normalized_code in user_data['backup_codes']:
        # 移除已使用的备用码
        user_data['backup_codes'].remove(normalized_code)
        data[username] = user_data
        _save_totp_data(data)
        log_system(f'Backup code used for user {username}', 'INFO', 'totp')
        return True

    return False


def setup_2fa(username):
    """初始化2FA设置，生成密钥和QR码（尚未启用）"""
    secret = generate_secret()
    qr_base64 = generate_qr_code_base64(username, secret)

    log_system(f'2FA setup initiated for user {username}', 'INFO', 'totp')

    return {
        'status': 'success',
        'secret': secret,
        'qr_code': qr_base64,
        'issuer': TOTP_ISSUER,
        'message': '请使用认证应用扫描二维码'
    }


def enable_2fa(username, secret, verification_code):
    """验证验证码并启用2FA"""
    # 验证用户输入的验证码
    if not verify_totp_code(secret, verification_code):
        return {
            'status': 'error',
            'message': '验证码错误，请重试'
        }, 400

    # 生成备用验证码
    backup_codes = generate_backup_codes()

    # 保存2FA数据
    data = _load_totp_data()
    data[username] = {
        'secret': secret,
        'enabled': True,
        'backup_codes': backup_codes,
        'created_at': secrets.token_hex(8)  # 简单标记
    }
    _save_totp_data(data)

    log_system(f'2FA enabled for user {username}', 'INFO', 'totp')

    return {
        'status': 'success',
        'message': '双因素认证已启用',
        'backup_codes': backup_codes
    }


def disable_2fa(username, verification_code=None):
    """禁用2FA"""
    data = _load_totp_data()
    user_data = data.get(username)

    if not user_data or not user_data.get('enabled'):
        return {
            'status': 'error',
            'message': '双因素认证未启用'
        }, 400

    # 如果提供了验证码，需要验证
    if verification_code:
        if not verify_totp_code(user_data['secret'], verification_code):
            # 尝试备用验证码
            if not verify_backup_code(username, verification_code):
                return {
                    'status': 'error',
                    'message': '验证码错误'
                }, 401

    # 删除2FA数据
    del data[username]
    _save_totp_data(data)

    log_system(f'2FA disabled for user {username}', 'INFO', 'totp')

    return {
        'status': 'success',
        'message': '双因素认证已禁用'
    }


def get_2fa_status(username):
    """获取用户2FA状态"""
    data = _load_totp_data()
    user_data = data.get(username, {})

    return {
        'status': 'success',
        'enabled': user_data.get('enabled', False),
        'has_backup_codes': len(user_data.get('backup_codes', [])) > 0,
        'backup_codes_remaining': len(user_data.get('backup_codes', []))
    }


def verify_2fa_login(username, code):
    """登录时验证2FA验证码"""
    data = _load_totp_data()
    user_data = data.get(username)

    if not user_data or not user_data.get('enabled'):
        return False

    # 先验证TOTP验证码
    if verify_totp_code(user_data['secret'], code):
        return True

    # 再验证备用验证码
    if verify_backup_code(username, code):
        return True

    return False


def regenerate_backup_codes(username, verification_code):
    """重新生成备用验证码"""
    data = _load_totp_data()
    user_data = data.get(username)

    if not user_data or not user_data.get('enabled'):
        return {
            'status': 'error',
            'message': '双因素认证未启用'
        }, 400

    # 验证当前验证码
    if not verify_totp_code(user_data['secret'], verification_code):
        return {
            'status': 'error',
            'message': '验证码错误'
        }, 401

    # 生成新的备用验证码
    new_codes = generate_backup_codes()
    user_data['backup_codes'] = new_codes
    data[username] = user_data
    _save_totp_data(data)

    log_system(f'Backup codes regenerated for user {username}', 'INFO', 'totp')

    return {
        'status': 'success',
        'message': '备用验证码已重新生成',
        'backup_codes': new_codes
    }
