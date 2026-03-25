# -*- coding: utf-8 -*-
"""
MIoT局域网设备发现模块
"""
import asyncio
import logging
import secrets
import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from .types import InterfaceStatus, MIoTLanDeviceInfo, NetworkInfo

_LOGGER = logging.getLogger(__name__)


@dataclass
class _MIoTLanNetworkUpdateData:
    status: InterfaceStatus
    if_name: str


@dataclass
class _MIoTLanUnregDeviceData:
    key: str


@dataclass
class _MIoTLanRegDeviceData:
    key: str
    handler: Callable[[str, MIoTLanDeviceInfo, Any], Coroutine]
    handler_ctx: Any


class _MIoTLanDevice:
    """局域网设备"""

    _KA_TIMEOUT: float = 100

    def __init__(self, manager: "MIoTLan", did: str, ip: Optional[str] = None) -> None:
        self._manager = manager
        self.did = did
        self.offset = 0
        self._online = False
        self._ip = ip
        self._if_name = None
        self._ka_timer: Optional[asyncio.TimerHandle] = None

    def keep_alive(self, ip: str, if_name: str) -> None:
        """保持在线"""
        changed = False
        if not self._online:
            changed = True
            self._online = True
            _LOGGER.info("Device online: %s, %s", self.did, ip)
        if self._ip != ip:
            changed = True
            self._ip = ip
        if self._if_name != if_name:
            self._if_name = if_name

        if self._ka_timer:
            self._ka_timer.cancel()
        self._ka_timer = self._manager.internal_loop.call_later(
            self._KA_TIMEOUT, self._switch_offline
        )

        if changed:
            self._broadcast_info_changed()

    @property
    def online(self) -> bool:
        return self._online

    @online.setter
    def online(self, online: bool) -> None:
        if self._online != online:
            self._online = online
            self._broadcast_info_changed()

    @property
    def ip(self) -> Optional[str]:
        return self._ip

    @ip.setter
    def ip(self, ip: Optional[str]) -> None:
        if self._ip != ip:
            self._ip = ip
            self._broadcast_info_changed()

    def on_delete(self) -> None:
        if self._ka_timer:
            self._ka_timer.cancel()
            self._ka_timer = None
        self._online = False

    def _switch_offline(self) -> None:
        self.online = False

    def _broadcast_info_changed(self) -> None:
        self._manager.broadcast_device_info_changed(
            did=self.did,
            info=MIoTLanDeviceInfo(did=self.did, online=self._online, ip=self._ip),
        )


