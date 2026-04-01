#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XMIoT 全接口权限测试程序

测试所有对外API接口，检查是否需要开发者权限

用法:
    python test_all_apis.py                    # 交互模式
    python test_all_apis.py --code <auth_code> # 直接传入授权码
"""

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# 添加项目路径
sys.path.insert(0, '/Users/user2/Documents/code/ClaudeCode/XMIoT/xiaomi_iot_manager')

from miot_sdk import MIoTClient
from miot_sdk.types import (
    MIoTGetPropertyParam,
    MIoTSetPropertyParam,
    MIoTActionParam,
    MIoTOauthInfo,
)
from miot_sdk.error import MIoTError, MIoTOAuth2Error, MIoTHttpError


class APITester:
    """API测试器"""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.client: Optional[MIoTClient] = None
        self.test_results: List[Dict] = []
        self.oauth_code: Optional[str] = args.code
        self.access_token: Optional[str] = args.token
        self.devices: Dict = {}
        self.scenes: Dict = {}
        self.homes: Dict = {}
        # 使用固定UUID或从命令行传入
        self.uuid: str = args.uuid or "99072b52d3454281b98f0de082595e2b"

    def log(self, message: str, level: str = "INFO"):
        """打印日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def record_result(self, api_name: str, success: bool, error: Optional[str] = None, details: Optional[Dict] = None):
        """记录测试结果"""
        result = {
            "api_name": api_name,
            "success": success,
            "error": error,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅ 成功" if success else "❌ 失败"
        self.log(f"{api_name}: {status}")
        if error:
            self.log(f"  错误: {error}", "ERROR")
        if details:
            self.log(f"  详情: {json.dumps(details, ensure_ascii=False, default=str)[:200]}")

    async def test_oauth_url_generation(self) -> bool:
        """测试1: OAuth URL生成（无需认证）"""
        try:
            self.client = MIoTClient(
                uuid=self.uuid,  # 使用固定UUID
                redirect_uri="http://127.0.0.1:8000/callback",
                cache_path="./test_cache",
                cloud_server="cn",
            )
            await self.client.init()

            url = self.client.gen_oauth_url()
            await self.record_result(
                "gen_oauth_url",
                True,
                details={"url": url[:100] + "..."}
            )
            return True
        except Exception as e:
            await self.record_result("gen_oauth_url", False, str(e))
            return False

    async def test_get_access_token(self) -> bool:
        """测试2: 获取Access Token（需要授权码）"""
        if self.access_token:
            self.log("使用传入的access_token跳过OAuth认证")
            self.client.set_oauth_info(MIoTOauthInfo(
                access_token=self.access_token,
                refresh_token="",
                expires_ts=0
            ))
            await self.record_result(
                "set_oauth_info",
                True,
                details={"token_prefix": self.access_token[:20] + "..."}
            )
            return True

        if not self.oauth_code:
            self.log("\n请先在浏览器中完成授权：")
            url = self.client.gen_oauth_url()
            print(f"\n授权URL: {url}\n")

            if self.args.non_interactive:
                self.log("非交互模式，跳过需要授权的测试")
                return False

            try:
                self.oauth_code = input("请输入授权码(code): ").strip()
            except EOFError:
                self.log("无法读取输入，请使用 --code 参数传入授权码")
                return False

        try:
            oauth_info = await self.client.get_access_token(self.oauth_code)
            await self.record_result(
                "get_access_token",
                True,
                details={
                    "access_token": oauth_info.access_token[:20] + "...",
                    "refresh_token": oauth_info.refresh_token[:20] + "..." if oauth_info.refresh_token else None,
                    "expires_ts": oauth_info.expires_ts,
                }
            )
            return True
        except MIoTOAuth2Error as e:
            error_msg = str(e)
            await self.record_result("get_access_token", False, f"OAuth错误: {error_msg}")
            # 检查是否是权限问题
            if "96008" in error_msg or "passport" in error_msg.lower():
                self.log("⚠️ 检测到可能的权限问题（错误码96008）", "WARNING")
            return False
        except Exception as e:
            await self.record_result("get_access_token", False, str(e))
            return False

    async def test_refresh_token(self) -> bool:
        """测试3: 刷新Access Token"""
        try:
            oauth_info = await self.client.refresh_access_token()
            await self.record_result(
                "refresh_access_token",
                True,
                details={"new_token_prefix": oauth_info.access_token[:20] + "..."}
            )
            return True
        except Exception as e:
            await self.record_result("refresh_access_token", False, str(e))
            return False

    async def test_get_user_info(self) -> bool:
        """测试4: 获取用户信息"""
        try:
            user_info = await self.client.get_user_info()
            await self.record_result(
                "get_user_info",
                True,
                details={
                    "uid": user_info.uid,
                    "nickname": user_info.nickname,
                }
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_user_info", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_user_info", False, str(e))
            return False

    async def test_get_homes(self) -> bool:
        """测试5: 获取家庭列表"""
        try:
            homes = await self.client.get_homes()
            self.homes = homes
            await self.record_result(
                "get_homes",
                True,
                details={"home_count": len(homes)}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_homes", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_homes", False, str(e))
            return False

    async def test_get_devices(self) -> bool:
        """测试6: 获取设备列表"""
        try:
            devices = await self.client.get_devices()
            self.devices = devices
            await self.record_result(
                "get_devices",
                True,
                details={"device_count": len(devices)}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_devices", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_devices", False, str(e))
            return False

    async def test_get_device(self) -> bool:
        """测试7: 获取单个设备"""
        if not self.devices:
            await self.record_result("get_device", False, "没有可用设备")
            return False

        try:
            did = list(self.devices.keys())[0]
            device = await self.client.get_device(did)
            await self.record_result(
                "get_device",
                True,
                details={"did": did, "name": device.name if device else None}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_device", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_device", False, str(e))
            return False

    async def test_get_device_spec(self) -> bool:
        """测试8: 获取设备SPEC"""
        if not self.devices:
            await self.record_result("get_device_spec", False, "没有可用设备")
            return False

        try:
            device = list(self.devices.values())[0]
            spec = await self.client.get_device_spec_lite(device.urn)
            await self.record_result(
                "get_device_spec_lite",
                True,
                details={"urn": device.urn, "spec_count": len(spec) if spec else 0}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_device_spec_lite", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_device_spec_lite", False, str(e))
            return False

    async def test_get_property(self) -> bool:
        """测试9: 获取设备属性"""
        if not self.devices:
            await self.record_result("get_prop", False, "没有可用设备")
            return False

        try:
            device = list(self.devices.values())[0]
            # 尝试获取常见的属性（siid=2, piid=1 通常是开关）
            value = await self.client.get_prop(device.did, 2, 1)
            await self.record_result(
                "get_prop",
                True,
                details={"did": device.did, "value": value}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_prop", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_prop", False, str(e))
            return False

    async def test_set_property(self) -> bool:
        """测试10: 设置设备属性（谨慎测试，只读）"""
        await self.record_result(
            "set_prop",
            False,
            "跳过（避免修改设备状态）",
            {"note": "为避免影响设备，跳过写入测试"}
        )
        return False

    async def test_execute_action(self) -> bool:
        """测试11: 执行设备动作（谨慎测试，只读）"""
        await self.record_result(
            "action",
            False,
            "跳过（避免修改设备状态）",
            {"note": "为避免影响设备，跳过动作执行测试"}
        )
        return False

    async def test_get_manual_scenes(self) -> bool:
        """测试12: 获取手动场景"""
        try:
            scenes = await self.client.get_manual_scenes()
            self.scenes = scenes
            await self.record_result(
                "get_manual_scenes",
                True,
                details={"scene_count": len(scenes)}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("get_manual_scenes", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("get_manual_scenes", False, str(e))
            return False

    async def test_run_manual_scene(self) -> bool:
        """测试13: 执行手动场景（谨慎测试，只读）"""
        await self.record_result(
            "run_manual_scene",
            False,
            "跳过（避免触发场景）",
            {"note": "为避免触发场景动作，跳过执行测试"}
        )
        return False

    async def test_create_app_notify(self) -> bool:
        """测试14: 创建应用通知"""
        try:
            notify_id = await self.client.create_app_notify("XMIoT API测试通知")
            await self.record_result(
                "create_app_notify",
                True,
                details={"notify_id": notify_id}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("create_app_notify", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("create_app_notify", False, str(e))
            return False

    async def test_send_app_notify(self) -> bool:
        """测试15: 发送应用通知（完整流程）"""
        try:
            result = await self.client.send_app_notify_once("XMIoT API测试 - 完整通知流程")
            await self.record_result(
                "send_app_notify_once",
                True,
                details={"result": result}
            )
            return True
        except MIoTHttpError as e:
            await self.record_result("send_app_notify_once", False, f"HTTP错误: {e}")
            return False
        except Exception as e:
            await self.record_result("send_app_notify_once", False, str(e))
            return False

    async def test_ping_lan_devices(self) -> bool:
        """测试16: 探测局域网设备"""
        try:
            await self.client.ping_lan_devices()
            await self.record_result("ping_lan_devices", True)
            return True
        except Exception as e:
            await self.record_result("ping_lan_devices", False, str(e))
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        self.log("=" * 60)
        self.log("开始 XMIoT 全接口权限测试")
        self.log("=" * 60)

        # 阶段1: 无需认证的测试
        self.log("\n【阶段1】无需认证的接口")
        await self.test_oauth_url_generation()

        # 阶段2: 需要授权的测试
        self.log("\n【阶段2】OAuth认证相关")
        if await self.test_get_access_token():
            await self.test_refresh_token()

            # 阶段3: 用户信息
            self.log("\n【阶段3】用户信息接口")
            await self.test_get_user_info()

            # 阶段4: 家庭/设备管理
            self.log("\n【阶段4】家庭/设备管理接口")
            await self.test_get_homes()
            await self.test_get_devices()
            await self.test_get_device()
            await self.test_get_device_spec()

            # 阶段5: 设备控制
            self.log("\n【阶段5】设备控制接口")
            await self.test_get_property()
            await self.test_set_property()
            await self.test_execute_action()

            # 阶段6: 场景管理
            self.log("\n【阶段6】场景管理接口")
            await self.test_get_manual_scenes()
            await self.test_run_manual_scene()

            # 阶段7: 通知
            self.log("\n【阶段7】通知接口")
            await self.test_create_app_notify()
            await self.test_send_app_notify()

            # 阶段8: 局域网
            self.log("\n【阶段8】局域网接口")
            await self.test_ping_lan_devices()

        # 清理
        if self.client:
            await self.client.deinit()

        # 输出测试报告
        await self.print_report()

    async def print_report(self):
        """打印测试报告"""
        self.log("\n" + "=" * 60)
        self.log("测试报告")
        self.log("=" * 60)

        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r["success"])
        failed = total - success

        print(f"\n总计: {total} 个接口")
        print(f"✅ 成功: {success} 个")
        print(f"❌ 失败: {failed} 个")
        print(f"成功率: {success/total*100:.1f}%" if total > 0 else "N/A")

        # 失败的接口
        failed_apis = [r for r in self.test_results if not r["success"]]
        if failed_apis:
            print("\n【失败的接口】")
            for r in failed_apis:
                print(f"  - {r['api_name']}: {r['error']}")

        # 权限相关错误
        permission_errors = [r for r in self.test_results
                            if r["error"] and ("unauthorized" in r["error"].lower()
                                              or "permission" in r["error"].lower()
                                              or "code:9" in r["error"]
                                              or "96008" in r["error"]
                                              or "401" in r["error"])]
        if permission_errors:
            print("\n【疑似权限问题的接口】")
            for r in permission_errors:
                print(f"  - {r['api_name']}: {r['error']}")

        # 保存详细报告
        report_file = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "success": success,
                    "failed": failed,
                    "success_rate": success/total if total > 0 else 0,
                },
                "results": self.test_results,
            }, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n详细报告已保存: {report_file}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="XMIoT API权限测试")
    parser.add_argument("--code", help="OAuth授权码")
    parser.add_argument("--token", help="已有access_token")
    parser.add_argument("--uuid", help="固定UUID（用于匹配授权时的device_id）")
    parser.add_argument("--non-interactive", action="store_true", help="非交互模式")
    args = parser.parse_args()

    tester = APITester(args)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
