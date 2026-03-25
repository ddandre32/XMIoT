# -*- coding: utf-8 -*-
"""
MIoT类型定义 - 所有数据模型和类型定义
"""
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class MIoTUserInfo(BaseModel):
    """小米IoT用户信息"""
    uid: str = Field(description="用户ID")
    nickname: str = Field(description="用户昵称")
    icon: str = Field(description="用户头像URL")
    union_id: str = Field(description="OAuth2 Union ID")


class MIoTOauthInfo(BaseModel):
    """小米IoT OAuth认证信息"""
    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    expires_ts: int = Field(description="令牌过期时间戳")
    user_info: Optional[MIoTUserInfo] = Field(default=None, description="用户信息")


class MIoTRoomInfo(BaseModel):
    """房间信息"""
    room_id: str = Field(description="房间ID")
    room_name: str = Field(description="房间名称")
    create_ts: int = Field(description="创建时间戳")
    dids: List[str] = Field(description="房间内设备ID列表")


class MIoTHomeInfo(BaseModel):
    """家庭信息"""
    home_id: str = Field(description="家庭ID")
    home_name: str = Field(description="家庭名称")
    share_home: bool = Field(description="是否为共享家庭")
    uid: str = Field(description="家庭所有者ID")
    room_list: Dict[str, MIoTRoomInfo] = Field(description="房间列表")
    create_ts: int = Field(description="创建时间戳")
    dids: List[str] = Field(description="设备ID列表")
    group_id: str = Field(description="群组ID")
    city_id: Optional[int] = Field(default=None, description="城市ID")
    longitude: Optional[float] = Field(default=None, description="经度")
    latitude: Optional[float] = Field(default=None, description="纬度")
    address: Optional[str] = Field(default=None, description="地址")


class MIoTDeviceInfo(BaseModel):
    """设备信息"""
    did: str = Field(description="设备ID")
    name: str = Field(description="设备名称")
    uid: str = Field(description="用户ID")
    urn: str = Field(description="设备URN")
    model: str = Field(description="设备型号")
    manufacturer: str = Field(description="制造商")
    connect_type: int = Field(description="连接类型")
    pid: int = Field(description="产品ID")
    token: str = Field(description="设备令牌")
    online: bool = Field(description="在线状态")
    voice_ctrl: int = Field(description="语音控制状态")
    order_time: int = Field(description="绑定时间")
    sub_devices: Dict[str, "MIoTDeviceInfo"] = Field(default={}, description="子设备")
    is_set_pincode: int = Field(default=0, description="是否设置PIN码")
    pincode_type: int = Field(default=0, description="PIN码类型")
    home_id: Optional[str] = Field(default=None, description="家庭ID")
    home_name: Optional[str] = Field(default=None, description="家庭名称")
    room_id: Optional[str] = Field(default=None, description="房间ID")
    room_name: Optional[str] = Field(default=None, description="房间名称")
    rssi: Optional[int] = Field(default=None, description="信号强度")
    lan_status: Optional[bool] = Field(default=None, description="局域网状态")
    local_ip: Optional[str] = Field(default=None, description="本地IP")
    ssid: Optional[str] = Field(default=None, description="WiFi名称")
    bssid: Optional[str] = Field(default=None, description="WiFi BSSID")
    icon: Optional[str] = Field(default=None, description="设备图标")
    parent_id: Optional[str] = Field(default=None, description="父设备ID")
    owner_id: Optional[str] = Field(default=None, description="所有者ID")
    owner_nickname: Optional[str] = Field(default=None, description="所有者昵称")
    fw_version: Optional[str] = Field(default=None, description="固件版本")
    mcu_version: Optional[str] = Field(default=None, description="MCU版本")
    platform: Optional[str] = Field(default=None, description="平台")


class MIoTCameraStatus(int, Enum):
    """摄像头状态"""
    DISCONNECTED = 1
    CONNECTING = auto()
    RE_CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()


class MIoTCameraInfo(MIoTDeviceInfo):
    """摄像头信息，继承自设备信息"""
    channel_count: int = Field(default=1, description="通道数")
    camera_status: MIoTCameraStatus = Field(default=MIoTCameraStatus.DISCONNECTED, description="摄像头状态")


class MIoTLanDeviceInfo(BaseModel):
    """局域网设备信息"""
    did: str = Field(description="设备ID")
    online: bool = Field(description="在线状态")
    ip: Optional[str] = Field(default=None, description="IP地址")


class MIoTManualSceneInfo(BaseModel):
    """手动场景信息"""
    scene_id: str = Field(description="场景ID")
    scene_name: str = Field(description="场景名称")
    uid: str = Field(description="用户ID")
    update_ts: int = Field(description="更新时间")
    home_id: str = Field(description="家庭ID")
    room_id: Optional[str] = Field(default=None, description="房间ID")
    icon: Optional[str] = Field(default=None, description="图标")
    enable: Optional[bool] = Field(default=None, description="启用状态")
    dids: Optional[List[str]] = Field(default=None, description="关联设备ID")
    pd_ids: Optional[List[int]] = Field(default=None, description="PD ID列表")


class MIoTAppNotify(BaseModel):
    """应用通知"""
    id_: str = Field(description="通知ID")
    text: str = Field(description="通知内容")
    create_ts: int = Field(description="创建时间")


