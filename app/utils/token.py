import jwt
from datetime import datetime, timedelta
from config import settings
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 定义HTTPBearer依赖，用于提取请求头中的Authorization
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    从请求头的Token中解析并验证用户身份，返回用户openid
    
    流程：
    1. 提取Authorization头中的Bearer Token
    2. 验证Token签名和有效期
    3. 从Token payload中提取openid并返回
    """
    # 1. 检查Token是否存在
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供身份令牌（Token）",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials  # 获取Token字符串
    
    try:
        # 2. 验证Token签名并解码（使用配置中的密钥和算法）
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,  # 从配置读取密钥
            algorithms=[settings.JWT_ALGORITHM]  # 从配置读取算法（如HS256）
        )
        
        # 3. 验证Token有效期（如果payload中包含exp字段）
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            current_timestamp = datetime.utcnow().timestamp()
            if current_timestamp > exp_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已过期，请重新登录",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # 4. 提取openid（用户唯一标识）
        openid: str = payload.get("openid")
        if not openid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中未包含用户信息",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return openid  # 返回用户openid，供接口使用
    
    except jwt.ExpiredSignatureError:
        # Token过期
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        # Token无效（包括签名错误、格式错误等）
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已损坏",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # 捕获其他未预料的异常
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="身份验证过程出错:" + str(e),
        )


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