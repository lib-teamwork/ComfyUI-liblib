import requests
import numpy
import torch
import time
import io
import hmac
from hashlib import sha1
import base64
import uuid
import json
from enum import Enum
from PIL import Image

class ModelType(Enum):
    SDXL = "classic"    # 经典版
    FLUX1 = "ultra"     # 旗舰版
    
TEMPLATE_UUID = {
    "text2img": {
        "classic": "3af36dd5a61e4da88c6cb5eb57a8fe2e",
        "ultra": "5d7e67009b344550bc1aa6ccbfa1d7f4"
    },
    "img2img": {
        "classic": "e653a58128d34d1dbc231a03e4fedd6f",
        "ultra": "07e00af4fc464c7ab55ff906f8acf1b7"
    }
}

class GenerateStatus(Enum):
    PENDING = 1     # 等待执行
    PROCESSING = 2  # 执行中
    GENERATED = 3   # 已生图
    AUDITING = 4    # 审核中
    COMPLETED = 5   # 成功
    FAILED = 6      # 失败

class AuditStatus(Enum):
    PENDING = 1     # 待审核
    PROCESSING = 2  # 审核中
    PASSED = 3      # 审核通过
    BLOCKED = 4     # 审核拦截
    FAILED = 5      # 审核失败

class GeneratedImage:
    def __init__(self, data: dict):
        self.image_url = data.get('imageUrl', '')
        self.seed = data.get('seed', 0)
        self.audit_status = AuditStatus(data.get('auditStatus', 0))

class GenerateResult:
    def __init__(self, data: dict):
        self.generate_uuid = data.get('generateUuid', '')
        self.generate_status = GenerateStatus(data.get('generateStatus', 0))
        self.percent_completed = data.get('percentCompleted', 0)
        self.generate_msg = data.get('generateMsg', '')
        self.images = [GeneratedImage(img) for img in data.get('images', [])]

class LibLibClient:
    _BASE_URL = 'https://openapi.liblibai.cloud'

    def __init__(self, appkey, appsecret):
        self._appkey = appkey
        self._appsecret = appsecret

    def _make_signature(self, uri):
        """
        生成签名
        """
        # 当前毫秒时间戳
        timestamp = str(int(time.time() * 1000))
        # 随机字符串
        signature_nonce = str(uuid.uuid4())
        # 拼接请求数据
        content = '&'.join((uri, timestamp, signature_nonce))
        
        # 生成签名
        digest = hmac.new(self._appsecret.encode(), content.encode(), sha1).digest()
        # 移除为了补全base64位数而填充的尾部等号
        sign = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
        
        return sign, timestamp, signature_nonce

    def _make_request(self, uri, params):
        # 生成签名相关参数
        sign, timestamp, nonce = self._make_signature(uri)
        
        # 构建带签名的URL
        url = f"{self._BASE_URL}{uri}"
        url += f"?AccessKey={self._appkey}"
        url += f"&Signature={sign}"
        url += f"&Timestamp={timestamp}"
        url += f"&SignatureNonce={nonce}"
        
        # 发送请求
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=params
        )
        
        data = response.json()
        if data.get('code') != 0:
            raise ValueError(data.get('msg', '未知错误'))
            
        return data['data']

    def text_to_image(self, prompt, model_type=ModelType.SDXL, aspect_ratio=None,
                     width=None, height=None, img_count=1):
        """
        文生图接口
        model_type: ModelType.SDXL (经典版) 或 ModelType.FLUX1 (旗舰版)
        """
        uri = f"/api/generate/webui/text2img/{model_type.value}"
        

        
        if width is not None and (width < 512 or width > 2048):
            raise ValueError("宽度参数无效（必须在512到2048之间）")
        
        if height is not None and (height < 512 or height > 2048):
            raise ValueError("高度参数无效（必须在512到2048之间）")
        if width is not None and height is not None:
            image_size = {"width": width, "height": height}
            aspect_ratio = None
        else:
            image_size = None
            
        if aspect_ratio is None and image_size is None:   
            raise ValueError("必须指定至少一个尺寸参数")
        
        if aspect_ratio is not None and aspect_ratio not in ["square", "portrait", "landscape"]:
            raise ValueError("无效的宽高比参数")
        
        if img_count < 1 or img_count > 4:
            raise ValueError("图片数量参数无效（必须在1到4之间）")
            
        params = {
            "templateUuid": TEMPLATE_UUID["text2img"][model_type.value],
            "generateParams": {
                "prompt": prompt,
                "imgCount": img_count
            }
        }

        # 根据情况添加尺寸参数
        if aspect_ratio:
            params["generateParams"]["aspectRatio"] = aspect_ratio
        if image_size:
            params["generateParams"]["imageSize"] = image_size
            
        return self._make_request(uri, params)

    def image_to_image(self, prompt, image_url, model_type=ModelType.SDXL, img_count=1):
        """
        图生图接口
        model_type: ModelType.SDXL (经典版) 或 ModelType.FLUX1 (旗舰版)
        """
        uri = f"/api/generate/webui/img2img/{model_type.value}"
        
        if img_count < 1 or img_count > 4:
            raise ValueError("图片数量参数无效（必须在1到4之间）")
            
        params = {
            "templateUuid": TEMPLATE_UUID["img2img"][model_type.value],
            "generateParams": {
                "prompt": prompt,
                "sourceImage": image_url,
                "imgCount": img_count
            }
        }
        
        return self._make_request(uri, params)

    def query_generate_status(self, generate_uuid):
        """
        查询生成任务状态
        返回: GenerateResult 对象
        """
        uri = "/api/generate/webui/status"
        
        params = {
            "generateUuid": generate_uuid
        }
        
        data = self._make_request(uri, params)
        return GenerateResult(data)
    
    def download_and_convert_image(self, image_url):
        """
        下载图片并转换为tensor
        """
        with requests.get(image_url, stream=True) as req:
            image_data = req.content
            
        with Image.open(io.BytesIO(image_data)) as image:
            image_np = numpy.array(image).astype(numpy.float32) / 255.0
            tensor = torch.from_numpy(image_np)[None,]
            return tensor