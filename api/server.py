# -*- coding: utf-8 -*-
"""
API服务 - FastAPI Web服务
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from miot_sdk import MIoTClient
from core import DeviceManager, SceneManager, NotificationService
from api.routes import devices, scenes, system

_LOGGER = logging.getLogger(__name__)


class XiaomiIoTAPI:
    """小米IoT API服务"""

    def __init__(
        self,
        miot_client: MIoTClient,
        title: str = "小米IoT管理API",
        version: str = "1.0.0",
    ):
        self._client = miot_client
        self._device_manager = DeviceManager(miot_client)
        self._scene_manager = SceneManager(miot_client)
        self._notification_service = NotificationService(miot_client)

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """应用生命周期管理"""
            _LOGGER.info("Starting API server...")
            await self._client.init()
            yield
            _LOGGER.info("Shutting down API server...")
            await self._client.deinit()

        self._app = FastAPI(
            title=title,
            version=version,
            lifespan=lifespan,
        )

        # 添加CORS中间件
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 设置依赖
        self._app.state.device_manager = self._device_manager
        self._app.state.scene_manager = self._scene_manager
        self._app.state.notification_service = self._notification_service
        self._app.state.miot_client = self._client

        # 注册路由
        self._app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
        self._app.include_router(scenes.router, prefix="/api/v1/scenes", tags=["scenes"])
        self._app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

    @property
    def app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self._app

    def run(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
        """运行服务器"""
        import uvicorn
        uvicorn.run(self._app, host=host, port=port, reload=reload)
