"""
完整数据库诊断
找出处方数据在哪个数据库
"""
import pymysql
from app.core.config import settings

# 连接配置（不指定数据库）
HIS_DB_CONFIG_NO_DB = {
    "host": settings.his_mysql_host,
    "port": settings.his_mysql_port,
    "user": settings.his_mysql_user,
    "password": settings.his_mysql_pass,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

print("=" * 60)
print("完整数据库诊断")
print(f"MySQL地址: {settings.his_mysql_host}:{settings.his_mysql_port}")
print(f"配置数据库: {settings.his_mysql_db}")
print("=" * 60)

target_prescription_code = "012026070600125"

try:
    conn = pymysql.connect(**HIS_DB_CONFIG_NO_DB, connect_timeout=5)
    print("MySQL连接成功（不指定数据库）")
    
    with conn.cursor() as cursor:
        # 1. 获取所有数据库
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        
        print(f"\n数据库列表: {[db['Database'] for db in databases]}")
        
        # 2. 查找处方编码在哪个数据库
        print(f"\n查找处方编码 '{target_prescription_code}' 在哪个数据库:")
        print("=" * 60)
        
        found_in_db = None
        
        for db in databases:
            db_name = db['Database']
            
            # 跳过系统数据库
            if db_name in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                continue
            
            try:
                cursor.execute(f"USE `{db_name}`")
                
                # 检查是否有 prescriptions 表
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_name = 'prescriptions'
                """, (db_name,))
                
                result = cursor.fetchone()
                
                if result['count'] > 0:
                    print(f"\n数据库 '{db_name}' 有 prescriptions 表")
                    
                    # 查询处方编码
                    cursor.execute("""
                        SELECT prescription_code, status, id, created_at
                        FROM prescriptions
                        WHERE prescription_code = %s
                        LIMIT 1
                    """, (target_prescription_code,))
                    
                    presc_result = cursor.fetchone()
                    
                    if presc_result:
                        print(f"  找到处方: {presc_result}")
                        found_in_db = db_name
                        
                        # 查询药品明细
                        cursor.execute("""
                            SELECT COUNT(*) as count
                            FROM information_schema.tables
                            WHERE table_schema = %s
                            AND table_name = 'prescription_items'
                        """, (db_name,))
                        
                        items_table_result = cursor.fetchone()
                        
                        if items_table_result['count'] > 0:
                            cursor.execute("""
                                SELECT medicine_id, dosage, quantity
                                FROM prescription_items
                                WHERE prescription_id = %s
                                ORDER BY id ASC
                            """, (presc_result['id'],))
                            
                            items = cursor.fetchall()
                            
                            print(f"  药品明细数量: {len(items)}")
                            
                            for item in items:
                                print(f"    medicine_id={item['medicine_id']}")
                        
                        # 查询药品坐标
                        cursor.execute("""
                            SELECT COUNT(*) as count
                            FROM information_schema.tables
                            WHERE table_schema = %s
                            AND table_name = 'medicine_locations'
                        """, (db_name,))
                        
                        loc_table_result = cursor.fetchone()
                        
                        if loc_table_result['count'] > 0:
                            for item in items:
                                cursor.execute("""
                                    SELECT x, y, z, yaw
                                    FROM medicine_locations
                                    WHERE medicine_id = %s
                                    LIMIT 1
                                """, (item['medicine_id'],))
                                
                                loc = cursor.fetchone()
                                
                                if loc:
                                    print(f"      药品坐标: x={loc['x']}, y={loc['y']}, z={loc['z']}, yaw={loc['yaw']}")
                                else:
                                    print(f"      药品没有坐标信息")
                    else:
                        print(f"  处方编码 '{target_prescription_code}' 不存在")
                        
                        # 查询所有处方
                        cursor.execute("""
                            SELECT prescription_code, status
                            FROM prescriptions
                            ORDER BY created_at DESC
                            LIMIT 5
                        """)
                        
                        all_presc = cursor.fetchall()
                        
                        if all_presc:
                            print(f"  该数据库中的处方:")
                            for p in all_presc:
                                print(f"    {p['prescription_code']} (status={p['status']})")
                        else:
                            print(f"  prescriptions 表没有数据")
            
            except Exception as e:
                print(f"  查询数据库 '{db_name}' 失败: {e}")
        
        if found_in_db:
            print("\n" + "=" * 60)
            print(f"处方 '{target_prescription_code}' 在数据库 '{found_in_db}' 中找到")
            print("=" * 60)
            
            if found_in_db != settings.his_mysql_db:
                print(f"\nWARNING: 配置数据库是 '{settings.his_mysql_db}'，但处方在 '{found_in_db}' 中")
                print("建议修改配置文件 config.py:")
                print(f"  his_mysql_db = '{found_in_db}'")
        else:
            print("\n" + "=" * 60)
            print(f"处方 '{target_prescription_code}' 在所有数据库中都没有找到")
            print("=" * 60)
    
    conn.close()
    
except Exception as e:
    print(f"诊断失败: {e}")
    import traceback
    traceback.print_exc()