# 小米IoT CLI 协议文档

> 符合 [CLI设计规范](./cli-design-guide.md) 的命令行工具协议

---

## 一、设计原则

### 1.1 双用户兼容

CLI同时兼容两类用户：

| 用户类型 | 环境特征 | 默认格式 | 设计目标 |
|---------|---------|---------|---------|
| **人类用户** | TTY终端（交互式） | `table` | 可读性强，表格展示 |
| **Agent用户** | 非TTY（管道/脚本） | `json` | 结构化，易于解析 |

**自动检测逻辑：**
```python
if is_tty():
    default_format = "table"  # 人类友好
else:
    default_format = "json"   # 机器友好
```

### 1.2 配置层级

优先级从高到低：

1. **命令行参数**：`--format json`, `--config ~/.miot/config.json`
2. **环境变量**：`MIOT_FORMAT=json`, `MIOT_CONFIG_PATH=...`
3. **配置文件**：`~/.miot/config.json`
4. **系统默认**：自动检测TTY

### 1.3 管道友好

```bash
# 成功输出到stdout，可被管道处理
miot device list --json | jq '.data[] | select(.online)'

# 错误输出到stderr，不影响管道
miot device list 2>/dev/null || echo "出错但管道继续"

# 从stdin读取（批量操作）
echo '[{"did":"xxx","action":"turn_on"}]' | miot device batch
```

### 1.4 幂等性

相同输入产生相同输出，无副作用：

```bash
# 多次执行结果一致
miot device get <did>    # 总是返回当前状态
miot scene list          # 总是返回当前场景列表
```

---

## 二、输出格式

### 2.1 成功响应格式

```json
{
  "success": true,
  "data": { ... },      // 或数组 [...]
  "timestamp": "2026-03-31T12:00:00Z",
  "meta": { ... }       // 可选：分页、请求ID等
}
```

### 2.2 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "设备未找到",
    "suggestion": "运行 'miot device list' 查看可用设备ID"
  },
  "timestamp": "2026-03-31T12:00:00Z"
}
```

### 2.3 格式类型

| 格式 | 说明 | 适用场景 |
|-----|------|---------|
| `json` | JSON结构化输出 | 自动化脚本、Agent调用 |
| `yaml` | YAML格式（需安装pyyaml） | 配置文件、人类阅读 |
| `table` | 表格对齐 | 终端直接查看 |
| `human` | 简化键值对 | 快速查看单个结果 |

**显式指定格式：**
```bash
miot --format json device list    # 强制JSON
miot --json device list           # 快捷方式
miot device list --format table   # 子命令指定
```

---

## 三、错误码规范

### 3.1 错误码列表

| 错误码 | 说明 | 建议操作 |
|-------|------|---------|
| `NOT_AUTHENTICATED` | 未认证 | 运行 `miot system oauth-url` 获取授权URL |
| `AUTH_EXPIRED` | 认证过期 | 重新运行 `miot system auth <code>` |
| `AUTH_FAILED` | 认证失败 | 检查授权码是否正确 |
| `DEVICE_NOT_FOUND` | 设备未找到 | 运行 `miot device list` 查看可用设备 |
| `DEVICE_OFFLINE` | 设备离线 | 检查设备电源和网络连接 |
| `DEVICE_ERROR` | 设备操作失败 | 检查设备状态后重试 |
| `PROP_GET_ERROR` | 获取属性失败 | 检查属性ID是否正确 |
| `PROP_SET_ERROR` | 设置属性失败 | 检查属性值类型是否正确 |
| `ACTION_ERROR` | 执行动作失败 | 检查动作ID和参数 |
| `SPEC_NOT_FOUND` | SPEC未找到 | 设备可能不支持SPEC查询 |
| `SCENE_NOT_FOUND` | 场景未找到 | 运行 `miot scene list` 查看可用场景 |
| `SCENE_EXEC_ERROR` | 执行场景失败 | 检查场景是否启用 |
| `NETWORK_ERROR` | 网络错误 | 检查网络连接，稍后重试 |
| `TIMEOUT` | 操作超时 | 网络延迟较高，请稍后重试 |
| `INTERRUPTED` | 操作被中断 | 可以重新执行 |
| `INVALID_ARGUMENT` | 参数错误 | 使用 `--help` 查看用法 |
| `INVALID_FORMAT` | 格式错误 | 检查输入数据格式 |
| `CONFIG_ERROR` | 配置错误 | 检查配置文件格式 |
| `UNKNOWN_ERROR` | 未知错误 | 检查日志或重新认证 |

### 3.2 错误处理示例

```bash
# 捕获错误码
miot device get invalid_did --json > result.json 2>error.json
if [ $? -ne 0 ]; then
    error_code=$(cat error.json | jq -r '.error.code')
    echo "错误码: $error_code"
