import datetime
import os
from typing import Iterator, List

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm.schema import SYSTEM, USER, ContentItem, Message
from qwen_agent.settings import DEFAULT_WORKSPACE
from qwen_agent.utils.utils import extract_text_from_message, save_text_to_file

MAX_TRUNCATED_QUERY_LENGTH = 1000

EXTRACT_QUERY_TEMPLATE_ZH = """<给定文本>
{ref_doc}

上面的文本是包括一段材料和一个用户请求，这个请求一般在最开头或最末尾，请你帮我提取出那个请求，你不需要回答这个请求，只需要打印出用户的请求即可！"""

EXTRACT_QUERY_TEMPLATE_EN = """<Given Text>
{ref_doc}

The text above includes a section of reference material and a user request. The user request is typically located either at the beginning or the end. Please extract that request for me. You do not need to answer the request, just print out the user's request!"""

EXTRACT_QUERY_TEMPLATE = {'zh': EXTRACT_QUERY_TEMPLATE_ZH, 'en': EXTRACT_QUERY_TEMPLATE_EN}


# TODO: merge to retrieval tool
class DialogueRetrievalAgent(Assistant):
    """This is an agent for super long dialogue."""

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             session_id: str = '',
             **kwargs) -> Iterator[List[Message]]:
        """Process messages and response

        Answer questions by storing the long dialogue in a file
        and using the file retrieval approach to retrieve relevant information

        """
        assert messages and messages[-1].role == USER
        new_messages = []
        content = []
        for msg in messages[:-1]:
            if msg.role == SYSTEM:
                new_messages.append(msg)
            else:
                content.append(f'{msg.role}: {extract_text_from_message(msg, add_upload_info=True)}')
        # Process the newest user message
        text = extract_text_from_message(messages[-1], add_upload_info=False)
        if len(text) <= MAX_TRUNCATED_QUERY_LENGTH:
            query = text
        else:
            if len(text) <= MAX_TRUNCATED_QUERY_LENGTH * 2:
                latent_query = text
            else:
                latent_query = f'{text[:MAX_TRUNCATED_QUERY_LENGTH]} ... {text[-MAX_TRUNCATED_QUERY_LENGTH:]}'

            *_, last = self._call_llm(
                messages=[Message(role=USER, content=EXTRACT_QUERY_TEMPLATE[lang].format(ref_doc=latent_query))])
            query = last[-1].content
            # A little tricky: If the extracted query is different from the original query, it cannot be removed
            text = text.replace(query, '')
            content.append(text)

        # Save content as file: This file is related to the session and the time
        content = '\n'.join(content)
        file_path = os.path.join(DEFAULT_WORKSPACE, f'dialogue_history_{session_id}_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt')
        save_text_to_file(file_path, content)

        new_content = [ContentItem(text=query), ContentItem(file=file_path)]
        if isinstance(messages[-1].content, list):
            for item in messages[-1].content:
                if item.file or item.image or item.audio:
                    new_content.append(item)
        new_messages.append(Message(role=USER, content=new_content))

        return super()._run(messages=new_messages, lang=lang, **kwargs)
