# ComfyUI-liblib

A custom node collection for using the LibLib AI API within ComfyUI.

## Functional Nodes

### LibLib Auth Info
Creates authentication information. Requires the following inputs:
- **appkey**: The AppKey for the LibLib API.
- **appsecret**: The AppSecret for the LibLib API.

### Save LibLib Auth Info
Saves the authentication information to a configuration file for convenient reuse.

### Load LibLib Auth Info
Loads previously saved authentication information from the configuration file.

### LibLib Text to Image
A node for generating images from text. Features include:
- Input for **prompt**.
- Selection of model name (**Star-3-Alpha**).
- Option to set the number of images to generate (1-4).
- Preset aspect ratios:
  - **Square** (1024x1024)
  - **Portrait** (768x1024)
  - **Landscape** (1280x720)
- Customizable width and height (range: 512-2048).

### LibLib Image to Image (WIP)
A node for generating images from reference images. Features include:
- Input for a reference image.
- Input for **prompt**.
- Selection of model name (**Star-3-Alpha**).
- Option to set the number of images to generate (1-4).

## Usage Workflow

1. Use the **LibLib Auth Info** node to create authentication information.
2. Optionally, save the authentication information using the **Save LibLib Auth Info** node.
3. Load saved authentication information using the **Load LibLib Auth Info** node.
4. Connect the authentication information to the **Text to Image** or **Image to Image** node.
5. Configure the desired parameters and start generating images.

## Workflow Examples
1. Generate images using text-to-image node [example](./examples/text2img.json)
2. Generate images using image-to-image node [example](./examples/img2img.json)
3. Save authentication info to avoid exposure [example](./examples/save_auth_info.json) 
4. Generate images using saved authentication info [example](./examples/text2img_use_load_auth_info.json)

## Notes

- Registration on the LibLib AI platform is required to obtain the AppKey and AppSecret.
- The generation process involves real-time status checks until completion.
- Ensure the image dimensions are within the valid range (512-2048).
- A single request can generate 1-4 images.

## Example
<img width="1299" alt="image" src="https://github.com/user-attachments/assets/f36cceaa-e77a-4860-9659-ef21d02fabca">

