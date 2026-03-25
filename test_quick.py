# -*- coding: utf-8 -*-
"""
快速测试程序 - 验证XMIoT项目基础功能

使用方法:
1. python test_quick.py
2. 按提示访问OAuth URL并授权
3. 输入授权码
4. 查看测试结果
"""
import asyncio
import uuid

from miot_sdk import MIoTClient
from miot_sdk.const import OAUTH2_REDIRECT_URI_DEFAULT


async def quick_test():
    """快速测试"""
    print("=" * 50)
    print("XMIoT 快速测试")
    print("=" * 50)

    # 1. 初始化客户端
    print("\n1. 初始化客户端...")
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri=OAUTH2_REDIRECT_URI_DEFAULT,  # 使用官方允许的回调地址
        cache_path="./test_cache",
        cloud_server="cn",
    )
    await client.init()
    print("✅ 客户端初始化成功")

    # 2. OAuth授权
    print("\n2. OAuth授权")
    print("-" * 50)
    oauth_url = client.gen_oauth_url()
    print(f"请访问以下URL并授权：")
    print(f"{oauth_url}")
    print()
    code = input("请输入授权码: ").strip()

    if not code:
        print("❌ 未输入授权码")
        return

    print("正在获取token...")
    oauth_info = await client.get_access_token(code)
    print(f"✅ 授权成功！Token: {oauth_info.access_token[:20]}...")

    # 3. 获取用户信息
    print("\n3. 获取用户信息...")
    user_info = await client.get_user_info()
    print(f"✅ 用户: {user_info.nickname}")
    print(f"   UID: {user_info.uid}")

    # 4. 获取设备列表
    print("\n4. 发现设备...")
    devices = await client.get_devices()
    print(f"✅ 发现 {len(devices)} 个设备\n")

    # 显示设备
    for did, device in devices.items():
        status = "🟢在线" if device.online else "🔴离线"
        print(f"  {device.name}")
        print(f"    ID: {did}")
        print(f"    型号: {device.model}")
        print(f"    状态: {status}")

        # 识别设备类型
        model = device.model.lower()
        if any(kw in model for kw in ['lamp', 'light', '台灯']):
            print(f"    💡 类型: 台灯")
        elif any(kw in model for kw in ['speaker', '音箱']):
            print(f"    🔊 类型: 音箱")
        elif any(kw in model for kw in ['camera', '摄像头']):
            print(f"    📷 类型: 摄像头")
        print()

    # 5. 测试第一个设备
    if devices:
        first_device = list(devices.values())[0]
        print(f"\n5. 测试设备: {first_device.name}")
        print("-" * 50)

        # 获取SPEC
        print("获取设备SPEC...")
        spec = await client.get_device_spec_lite(first_device.urn)
        print(f"✅ 找到 {len(spec)} 个功能点\n")

        # 显示可读写属性
        for iid, item in list(spec.items())[:5]:
            access = []
            if item.readable:
                access.append("读")
            if item.writeable:
                access.append("写")
            print(f"  {item.description}")
            print(f"    IID: {iid}")
            print(f"    格式: {item.format}")
            print(f"    权限: {'/'.join(access)}")
            print()

        # 尝试读取一个属性
        prop_item = None
        for iid, item in spec.items():
            if item.readable and "prop" in iid:
                prop_item = item
                break

        if prop_item:
            parts = iid.split(".")
            if len(parts) == 4:
                _, _, siid, piid = parts
                print(f"读取属性 {prop_item.description}...")
                try:
                    value = await client.get_prop(
                        first_device.did, int(siid), int(piid)
                    )
                    print(f"✅ 值: {value}")
                except Exception as e:
                    print(f"❌ 读取失败: {e}")

    # 6. 获取场景
    print("\n6. 获取场景列表...")
    scenes = await client.get_manual_scenes()
    print(f"✅ 发现 {len(scenes)} 个场景")
    for scene_id, scene in scenes.items():
        print(f"  - {scene.scene_name}")

    # 清理
    await client.deinit()
    print("\n✅ 测试完成")


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except KeyboardInterrupt:
        print("\n\n测试已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
