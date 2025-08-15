import boto3  # 以AWS S3为例，其他云存储（如阿里云OSS）需替换对应SDK
from botocore.exceptions import ClientError
from app.config import settings  # 导入配置


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
