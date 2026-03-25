# -*- coding: utf-8 -*-
"""
小米IoT管理器使用示例

注意：本项目使用小米官方OAuth配置，无需注册开发者账号
"""
import asyncio
import uuid
from miot_sdk import MIoTClient
from core import DeviceManager, SceneManager, NotificationService


async def basic_example():
    """基础使用示例 - 使用小米官方内置配置"""
    # 创建客户端（使用小米官方内置OAuth配置，无需开发者注册）
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri="http://localhost:8000/callback",
        cache_path="./cache",
        cloud_server="cn",
    )

    # 初始化
    await client.init()

    # 获取OAuth授权URL（用户需要访问此URL登录小米账号并授权）
    oauth_url = client.gen_oauth_url()
    print(f"请访问以下链接进行授权：\n{oauth_url}")
    print("授权后获得code，用于获取access_token")

    # 获取设备列表
    devices = await client.get_devices()
    print(f"\n发现 {len(devices)} 个设备：")
    for did, device in devices.items():
        print(f"  - {device.name} ({device.model}): {'在线' if device.online else '离线'}")

    # 获取设备SPEC
    if devices:
        first_device = list(devices.values())[0]
        spec = await client.get_device_spec_lite(first_device.urn)
        print(f"\n设备 {first_device.name} 的SPEC：")
        for iid, item in spec.items():
            print(f"  - {iid}: {item.description}")

    # 执行设备控制（示例：假设是灯设备）
    # await client.set_prop(did, siid=2, piid=1, value=True)  # 开灯

    # 获取场景列表
    scenes = await client.get_manual_scenes()
    print(f"\n发现 {len(scenes)} 个场景：")
    for scene_id, scene in scenes.items():
        print(f"  - {scene.scene_name}")

    # 执行场景
    # for scene_id in scenes:
    #     await client.run_manual_scene_by_id(scene_id)
    #     break

    # 发送通知
    await client.send_app_notify_once("测试通知")

    # 反初始化
    await client.deinit()


async def device_manager_example():
    """设备管理服务示例"""
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri="http://localhost:8000/callback",
        cache_path="./cache",
    )
    await client.init()

    # 创建设备管理器
    manager = DeviceManager(client)

    # 刷新设备
    devices = await manager.refresh_devices()
    print(f"管理 {len(devices)} 个设备")

    # 按房间筛选
    living_room_devices = manager.get_devices_by_room("room_id_here")
    print(f"客厅有 {len(living_room_devices)} 个设备")

    # 获取在线设备
    online_devices = manager.get_online_devices()
    print(f"在线设备: {len(online_devices)}")

    # 批量控制
    operations = [
        {"type": "set_prop", "did": "device_1", "siid": 2, "piid": 1, "value": True},
        {"type": "set_prop", "did": "device_2", "siid": 2, "piid": 1, "value": False},
    ]
    results = await manager.batch_control(operations)
    for result in results:
        print(f"设备 {result.did}: {'成功' if result.success else '失败'}")

    await client.deinit()


async def scene_manager_example():
    """场景管理示例"""
    client = MIoTClient(
        uuid=uuid.uuid4().hex,
        redirect_uri="http://localhost:8000/callback",
        cache_path="./cache",
    )
    await client.init()

    # 创建场景管理器
    manager = SceneManager(client)

    # 刷新场景
    scenes = await manager.refresh_scenes()
    print(f"管理 {len(scenes)} 个场景")

    # 搜索场景
    sleep_scenes = manager.search_scenes("睡眠")
    print(f"找到 {len(sleep_scenes)} 个睡眠相关场景")

    # 执行场景
    if scenes:
        result = await manager.execute_scene(list(scenes.keys())[0])
        print(f"场景执行结果: {result}")

    await client.deinit()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(basic_example())
