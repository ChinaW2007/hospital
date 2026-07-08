"""
测试数据库查询药品坐标
检查是否能正确获取真数据
"""
import pymysql
from app.core.config import settings

# HIS 数据库连接配置（不指定数据库，查询所有数据库）
HIS_DB_CONFIG_NO_DB = {
    "host": settings.his_mysql_host,
    "port": settings.his_mysql_port,
    "user": settings.his_mysql_user,
    "password": settings.his_mysql_pass,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

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
print("测试数据库查询药品坐标")
print("=" * 60)
print(f"MySQL地址: {settings.his_mysql_host}:{settings.his_mysql_port}")
print(f"配置数据库: {settings.his_mysql_db}")
print("=" * 60)

# ===== 第一步：查询所有数据库 =====
print("\n" + "=" * 60)
print("第一步：查询所有数据库")
print("=" * 60)

try:
    conn = pymysql.connect(**HIS_DB_CONFIG_NO_DB, connect_timeout=5)
    print("MySQL连接成功（未指定数据库）")
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        
        print(f"数据库列表:")
        for db in databases:
            print(f"  - {db['Database']}")
    
    conn.close()
except Exception as e:
    print(f"查询数据库列表失败: {e}")

# ===== 第二步：查询每个数据库中的表 =====
print("\n" + "=" * 60)
print("第二步：查询每个数据库中的 prescriptions 表")
print("=" * 60)

try:
    conn = pymysql.connect(**HIS_DB_CONFIG_NO_DB, connect_timeout=5)
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        
        for db in databases:
            db_name = db['Database']
            
            # 查询该数据库是否有 prescriptions 表
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = '{db_name}'
                AND table_name = 'prescriptions'
            """)
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print(f"\n数据库 '{db_name}' 有 prescriptions 表")
                
                # 查询该数据库中的 prescriptions 数据
                cursor.execute(f"USE `{db_name}`")
                cursor.execute("SELECT COUNT(*) as count FROM prescriptions")
                count_result = cursor.fetchone()
                print(f"  prescriptions 表有 {count_result['count']} 条数据")
                
                if count_result['count'] > 0:
                    # 查询最新的处方
                    cursor.execute("""
                        SELECT id, prescription_code, status, created_at
                        FROM prescriptions
                        ORDER BY created_at DESC
                        LIMIT 3
                    """)
                    prescriptions = cursor.fetchall()
                    
                    for p in prescriptions:
                        print(f"  处方: id={p['id']}, prescription_code={p['prescription_code']}, status={p['status']}")
                        
                        # 查询该处方是否有药品明细
                        cursor.execute(f"""
                            SELECT COUNT(*) as count
                            FROM information_schema.tables
                            WHERE table_schema = '{db_name}'
                            AND table_name = 'prescription_items'
                        """)
                        items_table_result = cursor.fetchone()
                        
                        if items_table_result['count'] > 0:
                            cursor.execute("""
                                SELECT id, medicine_id, dosage, quantity
                                FROM prescription_items
                                WHERE prescription_id = %s
                            """, (p['id'],))
                            items = cursor.fetchall()
                            
                            print(f"    药品明细数量: {len(items)}")
                            for item in items:
                                print(f"      medicine_id={item['medicine_id']}")
    
    conn.close()
except Exception as e:
    print(f"查询表失败: {e}")
    import traceback
    traceback.print_exc()

# 测试处方编码
test_prescription_codes = [
    "012026070600125",
    "012026070600132",
]

try:
    print("\n正在连接 MySQL...")
    conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
    print("MySQL连接成功")
    
    with conn.cursor() as cursor:
        # 1. 查询 prescriptions 表
        print("\n" + "=" * 60)
        print("查询 prescriptions 表")
        print("=" * 60)
        
        cursor.execute("""
            SELECT id, prescription_code, status, created_at
            FROM prescriptions
            ORDER BY created_at DESC
            LIMIT 5
        """)
        prescriptions = cursor.fetchall()
        
        print(f"查询结果数量: {len(prescriptions)}")
        for i, p in enumerate(prescriptions):
            print(f"处方{i+1}: id={p['id']}, prescription_code={p['prescription_code']}, status={p['status']}")
        
        # 2. 查询 prescription_items 表
        print("\n" + "=" * 60)
        print("查询 prescription_items 表")
        print("=" * 60)
        
        cursor.execute("""
            SELECT id, prescription_id, medicine_id, dosage, quantity
            FROM prescription_items
            ORDER BY id DESC
            LIMIT 10
        """)
        items = cursor.fetchall()
        
        print(f"查询结果数量: {len(items)}")
        for i, item in enumerate(items):
            print(f"药品明细{i+1}: id={item['id']}, prescription_id={item['prescription_id']}, medicine_id={item['medicine_id']}")
        
        # 3. 查询 medicine_locations 表
        print("\n" + "=" * 60)
        print("查询 medicine_locations 表")
        print("=" * 60)
        
        cursor.execute("""
            SELECT medicine_id, x, y, z
            FROM medicine_locations
            ORDER BY medicine_id ASC
        """)
        locations = cursor.fetchall()
        
        print(f"查询结果数量: {len(locations)}")
        for i, loc in enumerate(locations):
            print(f"药品坐标{i+1}: medicine_id={loc['medicine_id']}, x={loc['x']}, y={loc['y']}, z={loc['z']}")
        
        # 4. 测试完整的联合查询（针对测试处方）
        print("\n" + "=" * 60)
        print("测试联合查询药品坐标")
        print("=" * 60)
        
        for prescription_code in test_prescription_codes:
            print(f"\n处方编码: {prescription_code}")
            
            sql_query = """
                SELECT 
                    ml.medicine_id,
                    ml.x,
                    ml.y,
                    ml.z
                FROM prescriptions p
                JOIN prescription_items pi ON p.id = pi.prescription_id
                JOIN medicine_locations ml ON pi.medicine_id = ml.medicine_id
                WHERE p.prescription_code = %s
                ORDER BY pi.id ASC
            """
            
            cursor.execute(sql_query, (prescription_code,))
            results = cursor.fetchall()
            
            print(f"查询结果数量: {len(results)}")
            
            if results:
                for i, row in enumerate(results):
                    print(f"  药品{i+1}: medicine_id={row['medicine_id']}, x={row['x']}, y={row['y']}, z={row['z']}")
            else:
                print("  未找到药品坐标信息")
                
                # 检查处方是否存在
                cursor.execute("SELECT id FROM prescriptions WHERE prescription_code = %s", (prescription_code,))
                presc = cursor.fetchone()
                
                if presc:
                    print(f"  处方存在: id={presc['id']}")
                    
                    # 检查处方是否有药品明细
                    cursor.execute("SELECT medicine_id FROM prescription_items WHERE prescription_id = %s", (presc['id'],))
                    items = cursor.fetchall()
                    
                    if items:
                        print(f"  处方有 {len(items)} 个药品明细:")
                        for item in items:
                            print(f"    medicine_id={item['medicine_id']}")
                            
                            # 检查药品是否有坐标
                            cursor.execute("SELECT x, y, z FROM medicine_locations WHERE medicine_id = %s", (item['medicine_id'],))
                            loc = cursor.fetchone()
                            
                            if loc:
                                print(f"      坐标: x={loc['x']}, y={loc['y']}, z={loc['z']}")
                            else:
                                print(f"      药品没有坐标信息!")
                    else:
                        print("  处方没有药品明细!")
                else:
                    print("  处方不存在!")
    
    conn.close()
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
except pymysql.Error as e:
    print(f"\nMySQL错误: {e}")
    print(f"错误代码: {e.args[0]}")
    print(f"错误信息: {e.args[1]}")
except Exception as e:
    print(f"\n测试失败: {e}")
    print(f"错误类型: {type(e).__name__}")