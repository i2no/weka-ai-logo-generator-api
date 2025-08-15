from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(64), nullable=False, index=True)  # 关联用户
    logo_id = Column(String(32), nullable=False, index=True)  # 关联LOGO任务ID
    create_time = Column(DateTime, default=datetime.now)  # 收藏时间

    # 联合唯一约束：同一用户不能重复收藏同一LOGO
    __table_args__ = (
        UniqueConstraint("openid", "logo_id", name="unique_user_logo"),
    )
