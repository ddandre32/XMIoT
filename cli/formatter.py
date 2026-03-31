# -*- coding: utf-8 -*-
"""
输出格式化工具 - 符合CLI设计规范

核心设计原则:
1. 统一的 JSON 输出格式: {success, data/error, timestamp}
2. 标准化错误码: NOT_AUTHENTICATED, DEVICE_NOT_FOUND 等
3. TTY检测: 自动根据环境选择输出格式
4. 支持多种格式: json/yaml/table/human
5. 进度显示: 长时间操作显示进度
"""
import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TextIO

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ErrorCode(str, Enum):
    """标准化错误码 - 符合CLI设计规范"""
    # 认证相关
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_FAILED = "AUTH_FAILED"

    # 设备相关
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    DEVICE_ERROR = "DEVICE_ERROR"

    # 属性/动作相关
    PROP_GET_ERROR = "PROP_GET_ERROR"
    PROP_SET_ERROR = "PROP_SET_ERROR"
    ACTION_ERROR = "ACTION_ERROR"
    SPEC_NOT_FOUND = "SPEC_NOT_FOUND"

    # 场景相关
    SCENE_NOT_FOUND = "SCENE_NOT_FOUND"
    SCENE_EXEC_ERROR = "SCENE_EXEC_ERROR"

    # 网络/系统相关
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    INTERRUPTED = "INTERRUPTED"

    # 输入/配置相关
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INVALID_FORMAT = "INVALID_FORMAT"
    CONFIG_ERROR = "CONFIG_ERROR"

    # 通用
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# 错误码对应的中文消息
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.NOT_AUTHENTICATED: "未认证，请先运行 'miot system auth <授权码>' 进行认证",
    ErrorCode.AUTH_EXPIRED: "认证已过期，请重新授权",
    ErrorCode.AUTH_FAILED: "认证失败",
    ErrorCode.DEVICE_NOT_FOUND: "设备未找到",
    ErrorCode.DEVICE_OFFLINE: "设备离线",
    ErrorCode.DEVICE_ERROR: "设备操作失败",
    ErrorCode.PROP_GET_ERROR: "获取属性失败",
    ErrorCode.PROP_SET_ERROR: "设置属性失败",
    ErrorCode.ACTION_ERROR: "执行动作失败",
    ErrorCode.SPEC_NOT_FOUND: "设备SPEC未找到",
    ErrorCode.SCENE_NOT_FOUND: "场景未找到",
    ErrorCode.SCENE_EXEC_ERROR: "执行场景失败",
    ErrorCode.NETWORK_ERROR: "网络错误",
    ErrorCode.TIMEOUT: "操作超时",
    ErrorCode.INTERRUPTED: "操作被用户中断",
    ErrorCode.INVALID_ARGUMENT: "参数错误",
    ErrorCode.INVALID_FORMAT: "格式错误",
    ErrorCode.CONFIG_ERROR: "配置错误",
    ErrorCode.UNKNOWN_ERROR: "未知错误",
}

# 错误码对应的建议
ERROR_SUGGESTIONS: Dict[ErrorCode, str] = {
    ErrorCode.NOT_AUTHENTICATED: "运行 'miot system oauth-url' 获取授权URL，然后使用 'miot system auth <code>' 完成认证",
    ErrorCode.AUTH_EXPIRED: "重新运行 'miot system auth <code>' 刷新认证",
    ErrorCode.AUTH_FAILED: "检查授权码是否正确，或重新获取授权URL",
    ErrorCode.DEVICE_NOT_FOUND: "运行 'miot device list' 查看可用设备ID",
    ErrorCode.DEVICE_OFFLINE: "检查设备电源和网络连接状态",
    ErrorCode.DEVICE_ERROR: "检查设备状态后重试，或使用 'miot device get <did>' 查看设备详情",
    ErrorCode.PROP_GET_ERROR: "检查属性ID是否正确，运行 'miot device spec <did>' 查看设备SPEC",
    ErrorCode.PROP_SET_ERROR: "检查属性值类型是否正确",
    ErrorCode.ACTION_ERROR: "检查动作ID和参数是否正确，运行 'miot device spec <did>' 查看设备SPEC",
    ErrorCode.SPEC_NOT_FOUND: "设备可能不支持SPEC查询，尝试直接操作",
    ErrorCode.SCENE_NOT_FOUND: "运行 'miot scene list' 查看可用场景ID",
    ErrorCode.SCENE_EXEC_ERROR: "检查场景是否启用，或重试",
    ErrorCode.NETWORK_ERROR: "检查网络连接，或稍后重试",
    ErrorCode.TIMEOUT: "网络延迟较高，请稍后重试",
    ErrorCode.INTERRUPTED: "操作被中断，可以重新执行",
    ErrorCode.INVALID_ARGUMENT: "检查命令参数是否正确，使用 --help 查看用法",
    ErrorCode.INVALID_FORMAT: "检查输入数据格式是否为有效的JSON",
    ErrorCode.CONFIG_ERROR: "检查配置文件格式，或删除后重新配置",
    ErrorCode.UNKNOWN_ERROR: "如果问题持续，请检查日志或重新认证",
}


