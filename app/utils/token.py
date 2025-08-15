import jwt
from datetime import datetime, timedelta
from app.config import settings


def generate_jwt_token(openid: str) -> str:
    """生成JWT令牌（包含openid，有效期7天）"""
    # 过期时间：7天
    expire = datetime.utcnow() + timedelta(days=7)

    #  payload数据
    payload = {
        "sub": openid,  # subject：用户唯一标识
        "exp": expire   # expiration：过期时间
    }

    # 生成令牌
    token = jwt.encode(
        payload=payload,
        key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return token
