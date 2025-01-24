import copy
import datetime
import json
from typing import Dict, Iterator, List, Literal, Optional, Union

from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE, SYSTEM, ContentItem, Message
from qwen_agent.log import logger
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import get_basename_from_url, print_traceback

KNOWLEDGE_TEMPLATE_ZH = """# 知识库

{knowledge}"""

KNOWLEDGE_TEMPLATE_EN = """# Knowledge Base

{knowledge}"""

KNOWLEDGE_TEMPLATE = {'zh': KNOWLEDGE_TEMPLATE_ZH, 'en': KNOWLEDGE_TEMPLATE_EN}

KNOWLEDGE_SNIPPET_ZH = """## 来自 {source} 的内容：

```
{content}
```"""

KNOWLEDGE_SNIPPET_EN = """## The content from {source}:

```
{content}
```"""

KNOWLEDGE_SNIPPET = {'zh': KNOWLEDGE_SNIPPET_ZH, 'en': KNOWLEDGE_SNIPPET_EN}


def format_knowledge_to_source_and_content(result: Union[str, List[dict]]) -> List[dict]:
    knowledge = []
    if isinstance(result, str):
        result = f'{result}'.strip()
        try:
            docs = json.loads(result)
        except Exception:
            print_traceback()
            knowledge.append({'source': '上传的文档', 'content': result})
            return knowledge
    else:
        docs = result
    try:
        _tmp_knowledge = []
        assert isinstance(docs, list)
        for doc in docs:
            url, snippets = doc['url'], doc['text']
            assert isinstance(snippets, list)
            _tmp_knowledge.append({
                'source': f'[文件]({get_basename_from_url(url)})',
                'content': '\n\n...\n\n'.join(snippets)
            })
        knowledge.extend(_tmp_knowledge)
    except Exception:
        print_traceback()
        knowledge.append({'source': '上传的文档', 'content': result})
    return knowledge


class Assistant(FnCallAgent):
    """This is a widely applicable agent integrated with RAG capabilities and function call ability."""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None,
                 rag_cfg: Optional[Dict] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         files=files,
                         rag_cfg=rag_cfg)

    def _run(self,
             messages: List[Message],
             lang: Literal['en', 'zh'] = 'en',
             knowledge: str = '',
             **kwargs) -> Iterator[List[Message]]:
        """Q&A with RAG and tool use abilities.

        Args:
            knowledge: If an external knowledge string is provided,
              it will be used directly without retrieving information from files in messages.

        """

        new_messages = self._prepend_knowledge_prompt(messages=messages, lang=lang, knowledge=knowledge, **kwargs)
        return super()._run(messages=new_messages, lang=lang, **kwargs)

    def _prepend_knowledge_prompt(self,
                                  messages: List[Message],
                                  lang: Literal['en', 'zh'] = 'en',
                                  knowledge: str = '',
                                  **kwargs) -> List[Message]:
        messages = copy.deepcopy(messages)
        if not knowledge:
            # Retrieval knowledge from files
            *_, last = self.mem.run(messages=messages, lang=lang, **kwargs)
            knowledge = last[-1][CONTENT]

        logger.debug(f'Retrieved knowledge of type `{type(knowledge).__name__}`:\n{knowledge}')
        if knowledge:
            knowledge = format_knowledge_to_source_and_content(knowledge)
            logger.debug(f'Formatted knowledge into type `{type(knowledge).__name__}`:\n{knowledge}')
        else:
            knowledge = []
        snippets = []
        for k in knowledge:
            snippets.append(KNOWLEDGE_SNIPPET[lang].format(source=k['source'], content=k['content']))
        knowledge_prompt = ''
        if snippets:
            knowledge_prompt = KNOWLEDGE_TEMPLATE[lang].format(knowledge='\n\n'.join(snippets))

        if knowledge_prompt:
            if messages[0][ROLE] == SYSTEM:
                if isinstance(messages[0][CONTENT], str):
                    messages[0][CONTENT] += '\n\n' + knowledge_prompt
                else:
                    assert isinstance(messages[0][CONTENT], list)
                    messages[0][CONTENT] += [ContentItem(text='\n\n' + knowledge_prompt)]
            else:
                messages = [Message(role=SYSTEM, content=knowledge_prompt)] + messages
        return messages


def get_current_date_str(
    lang: Literal['en', 'zh'] = 'en',
    hours_from_utc: Optional[int] = None,
) -> str:
    if hours_from_utc is None:
        cur_time = datetime.datetime.now()
    else:
        cur_time = datetime.datetime.utcnow() + datetime.timedelta(hours=hours_from_utc)
    if lang == 'en':
        date_str = 'Current date: ' + cur_time.strftime('%A, %B %d, %Y')
    elif lang == 'zh':
        cur_time = cur_time.timetuple()
        date_str = f'当前时间：{cur_time.tm_year}年{cur_time.tm_mon}月{cur_time.tm_mday}日，星期'
        date_str += ['一', '二', '三', '四', '五', '六', '日'][cur_time.tm_wday]
        date_str += '。'
    else:
        raise NotImplementedError
    return date_str
