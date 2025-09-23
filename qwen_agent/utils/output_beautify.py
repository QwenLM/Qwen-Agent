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
from typing import List

from qwen_agent.llm.schema import ASSISTANT, FUNCTION

TOOL_CALL_S = '[TOOL_CALL]'
TOOL_CALL_E = ''
TOOL_RESULT_S = '[TOOL_RESPONSE]'
TOOL_RESULT_E = ''
THOUGHT_S = '[THINK]'
ANSWER_S = '[ANSWER]'


def typewriter_print(messages: List[dict], text: str) -> str:
    full_text = ''
    content = []
    for msg in messages:
        if msg['role'] == ASSISTANT:
            if msg.get('reasoning_content'):
                assert isinstance(msg['reasoning_content'], str), 'Now only supports text messages'
                content.append(f'{THOUGHT_S}\n{msg["reasoning_content"]}')
            if msg.get('content'):
                assert isinstance(msg['content'], str), 'Now only supports text messages'
                content.append(f'{ANSWER_S}\n{msg["content"]}')
            if msg.get('function_call'):
                content.append(f'{TOOL_CALL_S} {msg["function_call"]["name"]}\n{msg["function_call"]["arguments"]}')
        elif msg['role'] == FUNCTION:
            content.append(f'{TOOL_RESULT_S} {msg["name"]}\n{msg["content"]}')
        else:
            raise TypeError
    if content:
        full_text = '\n'.join(content)
        print(full_text[len(text):], end='', flush=True)

    return full_text

def multimodal_typewriter_print(messages: List[dict], text: str = '') -> str:
    """Enhanced typewriter print function that displays text and images in Jupyter notebooks."""
    
    try:
        from PIL import Image
        from IPython.display import display
        import requests
        JUPYTER_AVAILABLE = True
    except ImportError:
        JUPYTER_AVAILABLE = False

    def display_image_if_exists(image_path: str) -> bool:
        """Display image if it exists and Jupyter is available."""
        if JUPYTER_AVAILABLE:
            try:
                if image_path.startswith('http'):
                    img = Image.open(requests.get(image_path, stream=True).raw)
                else:
                    img = Image.open(image_path)
                display(img)
                return True
            except Exception as e:
                print(f"Error displaying image {image_path}: {e}")
                return False
        return False
    
    def parse_tool_response_content(content):
        """Parse tool response content for both text and images."""
        text_parts = []
        image_paths = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if 'image' in item:
                        image_paths.append(item['image'])
                    elif 'text' in item:
                        text_parts.append(item['text'])
                else:
                    # Handle non-dict items as text
                    text_parts.append(str(item))
        elif isinstance(content, dict):
            item = content
            if isinstance(item, dict):
                if 'image' in item:
                    image_paths.append(item['image'])
                elif 'text' in item:
                    text_parts.append(item['text'])
            else:
                # Handle non-dict items as text
                text_parts.append(str(item))
        elif isinstance(content, str):
            text_parts.append(content)
        else:
            raise TypeError(f"Unsupported content type: {type(content)}")
        return text_parts, image_paths
    
    # Build full content like original typewriter_print
    full_text = ''
    content_parts = []
    image_positions = {}  # Track where images should be displayed
    
    for msg in messages:
        if msg['role'] == ASSISTANT:
            if msg.get('reasoning_content'):
                assert isinstance(msg['reasoning_content'], str), 'Now only supports text messages'
                content_parts.append(f'{THOUGHT_S}\n{msg["reasoning_content"]}')
            if msg.get('content'):
                assert isinstance(msg['content'], str), 'Now only supports text messages'
                content_parts.append(f'{ANSWER_S}\n{msg["content"]}')
            if msg.get('function_call'):
                content_parts.append(f'{TOOL_CALL_S} {msg["function_call"]["name"]}\n{msg["function_call"]["arguments"]}')
        elif msg['role'] == FUNCTION:
            tool_name = msg.get("name", "unknown_tool")
            tool_content = msg.get("content", "")
            
            # Parse tool content for both text and images
            text_parts, image_paths = parse_tool_response_content(tool_content)
            
            # Build the text response - use parsed text if available, skipping the multimodal directory
            if text_parts:
                formatted_content = '\n'.join(text_parts)
            else:
                formatted_content = ''
            
            tool_response_text = f'{TOOL_RESULT_S} {tool_name}\n{formatted_content}'
            content_parts.append(tool_response_text)
            
            # Store images to display after this text block
            if image_paths:
                image_positions[len(content_parts) - 1] = image_paths
        else:
            raise TypeError(f"Unsupported message role: {msg.get('role', 'unknown')}")
    
    if content_parts:
        full_text = '\n'.join(content_parts)
        
        # Print only the new text (typewriter effect)
        new_text = full_text[len(text):]
        if new_text:
            print(new_text, end='', flush=True)
            
            # Check if we need to display images for the newly printed content
            current_pos = len(text)
            for part_idx, image_list in image_positions.items():
                # Calculate the position where this part ends in the full text
                part_end_pos = len('\n'.join(content_parts[:part_idx + 1]))
                
                # If this part is within the newly printed text, display its images
                if part_end_pos > current_pos:
                    print()  # New line before images
                    for image_path in image_list:
                        if not display_image_if_exists(image_path):
                            print(f"Image not found or cannot be displayed: {image_path}")
    
    return full_text