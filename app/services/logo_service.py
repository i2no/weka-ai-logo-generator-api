from sqlalchemy.orm import Session
from uuid import uuid4  # 生成唯一任务ID
from app.models.logo import LogoTask  # LOGO任务模型
from app.tasks.logo_generate import generate_logo_async  # 异步生成任务
from datetime import datetime, timedelta
from fastapi import HTTPException


def create_logo_task(
    db: Session,
    openid: str,
    company_name: str,
    industry: str,
    styles: list,
    colors: list,
    description: str = None
) -> LogoTask:
    """创建LOGO生成任务并触发异步生成"""
    # 生成唯一任务ID（32位UUID）
    task_id = str(uuid4()).replace("-", "")

    # 创建数据库记录（初始状态为pending）
    db_task = LogoTask(
        id=task_id,
        openid=openid,
        company_name=company_name,
        industry=industry,
        styles=str(styles),  # 存储为字符串（实际项目可序列化JSON）
        colors=str(colors),
        description=description,
        status="pending",
        create_time=datetime.now()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)  # 刷新获取完整记录

    # 触发异步生成任务（非阻塞，不影响接口响应速度）
    # 参数：任务ID、生成参数
    generate_logo_async.delay(
        task_id=task_id,
        company_name=company_name,
        industry=industry,
        styles=styles,
        colors=colors
    )

    return db_task


# 在基础上继续加的代码
def get_task_status(db: Session, task_id: str, openid: str) -> LogoTask | None:
    """
    查询指定任务的状态（仅允许查询当前用户的任务）

    参数：
        db: 数据库会话
        task_id: 任务ID
        openid: 用户唯一标识（用于权限验证）

    返回：
        LogoTask对象或None（任务不存在或无权限）
    """
    # 同时过滤task_id和openid，确保用户只能查询自己的任务
    return db.query(LogoTask).filter(
        LogoTask.id == task_id,
        LogoTask.openid == openid
    ).first()


# 在基础上继续加的
def get_valid_task_result(db: Session, task_id: str, openid: str) -> LogoTask:
    """
    获取并验证任务结果（增强版）
    - 验证任务归属（仅当前用户）
    - 检查任务有效性（未过期）
    - 补充状态校验逻辑
    """
    # 1. 查询任务并验证归属
    task = db.query(LogoTask).filter(
        LogoTask.id == task_id,
        LogoTask.openid == openid
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在（ID错误或不属于当前用户）"
        )

    # 2. 检查任务是否过期（默认保留7天）
    if task.create_time < (datetime.now() - timedelta(days=7)):
        raise HTTPException(
            status_code=410,
            detail="任务已过期（超过7天），请重新生成"
        )

    # 3. 处理异常状态（如长时间pending）
    if task.status == "pending" and (
        datetime.now() - task.create_time > timedelta(minutes=5)
    ):
        # 超过5分钟仍未处理，标记为失败
        task.status = "fail"
        task.result = "任务处理超时"
        db.commit()
        raise HTTPException(
            status_code=504,
            detail="任务处理超时，请重新提交"
        )

    return task
