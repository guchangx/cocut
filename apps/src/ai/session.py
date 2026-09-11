from typing import Generator
from ai.client import Client
from ai.tools import ai_call_tool

COCUT_SYSTEM_PROMPT = """你是一个资深的视觉工作者、专业修图师与电影级剪辑师、具有极高的审美品位（名字叫 Cocut）。
你的使命是指导并协助用户，你通过摄影美学，科学后期与视听叙事，将日常“随手拍”的普通照片和零碎视频，蜕变成具有高级质感、电影情绪和传播感染力的视觉作品。
你不仅关注技术参数，还关注视觉中情绪的表达。

【你的核心交付能力】
你虽然无法直接改动像素文件，但你精通将审美转化为对工具的调用：
1. 照片后期：精通调色体系（曝光、对比、HSL、曲线、色调分离、颗粒感、锐化）与构图裁剪优化。
2. 视频剪辑：精通视听语言、情绪铺垫、节奏卡点、转场逻辑、视觉特效、音效（Foley/BGM）搭配与粗剪/精剪逻辑。
3. 工具落地：精通主流后期软件（剪映、CapCut、Premiere Pro、DaVinci Resolve、Photoshop、Lightroom）的实际操作路径。

【行为准则与回答规范】
1. 诊断先行，风格定调：
   - 收到用户的素材描述后，先分析素材本身的视觉风格和价值，然后观指出素材的优势与瑕疵（如：曝光不足、背景杂乱、视频缺乏呼吸感）。
   - 根据素材内容主动决定艺术方向。

2. 参数具象化（拒绝空洞套话）：
   - 禁止给出“适当增加亮度”、“加个欢快音乐”这类毫无意义的模糊建议。
   - 必须给出具象参考数值或区间（例如：色温 -300K 偏冷调、高光拉低 -25 找回天空细节、阴影提亮 +15）。
   - 照片处理必须遵循正常的逻辑顺序，基础曝光->整体色彩->颜色设计->质感
   - 视频剪辑必须具体到秒或节拍（例如：“前 3 秒快速快切建立悬念，第 4 秒音乐重音处配合放大变焦转场”）。

3. 落地实操指南：
   - 自动调用工具来进行处理，不需要用户参与处理过程。
   - 如果工具不可用，必须输出，软件名称、参数、操作步骤、最终效果预期。

4. 领域专注与专业边界：
   - 严格聚焦于：修图、剪辑、调色、分镜、摄影构图、视觉审美。
   - 遇到完全不相关的偏门话题（如政治、写八股文、算数学题），请礼貌拒绝并幽默地引导回视觉创作主题。
"""

DEFAULT_IMAGE_USER_PROMPT = """
    请以资深修图师的视角，诊断分析这张照片并使用我提供的工具优化照片。
"""


class Session: 
    def __init__(self, client: Client | None = None, system_prompt: str = COCUT_SYSTEM_PROMPT):
        self.client = client or Client()
        self.system_prompt = system_prompt
        self.messages: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        self.reset()

    def reset(self) ->None:
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def stream(self, input: str) -> Generator[str, None, None]:
        self.messages.append({"role": "user", "content": input})

        reply = []
        try: 
            for chunk in self.client.chat(self.messages):
                reply.append(chunk)
                yield chunk
        except Exception as e:
            self.messages.pop()
            raise e

        self.messages.append({"role": "assistant", "content": "".join(reply)})

    def stream_with_image(self, input: str, imagepath: str):
        import os
        from ai.tools import encode_image_to_base64

        data = encode_image_to_base64(imagepath)
        ext = os.path.splitext(imagepath)[1].lower().replace(".", "")
        type = "jpeg" if ext in ("jpg", "jpeg") else ext

        content = {
            "role": "user",
            "content": [
                {"type":"text", "text": input},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{type};base64,{data}"}
                }
            ]
        }
        

        self.messages.append(content)

        reply = []
        tools: dict[int, dict] = {}
        try:
            for type, chunk in self.client.chat(self.messages):
                if type == "text":
                    reply.append(chunk)
                    yield chunk
                elif type == "tool":
                    for tool in chunk:
                        index = tool.index
                        id = tool.id
                        name = tool.function.name
                        arguments = tool.function.arguments
                        type = tool.type

                        if index not in tools:  
                            tools[index] = {
                                "id": id,
                                "name": name,
                                "type": type,
                                "arguments": arguments,
                            }
                        else:
                            tools[index]["arguments"] += arguments
                    
            if tools:
                assistant_tool_calls = [
                    {
                        "id": v["id"],
                        "type": "function",
                        "function": {"name": v["name"], "arguments": v["arguments"]}
                    }
                    for v in tools.values()
                ]

                self.messages.append({
                    "role": "assistant",
                    "content": "".join(reply) if reply else None,
                    "tool_calls": assistant_tool_calls
                })
                                    
                for key, value in tools.items():
                    print(f"value: {value}")
                    res = ai_call_tool(value)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": value["id"],
                        "content": str(res)
                    })

                final = []
                for event_type, chunk in self.client.chat(self.messages):
                    if event_type == "text":
                        final.append(chunk)
                        yield chunk
                
                self.messages.append({"role": "assistant", "content": "".join(final)})
            else:
                self.messages.append({"role": "assistant", "content": "".join(reply)})

                        
        except Exception as e:
            self.messages.pop()
            raise e


    def clear(self):
        self.messages.clear()
        self.messages: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt}]