fi
```

---

## 四、环境变量

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `MIOT_CONFIG_PATH` | 配置文件路径 | `~/.miot/config.json` |
| `MIOT_CLOUD_SERVER` | 云服务器区域 | `cn`/`sg`/`us`/`de` |
| `MIOT_REDIRECT_URI` | OAuth回调地址 | `http://localhost:8000/callback` |
| `MIOT_CACHE_PATH` | 缓存路径 | `~/.miot/cache` |
| `MIOT_FORMAT` | 默认输出格式 | `json`/`yaml`/`table`/`human` |
| `MIOT_ACCESS_TOKEN` | 访问令牌（CI使用） | `sk-xxxxx` |

**CI/自动化场景：**
```bash
# 通过环境变量配置，无需交互式认证
export MIOT_ACCESS_TOKEN="sk-xxxxx"
export MIOT_FORMAT="json"
export MIOT_CLOUD_SERVER="cn"

miot device list --json | jq '.data[].name'
```

---

## 五、原子能力

### 5.1 内容发现

```bash
# 设备列表
miot device list [--online] [--room <id>] [--type <model>]

# 场景列表
miot scene list [--home <id>]

# 场景搜索
miot scene search <keyword>
```

### 5.2 内容获取

```bash
# 获取设备详情
miot device get <did>

# 获取设备SPEC
miot device spec <did>

# 获取单个场景
miot scene get <scene_id>
```

### 5.3 内容处理

```bash
# 获取属性
miot device prop get <did> <siid> <piid>

# 设置属性
miot device prop set <did> <siid> <piid> <value>

# 执行动作
miot device action <did> <siid> <aiid> [args...]

# 执行场景
miot scene run <scene_id>
```

### 5.4 内容导出

所有命令支持 `--format` / `--json` 选项：

```bash
miot device list --json > devices.json
miot device spec <did> --format yaml > spec.yaml
miot scene list --json | jq '.data[]'
```

---

## 六、使用示例

### 6.1 快速开始

```bash
# 1. 获取OAuth授权URL
miot system oauth-url
# 输出: {"oauth_url": "https://...", "success": true}

# 2. 完成认证（使用授权码）
miot system auth <code>

# 3. 列出设备（TTY默认table格式）
miot device list

# 4. 控制设备
miot device prop set <did> 2 1 true    # 开灯
miot device prop set <did> 2 1 false   # 关灯

# 5. 执行场景
miot scene run <scene_id>
```

### 6.2 管道使用

```bash
# 获取所有在线设备的名称
miot device list --online --json | jq -r '.data[].name'

# 获取特定类型的设备
miot device list --json | jq '.data[] | select(.model | contains("light"))'

# 批量获取设备详情
miot device list --json | jq -r '.data[].did' | xargs -I {} miot device get {} --json

# 批量控制设备（从文件）
cat operations.json | miot device batch

# 批量控制设备（直接传递）
echo '[
  {"did": "xxx", "action": "turn_on"},
  {"did": "yyy", "action": "turn_off"}
]' | miot device batch
```

### 6.3 脚本集成

