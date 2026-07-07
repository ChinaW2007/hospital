#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
功能说明：

Step 1: 小车从原点导航到药房取药点
Step 2: 机械臂执行抓药动作
Step 3: 小车导航到病房送药点
Step 4: 机械臂执行放药动作
Step 5: 小车返回原点

新增：方向控制 —— 每个导航点可指定小车朝向（yaw角度）

依赖：
    ROS1 Noetic
    move_base
    pymycobot

机械臂：
    MyCobot
串口：
    /dev/ttyACM0
"""

import rospy
import actionlib
import time
import math
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from std_msgs.msg import String
from his_sub.msg import HisSub
from pymycobot.mycobot import MyCobot


# =========================
# MyCobot初始化
# =========================
mc = MyCobot('/dev/ttyACM0', 115200)


# =========================
# 方向工具：yaw → 四元数
# =========================
def yaw_to_quaternion(yaw_deg):
    """
    将偏航角（度）转换为四元数

    参数:
        yaw_deg : 偏航角，单位：度
                  0°   → 朝向 x 轴正方向
                  90°  → 朝向 y 轴正方向
                  180° → 朝向 x 轴负方向
                  -90° → 朝向 y 轴负方向

    返回:
        (x, y, z, w) 四元数
    """
    yaw_rad = math.radians(yaw_deg)
    qz = math.sin(yaw_rad / 2.0)
    qw = math.cos(yaw_rad / 2.0)
    return (0.0, 0.0, qz, qw)


# =========================
# 机械臂抓药动作
# =========================
def arm_pick():
    """
    抓药流程：

    1. 回零
    2. 到预抓取姿态
    3. 打开夹爪
    4. 移动到抓取坐标
    5. 合拢夹爪
    6. 抬起药品
    7. 调整姿态
    """

    rospy.loginfo("Arm: moving to zero position...")
    mc.send_angles([0, 0, 0, 0, 0, 0], 20)
    time.sleep(2)

    rospy.loginfo("Arm: moving to pre-grasp pose...")
    mc.send_angles(
        [6.24, -55.63, -34.45, 5.97, -31.46, 80.41],
        20
    )
    time.sleep(3)

    rospy.loginfo("Arm: opening gripper...")
    mc.set_gripper_state(0, 100)
    time.sleep(3)

    rospy.loginfo("Arm: moving to grasp coordinates...")
    mc.send_coords(
        [281.45, -45.8, 119.1,
         -153.71, 0.76, -172.2],
        20,
        0
    )
    time.sleep(2)

    rospy.loginfo("Arm: closing gripper...")
    mc.set_gripper_state(1, 100)
    time.sleep(2)

    rospy.loginfo("Arm: lifting object...")
    mc.send_angle(3, 50, 20)
    time.sleep(2)

    rospy.loginfo("Arm: adjusting pose (retract)...")
    mc.send_angles([83.05, -103.53, 143.87, -72.15, 3.25, 46.49], 50)  #收缩
    time.sleep(3)

    rospy.loginfo("Arm: pick completed!")


# =========================
# 机械臂放药动作
# =========================
def arm_place():
    """
    放药流程：

    1. 打开夹爪释放药品
    2. 回零
    3. 合拢夹爪
    """

    rospy.loginfo("Arm: opening gripper...")
    mc.set_gripper_state(0, 100)
    time.sleep(3)

    rospy.loginfo("Arm: returning to zero position...")
    mc.send_angles([83.05, -103.53, 143.87, -72.15, 3.25, 46.49], 50)  #收缩
    time.sleep(3)

    rospy.loginfo("Arm: closing gripper...")
    mc.set_gripper_state(1, 100)
    time.sleep(3)

    rospy.loginfo("Arm: place completed!")


# =========================
# 导航函数（带方向）
# =========================
def goto_goal(client, x, y, yaw_deg=0.0):
    """
    导航到指定地图坐标，并设置朝向

    参数:
        x, y    : map坐标
        yaw_deg : 偏航角（度），0°=朝x正方向，90°=朝y正方向

    返回:
        True  -> 到达成功
        False -> 到达失败
    """

    goal = MoveBaseGoal()

    goal.target_pose.header.frame_id = "map"
    goal.target_pose.header.stamp = rospy.Time.now()

    goal.target_pose.pose.position.x = x
    goal.target_pose.pose.position.y = y

    # ---- 方向：yaw → 四元数 ----
    ox, oy, oz, ow = yaw_to_quaternion(yaw_deg)
    goal.target_pose.pose.orientation.x = ox
    goal.target_pose.pose.orientation.y = oy
    goal.target_pose.pose.orientation.z = oz
    goal.target_pose.pose.orientation.w = ow

    rospy.loginfo(
        "Navigating to (%.2f, %.2f) yaw=%.1f°",
        x, y, yaw_deg
    )

    client.send_goal(goal)

    client.wait_for_result()

    return client.get_state() == GoalStatus.SUCCEEDED




# =========================
# 主程序
# =========================
if __name__ == '__main__':

    rospy.init_node('medicine_delivery_robot')

    rospy.loginfo("Connecting move_base...")

    client = actionlib.SimpleActionClient(
        'move_base',
        MoveBaseAction
    )

    client.wait_for_server()

    rospy.loginfo("move_base connected!")

    # ==================================================
    # 全局标志位
    # ==================================================
    task_state = {
        "start_received": False,
        "prescription_code": "",
        "medicine_id": 0,
        "medicine_total": 0,
        "medicine_index": 0,
        "pick_x": 0.0,             # 药房取药点 x（来自 his_sub 消息）
        "pick_y": 0.0,             # 药房取药点 y（来自 his_sub 消息）
        "pick_z": 0.0,             # 药房取药点 z（来自 his_sub 消息）
        "pick_yaw": 0.0,           # 药房取药点偏航角（来自 his_sub 消息）
        "task_running": False,     # 任务运行中时忽略新的 start 信号
        "end_ack_sent": False,     # 修复：end回执去重标志（收到HIS的end后只回执一次）
    }

    # ==================================================
    # his_sub 回调：根据 msg.data 判断当前药单在后端的状态
    #   "start"   → 药单开始，触发任务
    #   "running" → 药单运行中
    #   "end"     → 药单已结束，不再运行，中止当前任务
    # 当任务正在运行时（task_running=True），忽略 start 信号
    #
    # his_sub 消息格式：
    #   string data             - 药单状态：start / running / end
    #   string prescription_code- 处方编号
    #   int32 medicine_id       - 药品 ID
    #   float32 x               - 药房取药点 x 坐标
    #   float32 y               - 药房取药点 y 坐标
    #   float32 z               - 药房取药点 z 坐标
    #   float32 yaw             - 药房取药点偏航角（yaw）
    #   int32 medicine_total    - 药品总数
    #   int32 medicine_index    - 当前药品索引
    # ==================================================
    def his_sub_callback(msg):
        rospy.loginfo(
            "Received his_sub message: data=%s, prescription_code=%s, medicine_id=%d, x=%.2f, y=%.2f, z=%.2f, yaw=%.1f, medicine_total=%d, medicine_index=%d",
            msg.data,
            msg.prescription_code,
            msg.medicine_id,
            msg.x,
            msg.y,
            msg.z,
            msg.yaw,
            msg.medicine_total,
            msg.medicine_index,
        )

        if msg.data == "start":
            if task_state["task_running"]:
                rospy.loginfo("Task is running, ignoring start signal (prescription_code=%s)", msg.prescription_code)
                return
            task_state["task_running"] = True
            task_state["start_received"] = True
            task_state["prescription_code"] = msg.prescription_code
            task_state["medicine_id"] = msg.medicine_id
            task_state["medicine_total"] = msg.medicine_total
            task_state["medicine_index"] = msg.medicine_index
            task_state["pick_x"] = msg.x
            task_state["pick_y"] = msg.y
            task_state["pick_z"] = msg.z
            task_state["pick_yaw"] = msg.yaw
            task_state["end_ack_sent"] = False  # 修复：新药品开始，重置end回执去重标志

            rospy.loginfo(
                "Received start signal, prescription_code=%s, medicine_id=%d, "
                "pick_point=(%.2f, %.2f, %.2f) yaw=%.1f°, "
                "medicine_total=%d, medicine_index=%d",
                msg.prescription_code, msg.medicine_id,
                msg.x, msg.y, msg.z, msg.yaw,
                msg.medicine_total, msg.medicine_index
            )
        elif msg.data == "running":
            if task_state["task_running"]:
                rospy.loginfo("Drug order is running in backend (prescription_code=%s)", msg.prescription_code)
            else:
                rospy.loginfo("Received 'running' but no task active, treating as start (prescription_code=%s)", msg.prescription_code)
                task_state["task_running"] = True
                task_state["start_received"] = True
                task_state["prescription_code"] = msg.prescription_code
                task_state["medicine_id"] = msg.medicine_id
                task_state["medicine_total"] = msg.medicine_total
                task_state["medicine_index"] = msg.medicine_index
                task_state["pick_x"] = msg.x
                task_state["pick_y"] = msg.y
                task_state["pick_z"] = msg.z
                task_state["pick_yaw"] = msg.yaw
        elif msg.data == "end":
            # ===== 修复：收到HIS Sender的end后，回执药品级end（去重）=====
            rospy.loginfo(
                "Received end signal from HIS Sender, medicine_id=%d, prescription_code=%s",
                msg.medicine_id, msg.prescription_code
            )

            if not task_state.get("end_ack_sent", False):
                # 第一次收到end，回执药品级end
                medicine_end_msg = f"{msg.medicine_id}_{msg.prescription_code}_end"
                pub.publish(medicine_end_msg)
                task_state["end_ack_sent"] = True
                rospy.loginfo("Published medicine-level end (ack): %s", medicine_end_msg)
            else:
                # 去重：第二次收到end，不重复回执
                rospy.loginfo("Duplicate end, already acked, ignoring")
        else:
            rospy.logwarn("Unknown his_sub data='%s', prescription_code=%s — ignored", msg.data, msg.prescription_code)

    # ==================================================
    # car02 回调：接收car02发来的消息
    # ==================================================
    def car02_callback(msg):
        rospy.loginfo("Received from car02: %s", msg.data)

    # 订阅 his_sub，实时监听启动信号（一直保持订阅，不取消）
    rospy.Subscriber("his_sub", HisSub, his_sub_callback, queue_size=10)

    # 订阅 car02_pub，接收car02消息
    rospy.Subscriber("car02_pub", String, car02_callback, queue_size=10)

    # 发布 car01 状态消息
    pub = rospy.Publisher("car01_pub", String, queue_size=10)

    # ==================================================
    # 辅助函数：给所有向外发送的消息加上 prescription_code 前缀
    # 修复：支持药单级（无medicine_id）和药品级（有medicine_id）两种格式
    # ==================================================
    def make_msg(text, include_medicine_id=True):
        code = task_state.get("prescription_code", "")
        if include_medicine_id:
            med_id = task_state.get("medicine_id", 0)
            return f"{med_id}_{code}_{text}"
        else:
            return f"{code}_{text}"

    # ==================================================
    # 地图坐标配置（含方向）
    # ==================================================

    # 原点（启动位置）
    HOME_X   = -1.5369
    HOME_Y   = -1.44362
    HOME_YAW = 0.0       # 方向：朝向 x 正方向

    # 药房取药点（需要修改）
    PICK_X   = 1.3223
    PICK_Y   = -0.965548
    PICK_YAW = 90.0      # 方向：朝向 y 正方向（面朝药架）

    # 病房送药点
    DROP_X   = -0.68189
    DROP_Y   = -1.05174
    DROP_YAW = -90.0     # 方向：朝向 y 负方向（面朝病床）

    # ==================================================
    # 主循环：持续监听 start，循环执行任务
    # ==================================================
    while not rospy.is_shutdown():

        # ---- 等待下一个 "start" 信号，重置全部参数 ----
        task_state["start_received"] = False
        task_state["task_running"] = False
        task_state["order_ended"] = False
        task_state["prescription_code"] = ""
        task_state["medicine_id"] = 0
        task_state["medicine_total"] = 0
        task_state["medicine_index"] = 0
        task_state["pick_x"] = 0.0
        task_state["pick_y"] = 0.0
        task_state["pick_z"] = 0.0
        task_state["pick_yaw"] = 0.0
        task_state["end_ack_sent"] = False  # 修复：重置end回执去重标志

        rospy.loginfo("Waiting for next 'start' signal on his_sub...")
        rate = rospy.Rate(1)  # 1 Hz 检查频率
        while not rospy.is_shutdown() and not task_state["start_received"]:
            rate.sleep()

        if rospy.is_shutdown():
            break



        current_code = task_state["prescription_code"]

        rospy.loginfo(
            "收到药单: %s",
            current_code
        )

        rospy.loginfo("===== 任务开始 =====")
        pub.publish(make_msg("running-started"))
        pub.publish(make_msg("running-started"))

        # ==================================================
        # Step 1：前往药房
        # ==================================================

        # 从 his_sub 消息中获取药房取药点坐标
        pick_x = task_state["pick_x"]
        pick_y = task_state["pick_y"]
        pick_yaw = task_state["pick_yaw"]

        rospy.loginfo(
            "===== Step 1: 正在前往药房 (%.2f, %.2f, yaw=%.1f°) =====",
            pick_x, pick_y, pick_yaw
        )
        pub.publish(make_msg("running-step1-navigate-to-pharmacy"))

        if not goto_goal(client, pick_x, pick_y, pick_yaw):
            rospy.logerr(
                "Failed to reach medicine station!"
            )
            pub.publish(make_msg("error-step1-cannot-reach-pharmacy"))
            rospy.loginfo("Task aborted, waiting for next start signal...")
            continue

        rospy.loginfo("Arrived at medicine station")

        # 底盘稳定
        time.sleep(2)

        # ==================================================
        # Step 2：抓药
        # ==================================================

        rospy.loginfo(
            "===== Step 2: 抓药 ====="
        )
        pub.publish(make_msg("running-step2-pick"))

        arm_pick()


        # ==================================================
        # Step 3：给予药剂师确认
        # ==================================================

        rospy.loginfo(
            "===== Step 3: 给予药剂师确认 ====="
        )
        pub.publish(make_msg("running-step3-navigate-docter"))

        if not goto_goal(client, DROP_X, DROP_Y, DROP_YAW):
            rospy.logerr(
                "Failed to reach patient room!"
            )
            pub.publish(make_msg("error-step3-cannot-reach-patient-room"))
            rospy.loginfo("Task aborted, waiting for next start signal...")
            continue

        rospy.loginfo("Arrived at patient room")

        time.sleep(2)


        # ==================================================
        # Step 4：放药
        # ==================================================

        rospy.loginfo(
            "===== Step 4: 放药 ====="
        )
        pub.publish(make_msg("running-step4-deliver-medicine"))

        arm_place()

        # 检查药单是否已被后端终止
       
        # ==================================================
        # Step 5：返回原点
        # 修复：发送药单级running-step5-return（无medicine_id）
        #       不主动发送end，等待HIS Sender发end后再回执药品级end
        # ==================================================

        rospy.loginfo(
            "===== Step 5: 返回原点 ====="
        )
        # 药单级消息（无medicine_id）：{prescription_code}_running-step5-return
        step5_return_msg = make_msg("running-step5-return", include_medicine_id=False)
        pub.publish(step5_return_msg)
        rospy.loginfo("Published prescription-level running-step5-return: %s", step5_return_msg)

        if goto_goal(client, HOME_X, HOME_Y, HOME_YAW):
            rospy.loginfo(
                "Mission completed successfully!"
            )
            # 修复：不主动发送end！
            # 等待HIS Sender发送end消息后，his_sub_callback会回执药品级end
            rospy.loginfo("Waiting for HIS Sender to send end signal...")
        else:
            rospy.logerr(
                "Failed to return home!"
            )
            pub.publish(make_msg("error-step5-cannot-return-to-home"))
        
        rospy.loginfo(
            "任务结束，prescription_code='%s'，等待下一个 start...",
            current_code
        )

    rospy.loginfo("Program finished.")
