#!/usr/bin/env python3
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

"""
Example of using Assistant with persistent conversation memory.

This example demonstrates how to enable vector-based memory for long-term context retention.
Requires chromadb: pip install chromadb
"""

import tempfile
import shutil
from qwen_agent.agents import Assistant

# Create a temporary directory for the vector database
temp_dir = tempfile.mkdtemp()

try:
    # Configure the agent with memory
    llm_cfg = {
        'model': 'qwen-turbo',  # Use a fast model for demo
        'model_type': 'qwen_dashscope',
    }

    memory_cfg = {
        'persist_dir': temp_dir,
        'collection_name': 'demo_conversations',
    }

    # Create agent with memory enabled
    bot = Assistant(
        llm=llm_cfg,
        memory_cfg=memory_cfg,
        system_message='You are a helpful assistant with memory of past conversations.'
    )

    # Simulate a conversation
    messages = []

    # First interaction
    query1 = "My name is Alice and I like programming."
    messages.append({'role': 'user', 'content': query1})
    print("User:", query1)

    response1 = bot.run_nonstream(messages)
    print("Bot:", response1[-1]['content'])
    messages.extend(response1)

    # Second interaction - should remember the name
    query2 = "What's my name and what do I like?"
    messages.append({'role': 'user', 'content': query2})
    print("\nUser:", query2)

    response2 = bot.run_nonstream(messages)
    print("Bot:", response2[-1]['content'])
    messages.extend(response2)

    # Third interaction - test memory retrieval
    query3 = "Tell me about programming."
    messages.append({'role': 'user', 'content': query3})
    print("\nUser:", query3)

    response3 = bot.run_nonstream(messages)
    print("Bot:", response3[-1]['content'])

finally:
    # Clean up
    shutil.rmtree(temp_dir)