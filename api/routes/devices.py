# -*- coding: utf-8 -*-
"""
设备管理API路由
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core import DeviceManager

router = APIRouter()


class SetPropertyRequest(BaseModel):
    did: str
    siid: int
    piid: int
    value: Any


class ExecuteActionRequest(BaseModel):
    did: str
    siid: int
    aiid: int
    in_list: Optional[List[Any]] = []


class BatchControlRequest(BaseModel):
    operations: List[Dict[str, Any]]


def get_device_manager(request: Request) -> DeviceManager:
    return request.app.state.device_manager


@router.get("/")
async def list_devices(manager: DeviceManager = Depends(get_device_manager)):
    """获取所有设备列表"""
    devices = manager.get_devices()
    return {"devices": [d.model_dump() for d in devices.values()]}


@router.get("/refresh")
async def refresh_devices(manager: DeviceManager = Depends(get_device_manager)):
    """刷新设备列表"""
    devices = await manager.refresh_devices()
    return {"devices": [d.model_dump() for d in devices.values()]}


@router.get("/{did}")
async def get_device(did: str, manager: DeviceManager = Depends(get_device_manager)):
    """获取单个设备信息"""
    device = manager.get_device(did)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device.model_dump()


@router.get("/{did}/spec")
async def get_device_spec(
    did: str, request: Request, manager: DeviceManager = Depends(get_device_manager)
):
    """获取设备SPEC"""
    device = manager.get_device(did)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    spec = await request.app.state.miot_client.get_device_spec_lite(device.urn)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    return {"spec": {k: v.model_dump() for k, v in spec.items()}}


@router.get("/{did}/properties/{siid}/{piid}")
async def get_property(
    did: str, siid: int, piid: int, manager: DeviceManager = Depends(get_device_manager)
):
    """获取设备属性值"""
    try:
        value = await manager.get_property(did, siid, piid)
        return {"did": did, "siid": siid, "piid": piid, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/properties/set")
async def set_property(
    request: SetPropertyRequest, manager: DeviceManager = Depends(get_device_manager)
):
    """设置设备属性值"""
    result = await manager.set_property(
        request.did, request.siid, request.piid, request.value
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result.model_dump()


@router.post("/actions/execute")
async def execute_action(
    request: ExecuteActionRequest, manager: DeviceManager = Depends(get_device_manager)
):
    """执行设备动作"""
    result = await manager.execute_action(
        request.did, request.siid, request.aiid, request.in_list or []
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result.model_dump()


@router.post("/batch-control")
async def batch_control(
    request: BatchControlRequest, manager: DeviceManager = Depends(get_device_manager)
):
    """批量控制设备"""
    results = await manager.batch_control(request.operations)
    return {"results": [r.model_dump() for r in results]}


@router.get("/by-room/{room_id}")
async def get_devices_by_room(
    room_id: str, manager: DeviceManager = Depends(get_device_manager)
):
    """按房间获取设备"""
    devices = manager.get_devices_by_room(room_id)
    return {"devices": [d.model_dump() for d in devices]}


@router.get("/by-home/{home_id}")
async def get_devices_by_home(
    home_id: str, manager: DeviceManager = Depends(get_device_manager)
):
    """按家庭获取设备"""
    devices = manager.get_devices_by_home(home_id)
    return {"devices": [d.model_dump() for d in devices]}


@router.get("/online/list")
async def get_online_devices(manager: DeviceManager = Depends(get_device_manager)):
    """获取在线设备"""
    devices = manager.get_online_devices()
    return {"devices": [d.model_dump() for d in devices]}
