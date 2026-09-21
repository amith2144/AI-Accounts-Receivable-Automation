import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.activity import ActivityType


class CollectionActivityBase(BaseModel):
    invoice_id: uuid.UUID
    customer_id: uuid.UUID
    activity_type: ActivityType
    performed_by: str = Field(default="SYSTEM_AUTOMATION", max_length=255)
    details: Dict[str, Any] = Field(default_factory=dict)


class CollectionActivityCreate(CollectionActivityBase):
    pass


class CollectionActivityResponse(CollectionActivityBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class CollectionActivityListResponse(BaseModel):
    items: List[CollectionActivityResponse]
    total: int
    offset: int
    limit: int
