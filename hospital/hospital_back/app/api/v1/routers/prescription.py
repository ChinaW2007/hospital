import pymysql
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from app.core.config import settings

router = APIRouter()

# HIS 数据库连接配置
HIS_DB_CONFIG = {
    "host": settings.his_mysql_host,
    "port": settings.his_mysql_port,
    "user": settings.his_mysql_user,
    "password": settings.his_mysql_pass,
    "database": settings.his_mysql_db,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# 本地 SQLite 数据库连接（用于查询 prescription_workflow_state）
LOCAL_ENGINE = create_engine(settings.database_url)

# 全局标记：MySQL 是否可用
_mysql_available = None
_mysql_check_time = None
_mysql_check_interval = 30  # 每 30 秒重新检查一次


def _check_mysql():
    """检测 HIS MySQL 数据库是否可用（带定期重试机制）"""
    global _mysql_available, _mysql_check_time
    import time
    current_time = time.time()
    
    # 如果缓存有效且未过期，直接返回
    if _mysql_available is not None and _mysql_check_time is not None:
        if current_time - _mysql_check_time < _mysql_check_interval:
            return _mysql_available
    
    # 重新检查 MySQL 连接
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=3)
        conn.close()
        _mysql_available = True
        _mysql_check_time = current_time
        return True
    except Exception as e:
        _mysql_available = False
        _mysql_check_time = current_time
        return False


def _get_his_connection():
    """获取 HIS MySQL 数据库连接"""
    return pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)


@router.get("/prescriptions/recent")
def get_recent_prescriptions(limit: int = 20):
    """获取最近的处方列表（含药品明细）"""
    if not _check_mysql():
        return {"total": 0, "pending": 0, "approved": 0, "dispensed": 0, "list": []}
    try:
        conn = _get_his_connection()
        with conn.cursor() as cursor:
            # 查询处方及关联的病人、医生信息
            cursor.execute("""
                SELECT
                    p.id,
                    p.patient_id,
                    p.doctor_id,
                    p.diagnosis,
                    p.status,
                    p.total_amount,
                    p.prescription_code,
                    p.created_at,
                    p.reviewed_at,
                    p.dispensed_at,
                    pt.name AS patient_name,
                    u.real_name AS doctor_name
                FROM prescriptions p
                LEFT JOIN patients pt ON p.patient_id = pt.id
                LEFT JOIN users u ON p.doctor_id = u.id
                ORDER BY p.created_at DESC
                LIMIT %s
            """, (limit,))
            prescriptions = cursor.fetchall()

            # 批量查询所有处方的药品明细
            if not prescriptions:
                return {"total": 0, "list": []}

            presc_ids = [p["id"] for p in prescriptions]
            placeholders = ",".join(["%s"] * len(presc_ids))
            cursor.execute(f"""
                SELECT
                    pi.prescription_id,
                    pi.medicine_id,
                    pi.dosage,
                    pi.usage_method,
                    pi.frequency,
                    pi.days,
                    pi.quantity,
                    m.name AS medicine_name,
                    m.specification,
                    m.unit,
                    m.price
                FROM prescription_items pi
                LEFT JOIN medicines m ON pi.medicine_id = m.id
                WHERE pi.prescription_id IN ({placeholders})
            """, presc_ids)
            items = cursor.fetchall()

            # 按处方 ID 分组药品明细
            items_by_prescription = {}
            for item in items:
                pid = item["prescription_id"]
                if pid not in items_by_prescription:
                    items_by_prescription[pid] = []
                items_by_prescription[pid].append(item)

            # 组装最终结果
            result = []
            for p in prescriptions:
                result.append({
                    "id": p["id"],
                    "prescription_code": p.get("prescription_code", ""),
                    "patient_name": p["patient_name"],
                    "doctor_name": p["doctor_name"],
                    "diagnosis": p["diagnosis"],
                    "status": p["status"],
                    "total_amount": float(p["total_amount"]) if p["total_amount"] else 0,
                    "created_at": str(p["created_at"]),
                    "reviewed_at": str(p["reviewed_at"]) if p["reviewed_at"] else None,
                    "dispensed_at": str(p["dispensed_at"]) if p["dispensed_at"] else None,
                    "items": items_by_prescription.get(p["id"], []),
                })

            return {
                "total": len(result),
                "pending": sum(1 for r in result if r["status"] == "pending"),
                "approved": sum(1 for r in result if r["status"] == "approved"),
                "dispensed": sum(1 for r in result if r["status"] == "dispensed"),
                "list": result,
            }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")
    finally:
        if "conn" in locals():
            conn.close()