class MIoTSetPropertyParam(BaseModel):
    """设置属性参数"""
    did: str = Field(description="设备ID")
    siid: int = Field(description="服务实例ID")
    piid: int = Field(description="属性实例ID")
    value: Any = Field(description="属性值")


class MIoTGetPropertyParam(BaseModel):
    """获取属性参数"""
    did: str = Field(description="设备ID")
    siid: int = Field(description="服务实例ID")
    piid: int = Field(description="属性实例ID")


class MIoTActionParam(BaseModel):
    """执行动作参数"""
    did: str = Field(description="设备ID")
    siid: int = Field(description="服务实例ID")
    aiid: int = Field(description="动作实例ID")
    in_: List[Any] = Field(serialization_alias="in", description="输入参数")


class MIoTSpecValueRange(BaseModel):
    """属性值范围"""
    min_: float = Field(alias="min", serialization_alias="min")
    max_: float = Field(alias="max", serialization_alias="max")
    step: float = Field(description="步长")


class MIoTSpecValueListItem(BaseModel):
    """属性值列表项"""
    name: str = Field(description="名称")
    value: Any = Field(description="值")
    description: str = Field(description="描述")


class MIoTSpecProperty(BaseModel):
    """SPEC属性定义"""
    iid: int = Field(description="实例ID")
    name: str = Field(description="名称")
    type_: Optional[str] = Field(alias="type", serialization_alias="type", default=None, description="类型URN")
    description: str = Field(description="描述")
    description_trans: str = Field(default="", description="翻译后的描述")
    format: str = Field(description="数据格式")
    access: List[str] = Field(description="访问权限")
    unit: Optional[str] = Field(default=None, description="单位")
    value_range: Optional[MIoTSpecValueRange] = Field(default=None, description="值范围")
    value_list: Optional[List[MIoTSpecValueListItem]] = Field(default=None, description="值列表")

    @property
    def readable(self) -> bool:
        """是否可读"""
        return "read" in self.access

    @property
    def writable(self) -> bool:
        """是否可写"""
        return "write" in self.access

    @property
    def notify(self) -> bool:
        """是否支持通知"""
        return "notify" in self.access


class MIoTSpecAction(BaseModel):
    """SPEC动作定义"""
    iid: int = Field(description="实例ID")
    name: str = Field(description="名称")
    type_: Optional[str] = Field(alias="type", serialization_alias="type", default=None, description="类型URN")
    description: str = Field(description="描述")
    description_trans: str = Field(default="", description="翻译后的描述")
    in_: List[MIoTSpecProperty] = Field(default=[], description="输入参数")
    out: List[MIoTSpecProperty] = Field(default=[], description="输出参数")


class MIoTSpecEvent(BaseModel):
    """SPEC事件定义"""
    iid: int = Field(description="实例ID")
    name: str = Field(description="名称")
    type_: Optional[str] = Field(alias="type", serialization_alias="type", default=None, description="类型URN")
    description: str = Field(description="描述")
    description_trans: str = Field(default="", description="翻译后的描述")
    arguments: List[MIoTSpecProperty] = Field(default=[], description="事件参数")


class MIoTSpecService(BaseModel):
    """SPEC服务定义"""
    iid: int = Field(description="实例ID")
    name: str = Field(description="名称")
    type_: Optional[str] = Field(alias="type", serialization_alias="type", default=None, description="类型URN")
    description: str = Field(description="描述")
    description_trans: str = Field(default="", description="翻译后的描述")
    properties: List[MIoTSpecProperty] = Field(default=[], description="属性列表")
    actions: List[MIoTSpecAction] = Field(default=[], description="动作列表")
    events: List[MIoTSpecEvent] = Field(default=[], description="事件列表")


class MIoTSpecDevice(BaseModel):
    """SPEC设备定义"""
    urn: str = Field(description="URN")
    name: str = Field(description="名称")
    description: str = Field(description="描述")
    description_trans: str = Field(default="", description="翻译后的描述")
    services: List[MIoTSpecService] = Field(default=[], description="服务列表")


class MIoTSpecDeviceLite(BaseModel):
    """简化版设备SPEC（用于LLM）"""
    iid: str = Field(description="实例ID")
    description: str = Field(description="描述")
    format: str = Field(description="数据格式")
    writeable: bool = Field(description="是否可写")
    readable: bool = Field(description="是否可读")
    unit: Optional[str] = Field(default=None, description="单位")
    value_range: Optional[MIoTSpecValueRange] = Field(default=None, description="值范围")
    value_list: Optional[List[MIoTSpecValueListItem]] = Field(default=None, description="值列表")


class DeviceControlResult(BaseModel):
    """设备控制结果"""
    did: str = Field(description="设备ID")
    success: bool = Field(description="是否成功")
    code: int = Field(description="返回码")
    message: Optional[str] = Field(default=None, description="消息")


class DevicePropertyValue(BaseModel):
    """设备属性值"""
    did: str = Field(description="设备ID")
    siid: int = Field(description="服务实例ID")
    piid: int = Field(description="属性实例ID")
    value: Any = Field(description="属性值")


class InterfaceStatus(int, Enum):
    """接口状态"""
    ADD = 0
    UPDATE = auto()
    REMOVE = auto()


class NetworkInfo(BaseModel):
    """网络信息"""
    name: str = Field(description="接口名称")
    ip: str = Field(description="IP地址")
    netmask: str = Field(description="子网掩码")
    net_seg: str = Field(description="网段")
