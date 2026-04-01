# -*- coding: utf-8 -*-
"""
MIoT常量定义 - 使用小米官方OAuth配置
"""

# 项目代码 (小米官方)
PROJECT_CODE: str = "mico"

# OAuth2配置 (小米官方应用)
OAUTH2_CLIENT_ID: str = "2882303761520431603"
OAUTH2_AUTH_URL: str = "https://account.xiaomi.com/oauth2/authorize"
OAUTH2_API_HOST_DEFAULT: str = f"{PROJECT_CODE}.api.mijia.tech"

# 允许的回调地址列表
OAUTH2_REDIRECT_URI_DEFAULT = "http://127.0.0.1:8000/callback"
OAUTH2_REDIRECT_URI_LIST = [
    "http://127.0.0.1:8000/callback",                         # localhost
    f"https://{PROJECT_CODE}.api.mijia.tech/login_redirect",  # 小米官方
]

# HTTP API配置
MIHOME_HTTP_API_TIMEOUT: int = 30
MIHOME_HTTP_USER_AGENT: str = f"{PROJECT_CODE}/docker"
MIHOME_HTTP_X_CLIENT_BIZID: str = f"{PROJECT_CODE}api"
MIHOME_HTTP_X_ENCRYPT_TYPE: str = "1"

# MIoT SPEC公钥 (用于API加密)
MIHOME_HTTP_API_PUBKEY: str = "\
-----BEGIN PUBLIC KEY-----\
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzH220YGgZOlXJ4eSleFb\
Beylq4qHsVNzhPTUTy/caDb4a3GzqH6SX4GiYRilZZZrjjU2ckkr8GM66muaIuJw\
r8ZB9SSY3Hqwo32tPowpyxobTN1brmqGK146X6JcFWK/QiUYVXZlcHZuMgXLlWyn\
zTMVl2fq7wPbzZwOYFxnSRh8YEnXz6edHAqJqLEqZMP00bNFBGP+yc9xmc7ySSyw\
OgW/muVzfD09P2iWhl3x8N+fBBWpuI5HjvyQuiX8CZg3xpEeCV8weaprxMxR0epM\
3l7T6rJuPXR1D7yhHaEQj2+dyrZTeJO8D8SnOgzV5j4bp1dTunlzBXGYVjqDsRhZ\
qQIDAQAB\
-----END PUBLIC KEY-----"

# 云服务器配置
CLOUD_SERVER_DEFAULT: str = "cn"
CLOUD_SERVERS: dict = {
    "cn": "中国大陆",
    "de": "Europe",
    "i2": "India",
    "ru": "Russia",
    "sg": "Singapore",
    "us": "United States"
}

# 语言配置
SYSTEM_LANGUAGE_DEFAULT: str = "zh-Hans"
SYSTEM_LANGUAGES = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "ja": "日本語",
    "ru": "Русский",
    "zh-Hans": "简体中文",
    "zh-Hant": "繁體中文"
}

# SPEC缓存有效期 (30天)
SPEC_STD_LIB_EFFECTIVE_TIME = 3600 * 24 * 30

# 摄像头配置
CAMERA_RECONNECT_TIME_MIN: int = 3
CAMERA_RECONNECT_TIME_MAX: int = 1200
CAMERA_FRAME_INTERVAL_DEFAULT = 500  # ms

# 局域网配置
LAN_PROBE_INTERVAL_MIN: float = 5
LAN_PROBE_INTERVAL_MAX: float = 45
LAN_OT_PORT: int = 54321

# 缓存配置
DEFAULT_CACHE_TTL = 3600  # 1小时
MAX_CACHE_SIZE = 1000
