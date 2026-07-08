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

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield


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

