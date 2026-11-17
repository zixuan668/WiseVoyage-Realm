"""Persisted recordings of complete scenic introductions, using Xingyun voices."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class ScenicAudio(SQLModel, table=True):
    __tablename__ = 'scenic_audio'
    spot_id: int = Field(primary_key=True, foreign_key='scenic_spot_info.spot_id')
    revision: str
    guide_id: int
    script: str
    file_name: str
    duration: float
    source: str = 'xingyun-recording'
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
