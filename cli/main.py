# -*- coding: utf-8 -*-
"""
小米IoT CLI工具主入口 - 符合CLI设计规范

CLI协议设计原则：
1. 双用户兼容: TTY环境（人类）默认table，非TTY（Agent）默认json
2. 统一JSON输出格式: {success, data/error, timestamp}
3. 标准化错误码: 包含code, message, suggestion
4. 全局--json选项: 所有命令支持JSON输出
5. 配置层级: 命令行 > 环境变量 > 配置文件 > 默认

使用示例:
    # 人类交互（TTY环境自动使用table格式）
    miot device list
    miot device get <did>
    miot device prop set <did> <siid> <piid> <value>

    # Agent调用（非TTY环境自动使用json格式）
    miot device list | jq '.data[] | select(.online)'
    miot --json device get <did> | jq '.data.name'

    # 场景管理
    miot scene list
    miot scene run <scene_id>

    # 系统管理
    miot system status
    miot system notify "消息内容"

环境变量:
    MIOT_CONFIG_PATH    配置文件路径
    MIOT_CLOUD_SERVER   云服务器(cn/sg/us)
    MIOT_FORMAT         默认输出格式(json/yaml/table/human)
    MIOT_ACCESS_TOKEN   访问令牌（用于CI/自动化）
"""
import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .commands_device import device_cmd
from .commands_scene import scene_cmd
from .commands_system import system_cmd
from .config import CLIConfig
from .formatter import ErrorCode, OutputFormat, get_default_format, is_tty, print_error


# 帮助信息格式化
class HelpFormatter(click.HelpFormatter):
    """自定义帮助格式化器"""

    def write_heading(self, heading):
        """写入标题"""
        self.write(f"\n{heading}\n")
        self.write("=" * len(heading))
        self.write("\n")


@click.group()
@click.version_option(version=__version__, prog_name="miot")
@click.option(
    "--config",
    "config_path",
    help="配置文件路径 (也可用 MIOT_CONFIG_PATH 环境变量)",
    default=None,
)
@click.option(
    "--format",
    "format_type",
    help="输出格式 (json/yaml/table/human，默认根据环境自动选择)",
    default=None,
    type=click.Choice(["json", "yaml", "table", "human"]),
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="JSON输出模式 (等同于 --format=json，适合自动化脚本)",
)
@click.option("-v", "--verbose", is_flag=True, help="详细输出")
@click.pass_context
def cli(ctx, config_path: Optional[str], format_type: Optional[str], json_mode: bool, verbose: bool):
    """
    小米IoT CLI工具 - 智能家居命令行控制

    \b
    核心能力:
      device    设备管理（发现、控制、查询）
      scene     场景管理（列表、执行）
      system    系统管理（认证、配置、通知）

    \b
    快速开始:
      miot system oauth-url                    # 获取授权URL
      miot system auth <code>                  # 完成认证
      miot device list                         # 列出设备
      miot device prop set <did> 2 1 true      # 开灯
      miot scene run <scene_id>                # 执行场景

    \b
    Agent使用示例:
      miot --json device list | jq '.data[]'                    # 解析设备列表
      miot --json device list | jq -r '.data[0].did'            # 获取首个设备ID
      miot --json device list --online | jq -r '.data[].name'   # 在线设备名称

    \b
    高级用法:
      # Shell轮询替代设备监听（每5分钟检查离线设备）
      */5 * * * * miot --json device list | jq -r '.data[] | select(.online==false) | .name' | xargs -I {} miot system notify "设备离线: {}"

      # at命令延迟通知（30分钟后）
      echo "miot system notify '会议提醒'" | at now + 30 minutes

    \b
    环境变量:
      MIOT_CONFIG_PATH    配置文件路径
      MIOT_CLOUD_SERVER   云服务器(cn/sg/us)
      MIOT_FORMAT         默认输出格式
      MIOT_ACCESS_TOKEN   访问令牌

    \b
    更多信息:
      miot <command> --help  查看具体命令帮助
    """
    # 确保上下文对象存在
    if ctx.obj is None:
        ctx.obj = {}

    # 加载配置
    config = CLIConfig(config_path)

    # 确定输出格式（优先级：--json > --format > 配置 > 自动检测）
    if json_mode:
        final_format = "json"
    elif format_type:
        final_format = format_type
    elif config.get_default_format():
        final_format = config.get_default_format()
    else:
        final_format = get_default_format()

    ctx.obj["config"] = config
    ctx.obj["format"] = final_format
    ctx.obj["verbose"] = verbose
    ctx.obj["is_tty"] = is_tty()


# 注册子命令
cli.add_command(device_cmd)
cli.add_command(scene_cmd)
cli.add_command(system_cmd)


# 便捷命令
@cli.command(name="devices")
@click.option("--refresh", is_flag=True, help="刷新设备列表")
@click.option("--online", is_flag=True, help="仅显示在线设备")
@click.option("--room", help="按房间ID筛选")
@click.option("--type", "device_type", help="按设备类型筛选")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.option("--json", "json_mode", is_flag=True, help="JSON输出")
@click.pass_context
def devices_shortcut(ctx, refresh: bool, online: bool, room: Optional[str],
                     device_type: Optional[str], format_type: Optional[str], json_mode: bool):
    """快捷命令: 列出设备 (等同于 'miot device list')"""
    from .commands_device import device_list
    final_format = _resolve_format(ctx, format_type, json_mode)
    ctx.invoke(device_list, refresh=refresh, online=online, room=room,
               home=None, device_type=device_type, format_type=final_format)


@cli.command(name="scenes")
@click.option("--refresh", is_flag=True, help="刷新场景列表")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.option("--json", "json_mode", is_flag=True, help="JSON输出")
@click.pass_context
def scenes_shortcut(ctx, refresh: bool, format_type: Optional[str], json_mode: bool):
    """快捷命令: 列出场景 (等同于 'miot scene list')"""
    from .commands_scene import scene_list
    final_format = _resolve_format(ctx, format_type, json_mode)
    ctx.invoke(scene_list, refresh=refresh, home=None, format_type=final_format)


@cli.command(name="status")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.option("--json", "json_mode", is_flag=True, help="JSON输出")
@click.pass_context
def status_shortcut(ctx, format_type: Optional[str], json_mode: bool):
    """快捷命令: 系统状态 (等同于 'miot system status')"""
    from .commands_system import system_status
    final_format = _resolve_format(ctx, format_type, json_mode)
    ctx.invoke(system_status, format_type=final_format)


def _resolve_format(ctx, format_type: Optional[str], json_mode: bool) -> str:
    """解析最终输出格式"""
    if json_mode:
        return "json"
    if format_type:
        return format_type
    return ctx.obj.get("format", get_default_format())


def main():
    """CLI入口点"""
    try:
        cli()
    except KeyboardInterrupt:
        print_error(
            error_message="操作被用户中断",
            code=ErrorCode.INTERRUPTED,
            format_type=OutputFormat.JSON
        )
        sys.exit(130)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.UNKNOWN_ERROR,
            format_type=OutputFormat.JSON
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
