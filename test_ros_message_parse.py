"""
测试 ROS 消息解析逻辑
验证新格式 {prescription_code}_running-started 是否能正确解析
"""

def parse_ros_message(data: str):
    """
    解析 ROS 消息，多版本适配
    
    支持格式：
    1. JSON 格式: {"status": "running_started", "prescription_code": "RX..."}
    2. 分隔符格式（竖线）: "running_started|RX..."
    3. 新格式（下划线）: "{prescription_code}_running-started"
    4. 纯字符串格式（旧版本兼容）: "running_started"
    
    返回：
    - status: ROS 状态字符串
    - prescription_code: 药单编码（可选）
    """
    import json
    
    # 尝试解析 JSON 格式
    if data.startswith("{") and data.endswith("}"):
        try:
            msg = json.loads(data)
            return {
                "status": msg.get("status", ""),
                "prescription_code": msg.get("prescription_code")
            }
        except json.JSONDecodeError:
            pass
    
    # 尝试解析分隔符格式（竖线）
    if "|" in data:
        parts = data.split("|")
        return {
            "status": parts[0],
            "prescription_code": parts[1] if len(parts) > 1 else None
        }
    
    # 尝试解析新格式: {prescription_code}_running-started
    # 检查是否包含 "_running-started" 或 "_running_started"
    if "_running-started" in data:
        parts = data.split("_running-started")
        if len(parts) >= 1:
            return {
                "status": "running-started",
                "prescription_code": parts[0] if parts[0] else None
            }
    
    if "_running_started" in data:
        parts = data.split("_running_started")
        if len(parts) >= 1:
            return {
                "status": "running_started",
                "prescription_code": parts[0] if parts[0] else None
            }
    
    # 纯字符串格式（旧版本兼容）
    return {
        "status": data,
        "prescription_code": None
    }


def test_parse():
    """测试各种消息格式"""
    
    print("=" * 60)
    print("测试 ROS 消息解析逻辑")
    print("=" * 60)
    
    # 测试案例
    test_cases = [
        # 新格式（实际ROS发送格式）
        ("012026070200525_running-started", "running-started", "012026070200525"),
        ("01_20260701_001_42_running-started", "running-started", "01_20260701_001_42"),
        
        # 旧格式（兼容）
        ("running_started", "running_started", None),
        ("012026070200525_running_started", "running_started", "012026070200525"),
        
        # 其他格式
        ("running_started|RX001", "running_started", "RX001"),
        ('{"status": "running_started", "prescription_code": "RX001"}', "running_started", "RX001"),
        
        # 其他状态
        ("running_step1_navigate_to_pharmacy", "running_step1_navigate_to_pharmacy", None),
        ("end", "end", None),
    ]
    
    for data, expected_status, expected_code in test_cases:
        result = parse_ros_message(data)
        status = result["status"]
        prescription_code = result["prescription_code"]
        
        # 验证结果
        status_match = status == expected_status
        code_match = prescription_code == expected_code
        
        print(f"\n输入: {data}")
        print(f"  解析结果:")
        print(f"    status: {status} [PASS]" if status_match else f"    status: {status} [FAIL - 期望: {expected_status}]")
        print(f"    prescription_code: {prescription_code} [PASS]" if code_match else f"    prescription_code: {prescription_code} [FAIL - 期望: {expected_code}]")
        
        if status_match and code_match:
            print(f"  结果: [PASS]")
        else:
            print(f"  结果: [FAIL]")


if __name__ == "__main__":
    test_parse()