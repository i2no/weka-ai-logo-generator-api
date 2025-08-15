# import os
import logging
import time
from typing import Dict, List
import torch  # 假设使用PyTorch训练模型
import numpy as np
from PIL import Image
from config import settings  # 加载模型路径等配置
from app.utils.storage import upload_image  # 图片上传到云存储的工具
import requests
import json
from fastapi import HTTPException

# 配置日志
logger = logging.getLogger(__name__)

def call_ai_logo_api(
    company_name: str,
    industry: str,
    styles: list,
    colors: list,
    description: str = ""
) -> dict:
    """
    调用外部AI服务生成LOGO图片
    
    参数：
        company_name: 企业名称
        industry: 行业类型
        styles: 风格列表（如["极简风", "科技风"]）
        colors: 颜色列表（如["#1677FF", "#303133"]）
        description: 额外描述（可选）
        
    返回：
        dict: AI服务返回的结果，包含生成的LOGO图片二进制数据或URL
              格式示例: {"success": True, "images": [b"图片二进制数据1", b"图片二进制数据2"]}
        
    异常：
        HTTPException: 调用失败时抛出（包含错误信息）
    """
    # 1. 准备AI服务请求参数
    payload = {
        "company_name": company_name,
        "industry": industry,
        "styles": styles,
        "colors": colors,
        "description": description,
        "api_key": settings.AI_SERVICE_API_KEY  # 从配置读取AI服务密钥
    }
    
    # 2. 调用AI服务API
    try:
        response = requests.post(
            url=settings.AI_SERVICE_ENDPOINT,  # AI服务接口地址（从配置读取）
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60  # 超时时间（生成LOGO可能需要较长时间）
        )
        
        # 3. 处理响应
        response_data = response.json()
        
        # 4. 检查AI服务返回状态
        if not response.ok:
            error_msg = response_data.get("error", f"AI服务调用失败（状态码：{response.status_code}）")
            raise HTTPException(status_code=500, detail=f"LOGO生成失败：{error_msg}")
        
        if not response_data.get("success", False):
            error_msg = response_data.get("message", "AI服务返回非成功状态")
            raise HTTPException(status_code=500, detail=f"LOGO生成失败：{error_msg}")
        
        # 5. 验证返回的图片数据
        images = response_data.get("images", [])
        if not images or not isinstance(images, list):
            raise HTTPException(status_code=500, detail="AI服务未返回有效的LOGO图片数据")
        
        return response_data
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="AI服务调用超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="AI服务连接失败，请检查服务是否可用")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI服务返回数据格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调用AI服务时发生错误：{str(e)}")
    

class LocalAIClient:
    """本地模型客户端，封装模型加载和LOGO生成逻辑"""

    def __init__(self):
        # 模型配置（从配置文件读取）
        self.model_path = settings.LOCAL_MODEL_PATH  # 本地模型权重路径
        self.device = "cuda" if torch.cuda.is_available() else "cpu"  # 优先使用GPU
        self.model = None  # 模型实例（延迟加载，节省启动时间）
        self.input_size = (512, 512)  # 模型输入尺寸
        self.num_logos_per_request = 3  # 每次生成的LOGO数量

    def _load_model(self):
        """延迟加载模型（首次调用时加载，避免服务启动时耗时过长）"""
        if self.model is None:
            try:
                logger.info(f"从 {self.model_path} 加载模型，使用设备：{self.device}")

                # 加载模型（根据你的模型类型调整，以下为示例）
                # 假设模型是用PyTorch训练的生成式模型
                self.model = torch.load(
                    self.model_path,
                    map_location=torch.device(self.device)
                )
                self.model.eval()  # 切换到评估模式
                logger.info("模型加载成功")

            except Exception as e:
                logger.error(f"模型加载失败：{str(e)}")
                raise Exception(f"本地模型初始化失败：{str(e)}")

    def _preprocess_input(self, params: Dict) -> Dict:
        """预处理用户输入参数，转换为模型可接受的格式"""
        # 提取用户输入的核心参数
        company_name = params.get("company_name", "")
        industry = params.get("industry", "")
        styles = params.get("styles", [])
        colors = params.get("colors", [])
        description = params.get("description", "")

        # 构造模型输入（根据你的模型需求调整格式）
        # 例如：将文本描述转换为嵌入向量，或拼接成prompt
        prompt = f"企业名称：{company_name}，行业：{industry}，风格：{','.join(styles)}，颜色：{','.join(colors)}。要求：{description}"

        return {
            "prompt": prompt,
            "input_size": self.input_size,
            "num_outputs": self.num_logos_per_request
        }

    def _postprocess_output(self, model_output: List[np.ndarray], task_id: str) -> Dict:
        """ 后处理模型输出，转换为图片URL并上传到存储 """
        logos = []  # 普通清晰度图片URL
        hd_keys = []  # 高清图片存储标识（用于后续生成高清URL）

        for i, image_array in enumerate(model_output):
            try:
                # 将模型输出转换为PIL图片
                image = Image.fromarray(image_array.astype(np.uint8))

                # 生成存储路径
                base_filename = f"logo_{task_id}_{i}"
                normal_path = f"normal/{base_filename}.png"
                hd_path = f"hd/{base_filename}_hd.png"

                # 上传普通清晰度图片（保留URL用于直接展示）
                normal_url = upload_image(
                    image=image,
                    object_key=normal_path,
                    quality=80
                )
                logos.append(normal_url)

                # 上传高清图片（仅记录路径，不保存URL，修复未使用变量问题）
                # 直接调用上传函数，不赋值给变量（或添加日志验证）
                upload_image(
                    image=image,
                    object_key=hd_path,
                    quality=100  # 保持高清
                )
                hd_keys.append(hd_path)  # 存储路径用于后续生成高清URL

                # 可选：添加日志确认上传成功
                logger.info(f"高清图片上传成功：{hd_path}")

            except Exception as e:
                logger.warning(f"图片处理失败（索引{i}）：{str(e)}")
                continue

        if not logos:
            raise Exception("模型生成成功，但图片处理/上传失败")

        return {
            "logos": logos,
            "hd_keys": hd_keys
        }

    def generate_logo(self, params: Dict, task_id: str) -> Dict:
        """
        调用本地模型生成LOGO

        参数：
            params: 用户输入的生成参数（企业名称、风格等）
            task_id: 本地任务ID（用于图片命名，避免冲突）

        返回：
            Dict: 包含生成的LOGO URL和高清标识的结果
        """
        try:
            # 1. 加载模型（首次调用时加载）
            self._load_model()

            # 2. 预处理输入参数
            model_input = self._preprocess_input(params)
            logger.info(f"本地模型推理开始，任务ID：{task_id}，prompt：{model_input['prompt']}")

            # 3. 模型推理（根据你的模型类型调整）
            start_time = time.time()
            with torch.no_grad():  # 关闭梯度计算，节省内存
                # 假设模型输入是prompt，输出是多个图片的numpy数组
                model_output = self.model.generate(
                    prompt=model_input["prompt"],
                    num_images=model_input["num_outputs"],
                    size=model_input["input_size"]
                )
            infer_time = time.time() - start_time
            logger.info(f"模型推理完成，耗时：{infer_time:.2f}秒，生成{len(model_output)}张图片")

            # 4. 后处理输出（转图片→上传→返回URL）
            result = self._postprocess_output(model_output, task_id)
            return result

        except Exception as e:
            logger.error(f"本地模型生成失败：{str(e)}")
            raise Exception(f"LOGO生成失败：{str(e)}")


# 实例化本地模型客户端（全局使用）
ai_client = LocalAIClient()
