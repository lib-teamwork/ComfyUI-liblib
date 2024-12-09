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

MODEL_INFO = [
    {
        "template_uuid": "3af36dd5a61e4da88c6cb5eb57a8fe2e",
        "model_name": "Star-3-Alpha",
        "url_type":"ultra",
        "text2img_template_uuid":"5d7e67009b344550bc1aa6ccbfa1d7f4",
        "img2img_template_uuid":"07e00af4fc464c7ab55ff906f8acf1b7",
    }
]

DEFAULT_MODEL_INFO = MODEL_INFO[0]

def find_model_by_name(model_name) -> dict:
    for info in MODEL_INFO:
        if info["model_name"] == model_name:
            return info
    return None

class GenerateStatus(Enum):
    PENDING = 1     # Waiting to execute
    PROCESSING = 2  # In progress
    GENERATED = 3   # Image generated
    AUDITING = 4    # Under review
    COMPLETED = 5   # Success
    FAILED = 6      # Failed

class AuditStatus(Enum):
    PENDING = 1     # Pending review
    PROCESSING = 2  # Under review
    PASSED = 3      # Review passed
    BLOCKED = 4     # Review blocked
    FAILED = 5      # Review failed

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
        Generate signature
        """
        # Current timestamp in milliseconds
        timestamp = str(int(time.time() * 1000))
        # Random string
        signature_nonce = str(uuid.uuid4())
        # Concatenate request data
        content = '&'.join((uri, timestamp, signature_nonce))
        
        # Generate signature
        digest = hmac.new(self._appsecret.encode(), content.encode(), sha1).digest()
        # Remove padding equals signs added to complete base64 length
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
        
        if response.status_code != 200:
            raise ValueError(f"Request failed with status code {response.status_code}", response.text)
        
        data = response.json()
        if data.get('code') != 0:
            raise ValueError(data.get('msg', 'Unknown error'))
            
        return data['data']

    def text_to_image(self, prompt, model_name=DEFAULT_MODEL_INFO['model_name'], aspect_ratio=None,
                     width=None, height=None, img_count=1):
        """
        Text to image interface
        model_name: Star-3-Alpha
        """
        
        model_info = find_model_by_name(model_name)
        uri = f"/api/generate/webui/text2img/{model_info['url_type']}"
        

        
        if width is not None and (width < 512 or width > 2048):
            raise ValueError("Invalid width parameter (must be between 512 and 2048)")
        
        if height is not None and (height < 512 or height > 2048):
            raise ValueError("Invalid height parameter (must be between 512 and 2048)")
        if width is not None and height is not None:
            image_size = {"width": width, "height": height}
            aspect_ratio = None
        else:
            image_size = None
            
        if aspect_ratio is None and image_size is None:   
            raise ValueError("At least one size parameter must be specified")
        
        if aspect_ratio is not None and aspect_ratio not in ["square", "portrait", "landscape"]:
            raise ValueError("Invalid aspect ratio parameter")
        
        if img_count < 1 or img_count > 4:
            raise ValueError("Invalid image count parameter (must be between 1 and 4)")
            
        params = {
            "templateUuid": model_info['text2img_template_uuid'],
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

    def image_to_image(self, prompt, image_url, model_name=DEFAULT_MODEL_INFO['model_name'], img_count=1):
        """
        Image to image interface
        model_name: Star-3-Alpha
        """
        model_info = find_model_by_name(model_name)
        uri = f"/api/generate/webui/img2img/{model_info['url_type']}"
        
        if img_count < 1 or img_count > 4:
            raise ValueError("Invalid image count parameter (must be between 1 and 4)")
            
        params = {
            "templateUuid": model_info['img2img_template_uuid'],
            "generateParams": {
                "prompt": prompt,
                "sourceImage": image_url,
                "imgCount": img_count
            }
        }
        
        return self._make_request(uri, params)

    def query_generate_status(self, generate_uuid):
        """
        Query generation task status
        Returns: GenerateResult object
        """
        uri = "/api/generate/webui/status"
        
        params = {
            "generateUuid": generate_uuid
        }
        
        data = self._make_request(uri, params)
        return GenerateResult(data)
    
    def download_and_convert_image(self, image_url):
        """
        Download image and convert to tensor
        """
        with requests.get(image_url, stream=True) as req:
            image_data = req.content
            
        with Image.open(io.BytesIO(image_data)) as image:
            image_np = numpy.array(image).astype(numpy.float32) / 255.0
            tensor = torch.from_numpy(image_np)[None,]
            return tensor