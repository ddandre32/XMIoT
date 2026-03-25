# -*- coding: utf-8 -*-
"""
核心服务层 - 设备管理服务
"""
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

from miot_sdk import MIoTClient
from miot_sdk.types import (
    DeviceControlResult,
    MIoTDeviceInfo,
    MIoTGetPropertyParam,
    MIoTSetPropertyParam,
    MIoTActionParam,
)

_LOGGER = logging.getLogger(__name__)


class DeviceManager:
    """设备管理服务"""

    def __init__(self, miot_client: MIoTClient):
        self._client = miot_client
        self._devices: Dict[str, MIoTDeviceInfo] = {}
        self._device_listeners: Dict[str, List[Callable]] = {}

    async def refresh_devices(self) -> Dict[str, MIoTDeviceInfo]:
        """刷新设备列表"""
        self._devices = await self._client.get_devices()
        _LOGGER.info("Refreshed %d devices", len(self._devices))
        return self._devices

    def get_devices(self) -> Dict[str, MIoTDeviceInfo]:
        """获取缓存的设备列表"""
        return self._devices

    def get_device(self, did: str) -> Optional[MIoTDeviceInfo]:
        """获取单个设备"""
        return self._devices.get(did)

    def get_devices_by_room(self, room_id: str) -> List[MIoTDeviceInfo]:
        """按房间获取设备"""
        return [d for d in self._devices.values() if d.room_id == room_id]

    def get_devices_by_home(self, home_id: str) -> List[MIoTDeviceInfo]:
        """按家庭获取设备"""
        return [d for d in self._devices.values() if d.home_id == home_id]

    def get_online_devices(self) -> List[MIoTDeviceInfo]:
        """获取在线设备"""
        return [d for d in self._devices.values() if d.online]

    def get_devices_by_type(self, device_type: str) -> List[MIoTDeviceInfo]:
        """按设备类型获取设备"""
        return [
            d for d in self._devices.values()
            if device_type in d.model.lower()
        ]

    async def get_property(self, did: str, siid: int, piid: int) -> Any:
        """获取设备属性"""
        return await self._client.get_prop(did, siid, piid)

    async def set_property(
        self, did: str, siid: int, piid: int, value: Any
    ) -> DeviceControlResult:
        """设置设备属性"""
        try:
            result = await self._client.set_prop(did, siid, piid, value)
            return DeviceControlResult(
                did=did,
                success=result.get("code", -1) == 0,
                code=result.get("code", -1),
                message=result.get("message"),
            )
        except Exception as e:
            _LOGGER.error("Failed to set property: %s", e)
            return DeviceControlResult(
                did=did, success=False, code=-1, message=str(e)
            )

    async def execute_action(
        self, did: str, siid: int, aiid: int, in_list: List[Any] = None
    ) -> DeviceControlResult:
        """执行设备动作"""
        try:
            result = await self._client.action(did, siid, aiid, in_list)
            return DeviceControlResult(
                did=did,
                success=result.get("code", -1) == 0,
                code=result.get("code", -1),
                message=result.get("message"),
            )
        except Exception as e:
            _LOGGER.error("Failed to execute action: %s", e)
            return DeviceControlResult(
                did=did, success=False, code=-1, message=str(e)
            )

    async def batch_control(
        self, operations: List[Dict[str, Any]]
    ) -> List[DeviceControlResult]:
        """
        批量控制设备

        Args:
            operations: 操作列表，每个操作是字典：
                - type: "set_prop" | "action"
                - did: 设备ID
                - siid: 服务ID
                - piid/aiid: 属性/动作ID
                - value/in_list: 值/参数
        """
        results = []
        for op in operations:
            if op.get("type") == "set_prop":
                result = await self.set_property(
                    op["did"], op["siid"], op["piid"], op.get("value")
                )
            elif op.get("type") == "action":
                result = await self.execute_action(
                    op["did"], op["siid"], op["aiid"], op.get("in_list", [])
                )
            else:
                result = DeviceControlResult(
                    did=op.get("did", "unknown"),
                    success=False,
                    code=-1,
                    message=f"Unknown operation type: {op.get('type')}",
                )
            results.append(result)
        return results

    def register_device_listener(
        self, did: str, callback: Callable[[MIoTDeviceInfo], Coroutine]
    ) -> None:
        """注册设备状态监听器"""
        if did not in self._device_listeners:
            self._device_listeners[did] = []
        self._device_listeners[did].append(callback)

    def unregister_device_listener(self, did: str, callback: Callable) -> None:
        """注销设备状态监听器"""
        if did in self._device_listeners:
            self._device_listeners[did] = [
                cb for cb in self._device_listeners[did] if cb != callback
            ]
