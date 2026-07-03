"""创建 prescription_workflow_state 表"""
import sys
sys.path.insert(0, 'hospital/hospital_back')

from app.db import models
from app.db.session import engine

# 创建所有表（包括 prescription_workflow_state）
models.Base.metadata.create_all(bind=engine)

print("[OK] 表创建成功")

# 验证表是否存在
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='prescription_workflow_state'"))
    if result.fetchone():
        print("[OK] prescription_workflow_state 表已存在")
    else:
        print("[FAIL] prescription_workflow_state 表不存在")