@router.get("/prescriptions/stats")
def get_prescription_stats():
    """获取处方统计概览"""
    if not _check_mysql():
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "dispensed": 0, "total_amount": 0, "today_count": 0}
    try:
        conn = _get_his_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected,
                    SUM(CASE WHEN status='dispensed' THEN 1 ELSE 0 END) AS dispensed,
                    COALESCE(SUM(total_amount), 0) AS total_amount,
                    SUM(CASE WHEN DATE(created_at)=CURDATE() THEN 1 ELSE 0 END) AS today_count
                FROM prescriptions
            """)
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "approved": row["approved"] or 0,
                "rejected": row["rejected"] or 0,
                "dispensed": row["dispensed"] or 0,
                "total_amount": float(row["total_amount"]) if row["total_amount"] else 0,
                "today_count": row["today_count"] or 0,
            }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")
    finally:
        if "conn" in locals():
            conn.close()


@router.get("/prescriptions/progress")
def get_prescriptions_progress(limit: int = 20):
    """
    获取每个处方的4节点进度条数据

    每个处方对应一条进度条：
    - 节点1（开具处方）：药师确认处方后高亮
    - 节点2（任务确认）：ROS 任务启动后高亮（优先使用 prescription_workflow_state 表）
    - 节点3（扫码复合）：当前处方全部追溯码扫到第2次后高亮
    - 节点4（站台交互）：当前处方全部追溯码扫到第3次后高亮

    返回每个处方的 prescription_code、patient_name、各节点状态
    """
    if not _check_mysql():
        return {"total": 0, "list": []}
    try:
        conn = _get_his_connection()
        with conn.cursor() as cursor:
            # 查询最近的处方（含患者信息）
            cursor.execute("""
                SELECT
                    p.id,
                    p.prescription_code,
                    p.status,
                    p.created_at,
                    pt.name AS patient_name,
                    u.real_name AS doctor_name
                FROM prescriptions p
                LEFT JOIN patients pt ON p.patient_id = pt.id
                LEFT JOIN users u ON p.doctor_id = u.id
                ORDER BY p.created_at DESC
                LIMIT %s
            """, (limit,))
            prescriptions = cursor.fetchall()

            if not prescriptions:
                return {"total": 0, "list": []}

            result = []
            for presc in prescriptions:
                presc_id = presc["id"]
                prescription_code = presc["prescription_code"]

                # 查询该处方关联的追溯码扫描状态
                try:
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total_codes,
                            SUM(CASE WHEN scan1_time IS NOT NULL THEN 1 ELSE 0 END) as scanned_1,
                            SUM(CASE WHEN scan2_time IS NOT NULL THEN 1 ELSE 0 END) as scanned_2,
                            SUM(CASE WHEN scan3_time IS NOT NULL THEN 1 ELSE 0 END) as scanned_3
                        FROM (
                            SELECT DISTINCT tc.id, tc.scan1_time, tc.scan2_time, tc.scan3_time
                            FROM medicine_trace_codes tc
                            LEFT JOIN prescription_trace_codes ptc ON ptc.trace_code_id = tc.id
                            WHERE ptc.prescription_id = %s OR tc.prescription_id = %s
                        ) linked_codes
                    """, (presc_id, presc_id))
                except pymysql.Error:
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total_codes,
                            SUM(CASE WHEN scan1_time IS NOT NULL THEN 1 ELSE 0 END) as scanned_1,
                            SUM(CASE WHEN scan2_time IS NOT NULL THEN 1 ELSE 0 END) as scanned_2,
                            SUM(CASE WHEN scan3_time IS NOT NULL THEN 1 ELSE 0 END) as scanned_3
                        FROM medicine_trace_codes
                        WHERE prescription_id = %s
                    """, (presc_id,))
                scan_stats = cursor.fetchone()

                total_codes = scan_stats["total_codes"] or 0
                scanned_1 = scan_stats["scanned_1"] or 0
                scanned_2 = scan_stats["scanned_2"] or 0
                scanned_3 = scan_stats["scanned_3"] or 0

                # 查询本地数据库的 prescription_workflow_state 表
                workflow_state = None
                try:
                    with LOCAL_ENGINE.connect() as local_conn:
                        ws_result = local_conn.execute(
                            text("SELECT * FROM prescription_workflow_state WHERE prescription_code = :code"),
                            {"code": prescription_code}
                        )
                        ws_row = ws_result.fetchone()
                        if ws_row:
                            # 将结果转换为字典（列索引已修正）
                            # 表结构：id(0), prescription_code(1), prescription_id(2), current_node(3),
                            #         node2_status(4), node2_desc(5), node3_status(6), node3_desc(7),
                            #         node4_status(8), node4_desc(9), ros_status(10), updated_at(11)
                            workflow_state = {
                                "current_node": ws_row[3],
                                "node2_status": ws_row[4],
                                "node2_desc": ws_row[5],
                                "node3_status": ws_row[6],
                                "node3_desc": ws_row[7],
                                "node4_status": ws_row[8],
                                "node4_desc": ws_row[9],
                                "ros_status": ws_row[10],
                            }
                except Exception as e:
                    # 表不存在或其他错误，忽略
                    pass

                # 计算4个节点的状态
                # 节点1：开具处方 - 只要处方存在（医生已下药），就是已完成（绿色）
                node1_completed = presc["status"] is not None  # 处方存在即为完成
                node1_active = False  # 节点1不再有"进行中"状态

                # 节点2：任务确认 - 优先使用 workflow_state 表的数据
                # 但如果节点1已完成，节点2不能是 pending，必须是 active 或 completed
                if workflow_state and workflow_state.get("node2_status"):
                    node2_status = workflow_state["node2_status"]
                    if node2_status == "completed":
                        node2_completed = True
                        node2_active = False
                        node2_desc = workflow_state.get("node2_desc", "任务确认完成")
                    elif node2_status == "active":
                        node2_completed = False
                        node2_active = True
                        node2_desc = workflow_state.get("node2_desc", "任务进行中")
                    else:
                        # 如果节点1已完成，节点2不能是 pending，必须是 active
                        if node1_completed:
                            node2_completed = False
                            node2_active = True
                            node2_desc = "等待任务确认"
                        else:
                            # 节点1未完成，节点2为 pending
                            node2_completed = False
                            node2_active = False
                            node2_desc = "等待开具处方"
                else:
                    # 没有 workflow_state 数据（未收到 ROS 状态），节点2为进行中
                    # 或使用追溯码判断（已扫码识别则为完成）
                    node2_completed = scanned_1 > 0
                    node2_active = node1_completed and not node2_completed  # 节点1完成后，节点2为进行中
                    node2_desc = f"已识别 {scanned_1}/{total_codes}" if node2_completed else "等待任务确认"

                has_trace_codes = total_codes > 0

                # 节点3：扫码复合 - 当前处方全部追溯码扫到第2次后完成
                node3_completed = has_trace_codes and scanned_2 == total_codes
                node3_active = node2_completed and not node3_completed
                if node3_completed:
                    node3_desc = f"已出库 {scanned_2}/{total_codes}"
                elif node3_active:
                    node3_desc = f"已出库 {scanned_2}/{total_codes}" if has_trace_codes else "等待处方追溯码"
                else:
                    node3_desc = "等待扫码复核"

                # 节点4：站台交互 - 当前处方全部追溯码扫到第3次后完成
                node4_completed = has_trace_codes and scanned_3 == total_codes
                node4_active = node3_completed and not node4_completed
                if node4_completed:
                    node4_desc = f"已完成 {scanned_3}/{total_codes}"
                elif node4_active:
                    node4_desc = f"已完成 {scanned_3}/{total_codes}"
                else:
                    node4_desc = "等待站台交互"

                # 判断当前活跃步骤
                if not node1_completed:
                    current_step = 1
                elif not node2_completed:
                    current_step = 2
                elif not node3_completed:
                    current_step = 3
                elif not node4_completed:
                    current_step = 4
                else:
                    current_step = 5  # 全部完成

                # 计算整体进度百分比
                progress = 0
                if node1_completed: progress += 25
                elif node1_active: progress += 8
                if node2_completed: progress += 25
                elif node2_active: progress += 8
                if node3_completed: progress += 25
                elif node3_active: progress += 8
                if node4_completed: progress += 25
                elif node4_active: progress += 8

                result.append({
                    "prescription_id": presc_id,
                    "prescription_code": presc.get("prescription_code", ""),
                    "patient_name": presc["patient_name"],
                    "doctor_name": presc["doctor_name"],
                    "status": presc["status"],
                    "created_at": str(presc["created_at"]),
                    "current_step": current_step,
                    "progress": progress,
                    "scan_stats": {
                        "total": total_codes,
                        "scanned_1": scanned_1,
                        "scanned_2": scanned_2,
                        "scanned_3": scanned_3,
                    },
                    "steps": [
                        {
                            "id": 1,
                            "name": "开具处方",
                            "status": "completed" if node1_completed else "pending",
                            "desc": "医生已开具处方" if node1_completed else "待开具",
                        },
                        {
                            "id": 2,
                            "name": "任务确认",
                            "status": "completed" if node2_completed else ("active" if node2_active else "pending"),
                            "desc": node2_desc,
                        },
                        {
                            "id": 3,
                            "name": "扫码复合",
                            "status": "completed" if node3_completed else ("active" if node3_active else "pending"),
                            "desc": node3_desc,
                        },
                        {
                            "id": 4,
                            "name": "站台交互",
                            "status": "completed" if node4_completed else ("active" if node4_active else "pending"),
                            "desc": node4_desc,
                        },
                    ],
                })

            return {
                "total": len(result),
                "list": result,
            }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")
    finally:
        if "conn" in locals():
            conn.close()


@router.get("/prescriptions/items/latest")
def get_latest_prescription_items(limit: int = 30):
    """获取最新的处方药品明细（用于实时下药监控）"""
    if not _check_mysql():
        return {"total": 0, "list": []}
    try:
        conn = _get_his_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    pi.id,
                    pi.prescription_id,
                    pi.medicine_id,
                    pi.dosage,
                    pi.usage_method,
                    pi.frequency,
                    pi.days,
                    pi.quantity,
                    m.name AS medicine_name,
                    m.specification,
                    m.unit,
                    m.price,
                    m.category,
                    p.status AS prescription_status,
                    p.prescription_code,
                    p.created_at AS prescription_created_at,
                    pt.name AS patient_name,
                    u.real_name AS doctor_name
                FROM prescription_items pi
                LEFT JOIN medicines m ON pi.medicine_id = m.id
                LEFT JOIN prescriptions p ON pi.prescription_id = p.id
                LEFT JOIN patients pt ON p.patient_id = pt.id
                LEFT JOIN users u ON p.doctor_id = u.id
                ORDER BY p.created_at DESC, pi.id ASC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "prescription_id": row["prescription_id"],
                    "prescription_code": row.get("prescription_code", ""),
                    "medicine_id": row["medicine_id"],
                    "medicine_name": row["medicine_name"],
                    "specification": row["specification"],
                    "unit": row["unit"],
                    "price": float(row["price"]) if row["price"] else 0,
                    "category": row["category"],
                    "dosage": row["dosage"],
                    "usage_method": row["usage_method"],
                    "frequency": row["frequency"],
                    "days": row["days"],
                    "quantity": row["quantity"],
                    "prescription_status": row["prescription_status"],
                    "patient_name": row["patient_name"],
                    "doctor_name": row["doctor_name"],
                    "created_at": str(row["prescription_created_at"]),
                })

            return {
                "total": len(result),
                "list": result,
            }
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")
    finally:
        if "conn" in locals():
            conn.close()
