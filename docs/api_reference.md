# 小米IoT SDK API 详细文档

## 核心类

### MIoTClient

小米IoT主客户端类，提供所有功能的统一入口。

#### 构造函数

```python
MIoTClient(
    uuid: str,                          # 设备唯一标识
    redirect_uri: str,                  # OAuth回调地址
    cache_path: Optional[str] = None,   # 缓存路径
    cloud_server: Optional[str] = None, # 云服务器区域 (cn/ru等)
    oauth_info: Optional[MIoTOauthInfo | Dict] = None,  # OAuth信息
)
```

#### 方法

##### init()

初始化客户端。

```python
await client.init()
```

##### deinit()

反初始化客户端，释放资源。

```python
await client.deinit()
```

##### gen_oauth_url()

生成OAuth授权URL。

```python
url = client.gen_oauth_url(
    redirect_uri: Optional[str] = None,
    scope: Optional[List[str]] = None,
)
# 返回: str
```

##### get_user_info()

获取用户信息。

```python
user_info = await client.get_user_info()
# 返回: MIoTUserInfo
# {
#   "uid": "12345",
#   "nickname": "用户名",
#   "icon": "头像URL",
#   "union_id": "union_id"
# }
```

##### get_homes()

获取家庭列表。

```python
homes = await client.get_homes(fetch_share_home: bool = False)
# 返回: Dict[str, MIoTHomeInfo]
```

##### get_devices()

获取设备列表。

```python
devices = await client.get_devices(
    home_list: Optional[List[MIoTHomeInfo]] = None,
    fetch_share_home: bool = False,
)
# 返回: Dict[str, MIoTDeviceInfo]
```

##### get_device()

获取单个设备。

```python
device = await client.get_device(did: str)
# 返回: Optional[MIoTDeviceInfo]
```

##### get_prop()

获取设备属性值。

```python
value = await client.get_prop(did: str, siid: int, piid: int)
# 返回: Any
```

##### set_prop()

设置设备属性值。

```python
result = await client.set_prop(
    did: str,
    siid: int,
    piid: int,
    value: Any,
)
# 返回: Dict
# {
#   "code": 0,  # 0表示成功
#   "message": "..."
# }
```

##### action()

执行设备动作。

```python
result = await client.action(
    did: str,
    siid: int,
    aiid: int,
    in_list: List[Any] = None,
)
# 返回: Dict
```

##### get_device_spec_lite()

获取设备简化版SPEC。

```python
spec = await client.get_device_spec_lite(urn: str)
# 返回: Dict[str, MIoTSpecDeviceLite]
```

##### get_manual_scenes()

获取手动场景列表。

```python
scenes = await client.get_manual_scenes(
    home_list: Optional[List[MIoTHomeInfo]] = None,
    fetch_share_home: bool = False,
)
# 返回: Dict[str, MIoTManualSceneInfo]
```

##### run_manual_scene()

执行手动场景。

```python
result = await client.run_manual_scene(scene_info: MIoTManualSceneInfo)
# 返回: bool
```

##### send_app_notify_once()

发送一次性应用通知。

```python
result = await client.send_app_notify_once(content: str)
# 返回: bool
```

---

## 数据类型

### MIoTDeviceInfo

设备信息模型。

| 字段 | 类型 | 说明 |
|------|------|------|
| did | str | 设备ID |
| name | str | 设备名称 |
| model | str | 设备型号 |
| urn | str | 设备URN |
| online | bool | 在线状态 |
| home_id | str | 家庭ID |
| home_name | str | 家庭名称 |
| room_id | str | 房间ID |
| room_name | str | 房间名称 |
| manufacturer | str | 制造商 |
| fw_version | str | 固件版本 |
| sub_devices | Dict[str, MIoTDeviceInfo] | 子设备 |

### MIoTSpecDeviceLite

简化版设备SPEC。

| 字段 | 类型 | 说明 |
|------|------|------|
| iid | str | 实例ID（如 "prop.0.2.1"） |
| description | str | 描述 |
| format | str | 数据格式 |
| writeable | bool | 是否可写 |
| readable | bool | 是否可读 |
| unit | str | 单位 |
| value_range | MIoTSpecValueRange | 值范围 |
| value_list | List[MIoTSpecValueListItem] | 值列表 |

### MIoTManualSceneInfo

手动场景信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| scene_id | str | 场景ID |
| scene_name | str | 场景名称 |
| uid | str | 用户ID |
| home_id | str | 家庭ID |
| room_id | str | 房间ID |
| enable | bool | 启用状态 |
| dids | List[str] | 关联设备ID列表 |

---

## 设备控制示例

### 开灯

```python
# 假设灯设备的 did="12345", siid=2, piid=1 (开关属性)
await client.set_prop("12345", 2, 1, True)
```

### 调节亮度

```python
# 假设亮度属性 piid=2，范围 1-100
await client.set_prop("12345", 2, 2, 50)
```

### 获取温度

```python
# 假设温度传感器 did="67890", siid=3, piid=1
temp = await client.get_prop("67890", 3, 1)
print(f"当前温度: {temp}°C")
```

### 执行扫地机器人动作

```python
# 假设扫地机器人有"开始清扫"动作，aiid=1
result = await client.action("robot_did", 2, 1, [])
```

---

## 场景控制示例

### 获取并执行场景

```python
# 获取所有场景
scenes = await client.get_manual_scenes()

# 找到"回家模式"场景
for scene_id, scene in scenes.items():
    if "回家" in scene.scene_name:
        # 执行场景
        result = await client.run_manual_scene(scene)
        print(f"场景执行结果: {result}")
        break
```

---

## 错误处理

所有方法都可能抛出以下异常：

| 异常 | 说明 | 处理建议 |
|------|------|----------|
| MIoTClientError | 客户端错误 | 检查参数是否正确 |
| MIoTHttpError | HTTP错误 | 检查网络连接，可能需要重新授权 |
| MIoTOAuth2Error | OAuth错误 | 需要重新获取授权 |
| MIoTSpecError | SPEC解析错误 | 设备可能不支持SPEC协议 |

### 错误处理示例

```python
from miot_sdk.error import MIoTError, MIoTHttpError

try:
    result = await client.set_prop(did, siid, piid, value)
except MIoTHttpError as e:
    if e.code == 401:
        # Token过期，需要重新授权
        print("Token已过期，请重新授权")
    else:
        print(f"HTTP错误: {e.message}")
except MIoTError as e:
    print(f"MIoT错误: {e.message}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 批量操作

### 批量获取属性

```python
from miot_sdk.types import MIoTGetPropertyParam

params = [
    MIoTGetPropertyParam(did="123", siid=2, piid=1),  # 开关
    MIoTGetPropertyParam(did="123", siid=2, piid=2),  # 亮度
    MIoTGetPropertyParam(did="456", siid=3, piid=1),  # 温度
]

results = await client.get_props(params)
for result in results:
    print(f"{result['did']}.{result['siid']}.{result['piid']}: {result['value']}")
```

### 批量设置属性

```python
from miot_sdk.types import MIoTSetPropertyParam

params = [
    MIoTSetPropertyParam(did="123", siid=2, piid=1, value=True),   # 开灯
    MIoTSetPropertyParam(did="123", siid=2, piid=2, value=100),   # 最大亮度
]

results = await client.set_props(params)
```
