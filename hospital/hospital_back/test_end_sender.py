"""
测试药品发送逻辑（包含 end 消息）
测试新的发送流程：start → running → end（两次）

测试场景：一个处方包含2个药品

新逻辑流程：
药品1: start → start → [收到running-started] → running → [收到step5-return] → 
      end → end（两次，间隔2秒） → 切换到药品2 → 
药品2: start → start → [收到running-started] → running → [收到step5-return] → 
      end → end → [收到all_completed] → 结束
"""
import websocket
import json
import time

# ROS WebSocket 地址
ROS_WS_URL = "ws://192.168.51.12:9090"
ROS_TOPIC = "/his_sub"

print("=" * 80)
print("测试药品发送逻辑（包含 end 消息）")
print("=" * 80)
print("测试场景：一个处方包含2个药品")
print("处方编码: 012026070600135")
print("药品总数: medicine_total = 2")
print("=" * 80)
print("新逻辑流程:")
print("  药品1: start → start → [收到running-started] → running → [收到step5-return]")
print("         → end → end（两次，间隔2秒） → 切换到药品2")
print("  药品2: start → start → [收到running-started] → running → [收到step5-return]")
print("         → end → end → [收到all_completed] → 结束")
print("=" * 80)

# 连接 WebSocket
print(f"\n正在连接: {ROS_WS_URL}")
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
prescription_code = "012026070600135"
medicine_total = 2  # 药单共包含2个药品

# 定义2个药品（包含yaw字段）
medicines = [
    {
        "medicine_id": 14,
        "medicine_name": "感冒灵",
        "x": 10.5,
        "y": 20.3,
        "z": 5.0,
        "yaw": 1.0
    },
    {
        "medicine_id": 15,
        "medicine_name": "止咳糖浆",
        "x": 15.0,
        "y": 25.0,
        "z": 8.0,
        "yaw": 2.0
    }
]

print("\n" + "=" * 80)
print(f"药单: {prescription_code}")
print(f"药品总数: {medicine_total}")
print("=" * 80)
for i, med in enumerate(medicines, start=1):
    print(f"药品{i}: ID={med['medicine_id']}, 名称={med['medicine_name']}, xyz=({med['x']}, {med['y']}, {med['z']}), yaw={med['yaw']}")
print("=" * 80)

# ===== 药品1发送流程 =====
medicine_index = 1
medicine = medicines[0]

print(f"\n{'='*80}")
print(f"【药品1】发送流程")
print(f"{'='*80}")

# 1. 发送 start（两次）
print(f"\n>>> 步骤1: 发送 start（两次）")
for send_count in range(2):
    msg = {
        "data": "start",
        "prescription_code": prescription_code,
        "medicine_id": medicine["medicine_id"],
        "x": medicine["x"],
        "y": medicine["y"],
        "z": medicine["z"],
        "yaw": medicine["yaw"],
        "medicine_total": medicine_total,
        "medicine_index": medicine_index
    }
    
    print(f"\n第 {send_count+1} 次发送 start:")
    print("发送内容:")
    print(json.dumps(msg, indent=2, ensure_ascii=False))
    
    ws.send(json.dumps({
        "op": "publish",
        "topic": ROS_TOPIC,
        "msg": msg
    }))
    
    print("发送成功!")
    time.sleep(2)

# 2. 模拟接收 running-started 消息（实际由 ROS 返回）
print(f"\n>>> 步骤2: 模拟接收 ROS 返回的 running-started 消息")
print(f"ROS 消息格式: {medicine['medicine_id']}_{prescription_code}_running-started")
print(f"说明: 实际运行时，ROS 会返回此消息，触发切换到 running")

# 3. 发送 running（模拟收到 running-started 后）
print(f"\n>>> 步骤3: 发送 running（模拟收到 running-started 后）")
msg_running = {
    "data": "running",
    "prescription_code": prescription_code,
    "medicine_id": medicine["medicine_id"],
    "x": medicine["x"],
    "y": medicine["y"],
    "z": medicine["z"],
    "yaw": medicine["yaw"],
    "medicine_total": medicine_total,
    "medicine_index": medicine_index
}

print("发送内容:")
print(json.dumps(msg_running, indent=2, ensure_ascii=False))

ws.send(json.dumps({
    "op": "publish",
    "topic": ROS_TOPIC,
    "msg": msg_running
}))

print("发送成功!")

# 4. 模拟接收 step5-return 消息（实际由 ROS 返回）
print(f"\n>>> 步骤4: 模拟接收 ROS 返回的 step5-return 消息")
print(f"ROS 消息格式: {medicine['medicine_id']}_{prescription_code}_running-step5-return")
print(f"说明: 实际运行时，ROS 会返回此消息，触发发送 end")

