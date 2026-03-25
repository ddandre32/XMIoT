# -*- coding: utf-8 -*-
"""
核心服务层 - 场景管理服务
"""
import logging
from typing import Dict, List, Optional

from miot_sdk import MIoTClient
from miot_sdk.types import MIoTManualSceneInfo

_LOGGER = logging.getLogger(__name__)


class SceneManager:
    """场景管理服务"""

    def __init__(self, miot_client: MIoTClient):
        self._client = miot_client
        self._scenes: Dict[str, MIoTManualSceneInfo] = {}

    async def refresh_scenes(self) -> Dict[str, MIoTManualSceneInfo]:
        """刷新场景列表"""
        self._scenes = await self._client.get_manual_scenes()
        _LOGGER.info("Refreshed %d scenes", len(self._scenes))
        return self._scenes

    def get_scenes(self) -> Dict[str, MIoTManualSceneInfo]:
        """获取缓存的场景列表"""
        return self._scenes

    def get_scene(self, scene_id: str) -> Optional[MIoTManualSceneInfo]:
        """获取单个场景"""
        return self._scenes.get(scene_id)

    def get_scenes_by_home(self, home_id: str) -> List[MIoTManualSceneInfo]:
        """按家庭获取场景"""
        return [s for s in self._scenes.values() if s.home_id == home_id]

    def get_scenes_by_room(self, room_id: str) -> List[MIoTManualSceneInfo]:
        """按房间获取场景"""
        return [s for s in self._scenes.values() if s.room_id == room_id]

    def get_enabled_scenes(self) -> List[MIoTManualSceneInfo]:
        """获取启用的场景"""
        return [s for s in self._scenes.values() if s.enable]

    async def execute_scene(self, scene_id: str) -> bool:
        """执行场景"""
        if scene_id not in self._scenes:
            _LOGGER.error("Scene not found: %s", scene_id)
            return False

        scene = self._scenes[scene_id]
        if not scene.enable:
            _LOGGER.warning("Scene is disabled: %s", scene_id)
            return False

        result = await self._client.run_manual_scene(scene)
        _LOGGER.info("Executed scene %s: %s", scene_id, result)
        return result

    async def execute_scenes(self, scene_ids: List[str]) -> Dict[str, bool]:
        """批量执行场景"""
        results = {}
        for scene_id in scene_ids:
            results[scene_id] = await self.execute_scene(scene_id)
        return results

    def search_scenes(self, keyword: str) -> List[MIoTManualSceneInfo]:
        """搜索场景"""
        keyword = keyword.lower()
        return [
            s for s in self._scenes.values()
            if keyword in s.scene_name.lower() or keyword in s.scene_id.lower()
        ]
