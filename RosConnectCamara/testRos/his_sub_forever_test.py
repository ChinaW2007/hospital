"""
HIS 系统发送药单编码到 ROS
从 HIS MySQL 数据库获取最新处方编码，发送到 ROS WebSocket
"""
import websocket
import json
import time
import pymysql

# HIS MySQL 数据库配置
HIS_DB_CONFIG = {
    "host": "192.168.51.133",
    "port": 3306,
    "user": "ros",
    "password": "123456",
    "database": "test",
    "charset": "utf8mb4",
}

# ROS WebSocket 地址
ROS_WS_URL = "ws://192.168.51.12:9090"
ROS_TOPIC = "/his_sub"


def get_latest_prescription_code():
    """
    从 HIS 数据库获取最新待处理的处方编码
    
    查询条件：
    - 状态为 approved（已审核通过）
    - 按创建时间倒序排列
    - 返回最新的处方编码
    """
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
        with conn.cursor() as cursor:
            # 查询最新待审核的处方（医生开具后状态为 pending）
            cursor.execute("""
                SELECT prescription_code, id, created_at
                FROM prescriptions
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                prescription_code = result[0]
                print(f"获取到处方编码: {prescription_code}")
                return prescription_code
            else:
                print("没有待处理的处方")
                return None
    except Exception as e:
        print(f"查询 HIS 数据库失败: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def send_prescription_code_to_ros(prescription_code: str):
    """
    发送药单编码到 ROS
    
    Args:
        prescription_code: 药单编码
    """
    try:
        ws = websocket.create_connection(ROS_WS_URL)
        
        # 注册 Topic（注意类型必须完全一致：his_sub/HisSub）
        ws.send(json.dumps({
            "op": "advertise",
            "topic": ROS_TOPIC,
            "type": "his_sub/HisSub"
        }))
        
        time.sleep(0.5)
        
        # 发送药单编码（JSON格式）
        message = json.dumps({
            "op": "publish",
            "topic": ROS_TOPIC,
            "msg": {
                "data": "start",
                "prescription_code": prescription_code
            }
        })
        ws.send(message)
        print(f"已发送药单编码到 ROS: start + {prescription_code}")
        
        ws.close()
        return True
    
    except Exception as e:
        print(f"发送到 ROS 失败: {e}")
        return False


def main_loop():
    """
    主循环：持续发送当前处方编码到 ROS，直到处方编码更新
    """
    print("启动 HIS-ROS 药单编码发送服务...")
    print(f"ROS WebSocket: {ROS_WS_URL}")
    print(f"Topic: {ROS_TOPIC}")
    print("逻辑: 持续发送当前处方编码，直到编码更新")
    print("-" * 50)
    
    last_prescription_code = None
    
    while True:
        try:
            # 获取最新处方编码
            current_code = get_latest_prescription_code()
            
            # 如果有处方编码，持续发送
            if current_code:
                # 检测是否是新编码
                if current_code != last_prescription_code:
                    print(f"\n{'='*20}")
                    print(f"处方编码更新: {last_prescription_code} -> {current_code}")
                    print(f"{'='*20}")
                    last_prescription_code = current_code
                
                # 发送当前处方编码到 ROS
                if send_prescription_code_to_ros(current_code):
                    print(f"[发送成功] 当前处方: {current_code}")
                else:
                    print("[发送失败] 等待重试...")
            else:
                print("[无处方] 等待新处方...")
            
            # 发送间隔（每2秒发送一次）
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n服务停止")
            break
        except Exception as e:
            print(f"主循环异常: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main_loop()