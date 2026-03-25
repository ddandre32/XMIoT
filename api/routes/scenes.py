# -*- coding: utf-8 -*-
"""
场景管理API路由
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core import SceneManager

router = APIRouter()


class ExecuteScenesRequest(BaseModel):
    scene_ids: List[str]


def get_scene_manager(request: Request) -> SceneManager:
    return request.app.state.scene_manager


@router.get("/")
async def list_scenes(manager: SceneManager = Depends(get_scene_manager)):
    """获取所有场景列表"""
    scenes = manager.get_scenes()
    return {"scenes": [s.model_dump() for s in scenes.values()]}


@router.get("/refresh")
async def refresh_scenes(manager: SceneManager = Depends(get_scene_manager)):
    """刷新场景列表"""
    scenes = await manager.refresh_scenes()
    return {"scenes": [s.model_dump() for s in scenes.values()]}


@router.get("/{scene_id}")
async def get_scene(scene_id: str, manager: SceneManager = Depends(get_scene_manager)):
    """获取单个场景信息"""
    scene = manager.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene.model_dump()


@router.post("/{scene_id}/execute")
async def execute_scene(
    scene_id: str, manager: SceneManager = Depends(get_scene_manager)
):
    """执行场景"""
    result = await manager.execute_scene(scene_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to execute scene")
    return {"success": True, "scene_id": scene_id}


@router.post("/batch-execute")
async def batch_execute_scenes(
    request: ExecuteScenesRequest,
    manager: SceneManager = Depends(get_scene_manager),
):
    """批量执行场景"""
    results = await manager.execute_scenes(request.scene_ids)
    return {"results": results}


@router.get("/by-home/{home_id}")
async def get_scenes_by_home(
    home_id: str, manager: SceneManager = Depends(get_scene_manager)
):
    """按家庭获取场景"""
    scenes = manager.get_scenes_by_home(home_id)
    return {"scenes": [s.model_dump() for s in scenes]}


@router.get("/search/{keyword}")
async def search_scenes(
    keyword: str, manager: SceneManager = Depends(get_scene_manager)
):
    """搜索场景"""
    scenes = manager.search_scenes(keyword)
    return {"scenes": [s.model_dump() for s in scenes]}
