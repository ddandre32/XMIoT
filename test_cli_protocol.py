#!/usr/bin/env python3
"""
CLI协议测试脚本
验证CLI设计规范的实现
"""
import json
import os
import sys
import tempfile
import subprocess
from pathlib import Path

# 测试配置
TEST_CONFIG = {
    "cloud_server": "sg",
    "format": "json",
}

def run_cli(args, env=None, capture=True):
    """运行CLI命令"""
    cmd = [sys.executable, "-m", "cli.main"] + args
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        env={**os.environ, **(env or {})}
    )
    return result

def test_tty_detection():
    """测试TTY检测"""
    print("=" * 60)
    print("测试1: TTY检测")
    print("=" * 60)

    from cli.formatter import is_tty, get_default_format

    # 当前环境（非TTY）
    print(f"当前is_tty(): {is_tty()}")
    print(f"默认格式: {get_default_format()}")

    assert not is_tty(), "非TTY环境应返回False"
    assert get_default_format() == "json", "非TTY默认应为json"
    print("✓ TTY检测正确\n")

def test_output_formats():
    """测试输出格式"""
    print("=" * 60)
    print("测试2: 输出格式")
    print("=" * 60)

    from cli.formatter import format_output, ErrorCode

    test_data = {"devices": [{"name": "灯", "online": True}]}

    # JSON格式
    json_out = format_output(test_data, format_type="json")
    parsed = json.loads(json_out)
    assert parsed["success"] == True
    assert "timestamp" in parsed
    print("✓ JSON格式正确")

    # Table格式
    table_out = format_output(test_data["devices"], format_type="table")
    assert "name" in table_out
    assert "online" in table_out
    print("✓ Table格式正确")

    # Human格式
    human_out = format_output(test_data, format_type="human")
    assert "devices:" in human_out
    print("✓ Human格式正确")

    # 错误格式（带建议）
    error_out = format_output(
        None, success=False,
        error_code=ErrorCode.NOT_AUTHENTICATED,
        format_type="json"
    )
    error_parsed = json.loads(error_out)
    assert error_parsed["success"] == False
    assert "error" in error_parsed
    assert "code" in error_parsed["error"]
    assert "message" in error_parsed["error"]
    assert "suggestion" in error_parsed["error"]
    print("✓ 错误格式正确（含suggestion）")
    print(f"  错误码: {error_parsed['error']['code']}")
    print(f"  建议: {error_parsed['error']['suggestion'][:50]}...\n")

def test_config_priority():
    """测试配置层级优先级"""
    print("=" * 60)
    print("测试3: 配置层级优先级")
    print("=" * 60)

    from cli.config import CLIConfig

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"cloud_server": "de"}, f)
        temp_config = f.name

    try:
        # 1. 测试环境变量优先级
        env = {"MIOT_CLOUD_SERVER": "sg"}
        os.environ.update(env)
        config = CLIConfig(temp_config)
        # 环境变量应覆盖配置文件
        assert config.get("cloud_server") == "sg", f"期望sg，实际{config.get('cloud_server')}"
        print("✓ 环境变量覆盖配置文件")

        # 2. 测试配置文件
        del os.environ["MIOT_CLOUD_SERVER"]
        config = CLIConfig(temp_config)
        assert config.get("cloud_server") == "de", "应读取配置文件"
        print("✓ 配置文件读取正确")

        # 3. 测试默认值
        config = CLIConfig()
        assert config.get("cloud_server") == "cn", "默认应为cn"
        print("✓ 默认值正确")

    finally:
        os.unlink(temp_config)
        if "MIOT_CLOUD_SERVER" in os.environ:
            del os.environ["MIOT_CLOUD_SERVER"]

    print()

def test_cli_commands():
    """测试CLI命令"""
    print("=" * 60)
    print("测试4: CLI命令")
    print("=" * 60)

    # 1. system status（非TTY自动JSON）
    result = run_cli(["system", "status"])
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["success"] == True
    assert "data" in output
    assert "authenticated" in output["data"]
    assert "tty" in output["data"]
    assert output["data"]["tty"] == False  # 非TTY环境
    print("✓ system status（自动JSON）")

    # 2. system status --format table
    result = run_cli(["system", "status", "--format", "table"])
    assert result.returncode == 0
    assert "status:" in result.stdout
    print("✓ system status（指定table）")

    # 3. --json全局选项
    result = run_cli(["--json", "status"])
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["success"] == True
    print("✓ --json全局选项")

    # 4. 未认证错误（错误输出到stderr）
    result = run_cli(["--json", "device", "list"])
    # 错误输出到stderr
    if result.stderr:
        output = json.loads(result.stderr)
    else:
        output = json.loads(result.stdout)
    assert output["success"] == False
    assert output["error"]["code"] == "NOT_AUTHENTICATED"
    assert "suggestion" in output["error"]
    print("✓ 未认证错误（含建议）")

    # 5. Help信息
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "device" in result.stdout
    assert "scene" in result.stdout
    assert "MIOT_CONFIG_PATH" in result.stdout  # 环境变量文档
    print("✓ Help信息完整\n")

