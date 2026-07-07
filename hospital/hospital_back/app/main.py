import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers.camera import router as camera_router
from app.api.v1.routers.sensors import router as sensors_router
from app.api.v1.routers.agent import router as agent_router
from app.api.v1.routers.data import router as data_router
from app.api.v1.routers.prescription import router as prescription_router
from app.api.v1.routers.workflow import router as workflow_router
from app.db import models
from app.db.session import engine
from app.services.ros_listener import start_ros_listener
from app.services.his_sender import start_his_sender, stop_his_sender

logger = logging.getLogger(__name__)

# ROS 监听后台任务
_ros_listener_task = None
# HIS 处方发送后台任务
_his_sender_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建数据库表 + 启动 ROS 监听 + 启动 HIS 处方发送
    print("=" * 60)
    print("Hospital Back 服务启动")
    print("=" * 60)
    
    # ===== 创建数据库表（添加错误处理） =====
    try:
        models.Base.metadata.create_all(bind=engine)
        print("[成功] 数据库表创建完成")
        logger.info("数据库表创建完成")
    except Exception as e:
        print(f"[警告] 数据库表创建失败: {e}")
        logger.warning(f"数据库表创建失败: {e}")
    
    # ===== 启动 ROS WebSocket 监听后台任务（添加错误处理） =====
    print("[启动] ROS WebSocket 监听后台任务...")
    logger.info("启动 ROS WebSocket 监听后台任务...")
    try:
        _ros_listener_task = asyncio.create_task(start_ros_listener())
        print("[成功] ROS WebSocket 监听任务已启动")
        logger.info("ROS WebSocket 监听任务已启动")
    except Exception as e:
        print(f"[警告] ROS WebSocket 监听任务启动失败: {e}")
        logger.warning(f"ROS WebSocket 监听任务启动失败: {e}")
        _ros_listener_task = None
    
    # ===== 启动 HIS 处方发送后台任务（添加错误处理） =====
    print("[启动] HIS 处方发送后台任务...")
    logger.info("启动 HIS 处方发送后台任务...")
    try:
        _his_sender_task = asyncio.create_task(start_his_sender())
        print("[成功] HIS 处方发送任务已启动")
        logger.info("HIS 处方发送任务已启动")
    except Exception as e:
        print(f"[警告] HIS 处方发送任务启动失败: {e}")
        logger.warning(f"HIS 处方发送任务启动失败: {e}")
        _his_sender_task = None
    
    print("=" * 60)
    print("服务启动完成，开始监听请求...")
    print("=" * 60)
    
    yield
    
    # 关闭时：取消后台任务（添加错误处理）
    if _ros_listener_task:
        print("[停止] ROS WebSocket 监听任务...")
        logger.info("停止 ROS WebSocket 监听任务...")
        _ros_listener_task.cancel()
        try:
            await _ros_listener_task
        except asyncio.CancelledError:
            print("[完成] ROS 监听任务已取消")
            logger.info("ROS 监听任务已取消")
        except Exception as e:
            print(f"[警告] ROS 监听任务取消失败: {e}")
            logger.warning(f"ROS 监听任务取消失败: {e}")
    
    if _his_sender_task:
        print("[停止] HIS 处方发送任务...")
        logger.info("停止 HIS 处方发送任务...")
        _his_sender_task.cancel()
        try:
            await stop_his_sender()
        except Exception as e:
            print(f"[警告] HIS Sender停止失败: {e}")
            logger.warning(f"HIS Sender停止失败: {e}")
        try:
            await _his_sender_task
        except asyncio.CancelledError:
            print("[完成] HIS 处方发送任务已取消")
            logger.info("HIS 处方发送任务已取消")
        except Exception as e:
            print(f"[警告] HIS 处方发送任务取消失败: {e}")
            logger.warning(f"HIS 处方发送任务取消失败: {e}")
    
    print("=" * 60)
    print("服务已关闭")
    print("=" * 60)


app = FastAPI(
    title="Medicine API Server",
    version="1.0.0",
    description="A FastAPI backend for sensors, AI agent, database data, and camera streaming.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(camera_router, prefix="/api/v1/camera", tags=["camera"])
app.include_router(sensors_router, prefix="/api/v1/sensors", tags=["sensors"])
app.include_router(agent_router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(data_router, prefix="/api/v1/data", tags=["data"])
app.include_router(prescription_router, prefix="/api/v1", tags=["prescription"])
app.include_router(workflow_router, prefix="/api/v1", tags=["workflow"])

