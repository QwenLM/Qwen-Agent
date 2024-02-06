from typing import List, Optional, Union

from pydantic import BaseModel, field_validator, model_validator

DEFAULT_SYSTEM_MESSAGE = 'You are a helpful assistant.'
ROLE = 'role'
USER = 'user'
ASSISTANT = 'assistant'
SYSTEM = 'system'
FUNCTION = 'function'
FILE = 'file'
IMAGE = 'image'

CONTENT = 'content'
MESSAGE = 'message'


class BaseModelCompatibleDict(BaseModel):

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def model_dump(self, **kwargs):
        return super().model_dump(exclude_none=True, **kwargs)

    def model_dump_json(self, **kwargs):
        return super().model_dump_json(exclude_none=True, **kwargs)

    def get(self, key, default=None):
        try:
            value = getattr(self, key)
            if value:
                return value
            else:
                return default
        except AttributeError:
            return default

    def __str__(self):
        return f'{self.model_dump()}'


class FunctionCall(BaseModelCompatibleDict):
    name: str
    arguments: str

    def __init__(self, name: str, arguments: str):
        super().__init__(name=name, arguments=arguments)

    def __repr__(self):
        return f'FunctionCall({self.model_dump()})'


class ContentItem(BaseModelCompatibleDict):
    text: Optional[str] = None
    image: Optional[str] = None
    file: Optional[str] = None

    def __init__(self,
                 text: Optional[str] = None,
                 image: Optional[str] = None,
                 file: Optional[str] = None):
        super().__init__(text=text, image=image, file=file)

    @model_validator(mode='after')
    def check_exclusivity(self):
        provided_fields = 0
        if self.text:
            provided_fields += 1
        if self.image:
            provided_fields += 1
        if self.file:
            provided_fields += 1

        if provided_fields != 1:
            raise ValueError(
                "Exactly one of 'text', 'image', or 'file' must be provided.")
        return self

    def __repr__(self):
        return f'ContentItem({self.model_dump()})'


class Message(BaseModelCompatibleDict):
    role: str
    content: Union[str, List[ContentItem]]
    name: Optional[str] = None
    function_call: Optional[FunctionCall] = None

    def __init__(self,
                 role: str,
                 content: Union[str, List[ContentItem]],
                 name: Optional[str] = None,
                 function_call: Optional[FunctionCall] = None):
        super().__init__(role=role,
                         content=content,
                         name=name,
                         function_call=function_call)

    def __repr__(self):
        return f'Message({self.model_dump()})'

    @field_validator('role')
    def role_checker(cls, value: str) -> str:
        if value not in [USER, ASSISTANT, SYSTEM, FUNCTION]:
            raise ValueError(
                f'{value} must be one of {",".join([USER, ASSISTANT, SYSTEM, FUNCTION])}'
            )
        return value


# For llm models that do not support function_call, use this built-in react template to implement
FN_NAME = 'Action'
FN_ARGS = 'Action Input'
FN_RESULT = 'Observation'
FN_EXIT = 'Answer'

FN_CALL_TEMPLATE_ZH = """

# 工具

## 你拥有如下工具：

{tool_descs}

## 你可以在回复中插入零次、一次或多次以下命令以调用工具：

%s: 工具名称，必须是[{tool_names}]之一。
%s: 工具输入
%s: 工具结果，需将图片用![](url)渲染出来。
%s: 根据工具结果进行回复""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE_EN = """

# Tools

## You have access to the following tools:

{tool_descs}

## When you need to call a tool, please insert the following command in your reply, which can be called zero or multiple times according to your needs:

%s: The tool to use, should be one of [{tool_names}]
%s: The input of the tool
%s: The result returned by the tool. The image needs to be rendered as ![](url)
%s: Reply based on tool result""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)

FN_CALL_TEMPLATE = {
    'zh': FN_CALL_TEMPLATE_ZH,
    'en': FN_CALL_TEMPLATE_EN,
}
