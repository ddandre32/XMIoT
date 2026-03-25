# -*- coding: utf-8 -*-
"""
MCP服务示例 - 为AI智能体提供接口
"""
import asyncio
import uuid
from miot_sdk import MIoTClient
from miot_sdk.const import OAUTH2_REDIRECT_URI_DEFAULT
from mcp import XiaomiIoTMCP


async def run_mcp_server():
    """运行MCP服务器"""
    # 创建MIoT客户端
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri=OAUTH2_REDIRECT_URI_DEFAULT,  # 使用官方允许的回调地址
        cache_path="./cache",
    )

    # 创建MCP服务
    mcp = XiaomiIoTMCP(
        miot_client=client,
        name="我的智能家居MCP",
    )

    # 运行服务器
    print("启动MCP服务器...")
    print("AI智能体现在可以通过MCP协议控制你的小米设备了！")
    await mcp.run_http(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    asyncio.run(run_mcp_server())
