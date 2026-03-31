#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI使用示例 - 展示如何使用miot命令行工具
"""
import subprocess
import json
import sys


def run_cmd(cmd):
    """运行命令并返回结果"""
    print(f"\n$ {' '.join(cmd)}")
    print("-" * 60)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    return result


def main():
    """CLI示例"""
    print("=" * 60)
    print("小米IoT CLI工具使用示例")
    print("=" * 60)

    # 1. 查看系统状态
    print("\n【1】查看系统状态")
    run_cmd(["python", "-m", "cli.main", "system", "status"])

    # 2. 获取OAuth URL (未认证时)
    print("\n【2】获取OAuth授权URL")
    result = run_cmd(["python", "-m", "cli.main", "system", "oauth-url"])

    # 3. 列出设备 (需要已认证)
    print("\n【3】列出所有设备")
    run_cmd(["python", "-m", "cli.main", "device", "list", "--format", "table"])

    # 4. 仅列出在线设备
    print("\n【4】列出在线设备")
    run_cmd(["python", "-m", "cli.main", "device", "list", "--online"])

    # 5. 获取设备详情示例
    print("\n【5】获取设备详情 (需要替换为实际did)")
    print("miot device get <did>")

    # 6. 控制设备示例
    print("\n【6】控制设备 (需要替换为实际did)")
    print("miot device prop set <did> 2 1 true   # 开灯")
    print("miot device prop set <did> 2 1 false  # 关灯")
    print("miot device prop set <did> 2 2 80     # 设置亮度80%")

    # 7. 场景操作
    print("\n【7】场景管理")
    run_cmd(["python", "-m", "cli.main", "scene", "list", "--format", "table"])

    print("\n【8】发送通知")
    print("miot system notify '测试消息'")

    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
