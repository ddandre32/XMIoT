# -*- coding: utf-8 -*-
"""
系统管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core import NotificationService

router = APIRouter()


class SendNotificationRequest(BaseModel):
    content: str


def get_notification_service(request: Request) -> NotificationService:
    return request.app.state.notification_service


@router.get("/status")
async def get_system_status(request: Request):
    """获取系统状态"""
    client = request.app.state.miot_client
    return {
        "status": "running",
        "initialized": True,
    }


@router.get("/oauth/url")
async def get_oauth_url(request: Request):
    """获取OAuth授权URL"""
    client = request.app.state.miot_client
    url = client.gen_oauth_url()
    return {"oauth_url": url}


@router.post("/notification/send")
async def send_notification(
    request: SendNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
):
    """发送通知"""
    result = await service.send_notification(request.content)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"success": True}