class MIoTLan:
    """MIoT局域网设备发现器"""

    OT_HEADER: bytes = b"\x21\x31"
    OT_PORT: int = 54321
    OT_PROBE_LEN: int = 32
    OT_MSG_LEN: int = 1400
    OT_PROBE_INTERVAL_MIN: float = 5
    OT_PROBE_INTERVAL_MAX: float = 45

    def __init__(
        self,
        net_ifs: List[str],
        virtual_did: Optional[int] = None,
    ) -> None:
        self._net_ifs = set(net_ifs)
        self._lan_devices: Dict[str, _MIoTLanDevice] = {}
        self._virtual_did = str(virtual_did) if virtual_did else str(secrets.randbits(64))

        # 初始化探测消息
        probe_bytes = bytearray(self.OT_PROBE_LEN)
        probe_bytes[:20] = b"!1\x00\x20\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xffMDID"
        probe_bytes[20:28] = struct.pack(">Q", int(self._virtual_did))
        probe_bytes[28:32] = b"\x00\x00\x00\x00"
        self._probe_msg = bytes(probe_bytes)
        self._read_buffer = bytearray(self.OT_MSG_LEN)

        self._available_net_ifs: Set[str] = set()
        self._broadcast_socks: Dict[str, socket.socket] = {}
        self._local_port: Optional[int] = None
        self._scan_timer: Optional[asyncio.TimerHandle] = None
        self._last_scan_interval: Optional[float] = None
        self._callbacks_device_status_changed: Dict[str, _MIoTLanRegDeviceData] = {}
        self._init_done = False
        self._internal_loop: asyncio.AbstractEventLoop
        self._thread: threading.Thread

    @property
    def internal_loop(self) -> asyncio.AbstractEventLoop:
        return self._internal_loop

    async def init(self) -> None:
        """初始化"""
        if self._init_done:
            _LOGGER.info("MIoT LAN already initialized")
            return

        # 即使没有网络接口也创建 _internal_loop，以便其他方法可以正常工作
        self._internal_loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._internal_loop_thread)
        self._thread.name = "miot_lan"
        self._thread.daemon = True
        self._thread.start()
        self._init_done = True

        # 如果没有网络接口，只记录日志，不进行探测
        if not self._net_ifs:
            _LOGGER.info("No network interfaces, LAN discovery disabled")
            return

        await asyncio.sleep(self.OT_PROBE_INTERVAL_MIN / 2)

    async def deinit(self) -> None:
        """反初始化"""
        if not self._init_done:
            return

        if hasattr(self, '_internal_loop') and self._internal_loop:
            self._internal_loop.call_soon_threadsafe(self._deinit)
        if hasattr(self, '_thread') and self._thread:
            self._thread.join()
        if hasattr(self, '_internal_loop') and self._internal_loop:
            self._internal_loop.close()

        self._lan_devices.clear()
        self._broadcast_socks.clear()
        self._callbacks_device_status_changed.clear()
        self._init_done = False
        _LOGGER.info("MIoT LAN deinitialized")

    async def get_devices(self) -> Dict[str, MIoTLanDeviceInfo]:
        """获取设备列表"""
        if not self._init_done or not hasattr(self, '_internal_loop'):
            _LOGGER.warning("LAN client not initialized, returning empty device list")
            return {}
        fut = asyncio.run_coroutine_threadsafe(
            self._get_devices_internal(), self._internal_loop
        )
        return await asyncio.wrap_future(fut)

    async def register_status_changed(
        self,
        key: str,
        handler: Callable[[str, MIoTLanDeviceInfo, Any], Coroutine],
        handler_ctx: Any = None,
    ) -> bool:
        """注册状态变化回调"""
        if not self._init_done or not hasattr(self, '_internal_loop'):
            return False
        self._internal_loop.call_soon_threadsafe(
            self._register_status_changed,
            _MIoTLanRegDeviceData(key=key, handler=handler, handler_ctx=handler_ctx),
        )
        return True

    async def unregister_status_changed(self, key: str) -> bool:
        """注销状态变化回调"""
        if not self._init_done or not hasattr(self, '_internal_loop'):
            return False
        self._internal_loop.call_soon_threadsafe(
            self._unregister_status_changed, _MIoTLanUnregDeviceData(key=key)
        )
        return True

    async def ping(self, if_name: Optional[str] = None, target_ip: Optional[str] = None) -> None:
        """发送探测"""
        if not self._init_done or not hasattr(self, '_internal_loop'):
            _LOGGER.warning("LAN client not initialized, skipping ping")
            return
        fut = asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(self._ping_internal, if_name, target_ip),
            self._internal_loop,
        )
        await asyncio.wrap_future(fut)

    def _ping_internal(
        self, if_name: Optional[str] = None, target_ip: Optional[str] = None
    ) -> None:
        """内部探测"""
        self._sendto(
            if_name=if_name,
            data=self._probe_msg,
            address=target_ip or "255.255.255.255",
            port=self.OT_PORT,
        )

    def broadcast_device_info_changed(self, did: str, info: MIoTLanDeviceInfo) -> None:
        """广播设备信息变化"""
        for handler_data in self._callbacks_device_status_changed.values():
            asyncio.run_coroutine_threadsafe(
                handler_data.handler(did, info, handler_data.handler_ctx),
                asyncio.get_event_loop(),
            )

    def _deinit(self) -> None:
        if self._scan_timer:
            self._scan_timer.cancel()
            self._scan_timer = None
        for device in self._lan_devices.values():
            device.on_delete()
        self._lan_devices.clear()
        self._deinit_socket()
        self._internal_loop.stop()

    def _internal_loop_thread(self) -> None:
        _LOGGER.info("MIoT LAN thread started")
        self._init_socket()
        self._scan_timer = self._internal_loop.call_later(
            int(3 * secrets.randbelow(100) / 100), self._scan_devices
        )
        self._internal_loop.run_forever()
        _LOGGER.info("MIoT LAN thread exited")

    def _init_socket(self) -> None:
        self._deinit_socket()
        for if_name in self._net_ifs:
            self._create_socket(if_name)

    def _create_socket(self, if_name: str) -> None:
        if if_name in self._broadcast_socks:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, if_name.encode())
            sock.bind(("", self._local_port or 0))
            self._internal_loop.add_reader(sock.fileno(), self._socket_read_handler, (if_name, sock))
            self._broadcast_socks[if_name] = sock
            self._local_port = self._local_port or sock.getsockname()[1]
            _LOGGER.info("Created socket: %s, port: %s", if_name, self._local_port)
        except Exception as e:
            _LOGGER.error("Failed to create socket %s: %s", if_name, e)

    def _deinit_socket(self) -> None:
        for if_name in list(self._broadcast_socks.keys()):
            self._destroy_socket(if_name)
        self._broadcast_socks.clear()

    def _destroy_socket(self, if_name: str) -> None:
        sock = self._broadcast_socks.pop(if_name, None)
        if sock:
            self._internal_loop.remove_reader(sock.fileno())
            sock.close()
            _LOGGER.info("Destroyed socket: %s", if_name)

    def _socket_read_handler(self, ctx: tuple) -> None:
        try:
            data_len, addr = ctx[1].recvfrom_into(self._read_buffer, self.OT_MSG_LEN, socket.MSG_DONTWAIT)
            if data_len < 0 or addr[1] != self.OT_PORT:
                return
            self._raw_message_handler(self._read_buffer[:data_len], data_len, addr[0], ctx[0])
        except Exception as e:
            _LOGGER.error("Socket read error: %s", e)

    def _raw_message_handler(
        self, data: bytearray, data_len: int, ip: str, if_name: str
    ) -> None:
        if data[:2] != self.OT_HEADER:
            return

        did = str(struct.unpack(">Q", data[4:12])[0])
        timestamp = struct.unpack(">I", data[12:16])[0]

        device = self._lan_devices.get(did)
        if not device:
            device = _MIoTLanDevice(self, did, ip)
            self._lan_devices[did] = device
            _LOGGER.info("New device: %s, %s", did, ip)

        device.offset = int(time.time()) - timestamp

        if data_len == self.OT_PROBE_LEN:
            device.keep_alive(ip=ip, if_name=if_name)

    def _sendto(
        self, if_name: Optional[str], data: bytes, address: str, port: int
    ) -> None:
        if if_name is None:
            for sock in self._broadcast_socks.values():
                try:
                    sock.sendto(data, socket.MSG_DONTWAIT, (address, port))
                except Exception:
                    pass
        else:
            sock = self._broadcast_socks.get(if_name)
            if sock:
                try:
                    sock.sendto(data, socket.MSG_DONTWAIT, (address, port))
                except Exception as e:
                    _LOGGER.error("Send error: %s", e)

    def _scan_devices(self) -> None:
        if self._scan_timer:
            self._scan_timer.cancel()
            self._scan_timer = None
        try:
            self._ping_internal()
        except Exception as e:
            _LOGGER.error("Scan error: %s", e)

        scan_time = self._get_next_scan_time()
        self._scan_timer = self._internal_loop.call_later(scan_time, self._scan_devices)

    def _get_next_scan_time(self) -> float:
        if not self._last_scan_interval:
            self._last_scan_interval = self.OT_PROBE_INTERVAL_MIN
        self._last_scan_interval = min(
            self._last_scan_interval * 2, self.OT_PROBE_INTERVAL_MAX
        )
        return self._last_scan_interval

    def _register_status_changed(self, data: _MIoTLanRegDeviceData) -> None:
        self._callbacks_device_status_changed[data.key] = data

    def _unregister_status_changed(self, data: _MIoTLanUnregDeviceData) -> None:
        self._callbacks_device_status_changed.pop(data.key, None)

    async def _get_devices_internal(self) -> Dict[str, MIoTLanDeviceInfo]:
        return {
            did: MIoTLanDeviceInfo(did=device.did, online=device.online, ip=device.ip)
            for did, device in self._lan_devices.items()
        }
