# ComfyUI-liblib

这是一个用于在 ComfyUI 中调用 LibLib AI API 的自定义节点集合。

## 功能节点

### LibLib Auth Info
用于创建认证信息,需要输入:
- appkey: LibLib API 的 AppKey
- appsecret: LibLib API 的 AppSecret

### Save LibLib Auth Info
将认证信息保存到配置文件中,方便后续使用。

### Load LibLib Auth Info 
从配置文件中加载已保存的认证信息。

### LibLib Text to Image
文本生成图片节点,支持:
- 输入提示词(prompt)
- 选择模型类型(SDXL/FLUX1)
- 设置生成图片数量(1-4张)
- 可选择预设尺寸比例(方形1024x1024/竖版768x1024/横版1280x720)
- 可自定义宽高(512-2048之间)

### LibLib Image to Image
图片生成图片节点,支持:
- 输入参考图片
- 输入提示词(prompt) 
- 选择模型类型(SDXL/FLUX1)
- 设置生成图片数量(1-4张)

## 使用流程

1. 首先使用 LibLib Auth Info 节点创建认证信息
2. 可以用 Save LibLib Auth Info 保存认证信息
3. 后续可以用 Load LibLib Auth Info 加载认证信息
4. 将认证信息连接到 Text to Image 或 Image to Image 节点
5. 设置相应参数开始生成图片

## 注意事项

- 需要先在 LibLib AI 平台注册并获取 AppKey 和 AppSecret
- 生成图片时会实时查询状态直到完成
- 图片尺寸需要在合理范围内(512-2048)
- 单次可生成1-4张图片
