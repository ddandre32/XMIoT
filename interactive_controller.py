# -*- coding: utf-8 -*-
"""
交互式小米设备控制器

使用方法:
1. python3 interactive_controller.py
2. 按提示授权登录
3. 输入指令控制设备

支持的指令:
- list: 列出所有设备
- spec <设备ID>: 查看设备功能
- on <设备ID>: 打开设备
- off <设备ID>: 关闭设备
- get <设备ID> <属性IID>: 读取属性
- set <设备ID> <属性IID> <值>: 设置属性
- action <设备ID> <动作IID>: 执行动作
- scenes: 列出场景
- run <场景ID>: 执行场景
- help: 显示帮助
- quit: 退出
"""
import asyncio
import sys
import uuid
from typing import Any, Dict, List, Optional

from miot_sdk import MIoTClient
from miot_sdk.types import (
    MIoTDeviceInfo,
    MIoTSpecDeviceLite,
    MIoTManualSceneInfo,
)
from miot_sdk.const import OAUTH2_REDIRECT_URI_DEFAULT


class InteractiveController:
    """交互式设备控制器"""

    def __init__(self):
        self.client: Optional[MIoTClient] = None
        self.devices: Dict[str, MIoTDeviceInfo] = {}
        self.specs: Dict[str, Dict[str, MIoTSpecDeviceLite]] = {}
        self.scenes: Dict[str, MIoTManualSceneInfo] = {}

    async def setup(self):
        """初始化"""
        print("=" * 60)
        print("🎛️  小米智能设备交互控制器")
        print("=" * 60)
        print()

        # 创建客户端
        self.client = MIoTClient(
            uuid=uuid.uuid4().hex,
            redirect_uri=OAUTH2_REDIRECT_URI_DEFAULT,
            cache_path="./controller_cache",
            cloud_server="cn",
        )
        await self.client.init()
        print("✅ 控制器初始化成功\n")

    async def authenticate(self) -> bool:
        """认证"""
        print("🔐 OAuth 授权")
        print("-" * 60)
        url = self.client.gen_oauth_url()
        print(f"请访问以下链接并授权：\n{url}\n")
        code = input("请输入授权码: ").strip()

        if not code:
            print("❌ 未输入授权码")
            return False

        try:
            await self.client.get_access_token(code)
            user_info = await self.client.get_user_info()
            print(f"✅ 授权成功！欢迎，{user_info.nickname}\n")
            return True
        except Exception as e:
            print(f"❌ 授权失败: {e}\n")
            return False

    async def refresh_devices(self):
        """刷新设备列表"""
        print("🔄 正在刷新设备列表...")
        self.devices = await self.client.get_devices()
        self.scenes = await self.client.get_manual_scenes()
        print(f"✅ 发现 {len(self.devices)} 个设备，{len(self.scenes)} 个场景\n")

    def print_device_list(self):
        """打印设备列表"""
        if not self.devices:
            print("❌ 暂无设备\n")
            return

        print("\n📱 设备列表:")
        print("-" * 60)
        print(f"{'序号':<6}{'设备名称':<20}{'设备ID':<15}{'型号':<25}{'状态'}")
        print("-" * 60)

        for idx, (did, device) in enumerate(self.devices.items(), 1):
            status = "🟢" if device.online else "🔴"
            model_short = device.model[:24] if len(device.model) > 24 else device.model
            name_short = device.name[:18] if len(device.name) > 18 else device.name
            did_short = did[:13] if len(did) > 13 else did
            print(f"{idx:<6}{name_short:<20}{did_short:<15}{model_short:<25}{status}")
        print()

    def print_help(self):
        """打印帮助信息"""
        print("\n📖 可用指令:")
        print("-" * 60)
        print("  list                    - 列出所有设备")
        print("  spec <设备ID/序号>      - 查看设备功能和属性")
        print("  on <设备ID/序号>        - 打开设备（自动查找开关）")
        print("  off <设备ID/序号>       - 关闭设备（自动查找开关）")
        print("  toggle <设备ID/序号>    - 切换设备开关状态")
        print("  get <设备ID/序号> <IID> - 读取设备属性值")
        print("  set <设备ID/序号> <IID> <值> - 设置设备属性值")
        print("  action <设备ID/序号> <动作IID> - 执行设备动作")
        print("  scenes                  - 列出所有场景")
        print("  run <场景ID>            - 执行场景")
        print("  refresh                 - 刷新设备列表")
        print("  help                    - 显示本帮助")
        print("  quit/exit               - 退出程序")
        print("-" * 60)
        print("\n💡 提示:")
        print("  - 设备ID可以使用完整ID，也可以使用列表中的序号(1, 2, 3...)")
        print("  - IID格式: prop.0.siid.piid (如: prop.0.2.1)")
        print("  - 布尔值: true/false, 1/0")
        print("  - 数值: 直接输入数字 (如: 50, 100)")
        print()

    async def get_device_by_id(self, device_id: str) -> Optional[MIoTDeviceInfo]:
        """通过ID或序号获取设备"""
        # 尝试作为序号解析
        try:
            idx = int(device_id) - 1
            devices_list = list(self.devices.items())
            if 0 <= idx < len(devices_list):
                return devices_list[idx][1]
        except ValueError:
            pass

        # 作为完整ID查找
        if device_id in self.devices:
            return self.devices[device_id]

        return None

    async def get_or_load_spec(self, device: MIoTDeviceInfo) -> Optional[Dict[str, MIoTSpecDeviceLite]]:
        """获取或加载设备SPEC"""
        if device.did in self.specs:
            return self.specs[device.did]

        print(f"🔄 正在获取 {device.name} 的SPEC...")
        spec = await self.client.get_device_spec_lite(device.urn)
        if spec:
            self.specs[device.did] = spec
        return spec

    def print_spec(self, device: MIoTDeviceInfo, spec: Dict[str, MIoTSpecDeviceLite]):
        """打印设备SPEC"""
        print(f"\n📋 设备 [{device.name}] 的功能列表:")
        print("-" * 60)

        # 分类显示
        properties = []
        actions = []

        for iid, item in spec.items():
            if iid.startswith("prop"):
                properties.append((iid, item))
            elif iid.startswith("action"):
                actions.append((iid, item))

        if properties:
            print(f"\n🔧 可控制属性 ({len(properties)}个):")
            print(f"{'IID':<25}{'描述':<30}{'格式':<10}{'权限'}")
            print("-" * 60)
            for iid, item in properties:
                access = []
                if item.readable:
                    access.append("读")
                if item.writeable:
                    access.append("写")
                access_str = "/".join(access) if access else "-"
                desc = item.description[:28] if len(item.description) > 28 else item.description
                print(f"{iid:<25}{desc:<30}{item.format:<10}{access_str}")

        if actions:
            print(f"\n⚡ 可执行动作 ({len(actions)}个):")
            print(f"{'IID':<25}{'描述':<30}{'输入参数'}")
            print("-" * 60)
            for iid, item in actions:
                desc = item.description[:28] if len(item.description) > 28 else item.description
                print(f"{iid:<25}{desc:<30}{item.format}")
        print()

    async def find_switch_property(self, device: MIoTDeviceInfo, spec: Dict[str, MIoTSpecDeviceLite]) -> Optional[tuple]:
        """查找开关属性"""
        for iid, item in spec.items():
            if not iid.startswith("prop"):
                continue
            desc = item.description.lower()
            # 查找开关属性
            if any(kw in desc for kw in ['开关', 'switch', '电源', 'power', '状态', 'status']):
                if item.writeable and item.format == "bool":
                    parts = iid.split(".")
                    if len(parts) == 4:
                        return (int(parts[2]), int(parts[3]))
        return None

    async def control_switch(self, device: MIoTDeviceInfo, turn_on: bool):
        """控制设备开关"""
        spec = await self.get_or_load_spec(device)
        if not spec:
            print(f"❌ 无法获取 {device.name} 的SPEC\n")
            return

        switch = await self.find_switch_property(device, spec)
        if not switch:
            print(f"❌ 未在 {device.name} 上找到开关属性\n")
            return

        siid, piid = switch
        try:
            value = turn_on
            print(f"🔄 正在{'打开' if turn_on else '关闭'} {device.name}...")
            result = await self.client.set_prop(device.did, siid, piid, value)
            if result.get("code") == 0:
                print(f"✅ {'已打开' if turn_on else '已关闭'} {device.name}\n")
            else:
                print(f"⚠️  操作结果: {result}\n")
        except Exception as e:
            print(f"❌ 控制失败: {e}\n")

    async def toggle_device(self, device: MIoTDeviceInfo):
        """切换设备状态"""
        spec = await self.get_or_load_spec(device)
        if not spec:
            print(f"❌ 无法获取 {device.name} 的SPEC\n")
            return

        switch = await self.find_switch_property(device, spec)
        if not switch:
            print(f"❌ 未找到开关属性\n")
            return

        siid, piid = switch
        try:
            # 读取当前状态
            current = await self.client.get_prop(device.did, siid, piid)
            new_state = not bool(current)
            await self.control_switch(device, new_state)
        except Exception as e:
            print(f"❌ 切换失败: {e}\n")

    async def get_property(self, device: MIoTDeviceInfo, iid: str):
        """读取属性"""
        parts = iid.split(".")
        if len(parts) != 4:
            print("❌ IID格式错误，应为: prop.0.siid.piid\n")
            return

        try:
            _, _, siid, piid = parts
            print(f"🔄 读取 {device.name} 的属性...")
            value = await self.client.get_prop(device.did, int(siid), int(piid))
            print(f"✅ 当前值: {value}\n")
        except Exception as e:
            print(f"❌ 读取失败: {e}\n")

    async def set_property(self, device: MIoTDeviceInfo, iid: str, value_str: str):
        """设置属性"""
        parts = iid.split(".")
        if len(parts) != 4:
            print("❌ IID格式错误\n")
            return

        # 解析值
        value = self.parse_value(value_str)

        try:
            _, _, siid, piid = parts
            print(f"🔄 设置 {device.name} 的属性为 {value}...")
            result = await self.client.set_prop(device.did, int(siid), int(piid), value)
            if result.get("code") == 0:
                print(f"✅ 设置成功\n")
            else:
                print(f"⚠️  结果: {result}\n")
        except Exception as e:
            print(f"❌ 设置失败: {e}\n")

    def parse_value(self, value_str: str) -> Any:
        """解析值"""
        value_str = value_str.strip().lower()

        # 布尔值
        if value_str in ['true', 'yes', 'on', '1']:
            return True
        if value_str in ['false', 'no', 'off', '0']:
            return False

        # 整数
        try:
            return int(value_str)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(value_str)
        except ValueError:
            pass

        # 字符串（去除引号）
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]

        return value_str

    async def execute_action(self, device: MIoTDeviceInfo, action_iid: str):
        """执行动作"""
        parts = action_iid.split(".")
        if len(parts) != 4:
            print("❌ 动作IID格式错误，应为: action.0.siid.aiid\n")
            return

        try:
            _, _, siid, aiid = parts
            print(f"🔄 执行 {device.name} 的动作...")
            result = await self.client.action(device.did, int(siid), int(aiid), [])
            if result.get("code") == 0:
                print(f"✅ 执行成功\n")
            else:
                print(f"⚠️  结果: {result}\n")
        except Exception as e:
            print(f"❌ 执行失败: {e}\n")

    def print_scenes(self):
        """打印场景列表"""
        if not self.scenes:
            print("❌ 暂无场景\n")
            return

        print("\n🎬 场景列表:")
        print("-" * 60)
        print(f"{'场景ID':<20}{'场景名称':<30}{'状态'}")
        print("-" * 60)
        for scene_id, scene in self.scenes.items():
            status = "✅" if scene.enable else "❌"
            name = scene.scene_name[:28] if len(scene.scene_name) > 28 else scene.scene_name
            print(f"{scene_id:<20}{name:<30}{status}")
        print()

    async def run_scene(self, scene_id: str):
        """执行场景"""
        if scene_id not in self.scenes:
            print(f"❌ 场景 {scene_id} 不存在\n")
            return

        scene = self.scenes[scene_id]
        print(f"🎬 正在执行场景: {scene.scene_name}...")
        try:
            result = await self.client.run_manual_scene(scene)
            print(f"✅ 场景执行{'成功' if result else '失败'}\n")
        except Exception as e:
            print(f"❌ 执行失败: {e}\n")

    async def handle_command(self, cmd: str):
        """处理指令"""
        parts = cmd.strip().split()
        if not parts:
            return

        action = parts[0].lower()
        args = parts[1:]

        if action == "help":
            self.print_help()

        elif action == "list":
            self.print_device_list()

        elif action == "refresh":
            await self.refresh_devices()

        elif action == "spec":
            if len(args) < 1:
                print("❌ 用法: spec <设备ID/序号>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            spec = await self.get_or_load_spec(device)
            if spec:
                self.print_spec(device, spec)

        elif action == "on":
            if len(args) < 1:
                print("❌ 用法: on <设备ID/序号>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            await self.control_switch(device, True)

        elif action == "off":
            if len(args) < 1:
                print("❌ 用法: off <设备ID/序号>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            await self.control_switch(device, False)

        elif action == "toggle":
            if len(args) < 1:
                print("❌ 用法: toggle <设备ID/序号>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            await self.toggle_device(device)

        elif action == "get":
            if len(args) < 2:
                print("❌ 用法: get <设备ID/序号> <IID>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            await self.get_property(device, args[1])

        elif action == "set":
            if len(args) < 3:
                print("❌ 用法: set <设备ID/序号> <IID> <值>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            await self.set_property(device, args[1], args[2])

        elif action == "action":
            if len(args) < 2:
                print("❌ 用法: action <设备ID/序号> <动作IID>\n")
                return
            device = await self.get_device_by_id(args[0])
            if not device:
                print(f"❌ 设备 {args[0]} 不存在\n")
                return
            await self.execute_action(device, args[1])

        elif action == "scenes":
            self.print_scenes()

        elif action == "run":
            if len(args) < 1:
                print("❌ 用法: run <场景ID>\n")
                return
            await self.run_scene(args[0])

        elif action in ["quit", "exit", "q"]:
            print("👋 再见！")
            return False

        else:
            print(f"❌ 未知指令: {action}")
            print("   输入 'help' 查看可用指令\n")

        return True

    async def run(self):
        """运行交互式控制器"""
        await self.setup()

        if not await self.authenticate():
            return

        await self.refresh_devices()
        self.print_device_list()
        self.print_help()

        while True:
            try:
                cmd = input("🎮 请输入指令: ").strip()
                if not cmd:
                    continue

                result = await self.handle_command(cmd)
                if result is False:
                    break

            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")

        await self.client.deinit()


async def main():
    """主函数"""
    controller = InteractiveController()
    await controller.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
