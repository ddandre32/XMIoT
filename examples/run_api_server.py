# -*- coding: utf-8 -*-
"""
API服务示例
"""
import asyncio
import uuid
from miot_sdk import MIoTClient
from miot_sdk.const import OAUTH2_REDIRECT_URI_DEFAULT
from api import XiaomiIoTAPI


def run_api_server():
    """运行API服务器"""
    # 创建MIoT客户端
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri=OAUTH2_REDIRECT_URI_DEFAULT,  # 使用官方允许的回调地址
        cache_path="./cache",
    )

    # 创建API服务
    api = XiaomiIoTAPI(
        miot_client=client,
        title="我的智能家居API",
        version="1.0.0",
    )

    # 运行服务器
    print("启动API服务器...")
    print("访问 http://localhost:8000/docs 查看API文档")
    api.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run_api_server()
