"""
独立测试工具 - 不依赖ROS WebSocket
用于测试药品坐标发送逻辑 + 摄像头语音播报联动
"""

import json
import time
import asyncio
import pymysql
from app.core.config import settings

# HIS 数据库连接配置
HIS_DB_CONFIG = {
    "host": settings.his_mysql_host,
    "port": settings.his_mysql_port,
    "user": settings.his_mysql_user,
    "password": settings.his_mysql_pass,
    "database": settings.his_mysql_db,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# 语音播报 ID 定义
AUDIO_ID_CAR_CAN_GO = 15       # 任务启动时播报一次
AUDIO_ID_CAR_ALREADY_ARRIVE = 14  # 机器人返回时播报两遍


async def play_audio_async(audio_id: int):
    """播放摄像头语音（异步）"""
    try:
        from app.services.audio_service import play_audio_async as real_play_audio
        success = await real_play_audio(audio_id)
        if success:
            print(f"[语音播报] 播放成功: audio_id={audio_id}")
        else:
            print(f"[语音播报] 播放失败: audio_id={audio_id}")
        return success
    except Exception as e:
        print(f"[语音播报] 播放异常: {e}")
        return False


def get_latest_pending_prescription():
    """从 HIS 数据库获取最新待处理的处方编码"""
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT prescription_code, id, created_at
                FROM prescriptions
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                print(f"[测试] 获取到最新处方: {result['prescription_code']}")
                return result["prescription_code"]
            else:
                print("[测试] 没有 pending 状态的处方")
                return None
    except Exception as e:
        print(f"[测试] 查询 HIS 数据库失败: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def get_prescription_medicine_locations(prescription_code: str) -> list:
    """根据处方编码查询该处方开具的所有药品的坐标"""
    print("=" * 60)
    print(f"[测试] 开始查询药品坐标")
    print(f"[测试] 处方编码: {prescription_code}")
    
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
        print(f"[测试] MySQL连接成功")
        
        with conn.cursor() as cursor:
            sql_query = """
                SELECT 
                    pi.medicine_id,
                    MIN(ml.x) as x,
                    MIN(ml.y) as y,
                    MIN(ml.z) as z,
                    MIN(ml.yaw) as yaw
                FROM prescriptions p
                JOIN prescription_items pi ON p.id = pi.prescription_id
                JOIN medicine_locations ml ON pi.medicine_id = ml.medicine_id
                WHERE p.prescription_code = %s
                GROUP BY pi.medicine_id
                ORDER BY pi.medicine_id ASC
            """
            cursor.execute(sql_query, (prescription_code,))
            results = cursor.fetchall()
            
            print(f"[测试] 查询结果数量: {len(results)}")
            
            if results:
                medicine_list = []
                for i, row in enumerate(results):
                    print(f"[测试] 查询结果{i+1}: medicine_id={row['medicine_id']}, x={row['x']}, y={row['y']}, z={row['z']}, yaw={row['yaw']}")
                    medicine_list.append({
                        "medicine_id": row["medicine_id"],
                        "x": float(row["x"]) if row["x"] else 0.0,
                        "y": float(row["y"]) if row["y"] else 0.0,
                        "z": float(row["z"]) if row["z"] else 0.0,
                        "yaw": float(row["yaw"]) if row["yaw"] else 0.0
                    })
                print("=" * 60)
                return medicine_list
            else:
                print("[测试] 未找到药品坐标信息")
                print("=" * 60)
                return []
    except Exception as e:
        print(f"[测试] 查询失败: {e}")
        print("=" * 60)
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def create_message(data: str, prescription_code: str, medicine_data: dict, medicine_total: int, medicine_index: int) -> dict:
    """创建发送消息"""
    return {
        "op": "publish",
        "topic": "/his_sub",
        "msg": {
            "data": data,
            "prescription_code": prescription_code,
            "medicine_id": medicine_data["medicine_id"],
            "x": medicine_data["x"],
            "y": medicine_data["y"],
            "z": medicine_data["z"],
            "yaw": medicine_data["yaw"],
            "medicine_total": medicine_total,
            "medicine_index": medicine_index
        }
    }


def send_to_console(message: dict):
    """发送到控制台（打印）"""
    print("\n" + "=" * 60)
    print("[发送] 消息内容:")
    print(json.dumps(message, indent=2, ensure_ascii=False))
    print("=" * 60)


def send_to_file(message: dict, file_path: str = "test_messages.json"):
    """发送到文件（追加写入）"""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(message, ensure_ascii=False) + "\n")
    print(f"[发送] 已写入文件: {file_path}")


def main():
    """主测试流程"""
    print("=" * 60)
    print("独立测试工具 - 药品坐标发送")
    print("=" * 60)
    
    # 1. 获取处方编码
    prescription_code = get_latest_pending_prescription()
    
    if not prescription_code:
        print("\n[提示] 没有 pending 状态的处方")
        print("[提示] 可以手动输入处方编码进行测试:")
        
        # 读取数据库中的所有处方，供用户选择
        try:
            conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
            with conn.cursor() as cursor:
                cursor.execute("SELECT prescription_code, status FROM prescriptions ORDER BY created_at DESC LIMIT 10")
                prescriptions = cursor.fetchall()
                
                if prescriptions:
                    print("\n可选处方列表:")
                    for i, p in enumerate(prescriptions):
                        print(f"  {i+1}. {p['prescription_code']} (状态: {p['status']})")
                    
                    print("\n输入处方编码进行测试（或按回车退出）:")
                    user_input = input().strip()
                    
                    if user_input:
                        prescription_code = user_input
                    else:
                        print("退出测试")
                        return
                else:
                    print("数据库中没有处方数据")
                    return
        except Exception as e:
            print(f"查询处方列表失败: {e}")
            return
        finally:
            if 'conn' in locals():
                conn.close()
    
    # 2. 查询药品坐标
    medicine_list = get_prescription_medicine_locations(prescription_code)
    
    if not medicine_list:
        print(f"\n[警告] 处方 {prescription_code} 没有药品数据")
        return
    
    medicine_total = len(medicine_list)
    print(f"\n处方 {prescription_code} 包含 {medicine_total} 个药品")
    
    # 3. 选择发送目标
    print("\n选择发送目标:")
    print("  1. 控制台打印")
    print("  2. 写入文件 (test_messages.json)")
    print("  3. 模拟完整流程（逐个药品发送，模拟 running-started 触发）")
    
    choice = input("输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        # 发送所有药品坐标到控制台
        for i, medicine_data in enumerate(medicine_list):
            medicine_index = i + 1
            message = create_message("start", prescription_code, medicine_data, medicine_total, medicine_index)
            send_to_console(message)
            
            input("按回车继续发送下一个药品...")
    
    elif choice == "2":
        # 发送所有药品坐标到文件
        for i, medicine_data in enumerate(medicine_list):
            medicine_index = i + 1
            message = create_message("start", prescription_code, medicine_data, medicine_total, medicine_index)
            send_to_file(message)
        
        print(f"\n所有药品坐标已写入 test_messages.json")
    
    elif choice == "3":
        # 模拟完整流程（循环发送 + ROS消息触发）
        print("\n" + "=" * 60)
        print("模拟完整流程（循环发送 + ROS消息触发）:")
        print("  1. 循环发送药品坐标（每2秒一次）")
        print("  2. 在发送过程中收到 ROS 消息")
        print("  3. 收到 running-started → 改为发送 running")
        print("  4. 收到 running-step5-return → 切换下一个药品")
        print("  5. 模拟用户输入 ROS 消息，系统根据消息改变发送内容")
        print("=" * 60)
        
        medicine_started = {}  # 药品是否已收到 running-started
        for medicine in medicine_list:
            medicine_started[medicine["medicine_id"]] = False
        
        current_medicine_index = 0  # 当前药品索引
        send_count = {}  # 发送计数
        for medicine in medicine_list:
            send_count[medicine["medicine_id"]] = 0
        
        ros_messages = []  # 模拟收到的 ROS 消息队列
        
        # ===== 语音播报状态（按单子触发） =====
        car_can_go_triggered = False  # 单子是否已触发 car_can_go
        car_already_arrive_triggered = False  # 单子是否已触发 car_already_arrive
        
        print("\n[提示] 你可以在发送过程中输入 ROS 消息")
        print("[提示] 格式: {medicine_id}_{prescription_code}_{status}")
        print("[提示] 例如: 1_012026070600125_running-started")
        print("[提示] 输入 'next' 进入下一个药品")
        print("[提示] 输入 'exit' 退出测试")
        print("[提示] 输入 'auto' 自动模拟完整流程")
        
        print("\n[语音播报规则]")
        print(f"  - car_can_go (audio_id={AUDIO_ID_CAR_CAN_GO}): 单子开始时播报一次（第一个药品收到 running-started）")
        print(f"  - car_already_arrive (audio_id={AUDIO_ID_CAR_ALREADY_ARRIVE}): 单子完成时播报两遍（最后一个药品收到 running-step5-return）")
        
        auto_mode = False  # 自动模式
        
        while current_medicine_index < medicine_total:
            medicine_data = medicine_list[current_medicine_index]
            medicine_id = medicine_data["medicine_id"]
            medicine_index = current_medicine_index + 1
            
            print(f"\n{'='*60}")
            print(f"当前药品: {medicine_index}/{medicine_total} (ID: {medicine_id})")
            print(f"started状态: {medicine_started.get(medicine_id, False)}")
            print(f"发送计数: {send_count.get(medicine_id, 0)}")
            print(f"{'='*60}")
            
            # ===== 循环发送当前药品 =====
            while True:
                # 判断发送内容
                is_started = medicine_started.get(medicine_id, False)
                
                if is_started:
                    data = "running"
                else:
                    # 如果发送次数 >= 2次，也改为 running（兼容旧逻辑）
                    if send_count.get(medicine_id, 0) >= 2:
                        data = "running"
                    else:
                        data = "start"
                
                # 创建发送消息
                message = create_message(data, prescription_code, medicine_data, medicine_total, medicine_index)
                
                print(f"\n[发送 {send_count.get(medicine_id, 0)+1}] 发送药品坐标:")
                print(json.dumps(message["msg"], indent=2, ensure_ascii=False))
                
                # 更新发送计数
                send_count[medicine_id] = send_count.get(medicine_id, 0) + 1
                
                # ===== 检查是否收到 ROS 消息 =====
                if auto_mode:
                    # 自动模式：自动生成 ROS 消息
                    print("\n[自动模式] 模拟收到 ROS 消息...")
                    import time
                    time.sleep(1)
                    
                    # 如果还没收到 running-started，自动生成
                    if not medicine_started.get(medicine_id, False):
                        ros_msg = f"{medicine_id}_{prescription_code}_running-started"
                        print(f"[自动] 收到: {ros_msg}")
                        ros_messages.append(ros_msg)
                    
                    # 如果已收到 running-started 且发送次数 >= 3，自动生成 running-step5-return
                    elif send_count.get(medicine_id, 0) >= 3:
                        ros_msg = f"{medicine_id}_{prescription_code}_running-step5-return"
                        print(f"[自动] 收到: {ros_msg}")
                        ros_messages.append(ros_msg)
                        break  # 切换下一个药品
                    
                    # 处理 ROS 消息
                    if ros_messages:
                        ros_msg = ros_messages.pop(0)
                        parts = ros_msg.split("_")
                        if len(parts) >= 3:
                            received_medicine_id = int(parts[0]) if parts[0].isdigit() else None
                            received_prescription_code = parts[1]
                            received_status = "_".join(parts[2:])
                            
                            print(f"[处理] 解析: medicine_id={received_medicine_id}, status={received_status}")
                            
                            # 处理 running-started
                            if received_status == "running-started":
                                if received_medicine_id == medicine_id and received_prescription_code == prescription_code:
                                    print(f"[处理] [OK] 药品ID匹配，started=True")
                                    medicine_started[medicine_id] = True
                                    
                                    # ===== 语音播报：单子开始时触发一次（第一个药品收到 running-started） =====
                                    if not car_can_go_triggered:
                                        print(f"[语音播报] 触发：单子开始（第一个药品收到 running-started）")
                                        print(f"[语音播报] 播放 audio_id={AUDIO_ID_CAR_CAN_GO} (car_can_go)")
                                        asyncio.run(play_audio_async(AUDIO_ID_CAR_CAN_GO))
                                        car_can_go_triggered = True  # 标记已触发，后续药品不再触发
                                    else:
                                        print(f"[语音播报] car_can_go 已触发过，不重复播放")
                                else:
                                    print(f"[处理] [ERROR] 药品ID不匹配，不处理")
                            
                            # 处理 running-step5-return
                            elif received_status == "running-step5-return" or received_status == "running_step5_return":
                                if received_medicine_id == medicine_id and received_prescription_code == prescription_code:
                                    print(f"[处理] [OK] 药品ID匹配，切换下一个药品")
                                    
                                    # 判断是否是最后一个药品
                                    is_last_medicine = (current_medicine_index == medicine_total - 1)
                                    
                                    # ===== 语音播报：单子完成时触发（最后一个药品收到 running-step5-return） =====
                                    if is_last_medicine and not car_already_arrive_triggered:
                                        print(f"[语音播报] 触发：单子完成（最后一个药品收到 running-step5-return）")
                                        print(f"[语音播报] 播放 audio_id={AUDIO_ID_CAR_ALREADY_ARRIVE} (car_already_arrive) - 第1次")
                                        asyncio.run(play_audio_async(AUDIO_ID_CAR_ALREADY_ARRIVE))
                                        print(f"[语音播报] 等待2秒...")
                                        time.sleep(2)
                                        print(f"[语音播报] 播放 audio_id={AUDIO_ID_CAR_ALREADY_ARRIVE} (car_already_arrive) - 第2次")
                                        asyncio.run(play_audio_async(AUDIO_ID_CAR_ALREADY_ARRIVE))
                                        car_already_arrive_triggered = True  # 标记已触发
                                    elif not is_last_medicine:
                                        print(f"[语音播报] 不是最后一个药品，暂不触发 car_already_arrive")
                                    else:
                                        print(f"[语音播报] car_already_arrive 已触发过，不重复播放")
                                    
                                    current_medicine_index += 1
                                    if current_medicine_index < medicine_total:
                                        next_medicine = medicine_list[current_medicine_index]
                                        next_medicine_id = next_medicine["medicine_id"]
                                        medicine_started[next_medicine_id] = False
                                        send_count[next_medicine_id] = 0
                                        print(f"[处理] 切换到药品 {current_medicine_index+1}/{medicine_total} (ID: {next_medicine_id})")
                                    break
                                else:
                                    print(f"[处理] [ERROR] 药品ID不匹配，不切换")
                    
                    # 继续循环
                    print("[自动] 继续发送...")
                    continue
                
                else:
                    # 手动模式：等待用户输入
                    print("\n输入 ROS 消息（或按回车继续发送）:")
                    user_input = input().strip()
                    
                    if user_input == "exit":
                        print("退出测试")
                        return
                    
                    elif user_input == "next":
                        print("[手动] 强制切换下一个药品")
                        current_medicine_index += 1
                        if current_medicine_index < medicine_total:
                            next_medicine = medicine_list[current_medicine_index]
                            next_medicine_id = next_medicine["medicine_id"]
                            medicine_started[next_medicine_id] = False
                            send_count[next_medicine_id] = 0
                            print(f"[手动] 切换到药品 {current_medicine_index+1}/{medicine_total} (ID: {next_medicine_id})")
                        break
                    
                    elif user_input == "auto":
                        print("[手动] 切换到自动模式")
                        auto_mode = True
                        continue
                    
                    elif user_input:
                        # 用户输入了 ROS 消息
                        print(f"[手动] 收到用户输入: {user_input}")
                        ros_messages.append(user_input)
                    
                    # 处理 ROS 消息队列
                    if ros_messages:
                        ros_msg = ros_messages.pop(0)
                        parts = ros_msg.split("_")
                        if len(parts) >= 3:
                            received_medicine_id = int(parts[0]) if parts[0].isdigit() else None
                            received_prescription_code = parts[1]
                            received_status = "_".join(parts[2:])
                            
                            print(f"[处理] 解析: medicine_id={received_medicine_id}, status={received_status}")
                            
                            # 处理 running-started
                            if received_status == "running-started":
                                if received_medicine_id == medicine_id and received_prescription_code == prescription_code:
                                    print(f"[处理] [OK] 药品ID匹配，started=True")
                                    medicine_started[medicine_id] = True
                                    
                                    # ===== 语音播报：单子开始时触发一次（第一个药品收到 running-started） =====
                                    if not car_can_go_triggered:
                                        print(f"[语音播报] 触发：单子开始（第一个药品收到 running-started）")
                                        print(f"[语音播报] 播放 audio_id={AUDIO_ID_CAR_CAN_GO} (car_can_go)")
                                        asyncio.run(play_audio_async(AUDIO_ID_CAR_CAN_GO))
                                        car_can_go_triggered = True  # 标记已触发，后续药品不再触发
                                    else:
                                        print(f"[语音播报] car_can_go 已触发过，不重复播放")
                                else:
                                    print(f"[处理] [ERROR] 药品ID不匹配，不处理")
                            
                            # 处理 running-step5-return
                            elif received_status == "running-step5-return" or received_status == "running_step5_return":
                                if received_medicine_id == medicine_id and received_prescription_code == prescription_code:
                                    print(f"[处理] [OK] 药品ID匹配，切换下一个药品")
                                    
                                    # 判断是否是最后一个药品
                                    is_last_medicine = (current_medicine_index == medicine_total - 1)
                                    
                                    # ===== 语音播报：单子完成时触发（最后一个药品收到 running-step5-return） =====
                                    if is_last_medicine and not car_already_arrive_triggered:
                                        print(f"[语音播报] 触发：单子完成（最后一个药品收到 running-step5-return）")
                                        print(f"[语音播报] 播放 audio_id={AUDIO_ID_CAR_ALREADY_ARRIVE} (car_already_arrive) - 第1次")
                                        asyncio.run(play_audio_async(AUDIO_ID_CAR_ALREADY_ARRIVE))
                                        print(f"[语音播报] 等待2秒...")
                                        time.sleep(2)
                                        print(f"[语音播报] 播放 audio_id={AUDIO_ID_CAR_ALREADY_ARRIVE} (car_already_arrive) - 第2次")
                                        asyncio.run(play_audio_async(AUDIO_ID_CAR_ALREADY_ARRIVE))
                                        car_already_arrive_triggered = True  # 标记已触发
                                    elif not is_last_medicine:
                                        print(f"[语音播报] 不是最后一个药品，暂不触发 car_already_arrive")
                                    else:
                                        print(f"[语音播报] car_already_arrive 已触发过，不重复播放")
                                    
                                    current_medicine_index += 1
                                    if current_medicine_index < medicine_total:
                                        next_medicine = medicine_list[current_medicine_index]
                                        next_medicine_id = next_medicine["medicine_id"]
                                        medicine_started[next_medicine_id] = False
                                        send_count[next_medicine_id] = 0
                                        print(f"[处理] 切换到药品 {current_medicine_index+1}/{medicine_total} (ID: {next_medicine_id})")
                                    break
                                else:
                                    print(f"[处理] [ERROR] 药品ID不匹配，不切换")
                    
                    # 模拟发送间隔
                    print("\n[模拟] 等待2秒...")
                    import time
                    time.sleep(2)
        
        print("\n" + "=" * 60)
        print("模拟流程完成!")
        print("=" * 60)
    
    else:
        print("无效选择")


if __name__ == "__main__":
    main()