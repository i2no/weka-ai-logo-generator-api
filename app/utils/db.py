from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings  # 导入配置（需实现）

# 数据库连接URL（从配置文件读取）
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset=utf8mb4"

# 创建引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类（所有模型继承该类）
Base = declarative_base()


# 获取数据库会话（依赖注入用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 创建所有数据库表（首次运行时调用）
def create_tables():
    Base.metadata.create_all(bind=engine)
