# -*- coding: utf-8 -*-
"""
MIoT HTTP客户端 - 与小米云API通信
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from .const import (
    CLOUD_SERVER_DEFAULT,
    MIHOME_HTTP_API_TIMEOUT,
    MIHOME_HTTP_USER_AGENT,
    MIHOME_HTTP_X_CLIENT_BIZID,
    MIHOME_HTTP_X_ENCRYPT_TYPE,
    OAUTH2_API_HOST_DEFAULT,
    OAUTH2_AUTH_URL,
    OAUTH2_CLIENT_ID,
    PROJECT_CODE,
    MIHOME_HTTP_API_PUBKEY,
)
from .error import MIoTErrorCode, MIoTHttpError, MIoTOAuth2Error
from .types import (
    MIoTActionParam,
    MIoTAppNotify,
    MIoTDeviceInfo,
    MIoTGetPropertyParam,
    MIoTHomeInfo,
    MIoTManualSceneInfo,
    MIoTOauthInfo,
    MIoTRoomInfo,
    MIoTSetPropertyParam,
    MIoTUserInfo,
)

_LOGGER = logging.getLogger(__name__)
TOKEN_EXPIRES_TS_RATIO = 0.7


class MIoTOAuth2Client:
    """OAuth2客户端"""

    def __init__(
        self,
        redirect_uri: str,
        cloud_server: str,
        uuid: str,
    ) -> None:
        """初始化"""
        if not redirect_uri:
            raise MIoTOAuth2Error("Invalid redirect_uri")
        if not cloud_server:
            raise MIoTOAuth2Error("Invalid cloud_server")
        if not uuid:
            raise MIoTOAuth2Error("Invalid uuid")

        self._redirect_uri = redirect_uri
        self._oauth_host = (
            OAUTH2_API_HOST_DEFAULT
            if cloud_server == "cn"
            else f"{cloud_server}.{OAUTH2_API_HOST_DEFAULT}"
        )
        self._device_id = f"{PROJECT_CODE}.{uuid}"
        self._state = hashlib.sha1(f"d={self._device_id}".encode("utf-8")).hexdigest()

    @property
    def state(self) -> str:
        """获取当前state"""
        return self._state

    def gen_auth_url(
        self,
        redirect_uri: Optional[str] = None,
        scope: Optional[List[str]] = None,
        skip_confirm: bool = False,
    ) -> str:
        """
        生成OAuth2授权URL

        Args:
            redirect_uri: 回调地址
            scope: 权限范围列表
            skip_confirm: 是否跳过确认

        Returns:
            OAuth2 URL
        """
        params: Dict = {
            "redirect_uri": redirect_uri or self._redirect_uri,
            "client_id": OAUTH2_CLIENT_ID,
            "response_type": "code",
            "device_id": self._device_id,
            "state": self._state,
        }
        if scope:
            params["scope"] = " ".join(scope).strip()
        params["skip_confirm"] = skip_confirm

        encoded_params = urlencode(params)
        return f"{OAUTH2_AUTH_URL}?{encoded_params}"

    async def check_state(self, redirect_state: str) -> bool:
        """检查state是否匹配"""
        return self._state == redirect_state

    async def _get_token(self, data: Dict) -> MIoTOauthInfo:
        """获取Token"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f"https://{self._oauth_host}/app/v2/{PROJECT_CODE}/oauth/get_token",
                params={"data": json.dumps(data)},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=aiohttp.ClientTimeout(total=MIHOME_HTTP_API_TIMEOUT),
            ) as response:
                if response.status == 401:
                    _LOGGER.error("Unauthorized, get_token: %s", data)
                    raise MIoTOAuth2Error("Unauthorized", MIoTErrorCode.CODE_OAUTH_UNAUTHORIZED)
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("HTTP error %d, get_token: %s -> %s", response.status, data, text)
                    raise MIoTOAuth2Error(f"HTTP error {response.status}: {text[:200]}")

                # 使用text()然后手动解析JSON，避免ContentType错误
                res_str = await response.text()
                try:
                    res_obj = json.loads(res_str)
                except json.JSONDecodeError as e:
                    _LOGGER.error("JSON decode error: %s, response: %s", e, res_str[:500])
                    raise MIoTOAuth2Error(f"Invalid JSON response: {res_str[:200]}")

                if (
                    not res_obj
                    or res_obj.get("code") != 0
                    or "result" not in res_obj
                    or not all(k in res_obj["result"] for k in ["access_token", "refresh_token", "expires_in"])
                ):
                    _LOGGER.error("Invalid response: %s", res_str[:500])
                    raise MIoTOAuth2Error(f"Invalid response: {res_str[:200]}")

                return MIoTOauthInfo(
                    access_token=res_obj["result"]["access_token"],
                    refresh_token=res_obj["result"]["refresh_token"],
                    expires_ts=int(time.time() + (res_obj["result"].get("expires_in", 0) * TOKEN_EXPIRES_TS_RATIO))
                )

    async def get_access_token(self, code: str) -> MIoTOauthInfo:
        """通过授权码获取access_token"""
        if not isinstance(code, str):
            raise MIoTOAuth2Error("Invalid code")

        return await self._get_token({
            "client_id": OAUTH2_CLIENT_ID,
            "redirect_uri": self._redirect_uri,
            "code": code,
            "device_id": self._device_id,
        })

    async def refresh_access_token(self, refresh_token: str) -> MIoTOauthInfo:
        """通过refresh_token刷新access_token"""
        if not isinstance(refresh_token, str):
            raise MIoTOAuth2Error("Invalid refresh_token")

        return await self._get_token({
            "client_id": OAUTH2_CLIENT_ID,
            "redirect_uri": self._redirect_uri,
            "refresh_token": refresh_token,
        })


