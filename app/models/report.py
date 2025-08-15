# from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ImageReport(Base):
    __tablename__ = "image_reports"

    id = Column(Integer, primary_key=True, index=True)  # 举报记录ID
    openid = Column(String(64), nullable=False, index=True)  # 举报人ID
    logo_id = Column(String(32), nullable=False, index=True)  # 被举报的LOGO任务ID
    reason = Column(Text, nullable=False)  # 举报原因
    status = Column(String(20), default="pending")  # 处理状态：pending/processed
    create_time = Column(DateTime, default=datetime.now)  # 举报时间
    handle_time = Column(DateTime, nullable=True)  # 处理时间

    # 可选：添加外键关联（如果需要严格约束）
    # __table_args__ = (ForeignKeyConstraint([logo_id], ["logo_tasks.id"]),)