class OutputFormat(str, Enum):
    """输出格式枚举"""
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    HUMAN = "human"


def is_tty(stream: Optional[TextIO] = None) -> bool:
    """
    检测是否为TTY环境（终端交互模式）

    根据CLI设计规范:
    - TTY环境（人类用户）→ 默认table/human格式
    - 非TTY环境（Agent用户）→ 默认json格式
    """
    if stream is None:
        stream = sys.stdout
    try:
        return stream.isatty()
    except (AttributeError, OSError):
        return False


def get_default_format() -> str:
    """根据环境自动选择默认输出格式"""
    return "table" if is_tty() else "json"


def format_output(
    data: Any,
    success: bool = True,
    format_type: Union[str, OutputFormat] = OutputFormat.JSON,
    error_message: Optional[str] = None,
    error_code: Optional[Union[str, ErrorCode]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """
    格式化输出 - 统一响应格式

    Args:
        data: 输出数据
        success: 是否成功
        format_type: 输出格式 (json/yaml/table/human)
        error_message: 错误消息（可选，默认使用错误码对应的消息）
        error_code: 错误代码（建议使用 ErrorCode 枚举）
        meta: 额外元数据（如分页信息、请求ID等）

    Returns:
        格式化后的字符串
    """
    # 标准化格式类型
    fmt = format_type.value if isinstance(format_type, OutputFormat) else format_type

    # 构建基础响应
    if success:
        result: Dict[str, Any] = {
            "success": True,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if meta:
            result["meta"] = meta
    else:
        # 标准化错误码
        code_enum = error_code if isinstance(error_code, ErrorCode) else ErrorCode(error_code or "UNKNOWN_ERROR")
        code = code_enum.value
        # 使用自定义消息或默认消息
        message = error_message or ERROR_MESSAGES.get(code_enum, "Unknown error")
        suggestion = ERROR_SUGGESTIONS.get(code_enum, "")

        result = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "suggestion": suggestion,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if meta:
            result["meta"] = meta

    # 根据格式类型输出
    if fmt == OutputFormat.JSON:
        return json.dumps(result, indent=2, ensure_ascii=False)
    elif fmt == OutputFormat.YAML:
        if YAML_AVAILABLE:
            return yaml.dump(result, allow_unicode=True, default_flow_style=False)
        else:
            return json.dumps(result, indent=2, ensure_ascii=False)
    elif fmt == OutputFormat.TABLE:
        return _format_table(data)
    elif fmt == OutputFormat.HUMAN:
        return _format_human_readable(result, success)
    else:
        return json.dumps(result, indent=2, ensure_ascii=False)


def _format_human_readable(result: Dict[str, Any], success: bool) -> str:
    """人类可读格式（简化版，适合直接查看）"""
    if success:
        data = result.get("data")
        if data is None:
            return "✓ 操作成功"
        elif isinstance(data, list):
            if not data:
                return "（无数据）"
            return _format_table(data)
        elif isinstance(data, dict):
            return _format_dict_simple(data)
        else:
            return str(data)
    else:
        error = result.get("error", {})
        code = error.get("code", "UNKNOWN_ERROR")
        message = error.get("message", "Unknown error")
        suggestion = error.get("suggestion", "")
        if suggestion:
            return f"✗ [{code}] {message}\n  建议: {suggestion}"
        return f"✗ [{code}] {message}"


def _format_dict_simple(data: Dict[str, Any], indent: int = 0) -> str:
    """简单字典格式化"""
    lines = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_format_dict_simple(value, indent + 1))
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                lines.append(f"{prefix}{key}:")
                lines.append(_format_table(value))
            else:
                lines.append(f"{prefix}{key}: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


def _format_table(data: Any) -> str:
    """格式化为表格"""
    if isinstance(data, list) and len(data) > 0:
        return _list_to_table(data)
    elif isinstance(data, dict):
        return _dict_to_table(data)
    else:
        return str(data)


def _list_to_table(data: List[Dict]) -> str:
    """列表转表格"""
    if not data:
        return "（无数据）"

    # 获取所有列
    columns = set()
    for item in data:
        if isinstance(item, dict):
            columns.update(item.keys())
    columns = sorted(columns)

    if not columns:
        return str(data)

    # 计算列宽
    col_widths = {}
    for col in columns:
        col_widths[col] = len(col)

    for item in data:
        if isinstance(item, dict):
            for col in columns:
                val = str(item.get(col, ""))
                col_widths[col] = max(col_widths[col], len(val))

    # 生成表格
    lines = []
    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    lines.append(header)
    lines.append("-" * len(header))

    for item in data:
        row = []
        for col in columns:
            val = str(item.get(col, ""))
            row.append(val.ljust(col_widths[col]))
        lines.append(" | ".join(row))

    return "\n".join(lines)


def _dict_to_table(data: Dict) -> str:
    """字典转表格"""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    lines.append(f"  [{i}] {item}")
                else:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


# =============================================================================
# 便捷输出函数
# =============================================================================

def print_success(
    data: Any,
    format_type: Union[str, OutputFormat] = OutputFormat.JSON,
    meta: Optional[Dict[str, Any]] = None
) -> None:
    """打印成功输出到stdout"""
    output = format_output(data, success=True, format_type=format_type, meta=meta)
    print(output)


def print_error(
    message: Optional[str] = None,
    code: Union[str, ErrorCode] = ErrorCode.UNKNOWN_ERROR,
    format_type: Union[str, OutputFormat] = OutputFormat.JSON,
    meta: Optional[Dict[str, Any]] = None
) -> None:
    """
    打印错误输出到stderr

    符合CLI设计规范:
    - 错误输出到stderr，便于管道处理
    - 包含错误码、消息和建议
    """
    # 如果没有提供消息，使用错误码对应的标准消息
    if message is None:
        code_enum = code if isinstance(code, ErrorCode) else ErrorCode(code)
        message = ERROR_MESSAGES.get(code_enum, "Unknown error")

    output = format_output(
        None, success=False, format_type=format_type,
        error_message=message, error_code=code, meta=meta
    )
    print(output, file=sys.stderr)


# =============================================================================
# 进度显示
# =============================================================================

class ProgressReporter:
    """
    进度报告器 - 用于长时间操作的进度显示

    自动检测TTY环境，非TTY环境下静默运行
    """

    def __init__(
        self,
        label: str,
        indeterminate: bool = True,
        total: Optional[int] = None,
        enabled: Optional[bool] = None,
        stream: Optional[Any] = sys.stderr
    ):
        self.label = label
        self.indeterminate = indeterminate
        self.total = total
        # 如果未指定enabled，自动检测TTY
        if enabled is None:
            enabled = is_tty(stream)
        self.enabled = enabled and stream is not None
        self.stream = stream
        self._completed = 0
        self._percent = 0
        self._started = False
        self._spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx = 0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.done()
        return False

    def start(self) -> None:
        """开始显示进度"""
        if not self.enabled or self._started:
            return
        self._started = True
        self._render()

    def _clear_line(self) -> None:
        """清除当前行"""
        if self.enabled:
            self.stream.write("\r\033[K")
            self.stream.flush()

    def _render(self) -> None:
        """渲染进度"""
        if not self.enabled:
            return
        self._clear_line()
        if self.indeterminate:
            char = self._spinner_chars[self._spinner_idx % len(self._spinner_chars)]
            self._spinner_idx += 1
            self.stream.write(f"{char} {self.label}")
        else:
            suffix = f" {self._percent:.0f}%"
            self.stream.write(f"{self.label}{suffix}")
        self.stream.flush()

    def set_label(self, label: str) -> None:
        """更新进度标签"""
        self.label = label
        self._render()

    def set_percent(self, percent: float) -> None:
        """更新进度百分比"""
        self._percent = max(0, min(100, percent))
        self.indeterminate = False
        self._render()

    def tick(self, delta: int = 1) -> None:
        """增加进度"""
        if self.total:
            self._completed = min(self.total, self._completed + delta)
            self.set_percent((self._completed / self.total) * 100)

    def done(self) -> None:
        """完成进度显示"""
        if not self.enabled or not self._started:
            return
        self._clear_line()
        self._started = False


def with_progress(
    label: str,
    work,
    indeterminate: bool = True,
    total: Optional[int] = None,
    enabled: Optional[bool] = None
):
    """
    带进度显示的执行函数

    Args:
        label: 进度标签
        work: 工作函数，接收 progress 参数
        indeterminate: 是否不确定进度（旋转指示器）
        total: 总步数（确定进度时）
        enabled: 是否启用进度显示（None则自动检测TTY）
    """
    with ProgressReporter(label, indeterminate=indeterminate, total=total, enabled=enabled) as progress:
        return work(progress)
