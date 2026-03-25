# -*- coding: utf-8 -*-
"""
核心服务层 - 通知服务
"""
import logging
from typing import Optional

from miot_sdk import MIoTClient

_LOGGER = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""

    def __init__(self, miot_client: MIoTClient):
        self._client = miot_client

    async def send_notification(self, content: str) -> bool:
        """发送应用通知"""
        try:
            result = await self._client.send_app_notify_once(content)
            if result:
                _LOGGER.info("Notification sent: %s", content[:50])
            else:
                _LOGGER.error("Failed to send notification")
            return result
        except Exception as e:
            _LOGGER.error("Error sending notification: %s", e)
            return False

    async def create_notification(self, content: str) -> Optional[str]:
        """创建通知（不发送）"""
        try:
            notify_id = await self._client.create_app_notify(content)
            _LOGGER.info("Notification created: %s", notify_id)
            return notify_id
        except Exception as e:
            _LOGGER.error("Error creating notification: %s", e)
            return None

    async def send_notification_by_id(self, notify_id: str) -> bool:
        """通过ID发送通知"""
        try:
            return await self._client.send_app_notify(notify_id)
        except Exception as e:
            _LOGGER.error("Error sending notification by ID: %s", e)
            return False
