from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
# from datetime import datetime
from sqlalchemy.orm import Session
from app.services.user_service import get_user_info
from app.utils.token import get_current_user  # 验证token并返回openid
from app.utils.db import get_db  # 数据库会话依赖
from app.services.user_service import login_service

router = APIRouter()


# 请求参数模型（Pydantic验证）
class LoginRequest(BaseModel):
    code: str  # 微信登录临时code


# 登录接口
@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    微信小程序登录接口
    - 接收微信临时code，获取openid并生成token
    """
    try:
        # 调用服务层处理登录逻辑
        result = login_service(code=data.code, db=db)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 响应模型：明确字段类型和序列化规则
class UserInfoResponse(BaseModel):
    user_id: int
    openid: str
    nickname: str | None = None
    avatar_url: str | None = None
    created_at: str  # 格式化后的时间字符串

    class Config:
        arbitrary_types_allowed = True  # 允许处理ORM模型


@router.get("/info", response_model=UserInfoResponse, summary="获取当前用户信息")
async def get_user_profile(
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)  # 数据库会话通过依赖注入
):
    """获取当前登录用户的基本信息（需要携带token）"""
    # 调用服务层查询用户信息（传入db会话）
    user = get_user_info(db, openid)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 脱敏处理openid（仅显示部分字符）
    masked_openid = f"{user.openid[:6]}***{user.openid[-4:]}"

    return UserInfoResponse(
        user_id=user.id,
        openid=masked_openid,
        nickname=user.nickname or "",  # 确保None转为空字符串
        avatar_url=user.avatar_url or "",
        created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )
