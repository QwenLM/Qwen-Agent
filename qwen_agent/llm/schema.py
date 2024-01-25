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
