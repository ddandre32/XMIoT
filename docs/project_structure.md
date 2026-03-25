# 项目目录结构

```
xiaomi_iot_manager/
├── pyproject.toml              # 项目配置和依赖
├── README.md                   # 项目说明文档
│
├── miot_sdk/                   # 核心SDK模块
│   ├── __init__.py             # SDK入口
│   ├── client.py               # 主客户端 (MIoTClient)
│   ├── cloud.py                # HTTP客户端 (MIoTHttpClient)
│   ├── lan.py                  # 局域网发现 (MIoTLan)
│   ├── spec.py                 # SPEC解析器 (MIoTSpecParser)
│   ├── storage.py              # 本地存储 (MIoTStorage)
│   ├── types.py                # 数据类型定义
│   ├── const.py                # 常量定义
│   └── error.py                # 异常定义
│
├── core/                       # 服务层
│   ├── __init__.py
│   ├── device_manager.py       # 设备管理服务
│   ├── scene_manager.py        # 场景管理服务
│   └── notification_service.py # 通知服务
│
├── api/                        # RESTful API
│   ├── __init__.py
│   ├── server.py               # FastAPI服务
│   └── routes/
│       ├── devices.py          # 设备API路由
│       ├── scenes.py           # 场景API路由
│       └── system.py           # 系统API路由
│
├── mcp/                        # MCP服务
│   ├── __init__.py
│   └── server.py               # MCP服务器
│
├── examples/                   # 使用示例
│   ├── basic_usage.py          # 基础使用
│   ├── run_api_server.py       # API服务示例
│   └── run_mcp_server.py       # MCP服务示例
│
├── docs/                       # 文档
│   ├── architecture.md         # 架构设计
│   ├── api_reference.md        # API参考
│   └── iot_analysis_report.md  # IOT接口分析报告
│
└── tests/                      # 测试（待添加）
    ├── __init__.py
    ├── test_client.py
    ├── test_cloud.py
    └── test_spec.py
```

## 文件说明

### SDK层 (miot_sdk/)

| 文件 | 说明 | 核心类 |
|------|------|--------|
| client.py | 主客户端 | MIoTClient |
| cloud.py | HTTP客户端 | MIoTHttpClient, MIoTOAuth2Client |
| lan.py | 局域网发现 | MIoTLan |
| spec.py | SPEC解析 | MIoTSpecParser |
| storage.py | 本地缓存 | MIoTStorage |
| types.py | 数据类型 | 所有数据模型 |
| const.py | 常量 | 配置常量 |
| error.py | 异常 | 所有异常类 |

### 服务层 (core/)

| 文件 | 说明 | 核心类 |
|------|------|--------|
| device_manager.py | 设备管理 | DeviceManager |
| scene_manager.py | 场景管理 | SceneManager |
| notification_service.py | 通知 | NotificationService |

### API层 (api/)

| 文件 | 说明 |
|------|------|
| server.py | FastAPI服务初始化 |
| routes/devices.py | 设备相关API |
| routes/scenes.py | 场景相关API |
| routes/system.py | 系统相关API |

### MCP层 (mcp/)

| 文件 | 说明 | 核心类 |
|------|------|--------|
| server.py | MCP服务 | XiaomiIoTMCP |

## 依赖关系

```
Application
    │
    ├──▶ API (FastAPI)
    │       └──▶ DeviceManager
    │       └──▶ SceneManager
    │
    ├──▶ MCP (fastmcp)
    │       └──▶ DeviceManager
    │       └──▶ SceneManager
    │
    └──▶ SDK (直接)
            │
            ├──▶ HTTP Client (aiohttp)
            │       └──▶ 小米云API
            │
            ├──▶ LAN Discovery (socket)
            │       └──▶ 局域网设备
            │
            └──▶ SPEC Parser (aiohttp)
                    └──▶ SPEC服务
```