# 5. 发送 end（两次，间隔2秒）- 新增逻辑
print(f"\n>>> 步骤5: 发送 end（两次，间隔2秒）- 新增逻辑")
for send_count in range(2):
    msg_end = {
        "data": "end",
        "prescription_code": prescription_code,
        "medicine_id": medicine["medicine_id"],
        "x": medicine["x"],
        "y": medicine["y"],
        "z": medicine["z"],
        "yaw": medicine["yaw"],
        "medicine_total": medicine_total,
        "medicine_index": medicine_index
    }
    
    print(f"\n第 {send_count+1} 次发送 end:")
    print("发送内容:")
    print(json.dumps(msg_end, indent=2, ensure_ascii=False))
    
    ws.send(json.dumps({
        "op": "publish",
        "topic": ROS_TOPIC,
        "msg": msg_end
    }))
    
    print("发送成功!")
    
    if send_count == 0:  # 第一次发送后，等待2秒
        print("等待2秒后发送第二次...")
        time.sleep(2)

print(f"\n>>> 步骤6: 切换到药品2")

# ===== 药品2发送流程 =====
medicine_index = 2
medicine = medicines[1]

print(f"\n{'='*80}")
print(f"【药品2】发送流程")
print(f"{'='*80}")

# 1. 发送 start（两次）
print(f"\n>>> 步骤1: 发送 start（两次）")
for send_count in range(2):
    msg = {
        "data": "start",
        "prescription_code": prescription_code,
        "medicine_id": medicine["medicine_id"],
        "x": medicine["x"],
        "y": medicine["y"],
        "z": medicine["z"],
        "yaw": medicine["yaw"],
        "medicine_total": medicine_total,
        "medicine_index": medicine_index
    }
    
    print(f"\n第 {send_count+1} 次发送 start:")
    print("发送内容:")
    print(json.dumps(msg, indent=2, ensure_ascii=False))
    
    ws.send(json.dumps({
        "op": "publish",
        "topic": ROS_TOPIC,
        "msg": msg
    }))
    
    print("发送成功!")
    time.sleep(2)

# 2. 模拟接收 running-started 消息
print(f"\n>>> 步骤2: 模拟接收 ROS 返回的 running-started 消息")
print(f"ROS 消息格式: {medicine['medicine_id']}_{prescription_code}_running-started")

# 3. 发送 running
print(f"\n>>> 步骤3: 发送 running")
msg_running = {
    "data": "running",
    "prescription_code": prescription_code,
    "medicine_id": medicine["medicine_id"],
    "x": medicine["x"],
    "y": medicine["y"],
    "z": medicine["z"],
    "yaw": medicine["yaw"],
    "medicine_total": medicine_total,
    "medicine_index": medicine_index
}

print("发送内容:")
print(json.dumps(msg_running, indent=2, ensure_ascii=False))

ws.send(json.dumps({
    "op": "publish",
    "topic": ROS_TOPIC,
    "msg": msg_running
}))

print("发送成功!")

# 4. 模拟接收 step5-return 消息
print(f"\n>>> 步骤4: 模拟接收 ROS 返回的 step5-return 消息")
print(f"ROS 消息格式: {medicine['medicine_id']}_{prescription_code}_running-step5-return")

# 5. 发送 end（两次，间隔2秒）
print(f"\n>>> 步骤5: 发送 end（两次，间隔2秒）")
for send_count in range(2):
    msg_end = {
        "data": "end",
        "prescription_code": prescription_code,
        "medicine_id": medicine["medicine_id"],
        "x": medicine["x"],
        "y": medicine["y"],
        "z": medicine["z"],
        "yaw": medicine["yaw"],
        "medicine_total": medicine_total,
        "medicine_index": medicine_index
    }
    
    print(f"\n第 {send_count+1} 次发送 end:")
    print("发送内容:")
    print(json.dumps(msg_end, indent=2, ensure_ascii=False))
    
    ws.send(json.dumps({
        "op": "publish",
        "topic": ROS_TOPIC,
        "msg": msg_end
    }))
    
    print("发送成功!")
    
    if send_count == 0:
        print("等待2秒后发送第二次...")
        time.sleep(2)

# 6. 模拟接收 all_completed 消息
print(f"\n>>> 步骤6: 模拟接收 ROS 返回的 all_completed 消息")
print(f"ROS 消息格式: {prescription_code}_all_completed")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
print("总结：")
print(f"  药单编码: {prescription_code}")
print(f"  药品总数: medicine_total = {medicine_total}")
print(f"  发送流程:")
print(f"    药品1: start(2次) → running → end(2次)")
print(f"    药品2: start(2次) → running → end(2次)")
print(f"  新增功能: 在切换到下一个药品前，发送 end 消息（两次，间隔2秒）")
print("=" * 80)

# 关闭连接
ws.close()
print("\n连接已关闭")