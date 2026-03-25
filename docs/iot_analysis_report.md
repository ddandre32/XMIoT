# 小米IoT接口管理项目 - IOT接口分析报告

## 1. MiLoco项目IOT接口梳理

### 1.1 核心SDK模块 (miot_kit/miot/)

#### client.py - 主客户端
| 接口 | 功能 | 输入参数 | 输出 |
|------|------|----------|------|
| get_devices_async | 获取设备列表 | home_list, fetch_share_home | Dict[str, MIoTDeviceInfo] |
| get_homes_async | 获取家庭列表 | fetch_share_home | Dict[str, MIoTHomeInfo] |
| get_cameras_async | 获取摄像头 | home_list | Dict[str, MIoTCameraInfo] |
| get_manual_scenes_async | 获取场景 | home_list | Dict[str, MIoTManualSceneInfo] |
| run_manual_scene_async | 执行场景 | scene_info | bool |
| send_app_notify_async | 发送通知 | notify_id | bool |
| create_camera_instance_async | 创建摄像头 | camera_info | MIoTCameraInstance |

#### cloud.py - HTTP客户端
| 接口 | HTTP方法 | API端点 | 功能 |
|------|----------|---------|------|
| get_props_async | POST | /app/v2/miotspec/prop/get | 批量获取属性 |
| get_prop_async | POST | /app/v2/miotspec/prop/get | 获取单个属性 |
| set_prop_async | POST | /app/v2/miotspec/prop/set | 设置属性 |
| set_props_async | POST | /app/v2/miotspec/prop/set | 批量设置属性 |
| action_async | POST | /app/v2/miotspec/action | 执行动作 |
| get_devices_async | POST | /app/v2/home/device_list_page | 获取设备 |
| run_manual_scene_async | POST | /app/appgateway/miot/appsceneservice/AppSceneService/NewRunScene | 执行场景 |
| send_app_notify_async | POST | /app/v2/oauth/send_push | 发送通知 |

#### lan.py - 局域网发现
| 接口 | 协议 | 功能 |
|------|------|------|
| ping_async | UDP广播 | 探测局域网设备 |
| get_devices_async | UDP | 获取在线设备 |
| register_status_changed_async | Callback | 设备状态变化监听 |

### 1.2 服务端接口

#### miot_controller.py - REST API
| 端点 | 方法 | 功能 |
|------|------|------|
| /miot/xiaomi_home_callback | GET | OAuth回调 |
| /miot/login_status | GET | 登录状态 |
| /miot/user_info | GET | 用户信息 |
| /miot/camera_list | GET | 摄像头列表 |
| /miot/device_list | GET | 设备列表 |
| /miot/refresh_miot_* | GET | 刷新各类信息 |
| /miot/send_notify | GET | 发送通知 |
| /miot/ws/video_stream | WebSocket | 视频流 |

#### mcp.py - MCP工具
| 工具名 | 功能 |
|--------|------|
| get_devices | 获取设备列表 |
| get_device_spec | 获取设备SPEC |
| get_property | 获取属性 |
| set_property | 设置属性 |
| execute_action | 执行动作 |
| get_scenes | 获取场景 |
| trigger_scene | 执行场景 |

### 1.3 指令类型分类

#### 属性操作
- **读取**: GET /app/v2/miotspec/prop/get
- **写入**: POST /app/v2/miotspec/prop/set
- **批量**: 支持批量读写

#### 动作执行
- **执行**: POST /app/v2/miotspec/action
- **参数**: did, siid, aiid, in_list

#### 场景控制
- **列表**: GetManualSceneList
- **执行**: NewRunScene

#### 摄像头控制
- **连接**: 通过C库(libmiot_camera_lite.so)
- **视频流**: H264/H265解码
- **音频流**: PCM/G711/OPUS

#### 局域网探测
- **协议**: UDP广播
- **端口**: 54321
- **消息头**: 0x21 0x31

## 2. 移植实现总结

### 2.1 已实现功能

#### SDK层 (miot_sdk/)
- [x] client.py - 主客户端，整合所有功能
- [x] cloud.py - HTTP客户端，支持OAuth和API调用
- [x] lan.py - 局域网设备发现
- [x] spec.py - SPEC解析器
- [x] storage.py - 本地缓存
- [x] types.py - 完整数据类型定义
- [x] error.py - 异常定义
- [x] const.py - 常量定义

#### 服务层 (core/)
- [x] device_manager.py - 设备管理
- [x] scene_manager.py - 场景管理
- [x] notification_service.py - 通知服务

#### API层 (api/)
- [x] server.py - FastAPI服务
- [x] routes/devices.py - 设备API
- [x] routes/scenes.py - 场景API
- [x] routes/system.py - 系统API

#### MCP层 (mcp/)
- [x] server.py - MCP服务
- [x] 设备查询工具
- [x] 设备控制工具
- [x] 场景管理工具

### 2.2 功能完整性对比

| 功能 | MiLoco | 本项目 | 状态 |
|------|--------|--------|------|
| OAuth认证 | ✓ | ✓ | 完整 |
| 设备获取 | ✓ | ✓ | 完整 |
| 属性读写 | ✓ | ✓ | 完整 |
| 动作执行 | ✓ | ✓ | 完整 |
| 场景控制 | ✓ | ✓ | 完整 |
| 局域网发现 | ✓ | ✓ | 完整 |
| SPEC解析 | ✓ | ✓ | 完整 |
| 摄像头 | ✓ | - | 简化（无C库依赖）|
| RESTful API | ✓ | ✓ | 完整 |
| MCP支持 | ✓ | ✓ | 完整 |

### 2.3 关键差异

1. **摄像头支持**: 移除了C库依赖，保留接口结构，可后续添加
2. **SPEC缓存**: 添加了本地缓存机制
3. **批量操作**: 增强了批量控制能力
4. **错误处理**: 更详细的错误分类

## 3. 接口调用流程

### 3.1 设备控制流程
```
AI Agent → MCP工具 → DeviceManager → MIoTClient → MIoTHttpClient → 小米云API → 设备
```

### 3.2 设备发现流程
```
初始化 → 获取家庭列表 → 获取设备列表 → 局域网探测 → 合并状态 → 缓存 → 返回
```

### 3.3 SPEC解析流程
```
请求SPEC → 检查缓存 → 云端获取 → 解析 → 缓存 → 返回简化版
```

## 4. 推荐用法

### 4.1 AI智能体接入
使用MCP协议，AI可以：
1. 查询设备列表和状态
2. 获取设备SPEC了解能力
3. 设置属性控制设备
4. 执行动作触发功能
5. 执行场景批量控制

### 4.2 Web应用接入
使用RESTful API：
1. 获取设备展示在UI
2. 通过API控制设备
3. 批量操作提升效率

### 4.3 自动化脚本
直接使用SDK：
1. 创建MIoTClient
2. 编写控制逻辑
3. 定时执行或事件触发
