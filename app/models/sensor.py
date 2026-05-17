from datetime import datetime

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    reading_id: str
    machine_id: str
    sensor_type: str  # e.g. "vibration", "temperature", "pressure"
    unit: str
    value: float
    recorded_at: datetime
    is_anomaly: bool = False
    anomaly_score: float | None = Field(default=None, ge=0.0, le=1.0)


class AnomalySummary(BaseModel):
    machine_id: str
    sensor_type: str
    window_start: datetime
    window_end: datetime
    anomaly_count: int = Field(ge=0)
    max_deviation: float
    mean_value: float
    description: str = ""
