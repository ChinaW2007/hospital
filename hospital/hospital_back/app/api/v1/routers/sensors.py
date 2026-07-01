from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db import crud
from app.schemas.sensor import SensorDataCreate, SensorDataRead

router = APIRouter()


@router.get("/", response_model=List[SensorDataRead])
def list_sensors(db: Session = Depends(get_db)):
    return crud.get_sensor_records(db=db)


@router.post("/", response_model=SensorDataRead, status_code=201)
def create_sensor(sensor: SensorDataCreate, db: Session = Depends(get_db)):
    return crud.create_sensor_record(db=db, sensor_data=sensor)
