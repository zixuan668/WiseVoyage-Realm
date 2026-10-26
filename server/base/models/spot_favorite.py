from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class SpotFavorite(SQLModel, table=True):
    __tablename__ = "spot_favorite"
    user_id: int = Field(primary_key=True, foreign_key="user_info.user_id")
    spot_id: int = Field(primary_key=True, foreign_key="scenic_spot_info.spot_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SpotView(SQLModel, table=True):
    __tablename__ = "spot_view_history"
    user_id: int = Field(primary_key=True, foreign_key="user_info.user_id")
    spot_id: int = Field(primary_key=True, foreign_key="scenic_spot_info.spot_id")
    viewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
