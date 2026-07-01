from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SensorDataBase(BaseModel):
    name: str
    value: float
    unit: str = "unit"


class SensorDataCreate(SensorDataBase):
    pass


class SensorDataRead(SensorDataBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
