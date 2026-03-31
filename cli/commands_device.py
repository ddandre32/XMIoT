# -*- coding: utf-8 -*-
"""
设备管理命令
"""
import json
import sys
from typing import Optional

import click

from .client import CLIClient, run_async
from .config import CLIConfig
from .formatter import ErrorCode, OutputFormat, print_error, print_success


@click.group(name="device")
@click.pass_context
def device_cmd(ctx):
    """设备管理命令"""
    pass


@device_cmd.command(name="list")
@click.option("--refresh", is_flag=True, help="刷新设备列表")
@click.option("--online", is_flag=True, help="仅显示在线设备")
@click.option("--room", help="按房间ID筛选")
@click.option("--home", help="按家庭ID筛选")
@click.option("--type", "device_type", help="按设备类型筛选")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def device_list(ctx, refresh: bool, online: bool, room: Optional[str],
                home: Optional[str], device_type: Optional[str], format_type: Optional[str]):
    """获取设备列表

    \b
    使用示例:
      miot device list                    # 列出所有设备
      miot device list --online           # 仅在线设备
      miot device list --room <room_id>   # 特定房间
      miot device list --type light       # 特定类型（如灯）

    \b
    Agent使用:
      miot --json device list | jq -r '.data[].did'              # 提取所有设备ID
      miot --json device list --online | jq '.data[] | {did,name,model}'  # 在线设备信息
      miot --json device list | jq '.data[] | select(.name=="客厅灯")'    # 查找指定设备
    """
    config = ctx.obj["config"]
    client = CLIClient(config)

    # 使用传入的格式或上下文中的格式
    fmt = format_type or ctx.obj.get("format", "table")

    if not config.is_authenticated:
        print_error(
            code=ErrorCode.NOT_AUTHENTICATED,
            format_type=fmt
        )
        return

    try:
        devices = run_async(client.get_devices(refresh=refresh))

        # 筛选
        result = []
        for did, device in devices.items():
            if online and not device.online:
                continue
            if room and device.room_id != room:
                continue
            if home and device.home_id != home:
                continue
            if device_type and device_type.lower() not in device.model.lower():
                continue

            result.append({
                "did": device.did,
                "name": device.name,
                "model": device.model,
                "online": device.online,
                "home_name": device.home_name,
                "room_name": device.room_name,
                "local_ip": device.local_ip,
            })

        print_success(result, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.DEVICE_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@device_cmd.command(name="get")
@click.argument("did")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def device_get(ctx, did: str, format_type: Optional[str]):
    """获取单个设备信息"""
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
        device = run_async(client.get_device(did))
        if device:
            print_success(device.model_dump(), fmt)
        else:
            print_error(
                error_message=f"设备未找到: {did}",
                code=ErrorCode.DEVICE_NOT_FOUND,
                format_type=fmt
            )
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.DEVICE_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@device_cmd.command(name="spec")
@click.argument("did")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def device_spec(ctx, did: str, format_type: Optional[str]):
    """获取设备SPEC"""
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
        spec = run_async(client.get_device_spec(did))
        if not spec:
            print_error(
                error_message=f"设备SPEC未找到: {did}",
                code=ErrorCode.SPEC_NOT_FOUND,
                format_type=fmt
            )
            return

        # 转换为可序列化的格式
        spec_dict = {k: v.model_dump() for k, v in spec.items()}
        print_success(spec_dict, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.SPEC_NOT_FOUND,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@device_cmd.group(name="prop")
@click.pass_context
def device_prop(ctx):
    """设备属性操作"""
    pass


@device_prop.command(name="get")
@click.argument("did")
@click.argument("siid", type=int)
@click.argument("piid", type=int)
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def prop_get(ctx, did: str, siid: int, piid: int, format_type: Optional[str]):
    """获取设备属性值"""
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
        value = run_async(client.get_property(did, siid, piid))
        print_success({
            "did": did,
            "siid": siid,
            "piid": piid,
            "value": value,
        }, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.PROP_GET_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@device_prop.command(name="set")
@click.argument("did")
@click.argument("siid", type=int)
@click.argument("piid", type=int)
@click.argument("value")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def prop_set(ctx, did: str, siid: int, piid: int, value: str, format_type: Optional[str]):
    """设置设备属性值

    \b
    参数: DID(设备ID) SIID(服务ID) PIID(属性ID) VALUE(值)

    \b
    使用示例:
      miot device prop set <did> 2 1 true    # 开灯
      miot device prop set <did> 2 1 false   # 关灯
      miot device prop set <did> 2 2 50      # 设置亮度50%

    \b
    Agent使用:
      DID=$(miot --json device list --online | jq -r '.data[0].did')
      miot device prop set $DID 2 1 true --json
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
        # 尝试解析value为合适的类型
        parsed_value = _parse_value(value)
        result = run_async(client.set_property(did, siid, piid, parsed_value))
        print_success(result, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.PROP_SET_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@device_cmd.command(name="action")
@click.argument("did")
@click.argument("siid", type=int)
@click.argument("aiid", type=int)
@click.argument("in_list", nargs=-1)
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def device_action(ctx, did: str, siid: int, aiid: int, in_list: tuple, format_type: Optional[str]):
    """执行设备动作"""
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
        # 解析输入参数
        parsed_in_list = [_parse_value(v) for v in in_list]
        result = run_async(client.execute_action(did, siid, aiid, parsed_in_list))
        print_success(result, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.ACTION_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@device_cmd.command(name="batch")
@click.option("--file", "file_path", help="批量操作JSON文件路径")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def device_batch(ctx, file_path: Optional[str], format_type: Optional[str]):
    """批量控制设备

    \b
    使用示例:
      miot device batch --file ops.json          # 从文件读取
      echo '[{"type":"set_prop","did":"x","siid":2,"piid":1,"value":true}]' | miot device batch

    \b
    JSON格式:
      [{"type":"set_prop|action","did":"...","siid":N,"piid":N,"value":V}]

    \b
    Agent使用:
      # 批量关闭所有灯
      miot --json device list | jq '[.data[] | select(.name | contains("灯")) | {type:"set_prop",did:.did,siid:2,piid:1,value:false}]' | miot device batch --json
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
        # 读取操作列表
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                operations = json.load(f)
        else:
            # 从stdin读取（管道友好）
            operations = json.load(sys.stdin)

        if not isinstance(operations, list):
            print_error(
                error_message="操作列表必须是数组",
                code=ErrorCode.INVALID_FORMAT,
                format_type=fmt
            )
            return

        results = run_async(client.batch_control(operations))
        print_success(results, fmt)
    except json.JSONDecodeError as e:
        print_error(
            error_message=f"JSON解析错误: {e}",
            code=ErrorCode.INVALID_FORMAT,
            format_type=fmt
        )
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.DEVICE_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


def _parse_value(value: str):
    """解析值为合适的数据类型"""
    # 尝试布尔值
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() == "null" or value.lower() == "none":
        return None

    # 尝试整数
    try:
        return int(value)
    except ValueError:
        pass

    # 尝试浮点数
    try:
        return float(value)
    except ValueError:
        pass

    # 尝试JSON解析
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    # 返回字符串
    return value
