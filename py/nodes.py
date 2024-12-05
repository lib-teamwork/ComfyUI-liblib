import configparser
import os
import base64
import io
from PIL import Image
import numpy as np
import time
import torch
import requests
from .liblib_client import LibLibClient, ModelType, GenerateStatus

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
config_path = os.path.join(parent_dir, 'config.ini')

CATEGORY_NAME = 'LibLib'

class LibLibAuthInfo:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'appkey': ('STRING', {'default': ''}),
                'appsecret': ('STRING', {'default': ''})
            }
        }
        
    CATEGORY = CATEGORY_NAME
    FUNCTION = 'make_auth_info'
    RETURN_TYPES = ('LIB_LIB_AUTH_INFO',)
    RETURN_NAMES = ('auth_info',)

    def make_auth_info(self, appkey, appsecret):
        if not appkey or not appsecret:
            raise ValueError('Appkey 和 Appsecret 是必填项')
        
        auth_info = {
            'appkey': appkey,
            'appsecret': appsecret
        }
        return (auth_info,)

class SaveLibLibAuthInfo:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'auth_info': ('LIB_LIB_AUTH_INFO', {'forceInput': True})
            }
        }
        
    CATEGORY = CATEGORY_NAME
    OUTPUT_NODE = True
    FUNCTION = 'save_auth_info'
    RETURN_TYPES = ()

    def save_auth_info(self, auth_info):
        config = configparser.ConfigParser()
        
        # 如果配置文件已存在，先读取它
        if os.path.exists(config_path):
            config.read(config_path)

        # 确保有 API 部分
        if 'API' not in config:
            config['API'] = {}

        # 保存认证信息
        config['API']['APPKEY'] = auth_info['appkey']
        config['API']['APPSECRET'] = auth_info['appsecret']

        # 写入配置文件
        with open(config_path, 'w') as f:
            config.write(f)
        return ()

class LoadLibLibAuthInfo:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {}
        }
        
    CATEGORY = CATEGORY_NAME
    FUNCTION = 'load_auth_info'
    RETURN_TYPES = ('LIB_LIB_AUTH_INFO',)
    RETURN_NAMES = ('auth_info',)

    def load_auth_info(self):
        config = configparser.ConfigParser()
        
        if not os.path.exists(config_path):
            raise ValueError('未找到配置文件，请先保存认证信息')

        config.read(config_path)

        try:
            appkey = config['API']['APPKEY']
            appsecret = config['API']['APPSECRET']

            if not appkey or not appsecret:
                raise ValueError('配置文件中未找到认证信息，请先保存认证信息')

            auth_info = {
                'appkey': appkey,
                'appsecret': appsecret
            }
            return (auth_info,)

        except KeyError:
            raise ValueError('配置文件中未找到认证信息，请先保存认证信息')

def _tensor_to_base64(tensor):
    # 将tensor转换为PIL Image
    tensor = tensor.squeeze(0)
    tensor = (tensor * 255).byte()
    image = Image.fromarray(tensor.cpu().numpy())
    
    # 转换为base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def _check_generate_status_and_download_image(client, generate_uuid):
    # 同步等待生成完成并下载图片
    while True:
        status = client.query_generate_status(generate_uuid)
        if status.generate_status == GenerateStatus.COMPLETED:
            images = [img.image_url for img in status.images]
            return [client.download_and_convert_image(image_url) for image_url in images]
        elif status.generate_status == GenerateStatus.FAILED:
            raise ValueError(f"生成失败: {status.generate_msg}")
        time.sleep(5)

class LibLibTextToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "auth_info": ("LIB_LIB_AUTH_INFO", {"forceInput": True}),
                "prompt": ("STRING", {"multiline": True}),
                "model_type": (["SDXL", "FLUX1"], {"default": "SDXL"}),
                "img_count": ("INT", {"default": 1, "min": 1, "max": 4}),
            },
            "optional": {  # 将尺寸相关参数设为可选
                "aspect_ratio": (["square:1024x1024", "portrait:768x1024", "landscape:1280x720"], {"default": ""}),
                "width": ("INT", {"default": 0, }),
                "height": ("INT", {"default": 0,}),
            }
        }
    
    CATEGORY = CATEGORY_NAME
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE",)
    
    def generate(self, auth_info, prompt, model_type, img_count, aspect_ratio=None, width=0, height=0):
        client = LibLibClient(auth_info["appkey"], auth_info["appsecret"])
        
        model_enum = ModelType[model_type]
        
        # 处理尺寸参数
        actual_width = width if width > 0 else None
        actual_height = height if height > 0 else None
        actual_aspect_ratio = aspect_ratio if not (actual_width and actual_height) else None
        actual_aspect_ratio = actual_aspect_ratio.split(':')[0] if actual_aspect_ratio else None
        
        result = client.text_to_image(
            prompt=prompt,
            model_type=model_enum,
            aspect_ratio=actual_aspect_ratio,
            width=actual_width,
            height=actual_height,
            img_count=img_count
        )
        
        images = _check_generate_status_and_download_image(client, result["generateUuid"])
        combined_tensor = torch.cat(images, dim=0)
        
        return (combined_tensor,)

class LibLibImageToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "auth_info": ("LIB_LIB_AUTH_INFO", {"forceInput": True}),
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True}),
                "model_type": (["SDXL", "FLUX1"], {"default": "SDXL"}),
                "img_count": ("INT", {"default": 1, "min": 1, "max": 4}),
            }
        }
    
    CATEGORY = CATEGORY_NAME
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE",)
    
    def generate(self, auth_info, image, prompt, model_type, img_count):
        client = LibLibClient(auth_info["appkey"], auth_info["appsecret"])
        
        image_base64 = _tensor_to_base64(image)
        
        # 将字符串转换为对应的ModelType枚举值
        model_enum = ModelType[model_type]
        
        result = client.image_to_image(
            prompt=prompt,
            image_url=image_base64,
            model_type=model_enum,
            img_count=img_count
        )
        
        images = _check_generate_status_and_download_image(client, result["generateUuid"])
        combined_tensor = torch.cat(images, dim=0)
        
        return (combined_tensor,)

NODE_CLASS_MAPPINGS = {
    'LibLibAuthInfo': LibLibAuthInfo,
    'SaveLibLibAuthInfo': SaveLibLibAuthInfo,
    'LoadLibLibAuthInfo': LoadLibLibAuthInfo,
    'LibLibTextToImage': LibLibTextToImage,
    'LibLibImageToImage': LibLibImageToImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    'LibLibAuthInfo': 'LibLib Auth Info',
    'SaveLibLibAuthInfo': 'Save LibLib Auth Info',
    'LoadLibLibAuthInfo': 'Load LibLib Auth Info',
    'LibLibTextToImage': 'LibLib Text to Image',
    'LibLibImageToImage': 'LibLib Image to Image',
}
