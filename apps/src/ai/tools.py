
import base64
import os
import json

def encode_image_to_base64(imagepath: str) -> str:

    path = imagepath.strip().strip('"').strip("'")

    if not os.path.exists(path):
        raise FileNotFoundError(f"can not find path: {path}")
        
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def adjust_brightness(image_path: str, factor: float) -> str:
    print(f"🔧 调用工具 [adjust_brightness] -> image_path: {image_path}, factor: {factor}")
    return f"亮度调整成功，参数 factor: {factor}"


def adjust_contrast(image_path: str, factor: float) -> str:
    print(f"🔧 调用工具 [adjust_contrast] -> image_path: {image_path}, factor: {factor}")
    return f"对比度调整成功，参数 factor: {factor}"


def adjust_color(image_path: str, factor: float) -> str:
    print(f"🔧 调用工具 [adjust_color] -> image_path: {image_path}, factor: {factor}")
    return f"色彩饱和度调整成功，参数 factor: {factor}"


def adjust_sharpness(image_path: str, factor: float) -> str:
    print(f"🔧 调用工具 [adjust_sharpness] -> image_path: {image_path}, factor: {factor}")
    return f"清晰度/锐化调整成功，参数 factor: {factor}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "adjust_brightness",
            "description": "调整指定图片的亮度。1.0 为原始亮度；>1.0 提亮（如 1.25）；<1.0 变暗（如 0.8）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片的本地文件路径"
                    },
                    "factor": {
                        "type": "number",
                        "description": "亮度调整倍数，默认 1.0"
                    }
                },
                "required": ["image_path", "factor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_contrast",
            "description": "调整指定图片的明暗对比度。1.0 为原始对比度；>1.0 增强反差；<1.0 使画面平缓柔和。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片的本地文件路径"
                    },
                    "factor": {
                        "type": "number",
                        "description": "对比度调整倍数，默认 1.0"
                    }
                },
                "required": ["image_path", "factor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_color",
            "description": "调整指定图片的色彩饱和度。1.0 为原始色彩；>1.0 色彩更浓郁艳丽；<1.0 色彩更素雅或偏黑白。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片的本地文件路径"
                    },
                    "factor": {
                        "type": "number",
                        "description": "色彩饱和度倍数，默认 1.0"
                    }
                },
                "required": ["image_path", "factor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_sharpness",
            "description": "调整指定图片的清晰度/锐度。1.0 为原始锐度；>1.0 提升画面细节和轮廓锐利度；<1.0 使画面柔焦朦胧。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片的本地文件路径"
                    },
                    "factor": {
                        "type": "number",
                        "description": "清晰度调整倍数，默认 1.0"
                    }
                },
                "required": ["image_path", "factor"]
            }
        }
    }
]


AVAILABLE_TOOLS = {
    "adjust_brightness": adjust_brightness,
    "adjust_contrast": adjust_contrast,
    "adjust_color": adjust_color,
    "adjust_sharpness": adjust_sharpness,
}

def ai_call_tool(tool: dict) -> str:
    func = AVAILABLE_TOOLS[tool["name"]]
    if not func:
        return f"not find tool, tool name: {func}"

    try:
        args = json.loads(tool["arguments"])
    except Exception as e:
        return f"parse arguments failed"

    res = func(**args)
    return res
