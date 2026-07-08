"""
药品运输流程跟踪 API
追踪处方从HIS同步到患者领药的完整流程
"""
import pymysql
from fastapi import APIRouter, HTTPException
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

# 全局标记：MySQL 是否可用
_mysql_available = None


def _check_mysql():
    """检测 HIS MySQL 数据库是否可用"""
    global _mysql_available
    if _mysql_available is not None:
        return _mysql_available
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=3)
        conn.close()
        _mysql_available = True
        return True
    except Exception:
        _mysql_available = False
        return False


def _get_his_connection():
    """获取 HIS MySQL 数据库连接"""
    return pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)


@router.get("/workflow/status")
def get_workflow_status():
    """
    获取当前药品运输流程的整体状态
    
    流程步骤：
    1. 处方同步：HIS数据同步完成
    2. 智能分拣：机械手臂落药完成
    3. 扫码复核：等待药剂师复核
    4. 窗口交付：患者窗口扫码领药
    
    返回：
    - current_step: 当前正在进行的步骤编号（1-4）
    - steps: 各步骤的详细状态
    - progress: 整体进度百分比
    """
    if not _check_mysql():
        # 数据库不可用时返回初始状态
        return {
            "current_step": 1,
            "progress": 0,
            "steps": [
                {"id": 1, "name": "处方同步", "status": "pending", "desc": "等待HIS数据同步"},
                {"id": 2, "name": "智能分拣", "status": "pending", "desc": "等待开始"},
                {"id": 3, "name": "扫码复核", "status": "pending", "desc": "等待开始"},
                {"id": 4, "name": "窗口交付", "status": "pending", "desc": "等待开始"},
            ]
        }
    
    try:
        conn = _get_his_connection()
        with conn.cursor() as cursor:
            # 查询处方状态统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN status = 'dispensed' THEN 1 ELSE 0 END) as dispensed,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM prescriptions
            """)
            presc_stats = cursor.fetchone()
            
            # 查询药品追溯码扫描状态
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'scanned_identify' THEN 1 ELSE 0 END) as identified,
                    SUM(CASE WHEN status = 'scanned_outbound' THEN 1 ELSE 0 END) as outbound,
                    SUM(CASE WHEN status = 'scanned_confirm' THEN 1 ELSE 0 END) as confirmed
                FROM medicine_trace_codes
            """)
            trace_stats = cursor.fetchone()
            
            # 计算各步骤状态
            # 新的状态逻辑：只有当前步骤是active，之前的是completed，之后的是pending
            
            # 步骤1：处方同步
            step1_completed = presc_stats["total"] > 0
            
            # 步骤2：智能分拣
            step2_completed = trace_stats["pending"] == 0
            
            # 步骤3：扫码复核
            step3_completed = trace_stats["outbound"] > 0 and trace_stats["outbound"] == trace_stats["identified"]
            
            # 步骤4：窗口交付
            step4_completed = trace_stats["confirmed"] > 0 and trace_stats["confirmed"] == trace_stats["total"]
            
            # 确定当前步骤（第一个未完成的步骤）
            current_step_num = 1
            if step1_completed:
                current_step_num = 2
            if step2_completed:
                current_step_num = 3
            if step3_completed:
                current_step_num = 4
            if step4_completed:
                current_step_num = 5  # 全部完成
            
            # 设置各步骤状态
            # 步骤1
            if step1_completed:
                step1_status = "completed"
                step1_desc = "HIS数据同步完成"
            elif current_step_num == 1:
                step1_status = "active"
                step1_desc = "等待HIS数据同步"
            else:
                step1_status = "pending"
                step1_desc = "等待HIS数据同步"
            
            # 步骤2
            if step2_completed:
                step2_status = "completed"
                step2_desc = "机械手臂落药完成"
            elif current_step_num == 2:
                step2_status = "active"
                if trace_stats["identified"] > 0:
                    progress_pct = int(trace_stats["identified"] / trace_stats["total"] * 100) if trace_stats["total"] > 0 else 0
                    step2_desc = f"机械手臂正在落药 ({progress_pct}%)"
                else:
                    step2_desc = "等待机械手臂开始"
            else:
                step2_status = "pending"
                step2_desc = "等待开始"
            
            # 步骤3
            if step3_completed:
                step3_status = "completed"
                step3_desc = "药剂师复核完成"
            elif current_step_num == 3:
                step3_status = "active"
                step3_desc = "等待药剂师复核药物"
            else:
                step3_status = "pending"
                step3_desc = "等待开始"
            
            # 步骤4
            if step4_completed:
                step4_status = "completed"
                step4_desc = "患者已扫码领药"
            elif current_step_num == 4:
                step4_status = "active"
                if trace_stats["confirmed"] > 0:
                    confirmed_pct = int(trace_stats["confirmed"] / trace_stats["total"] * 100) if trace_stats["total"] > 0 else 0
                    step4_desc = f"患者正在领药 ({confirmed_pct}%)"
                else:
                    step4_desc = "等待患者扫码领药"
            else:
                step4_status = "pending"
                step4_desc = "等待开始"
            
            # 计算整体进度
            progress = 0
            if step1_completed:
                progress += 25
            if step2_completed:
                progress += 25
            elif current_step_num == 2:
                progress += 12
            if step3_completed:
                progress += 25
            elif current_step_num == 3:
                progress += 12
            if step4_completed:
                progress += 25
            elif current_step_num == 4:
                progress += 12
            
            return {
                "current_step": current_step_num,
                "progress": progress,
                "prescription_stats": {
                    "total": presc_stats["total"],
                    "pending": presc_stats["pending"],
                    "approved": presc_stats["approved"],
                    "dispensed": presc_stats["dispensed"],
                },
                "trace_stats": {
                    "total": trace_stats["total"],
                    "pending": trace_stats["pending"],
                    "identified": trace_stats["identified"],
                    "outbound": trace_stats["outbound"],
                    "confirmed": trace_stats["confirmed"],
                },
                "steps": [
                    {"id": 1, "name": "处方同步", "status": step1_status, "desc": step1_desc},
                    {"id": 2, "name": "智能分拣", "status": step2_status, "desc": step2_desc},
                    {"id": 3, "name": "扫码复核", "status": step3_status, "desc": step3_desc},
                    {"id": 4, "name": "窗口交付", "status": step4_status, "desc": step4_desc},
                ]
            }
    
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")
    finally:
        if "conn" in locals():
            conn.close()