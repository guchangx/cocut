import os
from dataclasses import dataclass
from typing import Generator, Any
from openai import OpenAI
from openai.types.responses import Response
from ai.tools import TOOLS_SCHEMA

@dataclass
class Capabilities:
    support_response_id: bool = False

class Client:
    def __init__(
        self
    ):
        if not os.getenv("KEY"):
            candidates = [
                ".env",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")),
            ]
            for env_path in candidates:
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
                    break

        self.key = os.getenv("KEY")
        self.model = os.getenv("MODEL")
        self.base_url = os.getenv("BASE_URL")
            
        if not self.key or not self.model or not self.base_url:
            raise ValueError("don't find api key or model or base url.")

        self.capabilities: Capabilities = self._detect_capabilities()

        client_kwargs = {"api_key": self.key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def _detect_capabilities(self) -> Capabilities:
        model = (self.model or "").lower()
        base_url = (self.base_url or "").lower()
        support_response_id = False
        # 只有 OpenAI 官方端点且模型为 OpenAI (gpt/o1/o3) 时，才支持 response_id
        if ("openai" in model or "gpt" in model or "o1" in model or "o3" in model) and "deepseek" not in base_url and "aliyuncs" not in base_url:
            support_response_id = True

        return Capabilities(support_response_id=support_response_id)

    def create_response(
        self,
        input_items: str | list[dict[str, Any]] | list[Any],
        instructions: str | None = None,
        previous_response_id: str | Any | None = None,
        tools: list[dict[str, Any]] | None = TOOLS_SCHEMA,
    ) -> Generator[tuple[str, Any], None, None]:

        # 如果 previous_response_id 是包含 id 的结构体，提取其 id
        actual_prev_id = getattr(previous_response_id, "id", previous_response_id)

        # 如果 input_items 是结构体列表，提取其 message 字典
        formatted_inputs = input_items
        if isinstance(input_items, list):
            formatted_inputs = [
                getattr(item, "message", item) for item in input_items
            ]

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "input": formatted_inputs,
            "stream": True,
        }
        if instructions:
            create_kwargs["instructions"] = instructions
        if actual_prev_id:
            create_kwargs["previous_response_id"] = actual_prev_id
        if tools is not None:
            create_kwargs["tools"] = tools

        stream = self.client.responses.create(**create_kwargs)

        for event in stream:
            if event.type == "response.output_text.delta":
                yield ("text", event.delta)
            elif event.type == "response.reasoning_text.delta":
                yield ("reasoning", event.delta)
            elif event.type == "response.completed":
                response: Response = event.response
                if response.usage:
                    print(f"\n📊 [Token 账单]")
                    print(f"  - 输入 Token (Input): {response.usage.input_tokens}")
                    print(f"  - 输出 Token (Output): {response.usage.output_tokens}")
                    print(f"  - 总计 Token: {response.usage.total_tokens}")
                yield ("completed", response)

    def chat(self, messages: list[dict[str, Any]] | list[Any], instructions: str | None = None) -> Generator[tuple[str, Any], None, None]:
        """Convenience method compatible with list of messages using Responses API."""
        return self.create_response(input_items=messages, instructions=instructions)

    def chat_completions(self, messages: list[dict[str, Any]] | list[Any], instructions: str | None = None) -> Generator[tuple[str, Any], None, None]:
        """向下兼容别名：底层完全基于 Responses API，不走旧版 completions"""
        return self.create_response(input_items=messages, instructions=instructions)
