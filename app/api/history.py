from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from app.utils.token import get_current_user  # 用户身份验证
from app.utils.db import get_db  # 数据库会话
from app.services.history_service import get_history_records, delete_history_record, get_history_detail   # 业务逻辑
# from app.models.logo import LogoTask  # 任务模型

router = APIRouter()


# 单条历史记录响应模型
class HistoryItem(BaseModel):
    record_id: str  # 任务ID（与task_id一致）
    company_name: str  # 企业名称
    industry: Optional[str] = None  # 行业
    styles: List[str] = []  # 风格
    create_time: str  # 生成时间
    thumbnail: Optional[str] = None  # LOGO缩略图URL（取第一张）
    status: str  # 任务状态

    class Config:
        from_attributes = True


# 分页列表响应模型
class HistoryListResponse(BaseModel):
    total: int  # 总记录数
    page: int  # 当前页码
    size: int  # 每页条数
    total_pages: int  # 总页数
    records: List[HistoryItem]  # 记录列表

    class Config:
        json_schema_extra = {
            "example": {
                "total": 23,
                "page": 1,
                "size": 10,
                "total_pages": 3,
                "records": [
                    {
                        "record_id": "logo_123456",
                        "company_name": "云启科技",
                        "industry": "互联网",
                        "styles": ["极简风", "科技风"],
                        "create_time": "2023-10-01 14:30:00",
                        "thumbnail": "https://storage.example.com/logo1.png",
                        "status": "success"
                    }
                ]
            }
        }


@router.get("/list", response_model=HistoryListResponse, summary="获取历史记录列表")
def get_history(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    size: int = Query(10, ge=1, le=50, description="每页条数（1-50）"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    分页获取当前用户的LOGO生成历史记录：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 支持分页参数（page页码，size每页条数）
    - 按生成时间倒序排列（最新的在前）
    - 每条记录包含任务基本信息和LOGO缩略图
    """
    try:
        # 调用服务层获取分页数据
        result = get_history_records(
            db=db,
            openid=openid,
            page=page,
            page_size=size
        )

        # 处理返回数据
        return {
            "total": result["total"],
            "page": page,
            "size": size,
            "total_pages": (result["total"] + size - 1) // size,  # 计算总页数
            "records": result["records"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败：{str(e)}"
        )


# 删除响应模型
class DeleteResponse(BaseModel):
    success: bool
    message: str
    record_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "记录删除成功",
                "record_id": "logo_123456"
            }
        }


@router.delete("/delete", response_model=DeleteResponse, summary="删除历史记录")
def delete_history(
    record_id: str = Query(..., min_length=8, max_length=32, description="要删除的记录ID（即task_id）"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除当前用户的指定历史记录：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 仅允许删除当前用户创建的记录
    - 成功后返回删除确认信息
    """
    try:
        # 调用服务层执行删除操作
        delete_history_record(db, openid, record_id)

        return {
            "success": True,
            "message": "记录删除成功",
            "record_id": record_id
        }

    except HTTPException as e:
        # 捕获服务层抛出的已知异常（如记录不存在）
        raise e
    except Exception as e:
        # 捕获未预料的异常
        raise HTTPException(
            status_code=500,
            detail=f"删除失败：{str(e)}"
        )


class HistoryDetailResponse(BaseModel):
    record_id: str  # 任务ID
    company_name: str  # 企业名称
    industry: Optional[str] = None  # 行业
    styles: List[str] = []  # 风格列表
    colors: List[str] = []  # 颜色方案
    description: Optional[str] = None  # 额外描述（如有）
    status: str  # 任务状态
    create_time: str  # 生成时间
    update_time: str  # 最后更新时间
    logos: List[str] = []  # 所有LOGO图片URL
    is_favorite: bool = False  # 是否被收藏

    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "logo_123456",
                "company_name": "云启科技",
                "industry": "互联网",
                "styles": ["极简风", "科技风"],
                "colors": ["#1677FF", "#303133"],
                "description": "突出科技感和创新",
                "status": "success",
                "create_time": "2023-10-01 14:30:00",
                "update_time": "2023-10-01 14:35:22",
                "logos": [
                    "https://storage.example.com/logo1.png",
                    "https://storage.example.com/logo2.png"
                ],
                "is_favorite": True
            }
        }


@router.get("/detail", response_model=HistoryDetailResponse, summary="获取历史记录详情")
def get_history_detail_api(
    record_id: str = Query(..., min_length=8, max_length=32, description="记录ID（即task_id）"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定历史记录的详细信息：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 仅返回当前用户的记录详情
    - 包含完整的生成参数、所有LOGO图片URL和收藏状态
    """
    try:
        # 调用服务层获取详情数据
        detail_data = get_history_detail(db, openid, record_id)
        return detail_data

    except HTTPException as e:
        # 捕获服务层已知异常
        raise e
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="记录数据解析失败，可能已损坏"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取详情失败：{str(e)}"
        )
