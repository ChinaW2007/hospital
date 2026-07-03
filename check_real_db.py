"""直接查询app.db数据库文件"""
import sqlite3

db_path = r"d:\Demos\hospital\hospital\hospital_back\app.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询prescription_workflow_state表
cursor.execute("SELECT * FROM prescription_workflow_state ORDER BY updated_at DESC LIMIT 5")
rows = cursor.fetchall()

if rows:
    print("=" * 60)
    print("prescription_workflow_state 表数据（最近5条）:")
    print("=" * 60)
    for row in rows:
        print(f"处方编码: {row[1]}")
        print(f"节点2状态: {row[5]}, 描述: {row[6]}")
        print(f"节点3状态: {row[7]}, 描述: {row[8]}")
        print(f"节点4状态: {row[9]}, 描述: {row[10]}")
        print(f"ROS状态: {row[11]}")
        print(f"更新时间: {row[12]}")
        print("-" * 60)
else:
    print("[WARNING] prescription_workflow_state 表无数据")

conn.close()