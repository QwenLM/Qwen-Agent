import os
import pprint
import re
from typing import List, Optional, Union

from qwen_agent import Agent, MultiAgentHub
from qwen_agent.agents.user_agent import PENDING_USER_INPUT
from qwen_agent.gui.gradio_utils import format_cover_html
from qwen_agent.gui.utils import (are_similar_enough, convert_fncall_to_text, convert_history_to_chatbot,
                                  get_avatar_image)
from qwen_agent.llm.schema import CONTENT, FILE, IMAGE, NAME, ROLE, USER, Message
from qwen_agent.log import logger
from qwen_agent.utils.utils import print_traceback


class WebUI:
    """A Common chatbot application for agent."""

    def __init__(self, agent: Union[Agent, MultiAgentHub, List[Agent]], chatbot_config: Optional[dict] = None):
        """
        Initialization the chatbot.

        Args:
            agent: The agent or a list of agents,
                supports various types of agents such as Assistant, GroupChat, Router, etc.
            chatbot_config: The chatbot configuration.
                Set the configuration as {'user.name': '', 'user.avatar': '', 'agent.avatar': '', 'input.placeholder': '', 'prompt.suggestions': []}.
        """
        chatbot_config = chatbot_config or {}

        if isinstance(agent, MultiAgentHub):
            self.agent_list = [agent for agent in agent.nonuser_agents]
            self.agent_hub = agent
        elif isinstance(agent, list):
            self.agent_list = agent
            self.agent_hub = None
        else:
            self.agent_list = [agent]
            self.agent_hub = None

        user_name = chatbot_config.get('user.name', 'user')
        self.user_config = {
            'name': user_name,
            'avatar': chatbot_config.get(
                'user.avatar',
                get_avatar_image(user_name),
            ),
        }

        self.agent_config_list = [{
            'name': agent.name,
            'avatar': chatbot_config.get(
                'agent.avatar',
                get_avatar_image(agent.name),
            ),
            'description': agent.description or "I'm a helpful assistant.",
        } for agent in self.agent_list]

        self.input_placeholder = chatbot_config.get('input.placeholder', '跟我聊聊吧～')
        self.prompt_suggestions = chatbot_config.get('prompt.suggestions', [])
        self.verbose = chatbot_config.get('verbose', False)

    """
    Run the chatbot.

    Args:
        messages: The chat history.
    """

    def run(self, messages: List[Message] = None, share=False, server_name=None, concurrency_limit=10, **kwargs):
        self.run_kwargs = kwargs

        from qwen_agent.gui.gradio import gr, mgr

        customTheme = gr.themes.Default(
            primary_hue=gr.themes.utils.colors.blue,
            radius_size=gr.themes.utils.sizes.radius_none,
        )

        with gr.Blocks(
                css=os.path.join(os.path.dirname(__file__), 'assets/appBot.css'),
                theme=customTheme,
        ) as demo:
            history = gr.State([])

            with gr.Row(elem_classes='container'):
                with gr.Column(scale=4):
                    chatbot = mgr.Chatbot(
                        value=convert_history_to_chatbot(messages=messages),
                        avatar_images=[
                            self.user_config,
                            self.agent_config_list,
                        ],
                        height=600,
                        avatar_image_width=80,
                        flushing=False,
                    )

                    input = mgr.MultimodalInput(placeholder=self.input_placeholder,)

                with gr.Column(scale=1):
                    if len(self.agent_list) > 1:
                        agent_selector = gr.Dropdown(
                            [(agent.name, i) for i, agent in enumerate(self.agent_list)],
                            label='Agents',
                            info='选择一个Agent',
                            value=0,
                            interactive=True,
                        )

                    agent_info_block = self._create_agent_info_block()

                    agent_plugins_block = self._create_agent_plugins_block()

                    if self.prompt_suggestions:
                        gr.Examples(
                            label='推荐对话',
                            examples=self.prompt_suggestions,
                            inputs=[input],
                        )

                if len(self.agent_list) > 1:
                    agent_selector.change(
                        fn=self.change_agent,
                        inputs=[agent_selector],
                        outputs=[agent_selector, agent_info_block, agent_plugins_block],
                        queue=False,
                    )

                input_promise = input.submit(
                    fn=self.add_text,
                    inputs=[input, chatbot, history],
                    outputs=[input, chatbot, history],
                    queue=False,
                )

                if len(self.agent_list) > 1:
                    input_promise = input_promise.then(
                        self.add_mention,
                        [chatbot, agent_selector],
                        [chatbot, agent_selector],
                    ).then(
                        self.agent_run,
                        [chatbot, history, agent_selector],
                        [chatbot, history, agent_selector],
                    )
                else:
                    input_promise = input_promise.then(
                        self.agent_run,
                        [chatbot, history],
                        [chatbot, history],
                    )

                input_promise.then(self.flushed, None, [input])

            demo.load(self.chat_clear, None, None, queue=False)

        demo.queue(default_concurrency_limit=concurrency_limit).launch(share=share, server_name=server_name)

    def change_agent(self, agent_selector):
        yield agent_selector, self._create_agent_info_block(agent_selector), self._create_agent_plugins_block(
            agent_selector)

    def add_text(self, _input, _chatbot, _history):
        _history.append({
            ROLE: USER,
            CONTENT: [{
                'text': _input.text
            }],
        })

        if self.user_config[NAME]:
            _history[-1][NAME] = self.user_config[NAME]

        if _input.files:
            for file in _input.files:
                if file.mime_type.startswith('image/'):
                    _history[-1][CONTENT].append({IMAGE: 'file://' + file.path})
                else:
                    _history[-1][CONTENT].append({FILE: file.path})

        _chatbot.append([_input, None])

        from qwen_agent.gui.gradio import gr

        yield gr.update(interactive=False, value=None), _chatbot, _history

    def add_mention(self, _chatbot, _agent_selector):
        if len(self.agent_list) == 1:
            yield _chatbot, _agent_selector

        query = _chatbot[-1][0].text
        match = re.search(r'@\w+\b', query)
        if match:
            _agent_selector = self._get_agent_index_by_name(match.group()[1:])

        agent_name = self.agent_list[_agent_selector].name

        if ('@' + agent_name) not in query and self.agent_hub is None:
            _chatbot[-1][0].text = '@' + agent_name + ' ' + query

        yield _chatbot, _agent_selector

    def agent_run(self, _chatbot, _history, _agent_selector=None):
        if self.verbose:
            logger.info('agent_run input:\n' + pprint.pformat(_history, indent=2))

        last_response_text = None
        _chatbot[-1][1] = [None for _ in range(len(self.agent_list))]

        agent_runner = self.agent_list[_agent_selector or 0]
        if self.agent_hub:
            agent_runner = self.agent_hub
        response = []
        for response in agent_runner.run(_history, **self.run_kwargs):
            if not response:
                continue
            display_response = convert_fncall_to_text(response)

            if display_response is None or len(display_response) == 0:
                continue

            agent_name, response_text = (
                display_response[-1][NAME],
                display_response[-1][CONTENT],
            )
            if response_text is None:
                continue
            elif response_text == PENDING_USER_INPUT:
                logger.info('Interrupted. Waiting for user input!')
                continue

            # TODO: Remove this `are_similar_enough`. This hack is not smart.
            if last_response_text is not None and not are_similar_enough(last_response_text, response_text):
                _chatbot.append([None, None])
                _chatbot[-1][1] = [None for _ in range(len(self.agent_list))]

            agent_index = self._get_agent_index_by_name(agent_name)
            _chatbot[-1][1][agent_index] = response_text
            last_response_text = response_text

            if len(self.agent_list) > 1:
                _agent_selector = agent_index

            if _agent_selector is not None:
                yield _chatbot, _history, _agent_selector
            else:
                yield _chatbot, _history
        if response:
            _history.extend([res for res in response if res[CONTENT] != PENDING_USER_INPUT])

        if _agent_selector is not None:
            yield _chatbot, _history, _agent_selector
        else:
            yield _chatbot, _history

        if self.verbose:
            logger.info('agent_run response:\n' + pprint.pformat(response, indent=2))

    def flushed(self):
        from qwen_agent.gui.gradio import gr

        return gr.update(interactive=True)

    def chat_clear(self):
        # TODO: This code stinks. At present, all users are sharing the same state!
        return None

    def _get_agent_index_by_name(self, agent_name):
        if agent_name is None:
            return 0

        try:
            agent_name = agent_name.strip()
            for i, agent in enumerate(self.agent_list):
                if agent.name == agent_name:
                    return i
            return 0
        except Exception:
            print_traceback()
            return 0

    def _create_agent_info_block(self, agent_index=0):
        from qwen_agent.gui.gradio import gr

        agent_config_interactive = self.agent_config_list[agent_index]

        return gr.HTML(
            format_cover_html(
                bot_name=agent_config_interactive['name'],
                bot_description=agent_config_interactive['description'],
                bot_avatar=agent_config_interactive['avatar'],
            ))

    def _create_agent_plugins_block(self, agent_index=0):
        from qwen_agent.gui.gradio import gr

        agent_interactive = self.agent_list[agent_index]

        if agent_interactive.function_map:
            capabilities = [key for key in agent_interactive.function_map.keys()]
            return gr.CheckboxGroup(
                label='插件',
                value=capabilities,
                choices=capabilities,
                interactive=False,
            )

        else:
            return gr.CheckboxGroup(
                label='插件',
                value=[],
                choices=[],
                interactive=False,
            )
