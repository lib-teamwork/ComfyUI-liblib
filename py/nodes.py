import configparser
import os
import base64
import io
from PIL import Image
import time
import torch
from .liblib_client import LibLibClient, DEFAULT_MODEL_INFO, GenerateStatus

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
            raise ValueError('Appkey and Appsecret are required')
        
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
        
        # If config file exists, read it first
        if os.path.exists(config_path):
            config.read(config_path)

        # Ensure API section exists
        if 'API' not in config:
            config['API'] = {}

        # Save authentication info
        config['API']['APPKEY'] = auth_info['appkey']
        config['API']['APPSECRET'] = auth_info['appsecret']

        # Write to config file
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
            raise ValueError('Config file not found, please save authentication info first')

        config.read(config_path)

        try:
            appkey = config['API']['APPKEY']
            appsecret = config['API']['APPSECRET']

            if not appkey or not appsecret:
                raise ValueError('Authentication info not found in config file, please save it first')

            auth_info = {
                'appkey': appkey,
                'appsecret': appsecret
            }
            return (auth_info,)

        except KeyError:
            raise ValueError('Authentication info not found in config file, please save it first')

def _tensor_to_base64(tensor):
    # Convert tensor to PIL Image
    tensor = tensor.squeeze(0)
    tensor = (tensor * 255).byte()
    image = Image.fromarray(tensor.cpu().numpy())
    
    # Convert to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def _check_generate_status_and_download_image(client, generate_uuid):
    # Wait for generation to complete and download image synchronously
    while True:
        status = client.query_generate_status(generate_uuid)
        if status.generate_status == GenerateStatus.COMPLETED:
            images = [img.image_url for img in status.images]
            return [client.download_and_convert_image(image_url) for image_url in images]
        elif status.generate_status == GenerateStatus.FAILED:
            raise ValueError(f"Generation failed: {status.generate_msg}")
        time.sleep(5)

class LibLibTextToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "auth_info": ("LIB_LIB_AUTH_INFO", {"forceInput": True}),
                "prompt": ("STRING", {"multiline": True}),
                "model_name": ([DEFAULT_MODEL_INFO["model_name"]], {"default": DEFAULT_MODEL_INFO["model_name"]}),
                "img_count": ("INT", {"default": 1, "min": 1, "max": 4}),
            },
            "optional": {
                "aspect_ratio": (["square:1024x1024", "portrait:768x1024", "landscape:1280x720"], {"default": ""}),
                "width": ("INT", {"default": 0, }),
                "height": ("INT", {"default": 0,}),
            }
        }
    
    CATEGORY = CATEGORY_NAME
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE",)
    
    def generate(self, auth_info, prompt, model_name, img_count, aspect_ratio=None, width=0, height=0):
        client = LibLibClient(auth_info["appkey"], auth_info["appsecret"])
                
        # Handle size parameters
        actual_width = width if width > 0 else None
        actual_height = height if height > 0 else None
        actual_aspect_ratio = aspect_ratio if not (actual_width and actual_height) else None
        actual_aspect_ratio = actual_aspect_ratio.split(':')[0] if actual_aspect_ratio else None
        
        result = client.text_to_image(
            prompt=prompt,
            model_name=model_name,
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
                "image_url": ("STRING", {"default": ""}),
                "prompt": ("STRING", {"multiline": True}),
                "model_name": ([DEFAULT_MODEL_INFO["model_name"]], {"default": DEFAULT_MODEL_INFO["model_name"]}),
                "img_count": ("INT", {"default": 1, "min": 1, "max": 4}),
            }
        }
    
    CATEGORY = CATEGORY_NAME
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE",)
    
    def generate(self, auth_info, image_url, prompt, model_name, img_count):
        client = LibLibClient(auth_info["appkey"], auth_info["appsecret"])
        
        result = client.image_to_image(
            prompt=prompt,
            image_url=image_url,
            model_name=model_name,
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
