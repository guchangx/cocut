from typing import Generator, Any
from openai.types.responses import Response
from ai.client import Client
from ai.message import Message
from ai.tools import ai_call_tool
from ai.tracing import tracer


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
        self.last_response_id: str | None = None
        self.messages: list[Message] = []
        self.reset()

    def reset(self) -> None:
        self.last_response_id = None
        self.messages = []

    def clear(self) -> None:
        self.reset()

    def get_context_messages(self) -> list[dict[str, Any]]:
        """获取纯字典格式的消息列表，供不支持 response_id 的模型传递完整上下文"""
        return [item.message for item in self.messages]

    def _extract_text(self, resp: Response) -> str:
        """从 Response 结构体中提取所有的助手文本回答"""
        texts: list[str] = []
        for item in getattr(resp, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", []) or []:
                    if getattr(part, "type", None) == "output_text":
                        texts.append(getattr(part, "text", ""))
                    elif hasattr(part, "text"):
                        texts.append(str(part.text))
        if not texts and hasattr(resp, "content") and resp.content:
            texts.append(str(resp.content))
        return "".join(texts)

    def _process_tools_and_respond(self, completed_resp: Response) -> Generator[str, None, None]:
        tool_calls = [
            item for item in (completed_resp.output or [])
            if getattr(item, "type", None) == "function_call"
        ]

        # if no tool calls, indicate handle complete.
        if not tool_calls:
            content = self._extract_text(completed_resp)
            if content and content.strip():
                self.messages.append(
                    Message(
                        id=getattr(completed_resp, "id", None),
                        role="assistant",
                        content=content,
                    )
                )
            return

        content = self._extract_text(completed_resp)
        if content and content.strip():
            self.messages.append(
                Message(
                    id=getattr(completed_resp, "id", None),
                    role="assistant",
                    content=content,
                )
            )

        # tools call should add in memory
        for tool in tool_calls:
            self.messages.append(
                Message(
                    id=tool.call_id,
                    message={
                        "type": "function_call",
                        "call_id": tool.call_id,
                        "name": tool.name,
                        "arguments": tool.arguments,
                    },
                )
            )

        # 2. use tools
        executed_tools = []
        for tool in tool_calls:
            tool_dict = {
                "name": tool.name,
                "arguments": tool.arguments,
            }
            res = ai_call_tool(tool_dict)
            executed_tools.append((tool, res))

        # 3. tools call result should add in memeory
        for tool, res in executed_tools:
            self.messages.append(
                Message(
                    id=tool.call_id,
                    message={
                        "type": "function_call_output",
                        "call_id": tool.call_id,
                        "output": str(res),
                    },
                )
            )

        next_completed: Response | None = None
        with tracer.span("LLM-Tool-Feedback-Phase"):
            #support previous response id
            if self.client.capabilities.support_response_id:
                tool_outputs = [
                    {
                        "type": "function_call_output",
                        "call_id": tool.call_id,
                        "output": str(res),
                    }
                    for tool, res in executed_tools
                ]
                stream_gen = self.client.create_response(
                    input_items=tool_outputs,
                    previous_response_id=completed_resp.id,
                )
            #not support previous response id
            else:
                stream_gen = self.client.create_response(
                    input_items=self.messages,
                    instructions=self.system_prompt,
                    previous_response_id=None,
                )

            for event_type, chunk in stream_gen:
                if event_type == "text":
                    yield chunk
                elif event_type == "completed":
                    next_completed = chunk

        if next_completed:
            if self.client.capabilities.support_response_id and getattr(next_completed, "id", None):
                self.last_response_id = next_completed.id
            yield from self._process_tools_and_respond(next_completed)

    def stream(self, input: str) -> Generator[str, None, None]:
        user_msg = Message(id=None, role="user", content=input)
        self.messages.append(user_msg)

        completed_resp: Response | None = None
        with tracer.span("LLM-Reasoning-Phase"):
            if self.client.capabilities.support_response_id:
                stream_gen = self.client.create_response(
                    input_items=[user_msg],
                    instructions=self.system_prompt,
                    previous_response_id=self.last_response_id,
                )
            else:
                stream_gen = self.client.create_response(
                    input_items=self.messages,
                    instructions=self.system_prompt,
                    previous_response_id=None,
                )

            for event_type, chunk in stream_gen:
                if event_type == "text":
                    yield chunk
                elif event_type == "completed":
                    completed_resp = chunk

        # 走出 LLM-Reasoning-Phase 之后再进入工具处理，确保阶段 1 先于阶段 2 结束
        if completed_resp:
            if self.client.capabilities.support_response_id and getattr(completed_resp, "id", None):
                self.last_response_id = completed_resp.id
            yield from self._process_tools_and_respond(completed_resp)

    def stream_with_image(self, input: str, imagepath: str) -> Generator[str, None, None]:
        import os
        from ai.tools import encode_image_to_base64

        data = encode_image_to_base64(imagepath)
        ext = os.path.splitext(imagepath)[1].lower().replace(".", "")
        mime_type = "jpeg" if ext in ("jpg", "jpeg") else ext

        user_content = [
            {"type": "input_text", "text": input},
            {
                "type": "input_image",
                "image_url": f"data:image/{mime_type};base64,{data}",
            },
        ]
        user_msg = Message(id=None, role="user", content=user_content)
        self.messages.append(user_msg)

        completed_resp: Response | None = None
        with tracer.span("LLM-Reasoning-Phase"):
            if self.client.capabilities.support_response_id:
                stream_gen = self.client.create_response(
                    input_items=[user_msg],
                    instructions=self.system_prompt,
                    previous_response_id=self.last_response_id,
                )
            else:
                stream_gen = self.client.create_response(
                    input_items=self.messages,
                    instructions=self.system_prompt,
                    previous_response_id=None,
                )

            for event_type, chunk in stream_gen:
                if event_type == "text":
                    yield chunk
                elif event_type == "completed":
                    completed_resp = chunk

        # 走出 LLM-Reasoning-Phase 之后再进入工具处理
        if completed_resp:
            if self.client.capabilities.support_response_id and getattr(completed_resp, "id", None):
                self.last_response_id = completed_resp.id
            yield from self._process_tools_and_respond(completed_resp)