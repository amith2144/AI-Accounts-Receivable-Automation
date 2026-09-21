import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.cadence import ReminderTone


class ReminderCadenceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Rule name or title")
    trigger_offset_days: int = Field(..., description="Days relative to due date (negative=before, 0=on, positive=after)")
    reminder_tone: ReminderTone = Field(default=ReminderTone.STANDARD, description="Tone applied to template")
    email_subject_template: str = Field(..., min_length=1, max_length=255, description="Parameterized subject line")
    email_body_template: str = Field(..., min_length=1, description="Jinja2 parameterized email body template")
    is_active: bool = Field(default=True, description="Master rule toggle")


class ReminderCadenceCreate(ReminderCadenceBase):
    pass


class ReminderCadenceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    trigger_offset_days: Optional[int] = None
    reminder_tone: Optional[ReminderTone] = None
    email_subject_template: Optional[str] = Field(None, min_length=1, max_length=255)
    email_body_template: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class ReminderCadenceResponse(ReminderCadenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CadenceDispatchSummary(BaseModel):
    evaluated_cadences: int = 0
    scanned_invoices: int = 0
    dispatched_count: int = 0
    skipped_paused: int = 0
    throttled_count: int = 0
    errors: List[str] = Field(default_factory=list)
