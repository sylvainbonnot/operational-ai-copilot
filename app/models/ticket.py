from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncidentTicket(BaseModel):
    ticket_id: str
    machine_id: str
    site: str = ""
    symptom: str
    root_cause: str | None = None
    resolution: str | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    downtime_hours: float = Field(default=0.0, ge=0.0)
    occurred_at: datetime
    resolved_at: datetime | None = None
    operator_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class MaintenanceAction(BaseModel):
    action_id: str
    machine_id: str
    action_type: Literal["inspection", "replacement", "calibration", "cleaning", "repair"]
    component: str
    technician_id: str
    performed_at: datetime
    duration_hours: float = Field(ge=0.0)
    notes: str = ""
    parts_replaced: list[str] = Field(default_factory=list)
