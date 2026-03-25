# -*- coding: utf-8 -*-
"""
小米IoT SDK - 用于管理小米智能家居设备的Python SDK

主要功能：
- 设备发现和管理
- 设备属性读写
- 动作执行
- 场景控制
- 摄像头视频流
- 局域网设备发现
"""

from .client import MIoTClient
from .types import (
    MIoTUserInfo,
    MIoTOauthInfo,
    MIoTDeviceInfo,
    MIoTCameraInfo,
    MIoTHomeInfo,
    MIoTRoomInfo,
    MIoTManualSceneInfo,
    MIoTSetPropertyParam,
    MIoTGetPropertyParam,
    MIoTActionParam,
    MIoTSpecDevice,
    MIoTSpecService,
    MIoTSpecProperty,
    MIoTSpecAction,
    MIoTSpecDeviceLite,
    DeviceControlResult,
)
from .error import (
    MIoTError,
    MIoTClientError,
    MIoTHttpError,
    MIoTOAuth2Error,
    MIoTSpecError,
    MIoTCameraError,
)

__version__ = "1.0.0"
__all__ = [
    "MIoTClient",
    "MIoTUserInfo",
    "MIoTOauthInfo",
    "MIoTDeviceInfo",
    "MIoTCameraInfo",
    "MIoTHomeInfo",
    "MIoTRoomInfo",
    "MIoTManualSceneInfo",
    "MIoTSetPropertyParam",
    "MIoTGetPropertyParam",
    "MIoTActionParam",
    "MIoTSpecDevice",
    "MIoTSpecService",
    "MIoTSpecProperty",
    "MIoTSpecAction",
    "MIoTSpecDeviceLite",
    "DeviceControlResult",
    "MIoTError",
    "MIoTClientError",
    "MIoTHttpError",
    "MIoTOAuth2Error",
    "MIoTSpecError",
    "MIoTCameraError",
]
