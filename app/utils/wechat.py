import requests
from app.config import settings


def get_wechat_openid(code: str) -> str:
    """
    调用微信code2Session接口获取openid
    文档:https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/login/auth.code2Session.html
    """
    if not code:
        return ""

    # 构造请求参数
    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }

    # 调用微信接口
    response = requests.get(
        url="https://api.weixin.qq.com/sns/jscode2session",
        params=params,
        timeout=10
    )
    result = response.json()

    # 检查返回结果（errcode为0表示成功）
    if "errcode" in result and result["errcode"] != 0:
        return ""

    return result.get("openid", "")
