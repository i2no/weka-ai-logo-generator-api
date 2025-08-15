from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.wechat import get_wechat_openid
from app.utils.token import generate_jwt_token
# from app.config import settings


def login_service(code: str, db: Session):
    """处理登录业务逻辑：获取openid -> 查找/创建用户 -> 生成token"""
    # 1. 调用微信接口获取openid
    openid = get_wechat_openid(code)
    if not openid:
        raise ValueError("微信登录失败，无效的code")

    # 2. 查找用户，不存在则创建
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        # 创建新用户
        user = User(openid=openid)
        db.add(user)
        db.commit()
        db.refresh(user)
    # 3. 生成JWT令牌
    token = generate_jwt_token(openid=openid)

    # 4. 返回结果
    return {
        "token": token,
        "openid": openid,
        "user_id": user.id
    }


def get_user_info(db: Session, openid: str) -> User | None:
    """
    根据openid查询用户信息
    :param db: 数据库会话（由调用方传入）
    :param openid: 用户唯一标识
    :return: 用户模型实例或None
    """
    # 使用传入的db会话进行查询，避免手动管理会话生命周期
    return db.query(User).filter(User.openid == openid).first()
