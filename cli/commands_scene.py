# -*- coding: utf-8 -*-
"""
场景管理命令
"""
from typing import Optional

import click

from .client import CLIClient, run_async
from .formatter import ErrorCode, print_error, print_success


@click.group(name="scene")
@click.pass_context
def scene_cmd(ctx):
    """场景管理命令"""
    pass


@scene_cmd.command(name="list")
@click.option("--refresh", is_flag=True, help="刷新场景列表")
@click.option("--home", help="按家庭ID筛选")
@click.option("--room", help="按房间ID筛选")
@click.option("--enabled", is_flag=True, help="仅显示启用的场景")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def scene_list(ctx, refresh: bool, home: Optional[str], room: Optional[str], enabled: bool, format_type: Optional[str]):
    """获取场景列表

    \b
    使用示例:
      miot scene list                    # 列出所有场景
      miot scene list --home <home_id>   # 特定家庭
      miot scene list --room <room_id>   # 特定房间
      miot scene list --enabled          # 仅启用的场景

    \b
    Agent使用:
      miot --json scene list | jq -r '.data[0].scene_id'                    # 获取首个场景ID
      miot --json scene list | jq '.data[] | select(.scene_name | contains("回家"))'  # 搜索场景
    """
    config = ctx.obj["config"]
    client = CLIClient(config)
    fmt = format_type or ctx.obj.get("format", "table")

    if not config.is_authenticated:
        print_error(
            code=ErrorCode.NOT_AUTHENTICATED,
            format_type=fmt
        )
        return

    try:
        scenes = run_async(client.get_scenes(refresh=refresh))

        result = []
        for scene_id, scene in scenes.items():
            if home and scene.home_id != home:
                continue
            if room and scene.room_id != room:
                continue
            if enabled and not scene.enable:
                continue

            result.append({
                "scene_id": scene.scene_id,
                "scene_name": scene.scene_name,
                "home_id": scene.home_id,
                "room_id": scene.room_id,
                "enabled": scene.enable,
            })

        print_success(result, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.SCENE_EXEC_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@scene_cmd.command(name="get")
@click.argument("scene_id")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def scene_get(ctx, scene_id: str, format_type: Optional[str]):
    """获取单个场景信息"""
    config = ctx.obj["config"]
    client = CLIClient(config)
    fmt = format_type or ctx.obj.get("format", "table")

    if not config.is_authenticated:
        print_error(
            code=ErrorCode.NOT_AUTHENTICATED,
            format_type=fmt
        )
        return

    try:
        scenes = run_async(client.get_scenes())
        scene = scenes.get(scene_id)
        if scene:
            print_success(scene.model_dump(), fmt)
        else:
            print_error(
                error_message=f"场景未找到: {scene_id}",
                code=ErrorCode.SCENE_NOT_FOUND,
                format_type=fmt
            )
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.SCENE_EXEC_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@scene_cmd.command(name="search")
@click.argument("keyword")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def scene_search(ctx, keyword: str, format_type: Optional[str]):
    """搜索场景"""
    config = ctx.obj["config"]
    client = CLIClient(config)
    fmt = format_type or ctx.obj.get("format", "table")

    if not config.is_authenticated:
        print_error(
            code=ErrorCode.NOT_AUTHENTICATED,
            format_type=fmt
        )
        return

    try:
        scenes = run_async(client.get_scenes())
        keyword_lower = keyword.lower()

        result = []
        for scene_id, scene in scenes.items():
            if (keyword_lower in scene.scene_name.lower() or
                keyword_lower in scene.scene_id.lower()):
                result.append({
                    "scene_id": scene.scene_id,
                    "scene_name": scene.scene_name,
                    "home_id": scene.home_id,
                    "enabled": scene.enable,
                })

        print_success(result, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.SCENE_EXEC_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@scene_cmd.command(name="run")
@click.argument("scene_id")
@click.option("--batch", help="批量执行场景ID列表，逗号分隔")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def scene_run(ctx, scene_id: str, batch: Optional[str], format_type: Optional[str]):
    """执行场景

    \b
    使用示例:
      miot scene run <scene_id>                           # 执行单个场景
      miot scene run <scene_id> --batch "s1,s2,s3"        # 批量执行

    \b
    Agent使用:
      SCENE=$(miot --json scene list | jq -r '.data[0].scene_id')
      miot scene run $SCENE --json
    """
    config = ctx.obj["config"]
    client = CLIClient(config)
    fmt = format_type or ctx.obj.get("format", "table")

    if not config.is_authenticated:
        print_error(
            code=ErrorCode.NOT_AUTHENTICATED,
            format_type=fmt
        )
        return

    try:
        if batch:
            # 批量执行
            scene_ids = [s.strip() for s in batch.split(",")]
            results = {}
            for sid in scene_ids:
                result = run_async(client.execute_scene(sid))
                results[sid] = result
            print_success(results, fmt)
        else:
            # 单个执行
            result = run_async(client.execute_scene(scene_id))
            print_success({
                "scene_id": scene_id,
                "success": result,
            }, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.SCENE_EXEC_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())
