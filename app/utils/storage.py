import boto3  # 以AWS S3为例，其他云存储（如阿里云OSS）需替换对应SDK
from botocore.exceptions import ClientError
from config import settings  # 导入配置

import boto3
from botocore.exceptions import ClientError
import uuid
import mimetypes
from config import settings
from fastapi import HTTPException

def upload_image(image_data: bytes, file_ext: str = "png") -> dict:
    """
    上传图片到云存储（如S3兼容存储）
    
    参数：
        image_data: 图片二进制数据
        file_ext: 文件扩展名（默认png）
        
    返回：
        dict: 包含存储键（key）和基础信息的字典
              格式: {"key": "存储对象键", "content_type": "图片MIME类型"}
        
    异常：
        HTTPException: 上传失败时抛出
    """
    # 1. 生成唯一文件名（避免重复）
    # 格式: logos/{uuid}.{ext}（按业务分类存储）
    unique_filename = f"logos/{uuid.uuid4().hex}.{file_ext}"
    
    # 2. 自动识别MIME类型（如image/png、image/jpeg）
    content_type, _ = mimetypes.guess_type(f"temp.{file_ext}")
    if not content_type:
        content_type = f"image/{file_ext}"  # 兜底类型
    
    # 3. 初始化云存储客户端（以S3为例，其他存储需调整SDK）
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        region_name=settings.STORAGE_REGION
    )
    
    try:
        # 4. 上传图片到存储桶
        s3_client.put_object(
            Bucket=settings.STORAGE_BUCKET,
            Key=unique_filename,
            Body=image_data,
            ContentType=content_type,
            ACL="private"  # 私有访问（需签名URL访问）
        )
        
        # 5. 返回存储标识（用于后续生成访问URL）
        return {
            "key": unique_filename,
            "content_type": content_type
        }
        
    except ClientError as e:
        # 捕获云存储服务错误（如权限不足、存储桶不存在）
        error_code = e.response["Error"]["Code"]
        error_msg = f"图片上传失败：{error_code} - {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        # 捕获其他异常（如网络错误）
        raise HTTPException(
            status_code=500,
            detail=f"图片上传过程出错：{str(e)}"
        )

def generate_presigned_url(object_key: str, expires_in: int = 3600) -> str | None:
    """
    生成云存储对象的带签名临时URL（用于访问私有资源）

    参数：
        object_key: 存储对象的键（路径+文件名）
        expires_in: 有效期（秒），默认1小时

    返回：
        str: 带签名的URL；None: 生成失败
    """
    # 初始化云存储客户端（以S3为例，其他存储需调整）
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        region_name=settings.STORAGE_REGION
    )

    try:
        # 生成带签名的GET请求URL
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.STORAGE_BUCKET,
                'Key': object_key
            },
            ExpiresIn=expires_in
        )
        return response
    except ClientError as e:
        # 记录错误日志（实际项目中应添加日志系统）
        print(f"云存储签名URL生成失败：{str(e)}")
        return None
