# 小米IoT接口管理项目

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个功能完整的小米智能家居设备管理SDK，支持AI智能体通过标准接口控制小米IoT设备。

## 功能特性

- **完整的IoT SDK**: 设备发现、属性读写、动作执行、场景控制
- **设备管理**: 支持按家庭、房间、类型筛选和管理设备
- **SPEC解析**: 自动解析设备SPEC，支持标准MIoT协议
- **局域网发现**: UDP广播探测局域网设备
- **RESTful API**: 提供完整的HTTP API接口
- **MCP支持**: 支持Model Context Protocol，供AI智能体调用
- **CLI工具**: 高性能命令行接口，适合自动化脚本和智能体调用
- **类型安全**: 完整的类型注解和Pydantic模型验证

## 项目结构

```
xiaomi_iot_manager/
├── miot_sdk/           # 核心SDK模块
│   ├── __init__.py
│   ├── client.py       # 主客户端
│   ├── cloud.py        # HTTP云API客户端
│   ├── lan.py          # 局域网设备发现
│   ├── spec.py         # SPEC解析器
│   ├── storage.py      # 本地存储
│   ├── types.py        # 数据类型定义
│   ├── const.py        # 常量定义
│   └── error.py        # 异常定义
├── core/               # 服务层
│   ├── device_manager.py    # 设备管理
│   ├── scene_manager.py     # 场景管理
│   └── notification_service.py  # 通知服务
├── api/                # RESTful API
│   ├── server.py
│   └── routes/
│       ├── devices.py
│       ├── scenes.py
│       └── system.py
├── mcp/                # MCP服务
│   └── server.py
├── cli/                # CLI工具
│   ├── main.py         # CLI主入口
│   ├── config.py       # 配置管理
│   ├── commands_device.py   # 设备命令
│   ├── commands_scene.py    # 场景命令
│   ├── commands_system.py   # 系统命令
│   ├── client.py       # CLI客户端封装
│   └── formatter.py    # 输出格式化
├── examples/           # 使用示例
│   ├── basic_usage.py
│   ├── run_api_server.py
│   └── run_mcp_server.py
├── tests/              # 测试用例
├── docs/               # 文档
├── pyproject.toml      # 项目配置
└── README.md           # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/xiaomi_iot_manager.git
cd xiaomi_iot_manager

# 安装依赖
pip install -e ".[dev]"

# 如果需要MCP支持
pip install -e ".[mcp]"
```

### 2. 直接使用（无需开发者配置）

本项目使用小米官方OAuth配置，**无需注册开发者账号**，直接使用即可：

```python
import asyncio
import uuid
from miot_sdk import MIoTClient

async def main():
    # 创建客户端（使用小米官方内置配置）
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri="http://localhost:8000/callback",
        cache_path="./cache",
        cloud_server="cn",
    )

    # 初始化
    await client.init()

    # 获取授权URL并让用户访问进行OAuth授权
    oauth_url = client.gen_oauth_url()
    print(f"请访问: {oauth_url}")
    # 用户登录小米账号并授权后，会获得授权码(code)
    # 通过授权码获取access_token后即可控制设备

    # 获取设备列表
    devices = await client.get_devices()
    for did, device in devices.items():
        print(f"{device.name}: {'在线' if device.online else '离线'}")

    # 获取设备SPEC
    spec = await client.get_device_spec_lite(devices[0].urn)

    # 控制设备（示例：开灯）
    # await client.set_prop(did, siid=2, piid=1, value=True)

    # 执行场景
    scenes = await client.get_manual_scenes()
    for scene_id, scene in scenes.items():
        print(f"场景: {scene.scene_name}")

    # 发送通知
    await client.send_app_notify_once("你好，小米IoT！")

    await client.deinit()

asyncio.run(main())
```

### 3. 运行API服务

```python
from miot_sdk import MIoTClient
from api import XiaomiIoTAPI
import uuid

client = MIoTClient(
    uuid=uuid.uuid4().hex,
    redirect_uri="http://localhost:8000/callback",
    cache_path="./cache",
)

api = XiaomiIoTAPI(client)
api.run(host="0.0.0.0", port=8000)
```

API文档访问：`http://localhost:8000/docs`

### 4. 运行MCP服务

```python
import asyncio
from miot_sdk import MIoTClient
from mcp import XiaomiIoTMCP
import uuid

async def main():
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri="http://localhost:8000/callback",
        cache_path="./cache",
    )

    mcp = XiaomiIoTMCP(client)
    await mcp.run_http(host="0.0.0.0", port=8080)

asyncio.run(main())
```

