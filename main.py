from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import logo, history, favorite, image  # 导入所有接口路由
from app.utils.db import create_tables  # 数据库表初始化工具（需实现）

# 创建 FastAPI 实例
app = FastAPI(
    title="LOGO生成小程序后端API",
    description="提供LOGO生成、历史记录、收藏等功能接口",
    version="1.0.0"
)

# 配置跨域（允许小程序前端域名访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 本地前端开发地址
        "https://www.weka.cc",   # 线上小程序域名（需在微信公众平台配置）
        "https://www.ai-site.cc",   # 线上小程序域名（需在微信公众平台配置）
    ],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由（将之前实现的接口挂载到 /api 路径下）
app.include_router(logo.router, prefix="/api/logo", tags=["LOGO生成"])
app.include_router(history.router, prefix="/api/history", tags=["历史记录"])
app.include_router(favorite.router, prefix="/api/favorite", tags=["收藏管理"])
app.include_router(image.router, prefix="/api/image", tags=["图片操作"])


# 启动时初始化数据库表（首次运行时创建所有模型对应的表）
@app.on_event("startup")
def startup_event():
    create_tables()  # 创建数据库表（需实现该函数）
    print("服务启动成功，数据库表初始化完成")


# 根路径测试接口
@app.get("/", tags=["测试"])
def read_root():
    return {"message": "LOGO生成小程序后端API正常运行中"}
