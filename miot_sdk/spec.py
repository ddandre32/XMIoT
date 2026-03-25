# -*- coding: utf-8 -*-
"""
MIoT SPEC解析模块 - 解析设备SPEC定义
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp

from .error import MIoTSpecError
from .storage import MIoTStorage
from .types import (
    MIoTSpecAction,
    MIoTSpecDevice,
    MIoTSpecDeviceLite,
    MIoTSpecEvent,
    MIoTSpecProperty,
    MIoTSpecService,
    MIoTSpecValueListItem,
    MIoTSpecValueRange,
)

_LOGGER = logging.getLogger(__name__)
SPEC_STD_LIB_EFFECTIVE_TIME = 14 * 24 * 60 * 60  # 14天


async def http_get_json_async(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """异步HTTP GET请求JSON"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        _LOGGER.error("HTTP GET error: %s", e)
        return None


class MIoTSpecParser:
    """MIoT SPEC解析器"""

    VERSION: int = 1
    _DOMAIN: str = "miot_specs"

    def __init__(self, storage: Optional[MIoTStorage] = None) -> None:
        self._storage = storage
        self._spec_cache: Dict[str, MIoTSpecDevice] = {}
        self._spec_lite_cache: Dict[str, Dict[str, MIoTSpecDeviceLite]] = {}

    async def parse(self, urn: str, skip_cache: bool = False) -> Optional[MIoTSpecDevice]:
        """
        解析设备SPEC

        Args:
            urn: 设备URN
            skip_cache: 是否跳过缓存

        Returns:
            设备SPEC定义
        """
        if not skip_cache and urn in self._spec_cache:
            return self._spec_cache[urn]

        if self._storage and not skip_cache:
            cache_data = await self._storage.load_async(self._DOMAIN, urn.replace(":", "_"))
            if cache_data:
                try:
                    spec = MIoTSpecDevice(**cache_data)
                    self._spec_cache[urn] = spec
                    return spec
                except Exception:
                    pass

        # 从云端获取
        for attempt in range(3):
            try:
                spec = await self._fetch_and_parse(urn)
                if spec:
                    self._spec_cache[urn] = spec
                    if self._storage:
                        await self._storage.save_async(
                            self._DOMAIN, urn.replace(":", "_"), spec.model_dump()
                        )
                    return spec
            except Exception as e:
                _LOGGER.error("Parse error (attempt %d): %s", attempt + 1, e)

        return None

    async def parse_lite(self, urn: str, skip_cache: bool = False) -> Optional[Dict[str, MIoTSpecDeviceLite]]:
        """
        解析简化版SPEC（用于LLM）

        Args:
            urn: 设备URN
            skip_cache: 是否跳过缓存

        Returns:
            简化版SPEC字典
        """
        if not skip_cache and urn in self._spec_lite_cache:
            return self._spec_lite_cache[urn]

        spec = await self.parse(urn, skip_cache)
        if not spec:
            return None

        result: Dict[str, MIoTSpecDeviceLite] = {}
        for service in spec.services:
            for prop in service.properties:
                iid = f"prop.0.{service.iid}.{prop.iid}"
                name = service.description_trans
                if service.description_trans != prop.description_trans:
                    name += f" {prop.description_trans}"

                result[iid] = MIoTSpecDeviceLite(
                    iid=iid,
                    description=name,
                    format=prop.format,
                    writeable=prop.writable,
                    readable=prop.readable,
                    unit=prop.unit,
                    value_range=prop.value_range,
                    value_list=prop.value_list,
                )

            for action in service.actions:
                iid = f"action.0.{service.iid}.{action.iid}"
                name = service.description_trans
                if service.description_trans != action.description_trans:
                    name += f" {action.description_trans}"

                in_list = [f"{p.description_trans}: {p.format}" for p in action.in_]
                result[iid] = MIoTSpecDeviceLite(
                    iid=iid,
                    description=name,
                    format=json.dumps(in_list, ensure_ascii=False),
                    writeable=True,
                    readable=False,
                )

        self._spec_lite_cache[urn] = result
        return result

    async def _fetch_and_parse(self, urn: str) -> Optional[MIoTSpecDevice]:
        """获取并解析SPEC"""
        instance = await http_get_json_async(
            url="https://miot-spec.org/miot-spec-v2/instance",
            params={"type": urn},
        )

        if not instance or not all(k in instance for k in ["type", "description", "services"]):
            raise MIoTSpecError(f"Invalid instance for URN: {urn}")

        urn_parts = urn.split(":")
        device_name = urn_parts[3] if len(urn_parts) > 3 else "unknown"

        spec_device = MIoTSpecDevice(
            urn=urn,
            name=device_name,
            description=instance["description"],
            description_trans=instance["description"],
            services=[],
        )

        for service_data in instance.get("services", []):
            if not all(k in service_data for k in ["iid", "type", "description"]):
                continue

            service_type_parts = service_data["type"].split(":")
            service_name = service_type_parts[3] if len(service_type_parts) > 3 else "unknown"

            if service_name == "device-information":
                continue

            spec_service = MIoTSpecService(
                iid=service_data["iid"],
                name=service_name,
                type_=service_data["type"],
                description=service_data["description"],
                description_trans=service_data["description"],
                properties=[],
                actions=[],
                events=[],
            )

            # 解析属性
            for prop_data in service_data.get("properties", []):
                if not all(k in prop_data for k in ["iid", "type", "description", "format", "access"]):
                    continue

                prop_type_parts = prop_data["type"].split(":")
                prop_name = prop_type_parts[3] if len(prop_type_parts) > 3 else "unknown"

                spec_prop = MIoTSpecProperty(
                    iid=prop_data["iid"],
                    name=prop_name,
                    type_=prop_data["type"],
                    description=prop_data["description"],
                    description_trans=prop_data["description"],
                    format=prop_data["format"],
                    access=prop_data["access"],
                    unit=prop_data.get("unit"),
                )

                if "value-range" in prop_data:
                    spec_prop.value_range = MIoTSpecValueRange(
                        min=prop_data["value-range"][0],
                        max=prop_data["value-range"][1],
                        step=prop_data["value-range"][2],
                    )
                elif "value-list" in prop_data:
                    spec_prop.value_list = [
                        MIoTSpecValueListItem(
                            name=v.get("description", f"v_{v['value']}"),
                            value=v["value"],
                            description=v.get("description", ""),
                        )
                        for v in prop_data["value-list"]
                    ]

                spec_service.properties.append(spec_prop)

            # 解析动作
            for action_data in service_data.get("actions", []):
                if not all(k in action_data for k in ["iid", "type", "description", "in"]):
                    continue

                action_type_parts = action_data["type"].split(":")
                action_name = action_type_parts[3] if len(action_type_parts) > 3 else "unknown"

                spec_action = MIoTSpecAction(
                    iid=action_data["iid"],
                    name=action_name,
                    type_=action_data["type"],
                    description=action_data["description"],
                    description_trans=action_data["description"],
                )

                # 查找输入参数对应的属性
                for piid in action_data.get("in", []):
                    for prop in spec_service.properties:
                        if prop.iid == piid:
                            spec_action.in_.append(prop)
                            break

                for piid in action_data.get("out", []):
                    for prop in spec_service.properties:
                        if prop.iid == piid:
                            spec_action.out.append(prop)
                            break

                spec_service.actions.append(spec_action)

            # 解析事件
            for event_data in service_data.get("events", []):
                if not all(k in event_data for k in ["iid", "type", "description", "arguments"]):
                    continue

                event_type_parts = event_data["type"].split(":")
                event_name = event_type_parts[3] if len(event_type_parts) > 3 else "unknown"

                spec_event = MIoTSpecEvent(
                    iid=event_data["iid"],
                    name=event_name,
                    type_=event_data["type"],
                    description=event_data["description"],
                    description_trans=event_data["description"],
                )

                for piid in event_data.get("arguments", []):
                    for prop in spec_service.properties:
                        if prop.iid == piid:
                            spec_event.arguments.append(prop)
                            break

                spec_service.events.append(spec_event)

            spec_device.services.append(spec_service)

        return spec_device
