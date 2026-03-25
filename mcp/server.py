# -*- coding: utf-8 -*-
"""
MCP服务 - 为AI智能体提供标准化接口
"""
import json
import logging
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from fastmcp import FastMCP
    from fastmcp.tools import Tool
    from mcp.types import TextContent
    from mcp import ClientSession
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from miot_sdk import MIoTClient
from miot_sdk.types import (
    MIoTActionParam,
    MIoTDeviceInfo,
    MIoTGetPropertyParam,
    MIoTSetPropertyParam,
    MIoTSpecDeviceLite,
)
from core import DeviceManager, SceneManager

_LOGGER = logging.getLogger(__name__)


class DeviceInfo(BaseModel):
    """设备信息模型"""
    did: str = Field(description="设备ID")
    name: str = Field(description="设备名称")
    online: bool = Field(description="在线状态")
    home_info: str = Field(description="家庭/房间信息")
    device_class: str = Field(description="设备类型")


class SceneInfo(BaseModel):
    """场景信息模型"""
    scene_id: str = Field(description="场景ID")
    scene_name: str = Field(description="场景名称")
    enabled: bool = Field(description="是否启用")


class XiaomiIoTMCP:
    """小米IoT MCP服务"""

    def __init__(
        self,
        miot_client: MIoTClient,
        name: str = "Xiaomi IoT MCP Server",
    ):
        if not MCP_AVAILABLE:
            raise ImportError("fastmcp is required for MCP support. Install with: pip install xiaomi-iot-manager[mcp]")

        self._client = miot_client
        self._device_manager = DeviceManager(miot_client)
        self._scene_manager = SceneManager(miot_client)

        self._mcp = FastMCP(
            name=name,
            instructions="支持查询和控制小米智能家居设备",
        )

        self._register_tools()

    def _register_tools(self) -> None:
        """注册MCP工具"""
        # 设备查询工具
        self._mcp.add_tool(self.get_devices)
        self._mcp.add_tool(self.get_device_spec)

        # 设备控制工具
        self._mcp.add_tool(self.get_property)
        self._mcp.add_tool(self.set_property)
        self._mcp.add_tool(self.execute_action)

        # 场景工具
        self._mcp.add_tool(self.get_scenes)
        self._mcp.add_tool(self.execute_scene)

    async def get_devices(
        self,
        area_id: Annotated[Optional[str], Field(description="区域ID（可选）")] = None,
        device_class: Annotated[Optional[str], Field(description="设备类型（可选）")] = None,
    ) -> List[DeviceInfo]:
        """获取设备列表"""
        devices = await self._device_manager.refresh_devices()
        result = []
        for did, device in devices.items():
            if area_id and device.room_id != area_id:
                continue
            if device_class and device_class not in device.model.lower():
                continue
            result.append(DeviceInfo(
                did=did,
                name=device.name,
                online=device.online,
                home_info=f"{device.home_name or ''}-{device.room_name or ''}",
                device_class=device.model.split(".")[1] if "." in device.model else "unknown",
            ))
        return result

    async def get_device_spec(
        self,
        did: Annotated[str, Field(description="设备ID")],
    ) -> Dict[str, MIoTSpecDeviceLite]:
        """获取设备SPEC定义"""
        device = self._device_manager.get_device(did)
        if not device:
            return {}

        spec = await self._client.get_device_spec_lite(device.urn)
        return spec or {}

    async def get_property(
        self,
        did: Annotated[str, Field(description="设备ID")],
        siid: Annotated[int, Field(description="服务实例ID")],
        piid: Annotated[int, Field(description="属性实例ID")],
    ) -> Any:
        """获取设备属性值"""
        return await self._device_manager.get_property(did, siid, piid)

    async def set_property(
        self,
        did: Annotated[str, Field(description="设备ID")],
        siid: Annotated[int, Field(description="服务实例ID")],
        piid: Annotated[int, Field(description="属性实例ID")],
        value: Annotated[Any, Field(description="属性值")],
    ) -> str:
        """设置设备属性值"""
        result = await self._device_manager.set_property(did, siid, piid, value)
        if result.success:
            return f"成功设置设备 {did} 的属性"
        return f"设置失败: {result.message}"

    async def execute_action(
        self,
        did: Annotated[str, Field(description="设备ID")],
        siid: Annotated[int, Field(description="服务实例ID")],
        aiid: Annotated[int, Field(description="动作实例ID")],
        in_list: Annotated[Optional[List[Any]], Field(description="输入参数")] = None,
    ) -> str:
        """执行设备动作"""
        result = await self._device_manager.execute_action(did, siid, aiid, in_list or [])
        if result.success:
            return f"成功执行设备 {did} 的动作"
        return f"执行失败: {result.message}"

    async def get_scenes(self) -> List[SceneInfo]:
        """获取场景列表"""
        scenes = await self._scene_manager.refresh_scenes()
        return [
            SceneInfo(
                scene_id=s.scene_id,
                scene_name=s.scene_name,
                enabled=s.enable or True,
            )
            for s in scenes.values()
        ]

    async def execute_scene(
        self,
        scene_id: Annotated[str, Field(description="场景ID")],
    ) -> str:
        """执行场景"""
        result = await self._scene_manager.execute_scene(scene_id)
        if result:
            return f"成功执行场景 {scene_id}"
        return f"执行场景 {scene_id} 失败"

    async def run_http(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """启动HTTP服务"""
        await self._mcp.run_http_async(
            transport="streamable-http",
            host=host,
            port=port,
            path="/mcp",
        )

    @property
    def mcp_instance(self) -> FastMCP:
        """获取MCP实例"""
        return self._mcp
