# Agent 介绍

本文档介绍了Agent类的使用和开发流程。

## 1. Agent 使用
Agent类是Qwen-Agent的一个上层接口，一个Agent对象集成了工具调用和LLM调用接口。
Agent接收一个消息列表输入，并返回一个消息列表的生成器，即流式输出的消息列表。

不同Agent类具有不同的工作流程，我们在[agents](../qwen_agent/agents)目录提供了多个不同的基础的Agent子类，
例如[ArticleAgent](../qwen_agent/agents/article_agent.py)接收消息后，返回消息包含一篇文章；
[BasicDocQA](../qwen_agent/agents/doc_qa/basic_doc_qa.py)返回消息包含文档问答的结果。
可以看出，这类Agent回复模式相对固定，使用场景也比较固定。

### 1.1. Assistant 类
我们提供了一个通用的Agent类：[Assistant](../qwen_agent/agents/assistant.py) 类，直接实例化这个类，可以解决大部分Single-Agent任务。
这个类的特点是：
- 支持角色扮演；
- 可以自动规划并调用工具；
- 接受输入文档，并采用内置的RAG策略解析文档。

例如在下面的例子中，我们通过指定LLM、工具列表、和角色指令来实例化了一个图片生成Agent，
即可开始和这个Agent交互。
从回复内容可以看出，在用户询问“a cute cat”后，这个Agent按照角色扮演的需求，自动规划并执行了绘图和代码工具，并参考给定文档对图片进行了翻转。


