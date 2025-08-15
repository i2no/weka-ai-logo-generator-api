from celery import shared_task
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.models.logo import LogoTask
from app.utils.ai_client import call_ai_logo_api  # 调用AI生成接口的工具
import json


@shared_task(bind=True, max_retries=3)
def generate_logo_async(self, task_id: str, **kwargs):
    """异步执行LOGO生成任务"""
    db: Session = next(get_db())
    try:
        # 1. 调用AI接口生成LOGO（实际项目替换为真实AI服务）
        # 参数：企业名称、行业、风格、颜色等
        ai_result = call_ai_logo_api(** kwargs)

        # 2. 解析AI返回结果（假设返回图片URL列表）
        # 示例格式：{"success": true, "logos": ["url1", "url2", ...]}
        if ai_result.get("success"):
            # 更新任务状态为成功，存储结果
            task = db.query(LogoTask).filter(LogoTask.id == task_id).first()
            if task:
                task.status = "success"
                task.result = json.dumps(ai_result["logos"])  # 存储为JSON字符串
                db.commit()
        else:
            # AI生成失败
            raise Exception(f"AI生成失败：{ai_result.get('message', '未知错误')}")

    except Exception as e:
        # 失败时重试（最多3次）
        self.retry(exc=e, countdown=5)  # 5秒后重试
        # 最终失败则更新任务状态
        task = db.query(LogoTask).filter(LogoTask.id == task_id).first()
        if task:
            task.status = "fail"
            db.commit()
