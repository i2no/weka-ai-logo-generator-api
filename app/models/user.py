from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # 用户ID
    openid = Column(String(64), unique=True, nullable=False, index=True)  # 微信openid
    nickname = Column(String(100), nullable=True)  # 昵称
    avatar_url = Column(String(255), nullable=True)  # 头像URL
    created_at = Column(DateTime, default=datetime.now)  # 注册时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间
