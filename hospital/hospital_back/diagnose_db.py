"""
诊断数据库数据
检查处方、药品明细、药品坐标是否存在
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
print("开始诊断数据库")
print(f"MySQL地址: {settings.his_mysql_host}:{settings.his_mysql_port}")
print(f"数据库: {settings.his_mysql_db}")
print("=" * 60)

try:
    conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
    print("MySQL连接成功")
    
    with conn.cursor() as cursor:
        # 1. 检查 medicine_locations 表结构（字段名）
        print("\n[检查] medicine_locations 表结构:")
        cursor.execute("DESCRIBE medicine_locations")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  字段: {col['Field']}, 类型: {col['Type']}")
        
        # 2. 检查 prescriptions 表是否有数据
        print("\n[检查] prescriptions 表数据:")
        cursor.execute("SELECT prescription_code, status FROM prescriptions LIMIT 5")
        prescriptions = cursor.fetchall()
        print(f"  数量: {len(prescriptions)}")
        for p in prescriptions:
            print(f"    prescription_code: {p['prescription_code']}, status: {p['status']}")
        
        # 3. 检查处方 "012026070600125" 是否存在
        print("\n[检查] 处方 012026070600125 是否存在:")
        cursor.execute("SELECT * FROM prescriptions WHERE prescription_code = '012026070600125'")
        prescription = cursor.fetchone()
        if prescription:
            print(f"  找到处方: {prescription}")
        else:
            print(f"  未找到处方!")
        
        # 4. 检查 prescription_items 表是否有数据
        print("\n[检查] prescription_items 表数据:")
        cursor.execute("SELECT * FROM prescription_items LIMIT 5")
        items = cursor.fetchall()
        print(f"  数量: {len(items)}")
        for item in items:
            print(f"    prescription_id: {item['prescription_id']}, medicine_id: {item['medicine_id']}")
        
        # 5. 检查 medicine_locations 表是否有数据
        print("\n[检查] medicine_locations 表数据:")
        cursor.execute("SELECT * FROM medicine_locations LIMIT 5")
        locations = cursor.fetchall()
        print(f"  数量: {len(locations)}")
        for loc in locations:
            print(f"    medicine_id: {loc['medicine_id']}, x: {loc.get('x')}, y: {loc.get('y')}, z: {loc.get('z')}")
            # 打印所有字段
            print(f"    所有字段: {loc}")
        
        # 6. 执行完整的联合查询（模拟系统查询）
        print("\n[检查] 执行完整联合查询:")
        sql = """
            SELECT 
                pi.medicine_id,
                MIN(ml.x) as x,
                MIN(ml.y) as y,
                MIN(ml.z) as z,
                MIN(ml.yam) as yam
            FROM prescriptions p
            JOIN prescription_items pi ON p.id = pi.prescription_id
            JOIN medicine_locations ml ON pi.medicine_id = ml.medicine_id
            WHERE p.prescription_code = '012026070600125'
            GROUP BY pi.medicine_id
            ORDER BY pi.medicine_id ASC
        """
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            print(f"  查询结果数量: {len(results)}")
            for row in results:
                print(f"    medicine_id: {row['medicine_id']}, x: {row['x']}, y: {row['y']}, z: {row['z']}, yam: {row.get('yam')}")
        except pymysql.Error as e:
            print(f"  SQL执行失败: {e}")
            print(f"  可能字段名错误，尝试查询所有字段:")
            # 尝试查询所有字段
            cursor.execute("SELECT * FROM medicine_locations LIMIT 1")
            sample = cursor.fetchone()
            print(f"  示例数据: {sample}")
            print(f"  字段列表: {list(sample.keys()) if sample else '无数据'}")
    
    conn.close()
    print("\n诊断完成")
    
except pymysql.Error as e:
    print(f"MySQL错误: {e}")
except Exception as e:
    print(f"异常: {e}")