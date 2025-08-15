from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class LogoTask(Base):
    """LOGO生成任务表"""
    __tablename__ = "logo_tasks"

    id = Column(String(32), primary_key=True, comment="任务ID（UUID）")
    openid = Column(String(64), ForeignKey("users.openid"), nullable=False, comment="关联用户")
    company_name = Column(String(50), nullable=False, comment="企业名称")
    industry = Column(String(30), nullable=False, comment="行业类型")
    styles = Column(Text, nullable=False, comment="风格列表（JSON字符串）")
    colors = Column(Text, nullable=False, comment="颜色列表（JSON字符串）")
    description = Column(Text, nullable=True, comment="额外描述")
    status = Column(String(20), default="pending", comment="状态：pending/success/fail")
    result = Column(Text, nullable=True, comment="生成结果（LOGO URL列表，JSON字符串）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