class MIoTHttpClient:
    """MIoT HTTP客户端"""

    _GET_PROP_AGGREGATE_INTERVAL: float = 0.2
    _GET_PROP_MAX_REQ_COUNT = 150

    def __init__(
        self,
        cloud_server: str,
        access_token: str,
    ) -> None:
        """初始化"""
        self._host = OAUTH2_API_HOST_DEFAULT
        self._base_url = ""
        self._access_token = ""
        self._get_prop_timer: Optional[asyncio.TimerHandle] = None
        self._get_prop_list: Dict[str, Dict] = {}
        self._icon_map: Dict[str, str] = {}

        self.update_http_header(cloud_server=cloud_server, access_token=access_token)

        # 初始化加密
        self._random_aes_key = os.urandom(16)
        self._cipher = Cipher(
            algorithms.AES(self._random_aes_key),
            modes.CBC(self._random_aes_key),
            backend=default_backend(),
        )
        self._client_secret_b64 = base64.b64encode(
            load_pem_public_key(
                MIHOME_HTTP_API_PUBKEY.encode("utf-8"), default_backend()
            ).encrypt(plaintext=self._random_aes_key, padding=asym_padding.PKCS1v15())
        ).decode("utf-8")

    def update_http_header(
        self, cloud_server: Optional[str] = None, access_token: Optional[str] = None
    ) -> None:
        """更新HTTP头"""
        if isinstance(cloud_server, str):
            if cloud_server != "cn":
                self._host = f"{cloud_server}.{OAUTH2_API_HOST_DEFAULT}"
            self._base_url = f"https://{self._host}"
        if isinstance(access_token, str):
            self._access_token = access_token

    @property
    def _api_request_headers(self) -> Dict:
        """API请求头"""
        return {
            "Content-Type": "text/plain",
            "User-Agent": MIHOME_HTTP_USER_AGENT,
            "X-Client-BizId": MIHOME_HTTP_X_CLIENT_BIZID,
            "X-Encrypt-Type": MIHOME_HTTP_X_ENCRYPT_TYPE,
            "X-Client-AppId": OAUTH2_CLIENT_ID,
            "X-Client-Secret": self._client_secret_b64,
            "Host": self._host,
            "Authorization": f"Bearer{self._access_token}",
        }

    def aes_encrypt_with_b64(self, data: Dict) -> str:
        """AES加密"""
        encryptor = self._cipher.encryptor()
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(json.dumps(data).encode("utf-8")) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode("utf-8")

    def aes_decrypt_with_b64(self, data: str) -> Dict:
        """AES解密"""
        decryptor = self._cipher.decryptor()
        unpadder = sym_padding.PKCS7(128).unpadder()
        decrypted = decryptor.update(base64.b64decode(data)) + decryptor.finalize()
        unpadded_data = unpadder.update(decrypted) + unpadder.finalize()
        return json.loads(unpadded_data.decode("utf-8"))

    async def _mihome_api_post(
        self, url_path: str, data: Dict, timeout: int = MIHOME_HTTP_API_TIMEOUT
    ) -> Dict:
        """POST请求"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"{self._base_url}{url_path}",
                data=self.aes_encrypt_with_b64(data),
                headers=self._api_request_headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 401:
                    raise MIoTHttpError(
                        "Unauthorized", MIoTErrorCode.CODE_HTTP_INVALID_ACCESS_TOKEN
                    )
                if response.status != 200:
                    raise MIoTHttpError(f"HTTP error {response.status}")

                res_str = await response.text()
                res_obj = self.aes_decrypt_with_b64(res_str)
                if res_obj.get("code") != 0:
                    raise MIoTHttpError(
                        f"API error {res_obj.get('code')}: {res_obj.get('message')}"
                    )
                return res_obj

    async def get_user_info(self) -> MIoTUserInfo:
        """获取用户信息"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url="https://open.account.xiaomi.com/user/profile",
                params={"clientId": OAUTH2_CLIENT_ID, "token": self._access_token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=aiohttp.ClientTimeout(total=MIHOME_HTTP_API_TIMEOUT),
            ) as response:
                res_obj = await response.json()
                if not res_obj or res_obj.get("code") != 0:
                    raise MIoTHttpError("Failed to get user info")

                data = res_obj["data"]
                # 获取UID
                res_api = await self._mihome_api_post(
                    url_path="/app/v2/oauth/get_uid_by_unionid",
                    data={"union_id": data["unionId"]},
                )
                uid = str(res_api["result"]) if "result" in res_api else ""

                return MIoTUserInfo(
                    union_id=data["unionId"],
                    nickname=data.get("miliaoNick", ""),
                    icon=data.get("miliaoIcon", ""),
                    uid=uid,
                )

    async def get_homes(self, fetch_share_home: bool = False) -> Dict[str, MIoTHomeInfo]:
        """获取家庭列表"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/homeroom/gethome",
            data={
                "limit": 150,
                "fetch_share": fetch_share_home,
                "fetch_share_dev": fetch_share_home,
                "plat_form": 0,
                "app_ver": 9,
            },
        )

        if "result" not in res_obj or "homelist" not in res_obj["result"]:
            raise MIoTHttpError("Invalid response")

        home_infos: Dict[str, MIoTHomeInfo] = {}
        for home in [*res_obj["result"]["homelist"], *res_obj["result"].get("share_home_list", [])]:
            if "id" not in home or "name" not in home or "roomlist" not in home:
                continue

            uid = str(home.get("uid", ""))
            home_id = home["id"]
            home_infos[home_id] = MIoTHomeInfo(
                home_id=home_id,
                home_name=home["name"],
                share_home=home.get("shareflag", 0) == 1,
                uid=uid,
                room_list={
                    room["id"]: MIoTRoomInfo(
                        room_id=room["id"],
                        room_name=room["name"],
                        create_ts=room.get("create_time", 0),
                        dids=room.get("dids", []),
                    )
                    for room in home.get("roomlist", [])
                    if "id" in room
                },
                create_ts=home.get("create_time", 0),
                dids=home.get("dids", []),
                group_id=self._calc_group_id(uid, home_id),
                city_id=home.get("city_id"),
                longitude=home.get("longitude"),
                latitude=home.get("latitude"),
                address=home.get("address"),
            )

        return home_infos

    async def get_devices(
        self, home_infos: Optional[List[MIoTHomeInfo]] = None, fetch_share_home: bool = False
    ) -> Dict[str, MIoTDeviceInfo]:
        """获取设备列表"""
        if not home_infos:
            home_infos = list((await self.get_homes(fetch_share_home)).values())

        # 构建设备和家庭/房间的关联关系
        device_home_map: Dict = {}
        for home_info in home_infos:
            for did in home_info.dids or []:
                device_home_map[did] = {
                    "home_id": home_info.home_id,
                    "home_name": home_info.home_name,
                    "room_id": home_info.home_id,
                    "room_name": home_info.home_name,
                    "group_id": home_info.group_id,
                }
            for room_id, room_info in home_info.room_list.items():
                for did in room_info.dids:
                    device_home_map[did] = {
                        "home_id": home_info.home_id,
                        "home_name": home_info.home_name,
                        "room_id": room_id,
                        "room_name": room_info.room_name,
                        "group_id": home_info.group_id,
                    }

        dids = sorted(device_home_map.keys())
        device_infos: Dict[str, MIoTDeviceInfo] = {}

        # 分批获取设备信息
        for i in range(0, len(dids), 200):
            batch_dids = dids[i : i + 200]
            batch_devices = await self._get_device_list_page(batch_dids)
            device_infos.update(batch_devices)

        # 补充家庭信息
        for did, device in device_infos.items():
            if did in device_home_map:
                home_info = device_home_map[did]
                device.home_id = home_info["home_id"]
                device.home_name = home_info["home_name"]
                device.room_id = home_info["room_id"]
                device.room_name = home_info["room_name"]

        return device_infos

    async def _get_device_list_page(self, dids: List[str]) -> Dict[str, MIoTDeviceInfo]:
        """分页获取设备列表"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/home/device_list_page",
            data={"limit": 200, "get_split_device": True, "dids": dids},
        )

        if "result" not in res_obj:
            raise MIoTHttpError("Invalid response")

        result = res_obj["result"]
        device_infos: Dict[str, MIoTDeviceInfo] = {}

        for device in result.get("list", []):
            did = device.get("did")
            name = device.get("name")
            model = device.get("model")
            urn = device.get("spec_type")

            if not all([did, name, model]):
                continue

            device_infos[did] = MIoTDeviceInfo(
                did=did,
                name=name,
                uid=str(device.get("uid", "")),
                urn=urn or "",
                model=model,
                manufacturer=model.split(".")[0] if model else "",
                connect_type=device.get("pid", -1),
                pid=device.get("pid", 0),
                token=device.get("token", ""),
                online=device.get("isOnline", False),
                voice_ctrl=device.get("voice_ctrl", 0),
                order_time=device.get("orderTime", 0),
                rssi=device.get("rssi"),
                local_ip=device.get("local_ip"),
                ssid=device.get("ssid"),
                bssid=device.get("bssid"),
                icon=device.get("icon"),
                parent_id=device.get("parent_id"),
                fw_version=device.get("extra", {}).get("fw_version"),
                mcu_version=device.get("extra", {}).get("mcu_version"),
                platform=device.get("extra", {}).get("platform"),
                is_set_pincode=device.get("extra", {}).get("isSetPincode", 0),
                pincode_type=device.get("extra", {}).get("pincodeType", 0),
            )

            # 处理子设备
            if did and ".s" in did:
                parent_did = did.split(".s")[0]
                if parent_did in device_infos:
                    sub_id = did.split(".")[-1]
                    device_infos[parent_did].sub_devices[sub_id] = device_infos.pop(did)

        return device_infos

    async def get_props(self, params: List[MIoTGetPropertyParam]) -> List[Dict]:
        """批量获取属性"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/miotspec/prop/get",
            data={
                "datasource": 1,
                "params": [param.model_dump() for param in params],
            },
        )
        return res_obj.get("result", [])

    async def get_prop(self, param: MIoTGetPropertyParam) -> Any:
        """获取单个属性"""
        results = await self.get_props([param])
        if results and "value" in results[0]:
            return results[0]["value"]
        return None

    async def set_prop(self, param: MIoTSetPropertyParam) -> Dict:
        """设置属性"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/miotspec/prop/set",
            data={"params": [param.model_dump()]},
            timeout=15,
        )
        result = res_obj.get("result", [])
        if not result:
            raise MIoTHttpError("Invalid response result")
        return result[0]

    async def set_props(self, params: List[MIoTSetPropertyParam]) -> List[Dict]:
        """批量设置属性"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/miotspec/prop/set",
            data={"params": [param.model_dump() for param in params]},
            timeout=15,
        )
        return res_obj.get("result", [])

    async def action(self, param: MIoTActionParam) -> Dict:
        """执行动作"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/miotspec/action",
            data={"params": param.model_dump(by_alias=True)},
            timeout=15,
        )
        return res_obj.get("result", {})

    async def get_manual_scenes(
        self, home_infos: Optional[List[MIoTHomeInfo]] = None, fetch_share_home: bool = False
    ) -> Dict[str, MIoTManualSceneInfo]:
        """获取手动场景列表"""
        if not home_infos:
            home_infos = list((await self.get_homes(fetch_share_home)).values())

        scenes: Dict[str, MIoTManualSceneInfo] = {}
        for home_info in home_infos:
            home_scenes = await self._get_manual_scenes_with_home_id(
                uid=home_info.uid, home_id=home_info.home_id
            )
            scenes.update(home_scenes)

        return scenes

    async def _get_manual_scenes_with_home_id(
        self, uid: str, home_id: str
    ) -> Dict[str, MIoTManualSceneInfo]:
        """获取指定家庭的场景"""
        res_obj = await self._mihome_api_post(
            url_path="/app/appgateway/miot/appsceneservice/AppSceneService/GetManualSceneList",
            data={
                "home_id": home_id,
                "owner_uid": uid,
                "source": "zkp",
                "get_type": 2,
            },
        )

        if "result" not in res_obj:
            raise MIoTHttpError("Invalid response")

        return {
            scene["scene_id"]: MIoTManualSceneInfo(
                scene_id=scene["scene_id"],
                scene_name=scene["scene_name"],
                uid=uid,
                update_ts=scene.get("update_time", 0),
                home_id=home_id,
                room_id=scene.get("room_id"),
                icon=scene.get("icon"),
                enable=scene.get("enable", True),
                dids=scene.get("dids", []),
                pd_ids=scene.get("pd_ids", []),
            )
            for scene in res_obj["result"]
        }

    async def run_manual_scene(self, scene_info: MIoTManualSceneInfo) -> bool:
        """执行手动场景"""
        req_data = {
            "owner_uid": scene_info.uid,
            "scene_id": scene_info.scene_id,
            "scene_type": 2,
        }
        if scene_info.home_id:
            req_data["home_id"] = scene_info.home_id
        if scene_info.room_id:
            req_data["room_id"] = scene_info.room_id

        res_obj = await self._mihome_api_post(
            url_path="/app/appgateway/miot/appsceneservice/AppSceneService/NewRunScene",
            data=req_data,
        )
        return res_obj.get("result", False)

    async def create_app_notify(self, text: str) -> str:
        """创建应用通知"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/oauth/save_text", data={"text": text}
        )
        return res_obj.get("result", "")

    async def send_app_notify(self, notify_id: str) -> bool:
        """发送应用通知"""
        res_obj = await self._mihome_api_post(
            url_path="/app/v2/oauth/send_push", data={"key": notify_id}
        )
        return res_obj.get("result", False)

    @staticmethod
    def _calc_group_id(uid: str, home_id: str) -> str:
        """计算群组ID"""
        return hashlib.sha256(f"{uid}_{home_id}".encode()).hexdigest()[:16]
