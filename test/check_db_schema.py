"""检查数据库表的列顺序"""
import sqlite3

db_path = r"d:\Demos\hospital\hospital\hospital_back\app.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取表结构
cursor.execute("PRAGMA table_info(prescription_workflow_state)")
columns = cursor.fetchall()

print("=" * 60)
print("prescription_workflow_state 表结构:")
print("=" * 60)
for col in columns:
    print(f"列ID: {col[0]}, 列名: {col[1]}, 类型: {col[2]}")

print("\n" + "=" * 60)
print("实际数据示例:")
print("=" * 60)
cursor.execute("SELECT * FROM prescription_workflow_state LIMIT 1")
row = cursor.fetchone()
if row:
    for i, col in enumerate(columns):
        print(f"{col[1]} (索引{i}): {row[i]}")

conn.close()