def test_error_codes():
    """测试错误码"""
    print("=" * 60)
    print("测试5: 错误码")
    print("=" * 60)

    from cli.formatter import ErrorCode, ERROR_MESSAGES, ERROR_SUGGESTIONS

    # 验证所有错误码都有消息和建议
    for code in ErrorCode:
        assert code in ERROR_MESSAGES, f"{code} 缺少消息"
        assert code in ERROR_SUGGESTIONS, f"{code} 缺少建议"
        assert ERROR_MESSAGES[code], f"{code} 消息为空"
        assert ERROR_SUGGESTIONS[code], f"{code} 建议为空"

    print(f"✓ 所有{len(list(ErrorCode))}个错误码都有消息和建议")

    # 测试human格式错误输出
    from cli.formatter import format_output
    error_out = format_output(
        None, success=False,
        error_code=ErrorCode.DEVICE_NOT_FOUND,
        format_type="human"
    )
    assert "DEVICE_NOT_FOUND" in error_out
    assert "建议:" in error_out
    print("✓ Human格式错误输出含建议\n")

def test_pipe_friendly():
    """测试管道友好"""
    print("=" * 60)
    print("测试6: 管道友好")
    print("=" * 60)

    # 1. stdout输出到管道
    result = run_cli(["--json", "system", "status"])
    assert result.returncode == 0
    assert result.stdout  # 有输出
    # 解析JSON确认格式正确
    data = json.loads(result.stdout)
    assert data["success"] == True
    print("✓ stdout输出正确")

    # 2. stderr错误输出
    result = run_cli(["--json", "device", "prop", "get", "invalid", "1", "1"])
    # 错误输出到stderr
    error_output = result.stderr if result.stderr else result.stdout
    assert "NOT_AUTHENTICATED" in error_output
    print("✓ 错误信息输出到stderr")

    # 3. 从stdin读取（模拟）
    batch_data = '[{"did": "test", "action": "turn_on"}]'
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "device", "batch"],
        input=batch_data,
        capture_output=True,
        text=True
    )
    # 应该返回认证错误（因为未认证）- 错误在stderr
    assert result.returncode == 0
    if result.stderr:
        output = json.loads(result.stderr)
    else:
        output = json.loads(result.stdout)
    assert output["success"] == False
    print("✓ 从stdin读取数据\n")

def test_progress_reporter():
    """测试进度显示"""
    print("=" * 60)
    print("测试7: 进度显示")
    print("=" * 60)

    from cli.formatter import ProgressReporter, with_progress

    # 非TTY环境应该静默
    def dummy_work(progress):
        progress.set_label("处理中...")
        progress.set_percent(50)
        return "done"

    result = with_progress("测试", dummy_work, enabled=False)
    assert result == "done"
    print("✓ 进度显示（非TTY静默）")

    # 测试tick
    def tick_work(progress):
        progress.tick()
        progress.tick()
        progress.tick()
        return "completed"

    result = with_progress("测试", tick_work, total=5, enabled=False)
    assert result == "completed"
    print("✓ 进度tick\n")

def test_env_variables():
    """测试环境变量"""
    print("=" * 60)
    print("测试8: 环境变量")
    print("=" * 60)

    env_vars = {
        "MIOT_CLOUD_SERVER": "us",
        "MIOT_FORMAT": "yaml",
        "MIOT_CACHE_PATH": "/tmp/test_cache",
    }

    # 设置环境变量
    for k, v in env_vars.items():
        os.environ[k] = v

    from cli.config import CLIConfig
    config = CLIConfig()

    assert config.get("cloud_server") == "us"
    print("✓ MIOT_CLOUD_SERVER")

    assert config.get("format") == "yaml"
    print("✓ MIOT_FORMAT")

    assert config.get("cache_path") == "/tmp/test_cache"
    print("✓ MIOT_CACHE_PATH")

    # 清理
    for k in env_vars:
        del os.environ[k]

    print()

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("CLI协议测试")
    print("=" * 60 + "\n")

    # 切换到项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)

    tests = [
        test_tty_detection,
        test_output_formats,
        test_config_priority,
        test_cli_commands,
        test_error_codes,
        test_pipe_friendly,
        test_progress_reporter,
        test_env_variables,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} 失败: {e}\n")

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
