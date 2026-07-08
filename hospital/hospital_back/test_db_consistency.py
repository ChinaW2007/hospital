"""
检查 medicine_locations 表数据一致性
"""
import pymysql
from app.core.config import settings

HIS_DB_CONFIG = {
    "host": settings.his_mysql_host,
    "port": settings.his_mysql_port,
    "user": settings.his_mysql_user,
    "password": settings.his_mysql_pass,
    "database": settings.his_mysql_db,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

print("=" * 60)
print("检查 medicine_locations 表数据一致性")
print("=" * 60)

try:
    conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
    print("MySQL连接成功")
    
    with conn.cursor() as cursor:
        # 1. 查询所有数据（不聚合）
        print("\n" + "=" * 60)
        print("查询 medicine_locations 表所有数据")
        print("=" * 60)
        
        cursor.execute("""
            SELECT medicine_id, x, y, z, yaw
            FROM medicine_locations
            ORDER BY medicine_id ASC
        """)
        all_data = cursor.fetchall()
        
        print(f"总记录数: {len(all_data)}")
        
        # 检查是否有重复的 medicine_id
        medicine_id_counts = {}
        for row in all_data:
            med_id = row['medicine_id']
            if med_id not in medicine_id_counts:
                medicine_id_counts[med_id] = []
            medicine_id_counts[med_id].append(row)
        
        print("\n按 medicine_id 分组:")
        for med_id, rows in sorted(medicine_id_counts.items()):
            print(f"\nmedicine_id={med_id} (有{len(rows)}条记录):")
            for i, row in enumerate(rows):
                print(f"  记录{i+1}: x={row['x']}, y={row['y']}, z={row['z']}, yaw={row['yaw']}")
            
            # 检查数据是否一致
            if len(rows) > 1:
                first_row = rows[0]
                all_same = all(
                    row['x'] == first_row['x'] and 
                    row['y'] == first_row['y'] and 
                    row['z'] == first_row['z'] and 
                    row['yaw'] == first_row['yaw']
                    for row in rows
                )
                if not all_same:
                    print(f"  WARNING: 数据不一致!")
        
        # 2. 测试 MIN() 函数结果是否稳定
        print("\n" + "=" * 60)
        print("测试 MIN() 函数结果稳定性")
        print("=" * 60)
        
        for _ in range(3):
            cursor.execute("""
                SELECT 
                    medicine_id,
                    MIN(x) as x,
                    MIN(y) as y,
                    MIN(z) as z,
                    MIN(yaw) as yaw
                FROM medicine_locations
                GROUP BY medicine_id
                ORDER BY medicine_id ASC
            """)
            min_results = cursor.fetchall()
            
            print(f"\n查询结果:")
            for row in min_results[:5]:  # 只显示前5个
                print(f"  medicine_id={row['medicine_id']}, x={row['x']}, y={row['y']}, z={row['z']}, yaw={row['yaw']}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)
    
except Exception as e:
    print(f"查询失败: {e}")
    import traceback
    traceback.print_exc()