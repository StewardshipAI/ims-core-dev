from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CloudEvent(BaseModel):
    """
    CloudEvents v1.0 Compliant Event Schema
    """
    specversion: str = "1.0"
    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    source: str = Field(..., description="URI identifying the event producer")
    type: str = Field(..., description="Type of occurrence which has happened")
    time: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when the occurrence happened")
    correlation_id: Optional[str] = Field(None, description="ID for tracing requests across services")
    datacontenttype: str = "application/json"
    data: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific event data")

    class Config:
        json_encoders = {
            # Ensure UUIDs are serialized to strings
            UUID: lambda v: str(v),
            # Ensure datetimes are ISO 8601 strings
            datetime: lambda v: v.isoformat()
        }
