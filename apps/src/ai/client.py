import os
from typing import Generator
from openai import OpenAI
from ai.tools import TOOLS_SCHEMA

class Client :
    def __init__(self, key: str | None = None, base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-v4-flash-vision-exp"):

        self.key = "sk-956caea6d2954a53b7d45f83801fb448"
        if not self.key:
            raise ValueError("don't find api key");
        self.client = OpenAI(api_key = self.key, base_url = base_url)
        self.model = model

    def chat(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
        )

        for chunk in response:
            delta = chunk.choices[0].delta

            if delta and delta.content:
                yield ("text", delta.content)

            if delta and delta.tool_calls:
                yield ("tool", delta.tool_calls)
