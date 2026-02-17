# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pprint
import re
from typing import List, Optional, Union

from qwen_agent import Agent, MultiAgentHub
from qwen_agent.agents.user_agent import PENDING_USER_INPUT
from qwen_agent.gui.gradio_utils import format_cover_html
from qwen_agent.gui.utils import convert_fncall_to_text, convert_history_to_chatbot, get_avatar_image
from qwen_agent.llm.schema import AUDIO, CONTENT, FILE, IMAGE, NAME, ROLE, USER, VIDEO, Message
from qwen_agent.log import logger
from qwen_agent.utils.tokenization_qwen import count_tokens
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

    def run(self,
            messages: List[Message] = None,
            share: bool = False,
            server_name: str = None,
            server_port: int = None,
            concurrency_limit: int = 10,
            enable_mention: bool = False,
            **kwargs):
        self.run_kwargs = kwargs

        from qwen_agent.gui.gradio_dep import gr, mgr, ms

        customTheme = gr.themes.Default(
            primary_hue=gr.themes.utils.colors.blue,
            radius_size=gr.themes.utils.sizes.radius_none,
        )

        with gr.Blocks(
                css=os.path.join(os.path.dirname(__file__), 'assets/appBot.css'),
                theme=customTheme,
        ) as demo:
            history = gr.State([])
            with ms.Application():
                with gr.Row(elem_classes='container'):
                    with gr.Column(scale=4):
                        chatbot = mgr.Chatbot(value=convert_history_to_chatbot(messages=messages),
                                              avatar_images=[
                                                  self.user_config,
                                                  self.agent_config_list,
                                              ],
                                              height=850,
                                              avatar_image_width=80,
                                              flushing=False,
                                              show_copy_button=True,
                                              latex_delimiters=[{
                                                  'left': '\\(',
                                                  'right': '\\)',
                                                  'display': True
                                              }, {
                                                  'left': '\\begin{equation}',
                                                  'right': '\\end{equation}',
                                                  'display': True
                                              }, {
                                                  'left': '\\begin{align}',
                                                  'right': '\\end{align}',
                                                  'display': True
                                              }, {
                                                  'left': '\\begin{alignat}',
                                                  'right': '\\end{alignat}',
                                                  'display': True
                                              }, {
                                                  'left': '\\begin{gather}',
                                                  'right': '\\end{gather}',
                                                  'display': True
                                              }, {
                                                  'left': '\\begin{CD}',
                                                  'right': '\\end{CD}',
                                                  'display': True
                                              }, {
                                                  'left': '\\[',
                                                  'right': '\\]',
                                                  'display': True
                                              }])

                        input = mgr.MultimodalInput(placeholder=self.input_placeholder,)
                        audio_input = gr.Audio(
                            sources=["microphone"],
                            type="filepath"
                        )

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
                        inputs=[input, audio_input, chatbot, history],
                        outputs=[input, audio_input, chatbot, history],
                        queue=False,
                    )

                    if len(self.agent_list) > 1 and enable_mention:
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

            demo.load(None)

        demo.queue(default_concurrency_limit=concurrency_limit).launch(share=share,
                                                                       server_name=server_name,
                                                                       server_port=server_port)

    def change_agent(self, agent_selector):
        yield agent_selector, self._create_agent_info_block(agent_selector), self._create_agent_plugins_block(
            agent_selector)

    def add_text(self, _input, _audio_input, _chatbot, _history):
        # Check if the input is a command - more flexible matching
        input_text = _input.text.strip().lower()
        
        if input_text.startswith('/context'):
            # Process the /context command
            context_info = self._generate_context_info(_history)
            
            # Add the context info to the chatbot
            _chatbot.append([_input.text, context_info])
            
            # Also add to history as a system message
            _history.append({
                ROLE: 'system',
                CONTENT: context_info,
            })
            
            from qwen_agent.gui.gradio_dep import gr
            yield gr.update(interactive=False, value=None), None, _chatbot, _history
        elif input_text.startswith('/export'):
            # Process the /export command
            export_format = 'markdown'  # default format
            if ' ' in _input.text.strip():
                format_part = _input.text.strip().split(' ', 1)[1].lower()
                if format_part in ['json', 'txt', 'html']:
                    export_format = format_part
                elif format_part.startswith('json'):
                    export_format = 'json'
                elif format_part.startswith('txt'):
                    export_format = 'txt'
                elif format_part.startswith('html'):
                    export_format = 'html'
            
            export_content = self._generate_export_content(_history, export_format)
            
            # Add the export info to the chatbot
            _chatbot.append([_input.text, export_content])
            
            # Also add to history as a system message
            _history.append({
                ROLE: 'system',
                CONTENT: export_content,
            })
            
            from qwen_agent.gui.gradio_dep import gr
            yield gr.update(interactive=False, value=None), None, _chatbot, _history
        elif input_text.startswith('/guard'):
            # Process the /guard command
            guard_action = 'status'  # default action
            if ' ' in _input.text.strip():
                action_part = _input.text.strip().split(' ', 1)[1].lower()
                if action_part in ['on', 'enable', 'activate']:
                    guard_action = 'enable'
                elif action_part in ['off', 'disable', 'deactivate']:
                    guard_action = 'disable'
                elif action_part in ['status', 'info', 'show']:
                    guard_action = 'status'
                elif action_part.startswith('on') or action_part.startswith('enable'):
                    guard_action = 'enable'
                elif action_part.startswith('off') or action_part.startswith('disable'):
                    guard_action = 'disable'
                elif action_part.startswith('status') or action_part.startswith('info'):
                    guard_action = 'status'
            
            guard_content = self._generate_guard_content(guard_action)
            
            # Add the guard info to the chatbot
            _chatbot.append([_input.text, guard_content])
            
            # Also add to history as a system message
            _history.append({
                ROLE: 'system',
                CONTENT: guard_content,
            })
            
            from qwen_agent.gui.gradio_dep import gr
            yield gr.update(interactive=False, value=None), None, _chatbot, _history
        else:
            _history.append({
                ROLE: USER,
                CONTENT: [{
                    'text': _input.text
                }],
            })

            if self.user_config[NAME]:
                _history[-1][NAME] = self.user_config[NAME]

            # if got audio from microphone, append it to the multimodal inputs
            if _audio_input:
                from qwen_agent.gui.gradio_dep import gr, mgr, ms
                audio_input_file = gr.data_classes.FileData(path=_audio_input, mime_type="audio/wav")
                _input.files.append(audio_input_file)

            if _input.files:
                for file in _input.files:
                    if file.mime_type.startswith('image/'):
                        _history[-1][CONTENT].append({IMAGE: 'file://' + file.path})
                    elif file.mime_type.startswith('audio/'):
                        _history[-1][CONTENT].append({AUDIO: 'file://' + file.path})
                    elif file.mime_type.startswith('video/'):
                        _history[-1][CONTENT].append({VIDEO: 'file://' + file.path})
                    else:
                        _history[-1][CONTENT].append({FILE: file.path})

            _chatbot.append([_input, None])

            from qwen_agent.gui.gradio_dep import gr

            yield gr.update(interactive=False, value=None), None, _chatbot, _history

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

        num_input_bubbles = len(_chatbot) - 1
        num_output_bubbles = 1
        _chatbot[-1][1] = [None for _ in range(len(self.agent_list))]

        agent_runner = self.agent_list[_agent_selector or 0]
        if self.agent_hub:
            agent_runner = self.agent_hub
        responses = []
        for responses in agent_runner.run(_history, **self.run_kwargs):
            if not responses:
                continue
            if responses[-1][CONTENT] == PENDING_USER_INPUT:
                logger.info('Interrupted. Waiting for user input!')
                break

            display_responses = convert_fncall_to_text(responses)
            if not display_responses:
                continue
            if display_responses[-1][CONTENT] is None:
                continue

            while len(display_responses) > num_output_bubbles:
                # Create a new chat bubble
                _chatbot.append([None, None])
                _chatbot[-1][1] = [None for _ in range(len(self.agent_list))]
                num_output_bubbles += 1

            assert num_output_bubbles == len(display_responses)
            assert num_input_bubbles + num_output_bubbles == len(_chatbot)

            for i, rsp in enumerate(display_responses):
                agent_index = self._get_agent_index_by_name(rsp[NAME])
                _chatbot[num_input_bubbles + i][1][agent_index] = rsp[CONTENT]

            if len(self.agent_list) > 1:
                _agent_selector = agent_index

            if _agent_selector is not None:
                yield _chatbot, _history, _agent_selector
            else:
                yield _chatbot, _history

        if responses:
            _history.extend([res for res in responses if res[CONTENT] != PENDING_USER_INPUT])

        if _agent_selector is not None:
            yield _chatbot, _history, _agent_selector
        else:
            yield _chatbot, _history

        if self.verbose:
            logger.info('agent_run response:\n' + pprint.pformat(responses, indent=2))

    def flushed(self):
        from qwen_agent.gui.gradio_dep import gr

        return gr.update(interactive=True)

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

    def _generate_context_info(self, history: List[Message]) -> str:
        """
        Generate context usage information similar to Claude's /context command.
        """
        # Calculate total tokens in history
        total_text = ""
        for msg in history:
            if isinstance(msg.get(CONTENT), str):
                total_text += msg[CONTENT] + "\n"
            elif isinstance(msg.get(CONTENT), list):
                for item in msg[CONTENT]:
                    if isinstance(item, dict) and 'text' in item:
                        total_text += item['text'] + "\n"
                    elif isinstance(item, str):
                        total_text += item + "\n"

        total_tokens = count_tokens(total_text)
        
        # Define token limits (these can be adjusted based on the model)
        max_tokens = 128000  # Assuming a model with 128k context window
        used_percentage = min(100, (total_tokens / max_tokens) * 100)
        
        # Calculate usage by category
        system_tokens = 0
        user_tokens = 0
        assistant_tokens = 0
        function_tokens = 0
        tool_tokens = 0  # For function/tool calls
        custom_agent_tokens = 0  # For custom agents
        skill_tokens = 0  # For skills/tools
        
        # Track individual message counts too
        message_counts = {'system': 0, 'user': 0, 'assistant': 0, 'function': 0}
        
        for msg in history:
            role = msg.get(ROLE, '')
            content = msg.get(CONTENT, '')
            
            text_to_count = ""
            if isinstance(content, str):
                text_to_count = content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_to_count += item['text'] + "\n"
                    elif isinstance(item, str):
                        text_to_count += item + "\n"
            
            # Increment message count for this role
            if role in message_counts:
                message_counts[role] += 1
            
            # Add tokens based on role
            if role == 'system':
                system_tokens += count_tokens(text_to_count)
            elif role == 'user':
                user_tokens += count_tokens(text_to_count)
            elif role == 'assistant':
                assistant_tokens += count_tokens(text_to_count)
            elif role == 'function':
                function_tokens += count_tokens(text_to_count)
            # Check if this is a tool/function call message
            elif msg.get('function_call') or msg.get('name'):  # Tool call message
                tool_tokens += count_tokens(text_to_count)
        
        # Calculate percentages
        all_categories = [system_tokens, user_tokens, assistant_tokens, function_tokens, tool_tokens]
        total_calc_tokens = sum(all_categories)
        
        # Make sure we account for potential rounding issues
        system_pct = (system_tokens / max(total_calc_tokens, 1)) * 100
        user_pct = (user_tokens / max(total_calc_tokens, 1)) * 100
        assistant_pct = (assistant_tokens / max(total_calc_tokens, 1)) * 100
        function_pct = (function_tokens / max(total_calc_tokens, 1)) * 100
        tool_pct = (tool_tokens / max(total_calc_tokens, 1)) * 100
        
        # Create visual representation with different symbols for different categories
        # Similar to Claude's approach: different symbols for different usage types
        total_blocks = 20  # Total number of blocks to represent usage
        used_blocks = int((used_percentage / 100) * total_blocks)
        
        # Calculate proportional representation for each category
        system_blocks = int((system_pct / 100) * total_blocks)
        user_blocks = int((user_pct / 100) * total_blocks)
        assistant_blocks = int((assistant_pct / 100) * total_blocks)
        tool_blocks = int((max(function_pct, tool_pct) / 100) * total_blocks)
        
        # Create the progress bar with different symbols for different categories
        progress_bar = ""
        filled_blocks = 0
        
        # Add system tokens (using ⛁ symbol)
        for i in range(min(system_blocks, total_blocks - filled_blocks)):
            progress_bar += "⛁"
            filled_blocks += 1
        
        # Add user tokens (using ⛀ symbol)
        for i in range(min(user_blocks, total_blocks - filled_blocks)):
            progress_bar += ""
            filled_blocks += 1
        
        # Add assistant tokens (using ⛝ symbol)
        for i in range(min(assistant_blocks, total_blocks - filled_blocks)):
            progress_bar += "⛝"
            filled_blocks += 1
        
        # Add tool/function tokens (using ⛶ symbol)
        for i in range(min(tool_blocks, total_blocks - filled_blocks)):
            progress_bar += "⛶"
            filled_blocks += 1
        
        # Fill remaining blocks with free space indicator
        for i in range(total_blocks - filled_blocks):
            progress_bar += "⛶"
        
        # Format the response with enhanced details similar to Claude's format
        context_info = f"""<h3>Context Usage</h3>
<div style="font-family: monospace;">
  <div>{progress_bar}   Qwen-Agent · {total_tokens:,}/{max_tokens:,} tokens ({used_percentage:.1f}%)</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   Estimated usage by category</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛁ System prompt: {system_tokens:,} tokens ({system_pct:.1f}%)</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛀ User messages: {user_tokens:,} tokens ({user_pct:.1f}%)</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛝ Assistant messages: {assistant_tokens:,} tokens ({assistant_pct:.1f}%)</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛶ Tools/Skills: {max(function_tokens, tool_tokens):,} tokens ({max(function_pct, tool_pct):.1f}%)</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛷ Messages: {sum(message_counts.values()):,} messages</div>
  <div>  ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶ ⛶   ⛷ Functions: {message_counts['function']:,} calls</div>
  <div>  ⛶ ⛶ ⛶ ⛷ ⛷ ⛷ ⛷ ⛷ ⛷ ⛷   ⛶ Free space: {max_tokens - total_tokens:,} tokens ({100 - used_percentage:.1f}%)</div>
  <div>  ⛷ ⛷ ⛷ ⛷ ⛷ ⛷ ⛷ ⛷ ⛷ ⛷   ⛷ Compact buffer: {max(0, total_tokens - (max_tokens * 0.8)):,} tokens</div>
</div>"""
        return context_info.strip()

    def _generate_guard_content(self, action: str) -> str:
        """
        Generate content for the /guard command based on the requested action.
        """
        if action == 'enable':
            return """<h3>🛡️ Privacy Guard Activated</h3>
<div>
  <p><strong>Status:</strong> Active</p>
  <p><strong>Protection Level:</strong> High</p>
  <p><strong>Features Enabled:</strong></p>
  <ul>
    <li>Personal Information Filtering</li>
    <li>Credit Card Number Masking</li>
    <li>Email Address Sanitization</li>
    <li>IP Address Protection</li>
    <li>Temporary Session Mode</li>
  </ul>
  <p>Your conversation is now protected. Sensitive information will be filtered from the conversation context.</p>
  <p><em>Note: This protection applies to the current session only.</em></p>
</div>"""
        elif action == 'disable':
            return """<h3>🛡️ Privacy Guard Deactivated</h3>
<div>
  <p><strong>Status:</strong> Inactive</p>
  <p><strong>Protection Level:</strong> None</p>
  <p>Privacy protection has been turned off. Normal conversation processing resumed.</p>
  <p>Previous sensitive information may still be in the conversation context.</p>
</div>"""
        else:  # status/info
            return """<h3>🛡️ Privacy Guard Status</h3>
<div>
  <p><strong>Current Status:</strong> Inactive</p>
  <p><strong>Protection Level:</strong> None</p>
  <p><strong>Available Commands:</strong></p>
  <ul>
    <li><code>/guard on</code> - Activate privacy protection</li>
    <li><code>/guard off</code> - Deactivate privacy protection</li>
    <li><code>/guard status</code> - Show current status</li>
  </ul>
  <p>Privacy Guard helps protect sensitive information during your conversation.</p>
</div>"""

    def _generate_export_content(self, history: List[Message], format_type: str = 'markdown') -> str:
        """
        Generate export content in the specified format.
        """
        if format_type == 'json':
            import json
            # Convert history to a more readable JSON format
            formatted_history = []
            for msg in history:
                formatted_msg = {
                    'role': msg.get(ROLE, ''),
                    'content': msg.get(CONTENT, ''),
                    'name': msg.get(NAME, '') if msg.get(NAME) else None
                }
                formatted_history.append(formatted_msg)
            
            json_content = json.dumps(formatted_history, ensure_ascii=False, indent=2)
            return f"""<h3>Exported Conversation (JSON Format)</h3>
<pre style="white-space: pre-wrap; word-break: break-word;">{json_content}</pre>
<div><small>Copy the content above to save your conversation.</small></div>"""
        
        elif format_type == 'html':
            # Create a nicely formatted HTML representation
            html_content = "<!DOCTYPE html>\n<html>\n<head>\n<title>Qwen-Agent Conversation</title>\n</head>\n<body>\n<h1>Qwen-Agent Conversation</h1>\n"
            for msg in history:
                role = msg.get(ROLE, 'unknown')
                content = msg.get(CONTENT, '')
                
                # Format content based on type
                if isinstance(content, list):
                    content_text = ""
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            content_text += item['text'] + " "
                        elif isinstance(item, str):
                            content_text += item + " "
                    content = content_text
                elif not isinstance(content, str):
                    content = str(content)
                
                # Escape HTML characters
                content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                role_class = role.replace('_', '-')
                html_content += f'<div class="message {role_class}">\n<h3>{role.title()}</h3>\n<p>{content}</p>\n</div>\n<hr>\n'
            
            html_content += "</body>\n</html>"
            return f"""<h3>Exported Conversation (HTML Format)</h3>
<details>
  <summary>Click to view HTML content</summary>
  <pre style="white-space: pre-wrap; word-break: break-word;">{html_content}</pre>
</details>
<div><small>HTML content is available in the expanded section above.</small></div>"""
        
        elif format_type == 'txt':
            # Create plain text format
            txt_content = "Qwen-Agent Conversation Export\n"
            txt_content += "=" * 30 + "\n\n"
            
            for msg in history:
                role = msg.get(ROLE, 'unknown').upper()
                content = msg.get(CONTENT, '')
                
                # Format content based on type
                if isinstance(content, list):
                    content_text = ""
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            content_text += item['text'] + " "
                        elif isinstance(item, str):
                            content_text += item + " "
                    content = content_text
                elif not isinstance(content, str):
                    content = str(content)
                
                txt_content += f"{role}: {content}\n\n"
            
            return f"""<h3>Exported Conversation (Text Format)</h3>
<pre style="white-space: pre-wrap; word-break: break-word;">{txt_content}</pre>
<div><small>Copy the content above to save your conversation.</small></div>"""
        
        else:  # Default to markdown
            # Create markdown format
            md_content = "# Qwen-Agent Conversation\n\n"
            
            for msg in history:
                role = msg.get(ROLE, 'unknown').upper()
                content = msg.get(CONTENT, '')
                
                # Format content based on type
                if isinstance(content, list):
                    content_text = ""
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            content_text += item['text'] + " "
                        elif isinstance(item, str):
                            content_text += item + " "
                        elif isinstance(item, dict) and ('image' in item or 'audio' in item or 'video' in item or 'file' in item):
                            # Handle media content
                            for media_type in ['image', 'audio', 'video', 'file']:
                                if media_type in item:
                                    content_text += f"[{media_type.capitalize()}: {item[media_type]}] "
                    content = content_text
                elif not isinstance(content, str):
                    content = str(content)
                
                md_content += f"## {role}\n{content}\n\n"
            
            return f"""<h3>Exported Conversation (Markdown Format)</h3>
<div style="font-family: monospace; white-space: pre-wrap; word-break: break-word;">
{md_content}
</div>
<div><small>Copy the content above to save your conversation.</small></div>"""

    def _create_agent_info_block(self, agent_index=0):
        from qwen_agent.gui.gradio_dep import gr

        agent_config_interactive = self.agent_config_list[agent_index]

        return gr.HTML(
            format_cover_html(
                bot_name=agent_config_interactive['name'],
                bot_description=agent_config_interactive['description'],
                bot_avatar=agent_config_interactive['avatar'],
            ))

    def _create_agent_plugins_block(self, agent_index=0):
        from qwen_agent.gui.gradio_dep import gr

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