### 5. 使用CLI工具（推荐用于自动化和智能体）

CLI工具提供高性能的命令行接口，适合OpenClaw等智能体调用：

```bash
# 安装后自动可用
pip install -e "."

# 获取OAuth授权URL
miot system oauth-url

# 完成认证
miot system auth <授权码>

# 列出设备
miot device list

# 控制设备（开灯）
miot device prop set <did> 2 1 true

# 执行场景
miot scene run <scene_id>

# 发送通知
miot system notify "你好，小米IoT！"
```

CLI完整文档见 [cli/README.md](cli/README.md)

## API参考

### 设备管理

| 方法 | 说明 | 示例 |
|------|------|------|
| `get_devices()` | 获取设备列表 | `devices = await client.get_devices()` |
| `get_device(did)` | 获取单个设备 | `device = await client.get_device("12345")` |
| `get_prop(did, siid, piid)` | 获取属性 | `value = await client.get_prop("123", 2, 1)` |
| `set_prop(did, siid, piid, value)` | 设置属性 | `await client.set_prop("123", 2, 1, True)` |
| `action(did, siid, aiid, in_list)` | 执行动作 | `await client.action("123", 2, 1, [])` |

### 场景管理

| 方法 | 说明 | 示例 |
|------|------|------|
| `get_manual_scenes()` | 获取场景列表 | `scenes = await client.get_manual_scenes()` |
| `run_manual_scene(scene_info)` | 执行场景 | `await client.run_manual_scene(scene)` |

### 通知

| 方法 | 说明 | 示例 |
|------|------|------|
| `send_app_notify_once(content)` | 发送通知 | `await client.send_app_notify_once("消息")` |

## HTTP API端点

### 设备API

- `GET /api/v1/devices/` - 获取设备列表
- `GET /api/v1/devices/refresh` - 刷新设备列表
- `GET /api/v1/devices/{did}` - 获取设备详情
- `GET /api/v1/devices/{did}/spec` - 获取设备SPEC
- `GET /api/v1/devices/{did}/properties/{siid}/{piid}` - 获取属性
- `POST /api/v1/devices/properties/set` - 设置属性
- `POST /api/v1/devices/actions/execute` - 执行动作
- `POST /api/v1/devices/batch-control` - 批量控制

### 场景API

- `GET /api/v1/scenes/` - 获取场景列表
- `POST /api/v1/scenes/{scene_id}/execute` - 执行场景

### 系统API

- `GET /api/v1/system/status` - 获取系统状态
- `POST /api/v1/system/notification/send` - 发送通知

## MCP工具

AI智能体可以通过以下工具控制设备：

- `get_devices` - 获取设备列表
- `get_device_spec` - 获取设备SPEC
- `get_property` - 获取属性值
- `set_property` - 设置属性值
- `execute_action` - 执行动作
- `get_scenes` - 获取场景列表
- `execute_scene` - 执行场景

## CLI命令参考

### 设备命令

```bash
miot device list                    # 列出设备
miot device list --online           # 仅在线设备
miot device list --type light       # 按类型筛选
miot device get <did>               # 获取设备详情
miot device spec <did>              # 获取设备SPEC
miot device prop get <did> <siid> <piid>   # 获取属性
miot device prop set <did> <siid> <piid> <value>  # 设置属性
miot device action <did> <siid> <aiid>     # 执行动作
miot device batch --file ops.json   # 批量控制
```

### 场景命令

```bash
miot scene list                     # 列出场景
miot scene search <keyword>         # 搜索场景
miot scene run <scene_id>           # 执行场景
```

### 系统命令

```bash
miot system status                  # 系统状态
miot system oauth-url               # 获取OAuth URL
miot system auth <code>             # 完成认证
miot system notify <content>        # 发送通知
miot system config <key> [value]    # 配置管理
```

### 快捷命令

```bash
miot devices                        # 等同于 device list
miot scenes                         # 等同于 scene list
miot status                         # 等同于 system status
```

## 开发指南

### 添加新的设备类型支持

1. 在 `miot_sdk/spec.py` 中更新SPEC解析逻辑
2. 在 `core/device_manager.py` 中添加设备类型筛选方法

### 扩展API

1. 在 `api/routes/` 目录下创建新的路由文件
2. 在 `api/server.py` 中注册路由

### 自定义MCP工具

1. 在 `mcp/server.py` 中注册新的工具方法
2. 使用 `@self._mcp.add_tool()` 装饰器注册

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 致谢

本项目参考了小米官方的MiLoco项目架构设计。
