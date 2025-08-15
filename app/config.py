import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    # 微信小程序配置
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET: str = os.getenv("WECHAT_SECRET", "")

    # JWT配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # 生产环境需更换为强密钥
    JWT_ALGORITHM: str = "HS256"

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@localhost:3306/logo_db")

    # 补充服务器配置（新增）
    API_PORT: int = int(os.getenv("API_PORT", 8000))  # 服务启动端口
    ENV: str = os.getenv("ENV", "development")  # 环境标识（开发/生产）

    # 补充JWT有效期（新增，避免token永久有效）
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 1440))  # 默认24小时

    # 补充云存储配置（用于图片上传/高清URL生成，新增）
    STORAGE_ACCESS_KEY: str = os.getenv("STORAGE_ACCESS_KEY", "")  # 云存储访问密钥
    STORAGE_SECRET_KEY: str = os.getenv("STORAGE_SECRET_KEY", "")  # 云存储密钥
    STORAGE_REGION: str = os.getenv("STORAGE_REGION", "ap-beijing")  # 存储区域
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "logo-storage")  # 存储桶名称

    LOCAL_MODEL_PATH: str = os.getenv("LOCAL_MODEL_PATH", "./models/logo_generator_v1.pth")  # 模型权重路径


# 实例化配置
settings = Settings()
