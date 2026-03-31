# -*- coding: utf-8 -*-
"""
小米IoT CLI工具 - 命令行接口文档

## 安装

```bash
pip install -e ".[cli]"
```

## 快速开始

### 1. 初始化配置

```bash
# 查看系统状态
miot system status

# 获取OAuth授权URL
miot system oauth-url
```

访问输出的URL，登录小米账号并授权，然后获取授权码。

### 2. 完成认证

```bash
miot system auth <授权码>
```

### 3. 使用设备

```bash
# 列出所有设备
miot device list

# 仅列出在线设备
miot device list --online

# 按类型筛选（如灯具）
miot device list --type light

# 获取设备详情
miot device get <did>

# 获取设备SPEC
miot device spec <did>
```

### 4. 控制设备

```bash
# 获取属性值
miot device prop get <did> <siid> <piid>

# 设置属性值（开关）
miot device prop set <did> 2 1 true
miot device prop set <did> 2 1 false

# 设置属性值（亮度0-100）
miot device prop set <did> 2 2 80

# 执行动作
miot device action <did> <siid> <aiid>
```

### 5. 批量控制

```bash
# 从文件批量操作
miot device batch --file ops.json

# 从stdin批量操作
echo '[
  {"type":"set_prop","did":"123","siid":2,"piid":1,"value":true},
  {"type":"set_prop","did":"456","siid":2,"piid":1,"value":true}
]' | miot device batch
```

### 6. 场景管理

```bash
# 列出场景
miot scene list

# 搜索场景
miot scene search "回家"

# 执行场景
miot scene run <scene_id>

# 批量执行场景
miot scene run <scene_id1> --batch <scene_id2>,<scene_id3>
```

### 7. 系统管理

```bash
# 发送通知
miot system notify "测试消息"

# 配置管理
miot system config cloud_server cn
miot system config redirect_uri "http://localhost:8000/callback"
```

## 输出格式

支持三种输出格式：

- `json` (默认): JSON格式，适合程序解析
- `yaml`: YAML格式，便于阅读
- `table`: 表格格式，便于命令行查看

示例：
```bash
miot device list --format table
miot scene list -f yaml
```

## 配置文件

配置文件默认保存在 `~/.miot/config.json`：

```json
{
  "uuid": "your-uuid",
  "redirect_uri": "http://localhost:8000/callback",
  "cache_path": "~/.miot/cache",
  "cloud_server": "cn",
  "oauth_info": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_ts": 1234567890
  }
}
```

## 快捷命令

```bash
miot devices          # 等同于 miot device list
miot scenes           # 等同于 miot scene list
miot status           # 等同于 miot system status
```

## 完整命令列表

### 全局选项
- `--config`: 配置文件路径
- `--format`: 输出格式 (json/yaml/table)
- `-v, --verbose`: 详细输出

### 设备命令 (miot device)
- `list`: 列出设备
  - `--refresh`: 刷新列表
  - `--online`: 仅在线设备
  - `--room`: 按房间筛选
  - `--home`: 按家庭筛选
  - `--type`: 按类型筛选
- `get <did>`: 获取设备详情
- `spec <did>`: 获取设备SPEC
- `prop get <did> <siid> <piid>`: 获取属性
- `prop set <did> <siid> <piid> <value>`: 设置属性
- `action <did> <siid> <aiid> [in_list...]`: 执行动作
- `batch`: 批量控制
  - `--file`: 操作文件路径

### 场景命令 (miot scene)
- `list`: 列出场景
  - `--refresh`: 刷新列表
  - `--home`: 按家庭筛选
- `get <scene_id>`: 获取场景详情
- `search <keyword>`: 搜索场景
- `run <scene_id>`: 执行场景
  - `--batch`: 批量执行

### 系统命令 (miot system)
- `status`: 系统状态
- `oauth-url`: 获取OAuth URL
- `auth <code>`: 完成认证
- `notify <content>`: 发送通知
- `config <key> [value]`: 配置管理
  - `--unset`: 删除配置项
