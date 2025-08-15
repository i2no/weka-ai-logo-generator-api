from sqlalchemy.orm import Session
# from sqlalchemy import func, join
from sqlalchemy import func
# from sqlalchemy.sql import select
import json
from fastapi import HTTPException
from datetime import datetime
from app.models.favorite import Favorite
from app.models.logo import LogoTask  # 用于验证LOGO存在性


def toggle_favorite_status(db: Session, openid: str, logo_id: str, action: str) -> dict:
    """
    切换LOGO的收藏状态（添加/移除）

    参数：
        db: 数据库会话
        openid: 用户唯一标识
        logo_id: LOGO任务ID
        action: 操作类型（add/remove）

    返回：
        dict: 包含操作消息和当前收藏状态的字典

    异常：
        HTTPException: 当LOGO不存在、无权限或操作无效时抛出
    """
    # 1. 验证LOGO记录存在且属于当前用户
    logo_task = db.query(LogoTask).filter(
        LogoTask.id == logo_id,
        LogoTask.openid == openid
    ).first()

    if not logo_task:
        raise HTTPException(
            status_code=404,
            detail="LOGO记录不存在（ID错误或不属于当前用户）"
        )

    # 2. 检查当前收藏状态
    favorite = db.query(Favorite).filter(
        Favorite.openid == openid,
        Favorite.logo_id == logo_id
    ).first()

    # 3. 执行添加/移除操作
    if action == "add":
        if favorite:
            # 已收藏，无需重复添加
            return {
                "message": "已在收藏中",
                "is_favorite": True
            }

        # 创建新收藏记录
        new_favorite = Favorite(
            openid=openid,
            logo_id=logo_id,
            create_time=datetime.now()
        )
        db.add(new_favorite)
        db.commit()
        return {
            "message": "已添加到收藏",
            "is_favorite": True
        }

    elif action == "remove":
        if not favorite:
            # 未收藏，无需移除
            return {
                "message": "未在收藏中",
                "is_favorite": False
            }

        # 删除收藏记录
        db.delete(favorite)
        db.commit()
        return {
            "message": "已从收藏中移除",
            "is_favorite": False
        }

    else:
        # 无效操作类型（理论上被Pydantic拦截，此处为双重保险）
        raise HTTPException(
            status_code=400,
            detail="无效操作，action必须为'add'或'remove'"
        )


def get_favorite_list(db: Session, openid: str, page: int, page_size: int) -> dict:
    """
    分页获取用户的收藏列表（关联LOGO任务信息）

    参数：
        db: 数据库会话
        openid: 用户唯一标识
        page: 页码（从1开始）
        page_size: 每页条数

    返回：
        dict: 包含总记录数和当前页记录的字典
    """
    # 1. 计算总收藏数
    total = db.query(func.count(Favorite.id)).filter(
        Favorite.openid == openid
    ).scalar() or 0

    if total == 0:
        return {"total": 0, "records": []}

    # 2. 计算分页偏移量
    offset = (page - 1) * page_size

    # 3. 联合查询收藏记录和关联的LOGO任务信息
    # 按收藏时间倒序排列（最新收藏在前）
    favorite_query = db.query(
        Favorite,
        LogoTask  # 关联LOGO任务表
    ).join(
        LogoTask,
        Favorite.logo_id == LogoTask.id  # 关联条件
    ).filter(
        Favorite.openid == openid
    ).order_by(
        Favorite.create_time.desc()
    ).offset(offset).limit(page_size)

    # 4. 处理查询结果
    records = []
    for favorite, logo_task in favorite_query:
        # 解析风格列表
        styles = []
        if logo_task.styles:
            try:
                styles = json.loads(logo_task.styles)
            except json.JSONDecodeError:
                styles = []

        # 提取LOGO缩略图（取第一张）
        thumbnail = None
        if logo_task.status == "success" and logo_task.result:
            try:
                logos = json.loads(logo_task.result)
                if logos and isinstance(logos, list) and len(logos) > 0:
                    thumbnail = logos[0]
            except json.JSONDecodeError:
                thumbnail = None

        records.append({
            "favorite_id": favorite.id,
            "logo_id": favorite.logo_id,
            "company_name": logo_task.company_name,
            "styles": styles,
            "thumbnail": thumbnail,
            "favorite_time": favorite.create_time.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {
        "total": total,
        "records": records
    }


def delete_favorite(db: Session, openid: str, logo_id: str) -> None:
    """
    删除用户对指定LOGO的收藏记录

    参数：
        db: 数据库会话
        openid: 用户唯一标识
        logo_id: 要取消收藏的LOGO任务ID

    异常：
        HTTPException: 当LOGO不存在、无收藏记录或无权限时抛出
    """
    # 1. 验证LOGO记录存在且属于当前用户
    logo_task = db.query(LogoTask).filter(
        LogoTask.id == logo_id,
        LogoTask.openid == openid
    ).first()

    if not logo_task:
        raise HTTPException(
            status_code=404,
            detail="LOGO记录不存在（ID错误或不属于当前用户）"
        )

    # 2. 查询收藏记录
    favorite = db.query(Favorite).filter(
        Favorite.openid == openid,
        Favorite.logo_id == logo_id
    ).first()

    if not favorite:
        raise HTTPException(
            status_code=404,
            detail="未找到该LOGO的收藏记录"
        )

    # 3. 执行删除操作
    db.delete(favorite)
    db.commit()
