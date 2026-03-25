# -*- coding: utf-8 -*-
"""
MIoT异常定义
"""


class MIoTError(Exception):
    """基础异常"""
    def __init__(self, message: str, code: int = -1):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.code}] {self.message}"


class MIoTClientError(MIoTError):
    """客户端异常"""
    pass


class MIoTHttpError(MIoTError):
    """HTTP请求异常"""
    pass


class MIoTOAuth2Error(MIoTError):
    """OAuth认证异常"""
    pass


class MIoTSpecError(MIoTError):
    """SPEC解析异常"""
    pass


class MIoTCameraError(MIoTError):
    """摄像头异常"""
    pass


class MIoTLanError(MIoTError):
    """局域网异常"""
    pass


class MIoTDeviceOfflineError(MIoTError):
    """设备离线异常"""
    pass


class MIoTInvalidParamError(MIoTError):
    """参数无效异常"""
    pass


class MIoTErrorCode:
    """错误码定义"""
    CODE_SUCCESS = 0
    CODE_UNKNOWN = -1
    CODE_OAUTH_UNAUTHORIZED = 401
    CODE_HTTP_INVALID_ACCESS_TOKEN = 1001
    CODE_MIPS_INVALID_RESULT = 1002
    CODE_DEVICE_OFFLINE = 2001
    CODE_DEVICE_NOT_FOUND = 2002
    CODE_INVALID_PARAM = 3001
    CODE_SPEC_PARSE_FAILED = 4001
