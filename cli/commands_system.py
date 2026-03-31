# -*- coding: utf-8 -*-
"""
系统管理命令
"""
from typing import Optional

import click

from .client import CLIClient, run_async
from .config import CLIConfig
from .formatter import ErrorCode, print_error, print_success


@click.group(name="system")
@click.pass_context
def system_cmd(ctx):
    """系统管理命令"""
    pass


@system_cmd.command(name="status")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def system_status(ctx, format_type: Optional[str]):
    """获取系统状态"""
    config = ctx.obj["config"]
    fmt = format_type or ctx.obj.get("format", "table")

    status = {
        "status": "running",
        "initialized": True,
        "authenticated": config.is_authenticated,
        "config_path": config.config_path,
        "cloud_server": config.get("cloud_server"),
        "tty": ctx.obj.get("is_tty", False),
        "format": fmt,
    }

    print_success(status, fmt)


@system_cmd.command(name="oauth-url")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def system_oauth_url(ctx, format_type: Optional[str]):
    """获取OAuth授权URL"""
    config = ctx.obj["config"]
    client = CLIClient(config)
    fmt = format_type or ctx.obj.get("format", "table")

    try:
        url = run_async(client.get_oauth_url())
        print_success({"oauth_url": url}, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.AUTH_FAILED,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@system_cmd.command(name="auth")
@click.argument("code")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def system_auth(ctx, code: str, format_type: Optional[str]):
    """使用授权码完成认证

    \b
    认证流程:
      miot system oauth-url          # 获取OAuth URL
      # 浏览器打开URL完成授权
      miot system auth <code>        # 使用授权码完成认证

    \b
    Agent使用:
      miot system oauth-url --json | jq -r '.data.oauth_url'  # 获取URL给用户在浏览器打开
    """
    config = ctx.obj["config"]
    client = CLIClient(config)
    fmt = format_type or ctx.obj.get("format", "table")

    try:
        success = run_async(client.set_oauth_code(code))
        if success:
            print_success({"authenticated": True}, fmt)
        else:
            print_error(
                error_message="认证失败",
                code=ErrorCode.AUTH_FAILED,
                format_type=fmt
            )
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.AUTH_FAILED,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@system_cmd.command(name="notify")
@click.argument("content")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def system_notify(ctx, content: str, format_type: Optional[str]):
    """发送应用通知

    \b
    使用示例:
      miot system notify "设备离线告警"

    \b
    延迟通知:
      # 30分钟后发送（使用at命令）
      echo "miot system notify '会议提醒'" | at now + 30 minutes

      # 定时发送（cron）
      0 8 * * * /usr/bin/miot system notify "早安"
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
        result = run_async(client.send_notification(content))
        print_success({"sent": result}, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.NETWORK_ERROR,
            format_type=fmt
        )
    finally:
        run_async(client.close())


@system_cmd.command(name="config")
@click.argument("key")
@click.argument("value", required=False)
@click.option("--unset", is_flag=True, help="删除配置项")
@click.option("-f", "--format", "format_type", default=None, type=click.Choice(["json", "yaml", "table", "human"]))
@click.pass_context
def system_config(ctx, key: str, value: Optional[str], unset: bool, format_type: Optional[str]):
    """管理配置 (get/set/unset)"""
    config: CLIConfig = ctx.obj["config"]
    fmt = format_type or ctx.obj.get("format", "table")

    try:
        if unset:
            # 删除配置
            if key in config._config:
                del config._config[key]
                config.save()
            print_success({"deleted": key}, fmt)
        elif value is None:
            # 获取配置
            val = config.get(key)
            print_success({"key": key, "value": val}, fmt)
        else:
            # 设置配置
            # 尝试解析为JSON
            try:
                import json
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value

            config.set(key, parsed_value)
            config.save()
            print_success({"key": key, "value": parsed_value}, fmt)
    except Exception as e:
        print_error(
            error_message=str(e),
            code=ErrorCode.CONFIG_ERROR,
            format_type=fmt
        )
