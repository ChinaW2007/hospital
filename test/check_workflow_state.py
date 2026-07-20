"""查询workflow_state表数据"""
import sys
sys.path.insert(0, 'hospital/hospital_back')

from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM prescription_workflow_state ORDER BY updated_at DESC LIMIT 5"))
    rows = result.fetchall()
    if rows:
        print("=" * 60)
        print("prescription_workflow_state 表数据（最近5条）:")
        print("=" * 60)
        for row in rows:
            print(f"处方编码: {row[1]}")  # prescription_code
            print(f"节点2状态: {row[5]}, 描述: {row[6]}")  # node2_status, node2_desc
            print(f"节点3状态: {row[7]}, 描述: {row[8]}")  # node3_status, node3_desc
            print(f"节点4状态: {row[9]}, 描述: {row[10]}")  # node4_status, node4_desc
            print(f"ROS状态: {row[11]}")  # ros_status
            print(f"更新时间: {row[12]}")  # updated_at
            print("-" * 60)
    else:
        print("[WARNING] prescription_workflow_state 表无数据")