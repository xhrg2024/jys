"""
用户认证（轻量）：用户名+密码注册/登录，PBKDF2 加盐哈希，内存 token 会话。
作用仅限按用户隔离对话历史；不做角色/权限。
"""
import hashlib
import hmac
import json
import re
import secrets
import threading
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_FILE = DATA_DIR / "users.json"

_PBKDF2_ITERATIONS = 100_000

# 内存 token 会话：token -> 用户名。服务重启即失效（前端收到 401 自动清登录态）。
_TOKENS = {}
_LOCK = threading.Lock()


def _load_users():
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_users(users):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_password(password, salt=None):
    """返回 (salt_bytes, hash_bytes)。salt 为 None 时随机生成。"""
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt, dk


def verify_password(password, salt, expected):
    """校验密码：salt/expected 为 bytes。"""
    _, dk = hash_password(password, salt)
    return hmac.compare_digest(dk, expected)


def _validate_username(username):
    u = str(username or "").strip()
    if not u:
        raise ValueError("用户名不能为空")
    if len(u) > 32:
        raise ValueError("用户名过长（最多 32 字符）")
    if re.search(r'[\\/\x00-\x1f]', u):
        raise ValueError("用户名不能包含 / \\ 或控制字符")
    return u


def _validate_password(password):
    p = str(password or "")
    if len(p) < 4:
        raise ValueError("密码至少 4 位")
    return p


def register_user(username, password):
    """注册新用户；成功返回用户名，已存在/非法抛 ValueError。"""
    u = _validate_username(username)
    p = _validate_password(password)
    with _LOCK:
        users = _load_users()
        if u in users:
            raise ValueError("用户名已存在")
        salt, dk = hash_password(p)
        users[u] = {
            "salt": salt.hex(),
            "hash": dk.hex(),
            "created_at": datetime.now().isoformat(),
        }
        _save_users(users)
    return u


def login_user(username, password):
    """校验用户名密码，成功返回用户名，失败返回 None。"""
    u = str(username or "").strip()
    users = _load_users()
    rec = users.get(u)
    if not rec:
        return None
    try:
        salt = bytes.fromhex(rec.get("salt", ""))
        expected = bytes.fromhex(rec.get("hash", ""))
    except Exception:
        return None
    if not verify_password(str(password or ""), salt, expected):
        return None
    return u


def issue_token(username):
    token = secrets.token_hex(32)
    with _LOCK:
        _TOKENS[token] = username
    return token


def username_for_token(token):
    return _TOKENS.get(token or "")


def revoke_token(token):
    with _LOCK:
        _TOKENS.pop(token or "", None)
