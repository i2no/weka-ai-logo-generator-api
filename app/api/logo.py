from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import json
# from datetime import datetime
from app.utils.token import get_current_user
from app.utils.db import get_db
from app.services.logo_service import get_valid_task_result, create_logo_task, get_task_status  # 优化后的服务方法
# from app.models.logo import LogoTask

router = APIRouter()


# 请求参数模型（验证用户输入）
class LogoGenerateRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=50, description="企业名称")
    industry: str = Field(..., max_length=30, description="行业类型")
    styles: List[str] = Field(..., min_items=1, max_items=5, description="LOGO风格列表")
    colors: List[str] = Field(..., min_items=1, max_items=3, description="主色调列表（HEX格式）")
    # 可选参数：补充说明
    description: Optional[str] = Field(None, max_length=200, description="额外设计要求")


# 响应模型：定义任务状态返回结构
class LogoStatusResponse(BaseModel):
    task_id: str
    status: str  # pending/processing/success/fail
    progress: int  # 进度百分比（0-100）
    message: str | None = None  # 状态描述（如失败原因）

    class Config:
        from_attributes = True


@router.get("/status", response_model=LogoStatusResponse, summary="查询LOGO生成任务状态")
def query_logo_status(
    task_id: str = Query(..., description="LOGO生成任务ID"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询LOGO生成任务的实时状态：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 返回任务ID、状态、进度和描述信息
    - 状态说明：pending(待处理)/processing(生成中)/success(成功)/fail(失败)
    """
    # 调用服务层查询任务状态
    task = get_task_status(db, task_id, openid)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在（可能已过期或ID错误）"
        )

    # 映射状态到进度百分比（根据实际业务调整）
    status_map = {
        "pending": 0,
        "processing": 50,
        "success": 100,
        "fail": 100
    }

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": status_map.get(task.status, 0),
        "message": "生成成功" if task.status == "success" else "生成失败，请重试" if task.status == "fail" else None
    }


# 响应模型（返回任务信息）
class LogoTaskResponse(BaseModel):
    task_id: str
    status: str  # pending/success/fail
    message: str


@router.post("/generate", response_model=LogoTaskResponse, summary="创建LOGO生成任务")
def generate_logo(
    request: LogoGenerateRequest,
    openid: str = Depends(get_current_user),  # 从token获取用户标识
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    提交LOGO生成任务：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 接收企业名称、行业、风格、颜色等参数
    - 创建异步生成任务并返回task_id（用于查询结果）
    """
    try:
        # 调用服务层创建任务
        task = create_logo_task(
            db=db,
            openid=openid,
            company_name=request.company_name,
            industry=request.industry,
            styles=request.styles,
            colors=request.colors,
            description=request.description
        )
        return {
            "task_id": task.id,
            "status": task.status,
            "message": "生成任务已创建，正在处理中"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败：{str(e)}")


# 响应模型：精确规范返回字段和类型
class LogoResultResponse(BaseModel):
    task_id: str
    status: str  # 严格限制状态值
    logos: List[str] = []
    company_name: str
    industry: Optional[str] = None
    styles: List[str] = []
    colors: List[str] = []
    create_time: str
    message: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "task_id": "logo_123456",
                "status": "success",
                "logos": [
                    "https://storage.example.com/logo1.png",
                    "https://storage.example.com/logo2.png"
                ],
                "company_name": "云启科技",
                "industry": "互联网",
                "styles": ["极简风", "科技风"],
                "colors": ["#1677FF", "#303133"],
                "create_time": "2023-10-01 14:30:00",
                "message": None
            }
        }


@router.get("/result", response_model=LogoResultResponse, summary="获取LOGO生成结果")
def get_logo_result(
    task_id: str = Query(..., min_length=8, max_length=32, description="LOGO任务ID（8-32位）"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取LOGO生成任务的最终结果：
    - 仅返回当前用户创建的任务结果
    - 支持查询各状态任务（未完成/成功/失败）
    - 成功状态返回LOGO图片URL列表及完整参数
    """
    try:
        # 调用服务层获取并验证任务
        task = get_valid_task_result(db, task_id, openid)

        # 解析任务参数（带默认值防止空值错误）
        styles = json.loads(task.styles) if task.styles else []
        colors = json.loads(task.colors) if task.colors else []

        # 解析生成结果（仅成功状态处理）
        logos = []
        if task.status == "success" and task.result:
            logos = json.loads(task.result)
            # 验证URL格式（基础校验）
            for url in logos:
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise HTTPException(
                        status_code=500,
                        detail="生成结果包含无效URL，请重新生成"
                    )

        # 构建状态消息
        status_messages = {
            "pending": "任务等待处理中",
            "processing": "LOGO生成中，请稍后",
            "success": None,
            "fail": task.result or "生成失败，请重试"  # 失败时result存储错误信息
        }

        return {
            "task_id": task.id,
            "status": task.status,
            "logos": logos,
            "company_name": task.company_name,
            "industry": task.industry,
            "styles": styles,
            "colors": colors,
            "create_time": task.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "message": status_messages[task.status]
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="结果解析失败，可能是数据损坏"
        )
    except HTTPException:
        raise  # 直接抛出服务层或URL校验的异常
    except Exception as e:
        # 捕获未预料的异常
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误：{str(e)}"
        )
