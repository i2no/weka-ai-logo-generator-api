from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
from app.utils.token import get_current_user  # 用户身份验证
from app.utils.db import get_db  # 数据库会话
from app.services.image_service import get_hd_logo_url  # 业务逻辑
from app.services.image_service import create_image_report  # 业务逻辑
from pydantic import Field


router = APIRouter()


# 响应模型
class HDUrlResponse(BaseModel):
    logo_id: str
    hd_url: str  # 高清图片URL
    expires_at: str  # URL有效期（UTC时间，格式：YYYY-MM-DD HH:MM:SS）

    class Config:
        json_schema_extra = {
            "example": {
                "logo_id": "logo_123456",
                "hd_url": "https://storage.example.com/hd/logo1_hd.png",
                "expires_at": "2023-10-10 23:59:59"
            }
        }


@router.get("/hd-url", response_model=HDUrlResponse, summary="获取LOGO高清图片URL")
def get_hd_image_url(
    logo_id: str = Query(..., min_length=8, max_length=32, description="LOGO任务ID"),
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定LOGO的高清图片URL：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 仅允许获取当前用户创建的LOGO的高清资源
    - 返回高清URL及有效期（通常为24小时）
    """
    try:
        # 调用服务层获取高清URL
        hd_data = get_hd_logo_url(db, openid, logo_id)
        return hd_data

    except HTTPException as e:
        # 捕获服务层已知异常
        raise e
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="LOGO资源数据损坏，无法获取高清URL"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取高清图片失败：{str(e)}"
        )


class ImageReportRequest(BaseModel):
    logo_id: str = Field(..., min_length=8, max_length=32, description="被举报的LOGO任务ID")
    reason: str = Field(..., min_length=5, max_length=500, description="举报原因（5-500字）")


# 举报响应模型
class ImageReportResponse(BaseModel):
    success: bool
    message: str
    report_id: int  # 举报记录ID
    logo_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "举报已提交，我们将尽快处理",
                "report_id": 1001,
                "logo_id": "logo_123456"
            }
        }


@router.post("/report", response_model=ImageReportResponse, summary="举报有问题的LOGO图片")
def report_image(
    data: ImageReportRequest,
    openid: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    举报用户自己创建的有问题的LOGO图片：
    - 需要验证用户token（请求头Authorization: Bearer {token}）
    - 仅允许举报当前用户创建的LOGO
    - 举报原因需5-500字，说明具体问题（如内容违规、生成错误等）
    """
    try:
        # 调用服务层创建举报记录
        report_id = create_image_report(
            db=db,
            openid=openid,
            logo_id=data.logo_id,
            reason=data.reason
        )

        return {
            "success": True,
            "message": "举报已提交，我们将尽快处理",
            "report_id": report_id,
            "logo_id": data.logo_id
        }

    except HTTPException as e:
        # 捕获服务层已知异常
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"提交举报失败：{str(e)}"
        )
