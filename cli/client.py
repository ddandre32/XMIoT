# -*- coding: utf-8 -*-
"""
CLI客户端封装
"""
import asyncio
from typing import Any, Dict, List, Optional

from miot_sdk import MIoTClient
from miot_sdk.types import MIoTDeviceInfo, MIoTManualSceneInfo

from .config import CLIConfig


class CLIClient:
    """CLI客户端封装"""

    _instance: Optional["CLIClient"] = None
    _client: Optional[MIoTClient] = None

    def __new__(cls, config: CLIConfig):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = config
        return cls._instance

    async def _get_client(self) -> MIoTClient:
        """获取或创建MIoT客户端"""
        if self._client is None:
            uuid = self._config.get("uuid")
            if not uuid:
                import uuid as uuid_module
                uuid = uuid_module.uuid4().hex
                self._config.set("uuid", uuid)
                self._config.save()

            oauth_info = self._config.get_oauth_info()

            self._client = MIoTClient(
                uuid=uuid,
                redirect_uri=self._config.get("redirect_uri"),
                cache_path=self._config.get_cache_path(),
                cloud_server=self._config.get("cloud_server"),
                oauth_info=oauth_info,
            )
            await self._client.init()
        return self._client

    async def ensure_authenticated(self) -> bool:
        """确保已认证"""
        if not self._config.is_authenticated:
            return False
        client = await self._get_client()
        return client is not None

    async def get_devices(self, refresh: bool = False) -> Dict[str, MIoTDeviceInfo]:
        """获取设备列表"""
        client = await self._get_client()
        if refresh:
            return await client.refresh_devices()
        return await client.get_devices()

    async def get_device(self, did: str) -> Optional[MIoTDeviceInfo]:
        """获取单个设备"""
        client = await self._get_client()
        return await client.get_device(did)

    async def get_device_spec(self, did: str) -> Optional[Dict[str, Any]]:
        """获取设备SPEC"""
        client = await self._get_client()
        device = await client.get_device(did)
        if not device:
            return None
        return await client.get_device_spec_lite(device.urn)

    async def get_property(self, did: str, siid: int, piid: int) -> Any:
        """获取属性"""
        client = await self._get_client()
        return await client.get_prop(did, siid, piid)

    async def set_property(self, did: str, siid: int, piid: int, value: Any) -> Dict[str, Any]:
        """设置属性"""
        client = await self._get_client()
        result = await client.set_prop(did, siid, piid, value)
        return {
            "did": did,
            "success": result.get("code", -1) == 0,
            "code": result.get("code", -1),
            "message": result.get("message"),
        }

    async def execute_action(
        self, did: str, siid: int, aiid: int, in_list: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """执行动作"""
        client = await self._get_client()
        result = await client.action(did, siid, aiid, in_list or [])
        return {
            "did": did,
            "success": result.get("code", -1) == 0,
            "code": result.get("code", -1),
            "message": result.get("message"),
        }

    async def batch_control(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量控制"""
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
                result = {
                    "did": op.get("did", "unknown"),
                    "success": False,
                    "code": -1,
                    "message": f"Unknown operation type: {op.get('type')}",
                }
            results.append(result)
        return results

    async def get_scenes(self, refresh: bool = False) -> Dict[str, MIoTManualSceneInfo]:
        """获取场景列表"""
        client = await self._get_client()
        if refresh:
            return await client.get_manual_scenes()
        # 获取缓存的场景
        return await client.get_manual_scenes()

    async def execute_scene(self, scene_id: str) -> bool:
        """执行场景"""
        client = await self._get_client()
        return await client.run_manual_scene_by_id(scene_id)

    async def send_notification(self, content: str) -> bool:
        """发送通知"""
        client = await self._get_client()
        return await client.send_app_notify_once(content)

    async def get_oauth_url(self) -> str:
        """获取OAuth URL"""
        client = await self._get_client()
        return client.gen_oauth_url()

    async def set_oauth_code(self, code: str) -> bool:
        """设置OAuth授权码"""
        client = await self._get_client()
        oauth_info = await client.get_access_token(code)
        self._config.set_oauth_info({
            "access_token": oauth_info.access_token,
            "refresh_token": oauth_info.refresh_token,
            "expires_ts": oauth_info.expires_ts,
        })
        return True

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.deinit()
            self._client = None


# 同步包装函数
def run_async(coro):
    """运行异步协程"""
    return asyncio.run(coro)
