# -*- coding: utf-8 -*-
"""
MIoT主客户端 - 整合所有功能的统一入口
"""
import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from .cloud import MIoTOAuth2Client, MIoTHttpClient
from .error import MIoTClientError
from .lan import MIoTLan
from .spec import MIoTSpecParser
from .storage import MIoTStorage
from .types import (
    MIoTActionParam,
    MIoTCameraInfo,
    MIoTDeviceInfo,
    MIoTGetPropertyParam,
    MIoTHomeInfo,
    MIoTManualSceneInfo,
    MIoTOauthInfo,
    MIoTSetPropertyParam,
    MIoTSpecDevice,
    MIoTSpecDeviceLite,
    MIoTUserInfo,
)

_LOGGER = logging.getLogger(__name__)


class MIoTClient:
    """MIoT客户端"""

    def __init__(
        self,
        uuid: str,
        redirect_uri: str,
        cache_path: Optional[str] = None,
        cloud_server: Optional[str] = None,
        oauth_info: Optional[Union[MIoTOauthInfo, Dict]] = None,
    ):
        """
        初始化MIoT客户端

        Args:
            uuid: 设备唯一标识
            redirect_uri: OAuth回调地址
            cache_path: 缓存路径
            cloud_server: 云服务器区域 (cn, ru, etc.)
            oauth_info: OAuth认证信息
        """
        if not uuid:
            raise ValueError("uuid is required")
        if not redirect_uri:
            raise ValueError("redirect_uri is required")

        self._uuid = uuid
        self._redirect_uri = redirect_uri
        self._cache_path = cache_path
        self._cloud_server = cloud_server or "cn"

        self._oauth_info: Optional[MIoTOauthInfo] = None
        if oauth_info:
            self._oauth_info = (
                MIoTOauthInfo(**oauth_info)
                if isinstance(oauth_info, dict)
                else oauth_info
            )

        self._storage: Optional[MIoTStorage] = None
        self._spec_parser: Optional[MIoTSpecParser] = None
        self._oauth_client: Optional[MIoTOAuth2Client] = None
        self._http_client: Optional[MIoTHttpClient] = None
        self._lan_client: Optional[MIoTLan] = None

        self._device_buffer: Optional[Dict[str, MIoTDeviceInfo]] = None
        self._cameras_buffer: Optional[Dict[str, MIoTCameraInfo]] = None
        self._init_done = False

    async def init(self) -> None:
        """初始化客户端"""
        if self._init_done:
            _LOGGER.warning("Client already initialized")
            return

        # 初始化存储
        if self._cache_path:
            self._storage = MIoTStorage(self._cache_path)
            self._spec_parser = MIoTSpecParser(self._storage)

        # 初始化OAuth客户端
        self._oauth_client = MIoTOAuth2Client(
            redirect_uri=self._redirect_uri,
            cloud_server=self._cloud_server,
            uuid=self._uuid,
        )

        # 初始化HTTP客户端
        access_token = self._oauth_info.access_token if self._oauth_info else ""
        self._http_client = MIoTHttpClient(
            cloud_server=self._cloud_server,
            access_token=access_token,
        )

        # 初始化局域网客户端
        self._lan_client = MIoTLan(net_ifs=[])
        await self._lan_client.init()

        self._init_done = True
        _LOGGER.info("MIoT client initialized")

    async def deinit(self) -> None:
        """反初始化客户端"""
        if not self._init_done:
            return

        if self._lan_client:
            await self._lan_client.deinit()

        self._init_done = False
        _LOGGER.info("MIoT client deinitialized")

    # ========== OAuth认证 ==========

    def gen_oauth_url(
        self, redirect_uri: Optional[str] = None, scope: Optional[List[str]] = None
    ) -> str:
        """生成OAuth授权URL"""
        if not self._oauth_client:
            raise MIoTClientError("OAuth client not initialized")
        return self._oauth_client.gen_auth_url(redirect_uri, scope)

    async def check_oauth_state(self, state: str) -> bool:
        """检查OAuth state"""
        if not self._oauth_client:
            raise MIoTClientError("OAuth client not initialized")
        return await self._oauth_client.check_state(state)

    async def get_access_token(self, code: str) -> MIoTOauthInfo:
        """通过授权码获取access_token"""
        if not self._oauth_client:
            raise MIoTClientError("OAuth client not initialized")
        oauth_info = await self._oauth_client.get_access_token(code)
        self._oauth_info = oauth_info
        # 更新HTTP客户端的token
        if self._http_client:
            self._http_client.update_http_header(access_token=oauth_info.access_token)
        return oauth_info

    async def refresh_access_token(self) -> MIoTOauthInfo:
        """刷新access_token"""
        if not self._oauth_client:
            raise MIoTClientError("OAuth client not initialized")
        if not self._oauth_info or not self._oauth_info.refresh_token:
            raise MIoTClientError("No refresh token available")
        oauth_info = await self._oauth_client.refresh_access_token(self._oauth_info.refresh_token)
        self._oauth_info = oauth_info
        # 更新HTTP客户端的token
        if self._http_client:
            self._http_client.update_http_header(access_token=oauth_info.access_token)
        return oauth_info

    def set_oauth_info(self, oauth_info: MIoTOauthInfo) -> None:
        """设置OAuth信息"""
        self._oauth_info = oauth_info
        if self._http_client:
            self._http_client.update_http_header(access_token=oauth_info.access_token)

    # ========== 用户信息 ==========

    async def get_user_info(self) -> MIoTUserInfo:
        """获取用户信息"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.get_user_info()

    # ========== 家庭/房间 ==========

    async def get_homes(self, fetch_share_home: bool = False) -> Dict[str, MIoTHomeInfo]:
        """获取家庭列表"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.get_homes(fetch_share_home)

    # ========== 设备管理 ==========

    async def get_devices(
        self, home_list: Optional[List[MIoTHomeInfo]] = None, fetch_share_home: bool = False
    ) -> Dict[str, MIoTDeviceInfo]:
        """获取设备列表"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")

        devices = await self._http_client.get_devices(home_list, fetch_share_home)

        # 更新局域网状态
        if self._lan_client:
            lan_devices = await self._lan_client.get_devices()
            for did, device in devices.items():
                if did in lan_devices:
                    device.lan_status = lan_devices[did].online
                    device.local_ip = lan_devices[did].ip

        self._device_buffer = devices
        return devices

    async def get_device(self, did: str) -> Optional[MIoTDeviceInfo]:
        """获取单个设备"""
        if self._device_buffer and did in self._device_buffer:
            return self._device_buffer[did]

        devices = await self.get_devices()
        return devices.get(did)

    async def refresh_devices(self) -> Dict[str, MIoTDeviceInfo]:
        """刷新设备列表"""
        self._device_buffer = None
        return await self.get_devices()

    # ========== 设备控制 ==========

    async def get_prop(self, did: str, siid: int, piid: int) -> Any:
        """获取属性值"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.get_prop(
            MIoTGetPropertyParam(did=did, siid=siid, piid=piid)
        )

    async def get_props(self, params: List[MIoTGetPropertyParam]) -> List[Dict]:
        """批量获取属性值"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.get_props(params)

    async def set_prop(self, did: str, siid: int, piid: int, value: Any) -> Dict:
        """设置属性值"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.set_prop(
            MIoTSetPropertyParam(did=did, siid=siid, piid=piid, value=value)
        )

    async def set_props(self, params: List[MIoTSetPropertyParam]) -> List[Dict]:
        """批量设置属性值"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.set_props(params)

    async def action(self, did: str, siid: int, aiid: int, in_list: List[Any] = None) -> Dict:
        """执行动作"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.action(
            MIoTActionParam(did=did, siid=siid, aiid=aiid, in_=in_list or [])
        )

    # ========== 设备SPEC ==========

    async def get_device_spec(self, urn: str) -> Optional[MIoTSpecDevice]:
        """获取设备SPEC"""
        if not self._spec_parser:
            raise MIoTClientError("Spec parser not initialized")
        return await self._spec_parser.parse(urn)

    async def get_device_spec_lite(self, urn: str) -> Optional[Dict[str, MIoTSpecDeviceLite]]:
        """获取设备简化版SPEC"""
        if not self._spec_parser:
            raise MIoTClientError("Spec parser not initialized")
        return await self._spec_parser.parse_lite(urn)

    # ========== 场景管理 ==========

    async def get_manual_scenes(
        self, home_list: Optional[List[MIoTHomeInfo]] = None, fetch_share_home: bool = False
    ) -> Dict[str, MIoTManualSceneInfo]:
        """获取手动场景"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.get_manual_scenes(home_list, fetch_share_home)

    async def run_manual_scene(self, scene_info: MIoTManualSceneInfo) -> bool:
        """执行手动场景"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.run_manual_scene(scene_info)

    async def run_manual_scene_by_id(self, scene_id: str) -> bool:
        """通过ID执行手动场景"""
        scenes = await self.get_manual_scenes()
        if scene_id not in scenes:
            raise MIoTClientError(f"Scene not found: {scene_id}")
        return await self.run_manual_scene(scenes[scene_id])

    # ========== 通知 ==========

    async def create_app_notify(self, text: str) -> str:
        """创建应用通知"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.create_app_notify(text)

    async def send_app_notify(self, notify_id: str) -> bool:
        """发送应用通知"""
        if not self._http_client:
            raise MIoTClientError("HTTP client not initialized")
        return await self._http_client.send_app_notify(notify_id)

    async def send_app_notify_once(self, content: str) -> bool:
        """发送一次性通知"""
        notify_id = await self.create_app_notify(content)
        if not notify_id:
            return False
        result = await self.send_app_notify(notify_id)
        return result

    # ========== 局域网 ==========

    async def register_lan_device_changed(
        self, key: str, handler: Callable[[str, Any, Any], Coroutine], ctx: Any = None
    ) -> bool:
        """注册局域网设备变化回调"""
        if not self._lan_client:
            raise MIoTClientError("LAN client not initialized")
        return await self._lan_client.register_status_changed(key, handler, ctx)

    async def unregister_lan_device_changed(self, key: str) -> bool:
        """注销局域网设备变化回调"""
        if not self._lan_client:
            raise MIoTClientError("LAN client not initialized")
        return await self._lan_client.unregister_status_changed(key)

    async def ping_lan_devices(self) -> None:
        """探测局域网设备"""
        if not self._lan_client:
            raise MIoTClientError("LAN client not initialized")
        await self._lan_client.ping()
