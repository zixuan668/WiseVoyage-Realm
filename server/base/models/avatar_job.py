from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class AvatarJob(SQLModel, table=True):
    __tablename__ = "avatar_render_job"
    job_id: str = Field(primary_key=True)
    access_token: str = ""
    session_id: int = Field(foreign_key="tour_session_info.session_id", index=True)
    guide_id: int = Field(foreign_key="digital_guide_info.guide_id")
    message_id: int = Field(foreign_key="visitor_interaction.message_id")
    status: str = "queued"
    avatar_mode: str = "realistic"
    audio_path: str = ""
    video_url: str = ""
    error: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