```bash
#!/bin/bash
# 智能家居自动化脚本示例

set -e

# 设置JSON格式（非TTY环境自动使用json）
FORMAT="${MIOT_FORMAT:-json}"

# 获取所有在线灯具
LIGHTS=$(miot device list --online --json | jq -r '.data[] | select(.model | contains("light")) | .did')

# 批量关闭
for did in $LIGHTS; do
    echo "关闭设备: $did"
    miot device prop set "$did" 2 1 false --json > /dev/null
done

echo "所有灯具已关闭"
```

### 6.4 错误处理

```python
#!/usr/bin/env python3
import subprocess
import json

def run_miot(args):
    """运行miot命令并处理错误"""
    try:
        result = subprocess.run(
            ['miot', '--json'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        error = json.loads(e.stderr)
        print(f"错误: {error['error']['code']}")
        print(f"消息: {error['error']['message']}")
        print(f"建议: {error['error']['suggestion']}")
        raise

# 使用示例
try:
    devices = run_miot(['device', 'list'])
    print(f"找到 {len(devices['data'])} 个设备")
except Exception as e:
    print(f"操作失败: {e}")
```

---

## 七、配置文件

### 7.1 配置文件路径

默认：`~/.miot/config.json`

可通过以下方式覆盖：
- 命令行：`miot --config /path/to/config.json`
- 环境变量：`export MIOT_CONFIG_PATH=/path/to/config.json`

### 7.2 配置项

```json
{
  "uuid": "xxx-xxx-xxx",
  "redirect_uri": "http://localhost:8000/callback",
  "cache_path": "~/.miot/cache",
  "cloud_server": "cn",
  "format": "json",
  "oauth_info": {
    "access_token": "sk-xxxxx",
    "refresh_token": "rt-xxxxx",
    "expires_at": 1234567890
  }
}
```

### 7.3 配置管理命令

```bash
# 获取配置
miot system config cloud_server

# 设置配置
miot system config cloud_server sg

# 删除配置项
miot system config format --unset
```

---

## 八、API设计对比

### 8.1 vs 传统API

| 特性 | 传统API | CLI协议 |
|-----|---------|---------|
| 认证 | OAuth/Token集成 | 本地配置或环境变量 |
| 调用方式 | HTTP请求 | 命令执行 |
| 输出格式 | JSON/XML | JSON/YAML/Table/Human |
| 错误处理 | HTTP状态码 | 结构化错误+建议 |
| 管道支持 | 需额外编码 | 原生支持 |

### 8.2 vs SDK

| 特性 | SDK | CLI协议 |
|-----|-----|---------|
| 依赖管理 | 复杂 | 无（独立可执行） |
| 语言绑定 | 特定语言 | 任意语言调用 |
| 版本兼容 | 可能冲突 | 独立进程 |
| 学习成本 | 高（需读文档） | 低（--help即可） |

---

## 九、最佳实践

### 9.1 Agent集成

```yaml
# Skill定义示例
name: control-light
steps:
  - run: miot device list --json --online
    output: devices

  - run: |
      echo '{{steps.1.outputs.data}}' |
      jq -r '.[] | select(.name | contains("{{.room}}")) | .did'
    output: light_did

  - run: miot device prop set {{steps.2.outputs.light_did}} 2 1 {{.state}}
```

### 9.2 调试技巧

```bash
# 查看详细输出
miot -v device list

# 查看原始JSON
miot device list --json

# 格式化输出
miot device list --json | jq '.'

# 查看错误详情
miot device get invalid --json 2>&1 | jq '.'
```

### 9.3 性能优化

```bash
# 使用缓存（避免重复请求）
miot device list              # 使用缓存
miot device list --refresh    # 强制刷新

# 筛选减少数据传输
miot device list --online     # 仅在线设备
miot device list --room xxx   # 仅特定房间
```

---

## 十、参考

- [CLI设计规范](./cli-design-guide.md)
- [Podwise CLI](https://podwise.ai/) - 播客AI摘要CLI工具
- [硬地骇客 EP124](https://www.xiaoyuzhoufm.com/episode/69caa449e2c8be3155f03013) - 播客原声

---

*文档版本: 1.0.0*
*更新日期: 2026-03-31*
