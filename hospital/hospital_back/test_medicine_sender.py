"""
测试药品坐标发送到 ROS WebSocket
参考 his_sub_forever.py 脚本格式

测试场景：一个药单包含2个药品

正确逻辑：
- medicine_total: 药品总数（一个处方共包含几个药品）
- medicine_index: 当前药品序号（从1开始，表示当前发送的是第几个药品）

新增字段：
- yaw: 药品yaw值（和xyz类型一样）
"""
import websocket
import json
import time

# ROS WebSocket 地址
ROS_WS_URL = "ws://192.168.51.12:9090"
ROS_TOPIC = "/his_sub"

print("=" * 60)
print("测试药品坐标发送")
print("=" * 60)
print("测试场景：一个药单包含2个药品")
print("处方编码: 012026070600125")
print("药品总数: medicine_total = 2")
print("=" * 60)

# 连接 WebSocket
print(f"正在连接: {ROS_WS_URL}")
ws = websocket.create_connection(ROS_WS_URL)
print("连接成功")

# 1. 先清除旧的Topic注册
ws.send(json.dumps({
    "op": "unadvertise",
    "topic": ROS_TOPIC
}))
time.sleep(0.5)
print("已清除旧Topic注册")

# 2. 注册 topic（注意类型必须完全一致）
ws.send(json.dumps({
    "op": "advertise",
    "topic": ROS_TOPIC,
    "type": "his_sub/HisSub"
}))
time.sleep(1)
print(f"已注册 topic: {ROS_TOPIC} (类型: his_sub/HisSub)")

# 定义药单信息
prescription_code = "012026070600132"
medicine_total = 2  # 药单共包含2个药品

# 定义2个药品（包含yaw字段）
medicines = [
    {
        "medicine_id": 11,
        "medicine_name": "去疼片",
        "x": 10.5,
        "y": 20.3,
        "z": 5.0,
        "yaw": 1.0
    },
    {
        "medicine_id": 12,
        "medicine_name": "阿莫西林",
        "x": 15.0,
        "y": 25.0,
        "z": 8.0,
        "yaw": 2.0
    }
]

print("\n" + "=" * 60)
print(f"药单: {prescription_code}")
print(f"药品总数: {medicine_total}")
print("=" * 60)
for i, med in enumerate(medicines, start=1):
    print(f"药品{i}: ID={med['medicine_id']}, 名称={med['medicine_name']}, xyz=({med['x']}, {med['y']}, {med['z']}), yaw={med['yaw']}")
print("=" * 60)

# 逐个药品发送
for medicine_index, medicine in enumerate(medicines, start=1):
    print(f"\n{'='*40}")
    print(f"发送药品 {medicine_index}/{medicine_total}")
    print(f"药品ID: {medicine['medicine_id']}")
    print(f"药品名称: {medicine['medicine_name']}")
    print(f"坐标: x={medicine['x']}, y={medicine['y']}, z={medicine['z']}")
    print(f"{'='*40}")
    
    # 每个药品发送2次start
    for send_count in range(2):
        msg = {
            "data": "start",
            "prescription_code": prescription_code,
            "medicine_id": medicine["medicine_id"],
            "x": medicine["x"],
            "y": medicine["y"],
            "z": medicine["z"],
            "yaw": medicine["yaw"],
            "medicine_total": medicine_total,      # 药单共包含2个药品（固定值）
            "medicine_index": medicine_index        # 当前发送的是第几个药品（1或2）
        }
        
        print(f"\n第 {send_count+1} 次发送药品{medicine_index}:")
        print("发送内容:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))
        print(f"  yaw: {msg['yaw']}")
        
        ws.send(json.dumps({
            "op": "publish",
            "topic": ROS_TOPIC,
            "msg": msg
        }))
        
        print("发送成功!")
        time.sleep(2)

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("总结：")
print(f"  药单编码: {prescription_code}")
print(f"  药品总数: medicine_total = {medicine_total}")
print(f"  发送顺序: medicine_index依次为1, 2")
print("=" * 60)

# 关闭连接
ws.close()
print("连接已关闭")