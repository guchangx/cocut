from typing import Any


class Message:
    """统一消息结构体 (Unified Message Structure)

    在内存中维护 id 与 message 的一对一对应关系:
    - id: 会话响应标识或工具调用唯一标识 (如 'resp_xxx' 或 'call_xxx')
    - message: 标准字典格式的消息体 (如 {'role': 'user', 'content': ...})

    使用原则:
    - 如果需要 id，就使用 id (item.id)
    - 如果需要 message，就使用 message (item.message)
    """

    def __init__(
        self,
        id: str | None = None,
        message: dict[str, Any] | None = None,
        role: str | None = None,
        content: Any = None,
        **kwargs: Any,
    ):
        self.id = id
        if message is not None:
            self.message = dict(message)
        else:
            self.message = {}
            if role is not None:
                self.message["role"] = role
            if content is not None:
                self.message["content"] = content
            self.message.update(kwargs)

    @property
    def role(self) -> str | None:
        return self.message.get("role")

    @role.setter
    def role(self, value: str) -> None:
        self.message["role"] = value

    @property
    def content(self) -> Any:
        return self.message.get("content")

    @content.setter
    def content(self, value: Any) -> None:
        self.message["content"] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.message.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.message[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.message[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.message

    def __repr__(self) -> str:
        return f"Message(id={self.id!r}, message={self.message!r})"

