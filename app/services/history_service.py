from sqlalchemy.orm import Session
from sqlalchemy import func
import json
from app.models.logo import LogoTask
# from datetime import datetime
from app.models.favorite import Favorite
from fastapi import HTTPException


def get_history_records(db: Session, openid: str, page: int, page_size: int) -> dict:
    """
    获取用户的LOGO生成历史记录(分页)

    参数：
        db: 数据库会话
        openid: 用户唯一标识
        page: 页码(从1开始)
        page_size: 每页条数

    返回：
        dict: 包含总记录数和当前页记录的字典
    """
    # 1. 计算总记录数
    total = db.query(func.count(LogoTask.id)).filter(
        LogoTask.openid == openid
    ).scalar()

    # 2. 计算分页偏移量
    offset = (page - 1) * page_size

    # 3. 查询当前页记录（按创建时间倒序）
    tasks = db.query(LogoTask).filter(
        LogoTask.openid == openid
    ).order_by(
        LogoTask.create_time.desc()
    ).offset(offset).limit(page_size).all()

    # 4. 格式化记录数据
    records = []
    for task in tasks:
        # 解析风格列表
        styles = []
        if task.styles:
            try:
                styles = json.loads(task.styles)
            except json.JSONDecodeError:
                styles = []

        # 提取第一张LOGO作为缩略图
        thumbnail = None
        if task.status == "success" and task.result:
            try:
                logos = json.loads(task.result)
                if logos and isinstance(logos, list) and len(logos) > 0:
                    thumbnail = logos[0]  # 取第一个LOGO URL
            except json.JSONDecodeError:
                thumbnail = None

        records.append({
            "record_id": task.id,
            "company_name": task.company_name,
            "industry": task.industry,
            "styles": styles,
            "create_time": task.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "thumbnail": thumbnail,
            "status": task.status
        })

    return {
        "total": total,
        "records": records
    }


def get_history_detail(db: Session, openid: str, record_id: str) -> dict:
    """
    获取指定历史记录的详细信息

    参数：
        db: 数据库会话
        openid: 用户唯一标识
        record_id: 记录ID（task_id）

    返回：
        dict: 包含完整详情的字典

    异常：
        HTTPException: 记录不存在或无权限时抛出
    """
    # 1. 查询记录并验证归属
    task = db.query(LogoTask).filter(
        LogoTask.id == record_id,
        LogoTask.openid == openid
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="记录不存在（ID错误或不属于当前用户）"
        )

    # 2. 检查是否被收藏
    is_favorite = db.query(Favorite).filter(
        Favorite.logo_id == record_id,
        Favorite.openid == openid
    ).first() is not None

    # 3. 解析JSON格式字段
    styles = json.loads(task.styles) if task.styles else []
    colors = json.loads(task.colors) if task.colors else []
    logos = json.loads(task.result) if (task.status == "success" and task.result) else []

    # 4. 格式化时间
    create_time = task.create_time.strftime("%Y-%m-%d %H:%M:%S")
    update_time = task.updated_at.strftime("%Y-%m-%d %H:%M:%S") if task.updated_at else create_time

    # 5. 构建详情数据
    return {
        "record_id": task.id,
        "company_name": task.company_name,
        "industry": task.industry,
        "styles": styles,
        "colors": colors,
        "description": task.description,  # 假设模型中有description字段
        "status": task.status,
        "create_time": create_time,
        "update_time": update_time,
        "logos": logos,
        "is_favorite": is_favorite
    }


def delete_history_record(db: Session, openid: str, record_id: str) -> None:
    """
    删除用户的指定历史记录（及关联数据）

    参数：
        db: 数据库会话
        openid: 用户唯一标识（用于权限验证）
        record_id: 要删除的记录ID（task_id）

    异常：
        HTTPException: 记录不存在或无权限时抛出
    """
    # 1. 查询记录并验证归属
    task = db.query(LogoTask).filter(
        LogoTask.id == record_id,
        LogoTask.openid == openid
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="记录不存在（ID错误或不属于当前用户）"
        )

    # 2. 删除关联数据（如收藏记录）
    # 如果收藏表通过logo_id关联任务ID，需要先删除关联记录
    db.query(Favorite).filter(
        Favorite.logo_id == record_id,
        Favorite.openid == openid
    ).delete()

    # 3. 删除主记录
    db.delete(task)
    db.commit()
