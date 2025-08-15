from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel, Literal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.utils.token import get_current_user  # 用户身份验证
from app.utils.db import get_db  # 数据库会话
from app.services.favorite_service import toggle_favorite_status  # 业务逻辑
from app.services.favorite_service import get_favorite_list  # 业务逻辑
from typing import Literal, Optional
# import json
from typing import List
from fastapi import Query
from app.services.favorite_service import delete_favorite

router = APIRouter()


# 请求参数模型
class FavoriteToggleRequest(BaseModel):
    logo_id: str  # 要操作的LOGO任务ID（即record_id）
    action: Literal["add", "remove"]  # 操作类型：添加或移除收藏


# 响应模型
class FavoriteToggleResponse(BaseModel):
    success: bool
    message: str
    logo_id: str
    is_favorite: bool  # 当前收藏状态（操作后）

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "已添加到收藏",
                "logo_id": "logo_123456",
                "is_favorite": True
            }
        }


@router.post("/toggle", response_model=FavoriteToggleResponse, summary="切换LOGO收藏状态")
def toggle_favorite(
    data: FavoriteToggleRequest,
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    切换用户对指定LOGO的收藏状态：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 支持两种操作：添加收藏（action=add）或移除收藏（action=remove）
    - 仅允许操作当前用户创建的LOGO记录
    - 返回操作结果和当前收藏状态
    """
    try:
        # 调用服务层执行收藏状态切换
        result = toggle_favorite_status(
            db=db,
            openid=openid,
            logo_id=data.logo_id,
            action=data.action
        )

        return {
            "success": True,
            "message": result["message"],
            "logo_id": data.logo_id,
            "is_favorite": result["is_favorite"]
        }

    except HTTPException as e:
        # 捕获服务层抛出的已知异常（如LOGO不存在）
        raise e
    except Exception as e:
        # 捕获未预料的异常
        raise HTTPException(
            status_code=500,
            detail=f"操作失败：{str(e)}"
        )


# 单条收藏记录响应模型
class FavoriteItem(BaseModel):
    favorite_id: int  # 收藏记录ID
    logo_id: str  # 关联的LOGO任务ID
    company_name: str  # 企业名称
    styles: List[str] = []  # 风格列表
    thumbnail: Optional[str] = None  # LOGO缩略图URL
    favorite_time: str  # 收藏时间

    class Config:
        from_attributes = True


# 分页列表响应模型
class FavoriteListResponse(BaseModel):
    total: int  # 总收藏数
    page: int  # 当前页码
    size: int  # 每页条数
    total_pages: int  # 总页数
    records: List[FavoriteItem]  # 收藏列表

    class Config:
        json_schema_extra = {
            "example": {
                "total": 8,
                "page": 1,
                "size": 10,
                "total_pages": 1,
                "records": [
                    {
                        "favorite_id": 101,
                        "logo_id": "logo_123456",
                        "company_name": "云启科技",
                        "styles": ["极简风", "科技风"],
                        "thumbnail": "https://storage.example.com/logo1.png",
                        "favorite_time": "2023-10-02 09:15:30"
                    }
                ]
            }
        }


@router.get("/list", response_model=FavoriteListResponse, summary="获取收藏列表")
def get_favorites(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    size: int = Query(10, ge=1, le=50, description="每页条数（1-50）"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    分页获取当前用户的收藏列表：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 按收藏时间倒序排列（最新收藏在前）
    - 每条记录包含收藏ID、关联LOGO信息和收藏时间
    """
    try:
        # 调用服务层获取分页数据
        result = get_favorite_list(
            db=db,
            openid=openid,
            page=page,
            page_size=size
        )

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
            detail=f"获取收藏列表失败：{str(e)}"
        )


# 删除响应模型
class FavoriteDeleteResponse(BaseModel):
    success: bool
    message: str
    logo_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "收藏已删除",
                "logo_id": "logo_123456"
            }
        }


@router.delete("/delete", response_model=FavoriteDeleteResponse, summary="删除指定LOGO的收藏")
def delete_favorite_api(
    logo_id: str = Query(..., min_length=8, max_length=32, description="要取消收藏的LOGO任务ID"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除当前用户对指定LOGO的收藏记录：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 仅允许删除当前用户的收藏记录
    - 支持从收藏列表中移除指定LOGO
    """
    try:
        # 调用服务层执行删除操作
        delete_favorite(db, openid, logo_id)

        return {
            "success": True,
            "message": "收藏已删除",
            "logo_id": logo_id
        }

    except HTTPException as e:
        # 捕获服务层抛出的已知异常
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除收藏失败：{str(e)}"
        )
