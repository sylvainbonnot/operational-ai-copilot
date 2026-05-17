from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Machine(BaseModel):
    machine_id: str
    site: str
    machine_type: str
    component: str
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    commissioned_at: datetime | None = None
    notes: str = ""


class OperationalMemoryEntry(BaseModel):
    machine_id: str
    known_issues: list[str] = Field(default_factory=list)
    previous_interventions: list[str] = Field(default_factory=list)
    last_maintenance_at: datetime | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
