"""每位导游独立绑定星云应用，凭据不放入公开导游模型。"""
from sqlmodel import Field, SQLModel


class XingyunBootstrapState(SQLModel, table=True):
    """持久化初始化记录，管理员删除导游后不再自动创建。"""
    key: str = Field(primary_key=True)
    guide_id: int


class XingyunGuideBinding(SQLModel, table=True):
    guide_id: int = Field(primary_key=True, foreign_key="digital_guide_info.guide_id")
    app_id: str
    secret_encrypted: str
    voice_label: str = ""
    # 同一角色的英文应用（星云里另建一个英文音色应用），英文模式优先用它。
    app_id_en: str = ""
    secret_encrypted_en: str = ""
    voice_label_en: str = ""

