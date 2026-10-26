from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class MotionJob(SQLModel, table=True):
    __tablename__ = 'avatar_motion_job'
    job_id: str = Field(primary_key=True)
    guide_id: int = Field(foreign_key='digital_guide_info.guide_id', index=True)
    user_id: int = Field(foreign_key='user_info.user_id')
    provider_task_id: str = ''
    status: str = 'submitting'
    prompt: str = ''
    source_image: str = ''
    previous_source: str = ''
    video_path: str = ''
    video_metadata: str = ''
    error: str = ''
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
