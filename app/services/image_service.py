from sqlalchemy.orm import Session
from fastapi import HTTPException
import json
from datetime import datetime, timedelta
from app.models.logo import LogoTask
from app.utils.storage import generate_presigned_url  # 云存储工具（生成带签名的URL）
from app.models.report import ImageReport


def get_hd_logo_url(db: Session, openid: str, logo_id: str) -> dict:
    """
    获取指定LOGO的高清图片URL（带有效期的签名URL）

    参数：
        db: 数据库会话
        openid: 用户唯一标识
        logo_id: LOGO任务ID

    返回：
        dict: 包含高清URL、有效期和LOGO ID的字典

    异常：
        HTTPException: 当LOGO不存在、无权限或无高清资源时抛出
    """
    # 1. 验证LOGO记录存在且属于当前用户
    task = db.query(LogoTask).filter(
        LogoTask.id == logo_id,
        LogoTask.openid == openid
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="LOGO记录不存在（ID错误或不属于当前用户）"
        )

    # 2. 验证LOGO生成成功且有结果
    if task.status != "success" or not task.result:
        raise HTTPException(
            status_code=400,
            detail="LOGO未生成成功，无法获取高清图片"
        )

    # 3. 解析LOGO结果，获取高清资源标识（假设result中包含hd_key）
    try:
        result_data = json.loads(task.result)
        # 假设result格式：{"logos": [...], "hd_keys": ["hd_logo1.png", ...]}
        hd_keys = result_data.get("hd_keys", [])
        if not hd_keys or not isinstance(hd_keys, list):
            raise HTTPException(
                status_code=404,
                detail="该LOGO无高清资源可用"
            )
        # 取第一个高清资源（可根据需求扩展为多图支持）
        hd_key = hd_keys[0]
    except (json.JSONDecodeError, IndexError):
        raise HTTPException(
            status_code=500,
            detail="高清资源信息解析失败"
        )

    # 4. 调用云存储工具生成带签名的临时URL（有效期24小时）
    expires_in = 86400  # 24小时（秒）
    hd_url = generate_presigned_url(
        object_key=hd_key,
        expires_in=expires_in
    )

    if not hd_url:
        raise HTTPException(
            status_code=500,
            detail="生成高清图片URL失败"
        )

    # 5. 计算URL有效期（UTC时间）
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return {
        "logo_id": logo_id,
        "hd_url": hd_url,
        "expires_at": expires_at
    }


def create_image_report(db: Session, openid: str, logo_id: str, reason: str) -> int:
    """
    创建LOGO图片举报记录

    参数：
        db: 数据库会话
        openid: 举报人唯一标识
        logo_id: 被举报的LOGO任务ID
        reason: 举报原因

    返回：
        int: 新创建的举报记录ID

    异常：
        HTTPException: 当LOGO不存在、无权限或重复举报时抛出
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

    # 2. 检查是否已举报过该LOGO（避免重复举报）
    existing_report = db.query(ImageReport).filter(
        ImageReport.openid == openid,
        ImageReport.logo_id == logo_id,
        ImageReport.status == "pending"  # 仅限制未处理的重复举报
    ).first()

    if existing_report:
        raise HTTPException(
            status_code=400,
            detail="您已举报过该LOGO，我们正在处理中"
        )

    # 3. 创建举报记录
    new_report = ImageReport(
        openid=openid,
        logo_id=logo_id,
        reason=reason,
        status="pending",
        create_time=datetime.now()
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)  # 获取自动生成的ID

    # 4. 可选：更新LOGO任务的举报状态（如标记为待审核）
    logo_task.report_status = "reported"  # 需在LogoTask模型中添加该字段
    db.commit()

    return new_report.id
