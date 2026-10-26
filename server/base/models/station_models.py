"""Fixed service stations are independent of visitors' mobile tour sessions."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON


def utcnow():
    # Existing database timestamps are naive UTC; keep comparisons consistent.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ServiceStation(SQLModel, table=True):
    __tablename__ = 'service_station'
    station_id: str = Field(primary_key=True)
    name: str
    name_en: str = ''
    location: str
    location_en: str = ''
    anchor_key: str = 'gate:east'
    guide_id: int = 0
    default_language: str = 'zh'
    welcome: str = '您好，我是本站数字接待员。想去哪里，我来帮您安排。'
    welcome_en: str = 'Welcome. I can answer questions and plan a walk from this station.'
    idle_seconds: int = 120
    volume: float = .7
    enabled: bool = True
    demo: bool = True
    revision: int = 1
    announcements: list = Field(default_factory=list, sa_column=Column(JSON))
    facilities: list = Field(default_factory=list, sa_column=Column(JSON))
    last_seen: datetime | None = None
    updated_at: datetime = Field(default_factory=utcnow)


class StationVisit(SQLModel, table=True):
    __tablename__ = 'station_visit'
    visit_id: str = Field(primary_key=True)
    station_id: str = Field(index=True)
    access_hash: str
    language: str = 'zh'
    status: str = 'active'
    messages: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(index=True)


class StationPlan(SQLModel, table=True):
    __tablename__ = 'station_plan'
    plan_id: str = Field(primary_key=True)
    visit_id: str = Field(index=True)
    station_id: str
    snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(index=True)


class StationClaim(SQLModel, table=True):
    """QR bears an expiring token; only hashes and an independent snapshot persist."""
    __tablename__ = 'station_claim'
    claim_hash: str = Field(primary_key=True)
    station_id: str
    plan_id: str = Field(index=True)
    snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    expires_at: datetime = Field(index=True)
    mobile_session_id: int | None = None
    claimed_at: datetime | None = None
    receipt_hash: str = ''


class StationClaimCode(SQLModel, table=True):
    """Installation fallback: store only a hash of the human-readable pickup code."""
    __tablename__ = 'station_claim_code'
    code_hash: str = Field(primary_key=True)
    claim_hash: str = Field(index=True)
    expires_at: datetime = Field(index=True)
