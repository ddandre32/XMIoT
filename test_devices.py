# -*- coding: utf-8 -*-
"""
小米IoT设备测试程序
测试设备：台灯、音箱、摄像头

使用说明：
1. 运行程序
2. 访问生成的OAuth URL并授权
3. 复制授权码(code)输入到程序
4. 程序会自动发现设备并测试控制
"""
import asyncio
import sys
import uuid
from typing import Optional

from miot_sdk import MIoTClient, MIoTDeviceInfo
from miot_sdk.types import MIoTSpecDeviceLite
from miot_sdk.const import OAUTH2_REDIRECT_URI_DEFAULT


class XiaomiDeviceTester:
    """小米设备测试器"""

    def __init__(self):
        self.client: Optional[MIoTClient] = None
        self.devices: dict[str, MIoTDeviceInfo] = {}
        self.lamp: Optional[MIoTDeviceInfo] = None
        self.speaker: Optional[MIoTDeviceInfo] = None
        self.camera: Optional[MIoTDeviceInfo] = None

    async def setup(self):
        """初始化客户端"""
        print("=" * 60)
        print("小米IoT设备测试程序")
        print("=" * 60)
        print()

        # 创建客户端
        self.client = MIoTClient(
            uuid=uuid.uuid4().hex,
            redirect_uri=OAUTH2_REDIRECT_URI_DEFAULT,  # 使用官方允许的回调地址
            cache_path="./test_cache",
            cloud_server="cn",
        )

        # 初始化
        await self.client.init()
        print("✅ 客户端初始化成功")
        print()

    async def authenticate(self):
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
        code = input("请输入授权码(code): ").strip()

        if not code:
            print("❌ 未提供授权码，退出测试")
            return False

        try:
            # 获取access_token
            oauth_info = await self.client.get_access_token(code)
            print(f"✅ 授权成功！")
            print(f"   Access Token: {oauth_info.access_token[:20]}...")
            print(f"   过期时间: {oauth_info.expires_ts}")
            print()
            return True
        except Exception as e:
            print(f"❌ 授权失败: {e}")
            return False

    async def discover_devices(self):
        """发现设备"""
        print("🔍 正在发现设备...")
        print("-" * 60)

        try:
            self.devices = await self.client.get_devices()
            print(f"✅ 发现 {len(self.devices)} 个设备\n")

            # 分类设备
            for did, device in self.devices.items():
                model = device.model.lower()
                name = device.name

                print(f"设备: {name}")
                print(f"  ID: {did}")
                print(f"  型号: {device.model}")
                print(f"  在线: {'✅' if device.online else '❌'}")
                print(f"  URN: {device.urn}")
                print()

                # 识别设备类型
                if any(kw in model for kw in ['lamp', 'light', 'bulb', '台灯', '灯']):
                    self.lamp = device
                    print(f"   💡 识别为: 台灯/灯设备\n")
                elif any(kw in model for kw in ['speaker', 'audio', '音箱', '音响']):
                    self.speaker = device
                    print(f"   🔊 识别为: 音箱设备\n")
                elif any(kw in model for kw in ['camera', 'cam', '摄像头', '相机']):
                    self.camera = device
                    print(f"   📷 识别为: 摄像头设备\n")

        except Exception as e:
            print(f"❌ 发现设备失败: {e}")
            return False

        return True

    async def get_device_spec(self, device: MIoTDeviceInfo):
        """获取设备SPEC"""
        print(f"📋 获取设备 {device.name} 的SPEC...")
        print("-" * 60)

        try:
            spec = await self.client.get_device_spec_lite(device.urn)
            if not spec:
                print("❌ 无法获取SPEC")
                return None

            print(f"✅ 获取到 {len(spec)} 个功能点\n")

            # 显示所有功能点
            for iid, item in spec.items():
                access = []
                if item.readable:
                    access.append("读")
                if item.writeable:
                    access.append("写")

                print(f"  {iid}:")
                print(f"    描述: {item.description}")
                print(f"    格式: {item.format}")
                print(f"    权限: {'/'.join(access)}")
                if item.value_range:
                    print(f"    范围: {item.value_range.min_} ~ {item.value_range.max_}")
                if item.value_list:
                    values = [f"{v.value}={v.description}" for v in item.value_list[:3]]
                    print(f"    选项: {', '.join(values)}...")
                print()

            return spec

        except Exception as e:
            print(f"❌ 获取SPEC失败: {e}")
            return None

    async def test_lamp_control(self):
        """测试台灯控制"""
        if not self.lamp:
            print("❌ 未找到台灯设备，跳过测试")
            return

        print("💡 测试台灯控制")
        print("=" * 60)

        device = self.lamp
        spec = await self.get_device_spec(device)

        if not spec:
            return

        # 查找开关属性
        switch_iid = None
        brightness_iid = None

        for iid, item in spec.items():
            desc = item.description.lower()
            if any(kw in desc for kw in ['开关', 'switch', '电源', 'power']):
                switch_iid = iid
                print(f"✅ 找到开关功能: {iid}")
            elif any(kw in desc for kw in ['亮度', 'brightness', '明暗']):
                brightness_iid = iid
                print(f"✅ 找到亮度功能: {iid}")

        # 测试读取状态
        if switch_iid:
            parts = switch_iid.split(".")
            if len(parts) == 4:
                _, _, siid, piid = parts
                try:
                    value = await self.client.get_prop(device.did, int(siid), int(piid))
                    print(f"📊 当前开关状态: {value}")
                except Exception as e:
                    print(f"❌ 读取开关状态失败: {e}")

        # 测试控制（询问用户是否执行）
        print()
        choice = input("是否测试控制台灯开关? (y/n): ").strip().lower()
        if choice == 'y' and switch_iid:
            parts = switch_iid.split(".")
            _, _, siid, piid = parts
            try:
                # 开灯
                print("💡 尝试开灯...")
                result = await self.client.set_prop(device.did, int(siid), int(piid), True)
                print(f"✅ 开灯结果: {result}")

                await asyncio.sleep(2)

                # 关灯
                print("💡 尝试关灯...")
                result = await self.client.set_prop(device.did, int(siid), int(piid), False)
                print(f"✅ 关灯结果: {result}")

            except Exception as e:
                print(f"❌ 控制台灯失败: {e}")

        print()

    async def test_speaker_control(self):
        """测试音箱控制"""
        if not self.speaker:
            print("❌ 未找到音箱设备，跳过测试")
            return

        print("🔊 测试音箱控制")
        print("=" * 60)

        device = self.speaker
        spec = await self.get_device_spec(device)

        if not spec:
            return

        # 查找音量、播放控制属性
        volume_iid = None
        play_iid = None

        for iid, item in spec.items():
            desc = item.description.lower()
            if any(kw in desc for kw in ['音量', 'volume']):
                volume_iid = iid
                print(f"✅ 找到音量功能: {iid}")
            elif any(kw in desc for kw in ['播放', 'play', '暂停', 'pause']):
                play_iid = iid
                print(f"✅ 找到播放控制: {iid}")

        # 测试读取音量
        if volume_iid:
            parts = volume_iid.split(".")
            if len(parts) == 4:
                _, _, siid, piid = parts
                try:
                    value = await self.client.get_prop(device.did, int(siid), int(piid))
                    print(f"📊 当前音量: {value}")
                except Exception as e:
                    print(f"❌ 读取音量失败: {e}")

        print()

    async def test_camera_control(self):
        """测试摄像头"""
        if not self.camera:
            print("❌ 未找到摄像头设备，跳过测试")
            return

        print("📷 测试摄像头")
        print("=" * 60)

        device = self.camera
        spec = await self.get_device_spec(device)

        if not spec:
            return

        print("ℹ️  注意：当前版本摄像头视频流功能未实现")
        print("    但可以通过SPEC查看摄像头的其他可控属性")
        print()

        # 查找常见的摄像头控制
        for iid, item in spec.items():
            desc = item.description.lower()
            if any(kw in desc for kw in ['开关', '移动侦测', '夜视', '旋转']):
                print(f"✅ 发现控制功能: {item.description} ({iid})")

        print()

    async def test_scenes(self):
        """测试场景"""
        print("🎬 测试场景功能")
        print("=" * 60)

        try:
            scenes = await self.client.get_manual_scenes()
            print(f"✅ 发现 {len(scenes)} 个手动场景\n")

            for scene_id, scene in scenes.items():
                print(f"场景: {scene.scene_name}")
                print(f"  ID: {scene_id}")
                print(f"  启用: {'✅' if scene.enable else '❌'}")
                print()

            # 询问是否执行场景
            if scenes:
                choice = input("是否执行第一个场景? (y/n): ").strip().lower()
                if choice == 'y':
                    first_scene = list(scenes.values())[0]
                    print(f"▶️  执行场景: {first_scene.scene_name}")
                    result = await self.client.run_manual_scene(first_scene)
                    print(f"✅ 执行结果: {result}\n")

        except Exception as e:
            print(f"❌ 获取场景失败: {e}")
            print()

    async def cleanup(self):
        """清理"""
        if self.client:
            await self.client.deinit()
            print("✅ 客户端已关闭")

    async def run_all_tests(self):
        """运行所有测试"""
        try:
            # 初始化
            await self.setup()

            # 认证
            if not await self.authenticate():
                return

            # 发现设备
            if not await self.discover_devices():
                return

            print("\n" + "=" * 60)
            print("开始设备控制测试")
            print("=" * 60 + "\n")

            # 测试各个设备
            await self.test_lamp_control()
            await self.test_speaker_control()
            await self.test_camera_control()

            # 测试场景
            await self.test_scenes()

            # 总结
            print("\n" + "=" * 60)
            print("测试总结")
            print("=" * 60)
            print(f"💡 台灯: {'✅ 已找到' if self.lamp else '❌ 未找到'}")
            print(f"🔊 音箱: {'✅ 已找到' if self.speaker else '❌ 未找到'}")
            print(f"📷 摄像头: {'✅ 已找到' if self.camera else '❌ 未找到'}")
            print(f"📱 总设备数: {len(self.devices)}")
            print("=" * 60)

        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断测试")
        except Exception as e:
            print(f"\n❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()


def main():
    """主函数"""
    tester = XiaomiDeviceTester()

    try:
        asyncio.run(tester.run_all_tests())
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)


if __name__ == "__main__":
    main()
