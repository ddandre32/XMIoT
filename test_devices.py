# -*- coding: utf-8 -*-
"""
小米IoT交互式设备控制器
支持：设备列表查看、设备控制、属性读取、动作执行

使用说明：
1. 运行程序
2. 访问生成的OAuth URL并授权
3. 复制授权码(code)输入到程序
4. 使用交互式菜单控制设备

特殊指令：
- 在任意输入界面输入 'esc' 或 'exit' 或 'quit' 可安全退出程序
- 在设备控制界面输入 'back' 可返回设备列表
"""
import asyncio
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

from miot_sdk import MIoTClient, MIoTDeviceInfo
from miot_sdk.types import MIoTSpecDeviceLite
from miot_sdk.const import OAUTH2_REDIRECT_URI_DEFAULT


class XiaomiInteractiveController:
    """小米设备交互式控制器"""

    # 退出指令列表
    EXIT_COMMANDS = {'esc', 'exit', 'quit', 'q'}
    # 返回上级指令
    BACK_COMMAND = 'back'
    # 刷新指令
    REFRESH_COMMAND = 'refresh'

    def __init__(self):
        self.client: Optional[MIoTClient] = None
        self.devices: Dict[str, MIoTDeviceInfo] = {}
        self.running = True

    def print_header(self, title: str):
        """打印标题头"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)

    def print_sub_header(self, title: str):
        """打印子标题"""
        print("\n" + "-" * 60)
        print(f"  {title}")
        print("-" * 60)

    def check_exit(self, user_input: str) -> bool:
        """检查用户是否想退出"""
        return user_input.strip().lower() in self.EXIT_COMMANDS

    async def safe_input(self, prompt: str) -> Optional[str]:
        """
        安全获取用户输入，支持退出指令
        返回 None 表示用户想退出
        """
        try:
            user_input = input(prompt).strip()
            if self.check_exit(user_input):
                self.running = False
                return None
            return user_input
        except (EOFError, KeyboardInterrupt):
            self.running = False
            return None

    async def setup(self):
        """初始化客户端"""
        self.print_header("小米IoT交互式设备控制器")
        print("\n提示：在任意输入界面输入 'esc' 或 'exit' 可安全退出程序\n")

        # 创建客户端
        self.client = MIoTClient(
            uuid=uuid.uuid4().hex,
            redirect_uri=OAUTH2_REDIRECT_URI_DEFAULT,
            cache_path="./test_cache",
            cloud_server="cn",
        )

        # 初始化
        await self.client.init()
        print("✅ 客户端初始化成功\n")

    async def authenticate(self) -> bool:
        """用户认证流程"""
        # 生成OAuth URL
        oauth_url = self.client.gen_oauth_url()
        print("📱 请按以下步骤进行授权：")
        print("1. 复制以下链接到浏览器打开：")
        print(f"   {oauth_url}")
        print()
        print("2. 登录你的小米账号并授权")
        print("3. 授权后会跳转到回调地址，从URL中获取 'code' 参数")
        print()

        # 获取用户输入的授权码
        code = await self.safe_input("请输入授权码(code): ")

        if code is None:
            return False

        if not code:
            print("❌ 未提供授权码")
            return False

        try:
            # 获取access_token
            oauth_info = await self.client.get_access_token(code)
            print(f"✅ 授权成功！")
            print(f"   用户: {oauth_info.user_info.nickname if oauth_info.user_info else 'N/A'}")
            print(f"   Token: {oauth_info.access_token[:20]}...")
            print()
            return True
        except Exception as e:
            print(f"❌ 授权失败: {e}")
            return False

    async def discover_devices(self) -> bool:
        """发现设备"""
        print("🔍 正在发现设备...")

        try:
            self.devices = await self.client.get_devices()
            print(f"✅ 发现 {len(self.devices)} 个设备\n")
            return True
        except Exception as e:
            print(f"❌ 发现设备失败: {e}")
            return False

    def get_controllable_devices(self) -> List[Tuple[str, MIoTDeviceInfo]]:
        """获取所有可控设备（在线设备）"""
        controllable = []
        for did, device in self.devices.items():
            # 只显示在线设备
            if device.online:
                controllable.append((did, device))
        return controllable

    def get_device_icon(self, model: str) -> str:
        """根据设备型号获取图标"""
        model = model.lower()
        if any(kw in model for kw in ['lamp', 'light', 'bulb', '台灯', '灯']):
            return '💡'
        elif any(kw in model for kw in ['speaker', 'audio', '音箱', '音响']):
            return '🔊'
        elif any(kw in model for kw in ['camera', 'cam', '摄像头', '相机']):
            return '📷'
        elif any(kw in model for kw in ['fan', '风扇']):
            return '🌀'
        elif any(kw in model for kw in ['ac', 'air', '空调']):
            return '❄️'
        elif any(kw in model for kw in ['purifier', '净化器']):
            return '🌿'
        elif any(kw in model for kw in ['switch', '插座', '插排']):
            return '🔌'
        elif any(kw in model for kw in ['sensor', '传感器']):
            return '📡'
        elif any(kw in model for kw in ['lock', '锁']):
            return '🔒'
        else:
            return '📱'

    async def show_device_list(self) -> Optional[str]:
        """
        显示设备列表并让用户选择
        返回选择的设备did，None表示退出
        """
        while self.running:
            self.print_header("可控设备列表")

            controllable = self.get_controllable_devices()

            if not controllable:
                print("\n⚠️ 没有在线的可控设备")
                print("\n选项：")
                print("  [refresh] 刷新设备列表")
                print("  [esc/exit] 退出程序")

                choice = await self.safe_input("\n请输入选项: ")
                if choice is None:
                    return None
                if choice.lower() == self.REFRESH_COMMAND:
                    await self.discover_devices()
                    continue
                continue

            print(f"\n找到 {len(controllable)} 个在线设备：\n")

            for idx, (did, device) in enumerate(controllable, 1):
                icon = self.get_device_icon(device.model)
                status = "🟢" if device.online else "🔴"
                room = f" [{device.room_name}]" if device.room_name else ""
                print(f"  [{idx}] {icon} {device.name}{room}")
                print(f"      型号: {device.model}")
                print(f"      状态: {status} {'在线' if device.online else '离线'}")
                if device.local_ip:
                    print(f"      IP: {device.local_ip}")
                print()

            print("选项：")
            print(f"  [1-{len(controllable)}] 选择设备")
            print("  [refresh] 刷新设备列表")
            print("  [esc/exit] 退出程序")

            choice = await self.safe_input("\n请输入选项: ")
            if choice is None:
                return None

            if choice.lower() == self.REFRESH_COMMAND:
                await self.discover_devices()
                continue

            # 尝试解析为设备索引
            try:
                idx = int(choice)
                if 1 <= idx <= len(controllable):
                    return controllable[idx - 1][0]
                else:
                    print(f"❌ 请输入 1-{len(controllable)} 之间的数字")
                    await asyncio.sleep(1)
            except ValueError:
                print("❌ 无效的输入")
                await asyncio.sleep(1)

        return None

    async def get_device_spec(self, device: MIoTDeviceInfo) -> Optional[Dict[str, MIoTSpecDeviceLite]]:
        """获取设备SPEC"""
        try:
            print(f"  正在获取SPEC，URN: {device.urn}")
            spec = await self.client.get_device_spec_lite(device.urn)
            if spec is None:
                print(f"  ⚠️ SPEC返回None")
                return None
            print(f"  ✅ 获取到 {len(spec)} 个功能点")
            # 打印前3个功能点的key用于调试
            for i, k in enumerate(list(spec.keys())[:3]):
                print(f"     示例[{i}]: {k}")
            return spec
        except Exception as e:
            print(f"❌ 获取设备SPEC失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def format_control_instruction(self, iid: str, item: MIoTSpecDeviceLite) -> str:
        """格式化控制指令说明"""
        parts = iid.split(".")
        if len(parts) != 4:
            return ""

        # IID格式: prop.0.{siid}.{piid} 或 action.0.{siid}.{aiid}
        item_type = parts[0]  # prop 或 action
        siid = parts[2]
        piid = parts[3]

        instructions = []

        if item_type == "prop":
            # 属性控制
            if item.readable:
                instructions.append(f"读取: get {siid} {piid}")
            if item.writeable:
                # 根据数据格式给出示例
                if item.format == "bool":
                    example_value = "true/false 或 1/0"
                elif item.format in ["uint8", "uint16", "uint32", "int", "float"]:
                    if item.value_range:
                        example_value = f"数值 ({item.value_range.min_}-{item.value_range.max_})"
                    else:
                        example_value = "数值"
                elif item.value_list:
                    values = ", ".join([f"{v.value}={v.description}" for v in item.value_list[:3]])
                    example_value = f"枚举值 ({values}...)"
                else:
                    example_value = "值"
                instructions.append(f"设置: set {siid} {piid} <{example_value}>")

        elif item_type == "action":
            # 动作执行
            instructions.append(f"执行: action {siid} {piid}")

        return "  指令: " + " | ".join(instructions) if instructions else ""

    async def show_device_controls(self, did: str) -> bool:
        """
        显示设备的控制功能列表
        返回True表示返回上级，False表示退出程序
        """
        device = self.devices.get(did)
        if not device:
            print("❌ 设备不存在")
            return True

        # 获取设备SPEC
        spec = await self.get_device_spec(device)
        if not spec:
            print("⚠️ 无法获取设备SPEC，将返回设备列表")
            await asyncio.sleep(2)
            return True

        # 筛选可控制的功能点（可读写属性或可执行动作）
        controllable_items = {}
        for iid, item in spec.items():
            parts = iid.split(".")
            if len(parts) != 4:
                print(f"  ⚠️ 跳过无效IID格式: {iid}")
                continue
            # IID格式: prop.0.{siid}.{piid} 或 action.0.{siid}.{aiid}
            item_type = parts[0]  # prop 或 action

            # 包含可读写的属性和动作
            if item_type == "prop" and (item.readable or item.writeable):
                controllable_items[iid] = item
            elif item_type == "action":
                controllable_items[iid] = item

        while self.running:
            self.print_header(f"设备控制: {device.name}")
            print(f"型号: {device.model}")
            print(f"状态: {'🟢 在线' if device.online else '🔴 离线'}")
            print(f"DID: {did}")
            print()

            if not controllable_items:
                print("⚠️ 该设备没有可控制的功能点")
                print("\n按 Enter 返回设备列表...")
                await self.safe_input("")
                return True

            print(f"发现 {len(controllable_items)} 个可控制功能点：\n")

            # 分类显示：先显示属性，再显示动作
            props = {k: v for k, v in controllable_items.items() if k.startswith("prop.")}
            actions = {k: v for k, v in controllable_items.items() if k.startswith("action.")}

            idx_map = {}
            current_idx = 1

            if props:
                print("【属性控制】\n")
                for iid, item in sorted(props.items()):
                    parts = iid.split(".")
                    # IID格式: prop.0.{siid}.{piid}
                    siid = parts[2]
                    piid = parts[3]

                    access = []
                    if item.readable:
                        access.append("读")
                    if item.writeable:
                        access.append("写")

                    print(f"  [{current_idx}] {item.description}")
                    print(f"      IID: prop.{siid}.{piid}")
                    print(f"      格式: {item.format}")
                    print(f"      权限: {'/'.join(access)}")

                    # 显示值范围或选项
                    if item.value_range:
                        print(f"      范围: {item.value_range.min_} ~ {item.value_range.max_} {item.unit or ''}")
                    elif item.value_list:
                        values = ", ".join([f"{v.value}={v.description}" for v in item.value_list[:5]])
                        print(f"      选项: {values}")

                    # 显示控制指令
                    instruction = self.format_control_instruction(iid, item)
                    if instruction:
                        print(f"{instruction}")

                    idx_map[current_idx] = (iid, item, "prop")
                    current_idx += 1
                    print()

            if actions:
                print("【动作执行】\n")
                for iid, item in sorted(actions.items()):
                    parts = iid.split(".")
                    # IID格式: action.0.{siid}.{aiid}
                    siid = parts[2]
                    aiid = parts[3]

                    print(f"  [{current_idx}] {item.description}")
                    print(f"      IID: action.{siid}.{aiid}")
                    instruction = self.format_control_instruction(iid, item)
                    if instruction:
                        print(f"{instruction}")

                    idx_map[current_idx] = (iid, item, "action")
                    current_idx += 1
                    print()

            print("控制指令格式：")
            print("  - 读取属性: get <siid> <piid>")
            print("  - 设置属性: set <siid> <piid> <value>")
            print("  - 执行动作: action <siid> <aiid>")
            print()
            print("选项：")
            print(f"  [1-{len(idx_map)}] 选择功能点（自动检测并执行读写）")
            print("  [get/set/action] 直接输入控制指令")
            print("  [back] 返回设备列表")
            print("  [refresh] 刷新当前状态")
            print("  [esc/exit] 退出程序")

            choice = await self.safe_input("\n请输入选项: ")
            if choice is None:
                return False

            if choice.lower() == self.BACK_COMMAND:
                return True

            if choice.lower() == self.REFRESH_COMMAND:
                # 刷新设备状态
                await self.discover_devices()
                device = self.devices.get(did)
                continue

            # 解析直接控制指令
            if choice.lower().startswith("get "):
                await self.handle_get_command(device, choice[4:].strip())
                await asyncio.sleep(1)
                continue

            if choice.lower().startswith("set "):
                await self.handle_set_command(device, choice[4:].strip())
                await asyncio.sleep(1)
                continue

            if choice.lower().startswith("action "):
                await self.handle_action_command(device, choice[7:].strip())
                await asyncio.sleep(1)
                continue

            # 尝试解析为功能点索引
            try:
                idx = int(choice)
                if idx in idx_map:
                    iid, item, item_type = idx_map[idx]
                    await self.control_item(device, iid, item, item_type)
                    await asyncio.sleep(1)
                else:
                    print(f"❌ 请输入 1-{len(idx_map)} 之间的数字")
                    await asyncio.sleep(1)
            except ValueError:
                print("❌ 无效的输入")
                await asyncio.sleep(1)

        return False

    async def handle_get_command(self, device: MIoTDeviceInfo, params: str):
        """处理get指令"""
        parts = params.split()
        if len(parts) != 2:
            print("❌ 格式错误。正确格式: get <siid> <piid>")
            return

        try:
            siid = int(parts[0])
            piid = int(parts[1])
        except ValueError:
            print("❌ siid 和 piid 必须是数字")
            return

        try:
            print(f"📊 正在读取属性 (siid={siid}, piid={piid})...")
            value = await self.client.get_prop(device.did, siid, piid)
            print(f"✅ 读取成功: {value}")
        except Exception as e:
            print(f"❌ 读取失败: {e}")

    async def handle_set_command(self, device: MIoTDeviceInfo, params: str):
        """处理set指令"""
        parts = params.split()
        if len(parts) < 3:
            print("❌ 格式错误。正确格式: set <siid> <piid> <value>")
            return

        try:
            siid = int(parts[0])
            piid = int(parts[1])
            # 支持空格的值（如字符串）
            value_str = " ".join(parts[2:])
        except ValueError:
            print("❌ siid 和 piid 必须是数字")
            return

        # 尝试解析值类型
        value = self.parse_value(value_str)

        try:
            print(f"💡 正在设置属性 (siid={siid}, piid={piid}, value={value})...")
            result = await self.client.set_prop(device.did, siid, piid, value)
            print(f"✅ 设置成功: {result}")
        except Exception as e:
            print(f"❌ 设置失败: {e}")

    async def handle_action_command(self, device: MIoTDeviceInfo, params: str):
        """处理action指令"""
        parts = params.split()
        if len(parts) < 2:
            print("❌ 格式错误。正确格式: action <siid> <aiid>")
            return

        try:
            siid = int(parts[0])
            aiid = int(parts[1])
        except ValueError:
            print("❌ siid 和 aiid 必须是数字")
            return

        # 可选的输入参数
        in_list = []
        if len(parts) > 2:
            in_list = [self.parse_value(" ".join(parts[2:]))]

        try:
            print(f"▶️ 正在执行动作 (siid={siid}, aiid={aiid})...")
            result = await self.client.action(device.did, siid, aiid, in_list)
            print(f"✅ 执行成功: {result}")
        except Exception as e:
            print(f"❌ 执行失败: {e}")

    def parse_value(self, value_str: str) -> Any:
        """解析值字符串为合适的类型"""
        value_str = value_str.strip()

        # 布尔值
        if value_str.lower() in ('true', 'on', 'yes', '开', '1'):
            return True
        if value_str.lower() in ('false', 'off', 'no', '关', '0'):
            return False

        # 尝试整数
        try:
            return int(value_str)
        except ValueError:
            pass

        # 尝试浮点数
        try:
            return float(value_str)
        except ValueError:
            pass

        # 字符串（去掉引号）
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        return value_str

    async def control_item(self, device: MIoTDeviceInfo, iid: str, item: MIoTSpecDeviceLite, item_type: str):
        """控制单个功能点"""
        parts = iid.split(".")
        # IID格式: prop.0.{siid}.{piid} 或 action.0.{siid}.{aiid}
        siid = int(parts[2])
        piid = int(parts[3])

        if item_type == "prop":
            # 属性控制
            if item.readable:
                # 先读取当前值
                try:
                    print(f"📊 正在读取 {item.description}...")
                    value = await self.client.get_prop(device.did, siid, piid)
                    print(f"✅ 当前值: {value}")
                except Exception as e:
                    print(f"❌ 读取失败: {e}")

            if item.writeable:
                # 询问新值
                prompt = f"请输入新的 {item.description} 值"
                if item.value_range:
                    prompt += f" ({item.value_range.min_}-{item.value_range.max_})"
                elif item.value_list:
                    values = ", ".join([f"{v.value}={v.description}" for v in item.value_list])
                    prompt += f" [{values}]"
                prompt += " (直接回车跳过): "

                new_value = await self.safe_input(prompt)
                if new_value is None:
                    return

                if new_value:
                    value = self.parse_value(new_value)
                    try:
                        print(f"💡 正在设置 {item.description} = {value}...")
                        result = await self.client.set_prop(device.did, siid, piid, value)
                        print(f"✅ 设置成功: {result}")
                    except Exception as e:
                        print(f"❌ 设置失败: {e}")

        elif item_type == "action":
            # 动作执行
            try:
                print(f"▶️ 正在执行 {item.description}...")
                result = await self.client.action(device.did, siid, piid, [])
                print(f"✅ 执行成功: {result}")
            except Exception as e:
                print(f"❌ 执行失败: {e}")

    async def run(self):
        """运行主循环"""
        try:
            # 初始化
            await self.setup()

            # 认证
            if not await self.authenticate():
                return

            # 发现设备
            if not await self.discover_devices():
                return

            # 主交互循环
            while self.running:
                # 显示设备列表并选择
                did = await self.show_device_list()

                if not did:
                    break

                # 显示设备控制界面
                should_continue = await self.show_device_controls(did)

                if not should_continue:
                    break

        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        if self.client:
            await self.client.deinit()
            print("\n✅ 客户端已安全关闭")
        print("👋 感谢使用小米IoT交互式控制器！")


def main():
    """主函数"""
    controller = XiaomiInteractiveController()

    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断程序")
        print("👋 感谢使用！")
        sys.exit(0)


if __name__ == "__main__":
    main()