```py
import os
from qwen_agent.agents import Assistant
llm_cfg = {'model': 'qwen-max'}
tools = ['image_gen', 'amap_weather']  # image_gen and code_interpreter is a built-in tool in Qwen-Agent
system = 'According to the user\'s request, you first draw a picture and then automatically run code to download the picture ' + \
          'and select an image operation from the given document to process the image'

bot = Assistant(llm=llm_cfg,
                system_message=system,
                function_list=tools,
                files=[os.path.abspath('doc.pdf')])


messages = [{'role': 'user', 'content': 'a cute cat'}]
for response in bot.run(messages=messages):
    print('bot response:', response)

"""Running results：
[
    {'role': 'assistant', 'content': '', 'function_call': {'name': 'my_image_gen', 'arguments': '{"prompt": "a cute cat"}'}},
    {'role': 'function', 'content': '{"image_url": "https://image.pollinations.ai/prompt/a%20cute%20cat"}', 'name': 'my_image_gen'},
    {'role': 'assistant', 'content': "Here is the image of a cute cat based on your description:\n\n![](https://image.pollinations.ai/prompt/a%20cute%20cat)\n\nNow, let's proceed with downloading this image and performing an operation such as flipping it."},
    {'role': 'assistant', 'content': '', 'function_call': {'name': 'code_interpreter', 'arguments': '```py\nfrom PIL import Image\nimport requests\n\n# Downloading the cute cat image\nurl = "https://image.pollinations.ai/prompt/a%20cute%20cat"\nresponse = requests.get(url)\nwith open("cute_cat.jpg", \'wb\') as file:\n    file.write(response.content)\n\n# Flipping the image horizontally\ndef flip_image_horizontally(filename):\n    img = Image.open(filename)\n    flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)\n    flipped_img.save("flipped_cute_cat.jpg")\n    return flipped_img\n\n# Performing the horizontal flip\nflipped_cat = flip_image_horizontally("cute_cat.jpg")\n```'}},
    {'role': 'function', 'content': 'Finished execution.', 'name': 'code_interpreter'},
    {'role': 'assistant', 'content': 'The image of the cute cat has been downloaded and flipped horizontally. The flipped image has been saved as "flipped_cute_cat.jpg". Since we\'re in a text-based environment, I can\'t display the actual image here, but you can check it out at the location where the script was executed.'}
]
"""
```

我们在[examples](../examples)目录中提供了更多基于Assistant类开发的Single-Agent用例。

### 1.2. GroupChat 类

我们也提供了一个通用的Multi-Agent类：[GroupChat](../qwen_agent/agents/group_chat.py) 类。
这个类管理一个Agent列表，并自动维护Agent的发言顺序。这个类的特点是：
- 接收外部输入后，自动协调内置Agent的发言顺序，并依次将发言内容返回给用户；
- Human-in-the-loop: 将用户也定义为一个Agent，群聊会在必要时要求用户给予反馈；
- 用户可以随时打断群聊；

例如在下面的例子中，我们实例化一个五子棋群聊，其中真人用户下黑棋，并实例化白棋玩家和棋盘两个Agent作为NPC：
从结果可以看出，在用户小塘输入下棋位置<1,1>后，群聊先自动选择棋盘来更新；然后选择NPC小明发言；小明发言结束后棋盘再次更新；然后继续选择用户小塘发言，并等待用户输入。
然后用户小塘继续输入下棋位置<1,2>后，群聊又继续管理NPC发言......
```py
"""A chess play game implemented by group chat"""
from qwen_agent.agents import GroupChat
from qwen_agent.llm.schema import Message

# Define a configuration file for a multi-agent:
# one real player, one NPC player, and one chessboard
NPC_NAME = '小明'
USER_NAME = '小塘'
CFGS = {
    'background':
    f'一个五子棋群组，棋盘为5*5，黑棋玩家和白棋玩家交替下棋，每次玩家下棋后，棋盘进行更新并展示。{NPC_NAME}下白棋，{USER_NAME}下黑棋。',
    'agents': [{
        'name': '棋盘',
        'description': '负责更新棋盘',
        'instructions':
        '你扮演一个五子棋棋盘，你可以根据原始棋盘和玩家下棋的位置坐标，把新的棋盘用矩阵展示出来。棋盘中用0代表无棋子、用1表示黑棋、用-1表示白棋。用坐标<i,j>表示位置，i代表行，j代表列，棋盘左上角位置为<0,0>。',
        'selected_tools': ['code_interpreter']
    }, {
        'name':
        NPC_NAME,
        'description':
        '白棋玩家',
        'instructions':
        '你扮演一个玩五子棋的高手，你下白棋。棋盘中用0代表无棋子、用1黑棋、用-1白棋。用坐标<i,j>表示位置，i代表行，j代表列，棋盘左上角位置为<0,0>，请决定你要下在哪里，你可以随意下到一个位置，不要说你是AI助手不会下！返回格式为坐标：\n<i,j>\n除了这个坐标，不要返回其他任何内容',
    }, {
        'name': USER_NAME,
        'description': '黑棋玩家',
        'is_human': True
    }]
}


def app():
    # Define a group chat agent from the CFGS
    bot = GroupChat(agents=CFGS, llm={'model': 'qwen-max'})
    # Chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append(Message('user', query, name=USER_NAME))
        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        messages.extend(response)

if __name__ == '__main__':
    app()


"""运行结果示例：
user question:  <1,1>
bot response:
[
    Message({'role': 'assistant', 'content': '根据小塘的指令，他在棋盘的坐标 <1,1> 下了一枚黑棋。当前5x5棋盘的状态更新如下：\n\n```\n0 0 0 0 0\n0 1 0 0 0\n0 0 0 0 0\n0 0 0 0 0\n0 0 0 0 0\n```\n\n其中 (1, 1) 位置标记为1，表示此处是小塘下的黑棋。接下来轮到小明下白棋了。', 'name': '棋盘'}),
    Message({'role': 'assistant', 'content': '<0,1>', 'name': '小明'}),
    Message({'role': 'assistant', 'content': '根据小明的指令，他在棋盘的坐标 <0,1> 下了一枚白棋。当前5x5棋盘的状态更新如下：\n\n```\n0 -1 0 0 0\n0 1 0 0 0\n0 0 0 0 0\n0 0 0 0 0\n0 0 0 0 0\n```\n\n其中 (0, 1) 位置标记为-1，表示此处是小明下的白棋。现在轮到小塘下黑棋了。', 'name': '棋盘'})
]
user question:  <1,2>
bot response:
[
    Message({'role': 'assistant', 'content': '根据小塘的指令，他在棋盘的坐标 <1,2> 下了一枚黑棋。当前5x5棋盘的状态更新如下：\n\n```\n0 -1 0 0 0\n0 1 1 0 0\n0 0 0 0 0\n0 0 0 0 0\n0 0 0 0 0\n```\n\n其中 (1, 2) 位置标记为1，表示此处是小塘下的黑棋。现在轮到小明下白棋了。', 'name': '棋盘'}),
    Message({'role': 'assistant', 'content': '<2,0>', 'name': '小明'}),
    Message({'role': 'assistant', 'content': '根据小明的指令，他在棋盘的坐标 <2,0> 下了一枚白棋。当前5x5棋盘的状态更新如下：\n\n```\n0 -1 0 0 0\n0 1 1 0 0\n-1 0 0 0 0\n0 0 0 0 0\n0 0 0 0 0\n```\n\n其中 (2, 0) 位置标记为-1，表示此处是小明下的白棋。现在轮到小塘下黑棋了。', 'name': '棋盘'})
]
"""
```

我们在[examples](../examples)目录中提供了一个创造群聊和体验群聊的Gradio [Demo](../examples/group_chat_demo.py)，可以进一步体验群聊功能。
利用GroupChat开发可以参考[五子棋](../examples/group_chat_chess.py)用例。


## 2. Agent 开发

由于我们的一个Agent类定义为一种处理消息的工作流，因此，我们可以较灵活的开发特定的Agent类。
通过查看[Agent](../qwen_agent/agent.py)基类，可以看出，我们开发一个Agent子类时，只需要实现
`._run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]函数`,
它接收一个消息列表输入，并返回一个消息列表迭代器。

在开发过程中，可以使用`_call_llm(...)`和`_call_tool(...)`函数来调用LLM或Tool，也可以嵌套使用其他Agent，例如使用`Assistant.run(...)`来直接利用Assistant的Tool/LLM规划能力。

### 2.1. 嵌套开发
例如，在下面的例子中，我希望可以定制一个看图写作Agent，这个Agent只需要接收一个图片URL，就可以自动写出一篇作文：
在这个Agent中，我嵌套了一个image_agent，它使用Qwen-VL模型帮我理解图片内容，
然后也嵌套了一个writing_agent，它负责学习写作技巧并帮我写一篇作文。

注意：这只是看图写作Agent的其中一种实现方式，也可以使用其他方式来达成，
例如直接只使用一个image_agent来完成图片理解和写作。
但这种嵌套多个Agent合作的好处是，每个Agent可以使用独立的Prompt、工具和LLM，实现每个环节的最佳效果。

```py
import copy
from typing import Dict, Iterator, List, Optional, Union

from qwen_agent import Agent
from qwen_agent.agents import Assistant
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ContentItem, Message
from qwen_agent.tools import BaseTool

class VisualStorytelling(Agent):
    """Customize an agent for writing story from pictures"""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict,
                                                    BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None):
        super().__init__(llm=llm)

        # Nest one vl assistant for image understanding
        self.image_agent = Assistant(llm={'model': 'qwen-vl-max'})

        # Nest one assistant for article writing
        self.writing_agent = Assistant(
            llm=self.llm,
            function_list=function_list,
            system_message='你扮演一个想象力丰富的学生，你需要先理解图片内容，根据描述图片信息以后，' +
            '参考知识库中教你的写作技巧，发挥你的想象力，写一篇800字的记叙文',
            files=['https://www.jianshu.com/p/cdf82ff33ef8'])

    def _run(self,
             messages: List[Message],
             lang: str = 'zh',
             max_ref_token: int = 4000,
             **kwargs) -> Iterator[List[Message]]:
        """Define the workflow"""

        assert isinstance(messages[-1]['content'], list) and any([
            item.image for item in messages[-1]['content']
        ]), 'This agent requires input of images'

        # Image understanding
        new_messages = copy.deepcopy(messages)
        new_messages[-1]['content'].append(
            ContentItem(text='请详细描述这张图片的所有细节内容'))
        response = []
        for rsp in self.image_agent.run(new_messages):
            yield response + rsp
        response.extend(rsp)
        new_messages.extend(rsp)

        # Writing article
        new_messages.append(Message('user', '开始根据以上图片内容编写你的记叙文吧！'))
        for rsp in self.writing_agent.run(new_messages,
                                          lang=lang,
                                          max_ref_token=max_ref_token,
                                          **kwargs):
            yield response + rsp
```

### 2.2. 非嵌套开发
在这个例子中，我们使用基础的`_call_llm(...)`函数来调用LLM或Tool。

这个DocQA实现的一个工作流为：将给定的参考资料拼接到内置的Prompt中，并作为System Message，然后调用LLM生成返回结果。

```py
import copy
from typing import Iterator, List

from qwen_agent import Agent
from qwen_agent.llm.schema import CONTENT, ROLE, SYSTEM, Message

PROMPT_TEMPLATE_ZH = """
请充分理解以下参考资料内容，组织出满足用户提问的条理清晰的回复。
#参考资料：
{ref_doc}

"""

PROMPT_TEMPLATE_EN = """
Please fully understand the content of the following reference materials and organize a clear response that meets the user's questions.
# Reference materials:
{ref_doc}

"""

PROMPT_TEMPLATE = {
    'zh': PROMPT_TEMPLATE_ZH,
    'en': PROMPT_TEMPLATE_EN,
}


class DocQA(Agent):

    def _run(self,
             messages: List[Message],
             knowledge: str = '',
             lang: str = 'en',
             **kwargs) -> Iterator[List[Message]]:
        messages = copy.deepcopy(messages)
        system_prompt = PROMPT_TEMPLATE[lang].format(ref_doc=knowledge)
        if messages[0][ROLE] == SYSTEM:
            messages[0][CONTENT] += system_prompt
        else:
            messages.insert(0, Message(SYSTEM, system_prompt))

        return self._call_llm(messages=messages)

```

使用`_call_llm(...)`和`_call_tool(...)`函数组合来调用LLM和Tool的例子，可以参考[ReActChat](../qwen_agent/agents/react_chat.py)和[Assistant](../qwen_agent/agents/assistant.py)的实现。
