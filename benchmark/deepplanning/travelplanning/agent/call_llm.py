"""
Universal LLM calling module
Supports multiple providers: OpenAI, Anthropic (Claude), Google (Gemini), etc.
"""
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import openai


def load_model_config(model_name: str) -> Dict[str, Any]:
    """
    Load model configuration from models_config.json
    
    Searches for models_config.json in the following order:
    1. Current domain directory (travelplanning/)
    2. Parent directory (project root)
    
    Args:
        model_name: Name of the model
        
    Returns:
        Model configuration dict
        
    Raises:
        FileNotFoundError: If config file not found
        ValueError: If model not found in config
    """
    # Try domain directory first
    domain_config_path = Path(__file__).parent.parent / 'models_config.json'
    # Try project root (parent of domain directory)
    root_config_path = Path(__file__).parent.parent.parent / 'models_config.json'
    
    config_path = None
    if domain_config_path.exists():
        config_path = domain_config_path
    elif root_config_path.exists():
        config_path = root_config_path
    else:
        raise FileNotFoundError(
            f"models_config.json not found in:\n"
            f"  - Domain directory: {domain_config_path}\n"
            f"  - Project root: {root_config_path}\n"
            f"Please create models_config.json in the project root or domain directory."
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    models = config.get('models', {})
    if model_name not in models:
        available = ', '.join(models.keys())
        raise ValueError(
            f"Model '{model_name}' not found in models_config.json\n"
            f"Available models: {available}"
        )
    
    return models[model_name]


def create_client(model_name: str, model_config: Optional[Dict[str, Any]] = None):
    """
    Create appropriate client based on model configuration
    
    Args:
        model_name: Name of the model
        model_config: Model configuration (if None, will load from config file)
        
    Returns:
        Initialized client instance
    """
    if model_config is None:
        model_config = load_model_config(model_name)
    
    model_type = model_config.get('model_type', 'openai')
    base_url = model_config['base_url']
    api_key_env = model_config.get('api_key_env')
    api_key = os.getenv(api_key_env) if api_key_env else None
    
    if not api_key:
        raise RuntimeError(
            f"API key not found for model '{model_name}'\n"
            f"Please set environment variable: {api_key_env}"
        )
    
    if model_type == 'openai':
        # OpenAI and OpenAI-compatible APIs (Qwen, DeepSeek, etc.)
        return openai.OpenAI(api_key=api_key, base_url=base_url)
    else:
        raise NotImplementedError(
            f"Model type '{model_type}' is not currently supported. "
            f"Supported types: openai"
        )


def call_llm(
    config_name: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None
):
    """
    Universal LLM call with automatic client creation and retry logic
    
    Args:
        config_name: Configuration name from models_config.json (display name)
        messages: Message list
        tools: Tool definitions (optional)
    
    Returns:
        API response object
        
    Note:
        All parameters (model_name, temperature, extra_body, etc.) are loaded
        from models_config.json based on the config_name.
    """
    # Load model config and create client
    model_config = load_model_config(config_name)
    client = create_client(config_name, model_config)
    
    # Get actual model name for API call (fallback to config_name if not specified)
    actual_model_name = model_config.get('model_name', config_name)
    
    # Get parameters from config or use defaults
    temperature = model_config.get('temperature', None)
    max_retries = model_config.get('max_retries', 30)
    backoff = model_config.get('backoff', 1.5)
    tool_choice = model_config.get('tool_choice', 'auto')
    extra_body = model_config.get('extra_body')  # Get from config
    
    # Detect reasoning models (don't support temperature)
    is_reasoning_model = any(x in actual_model_name.lower() for x in ['o1', 'o3', 'o4-mini', 'reasoner'])
    
    last_err = None
    
    for attempt in range(max_retries):
        try:
            params = {
                "model": actual_model_name,
                "messages": messages,
            }
            
            if tools:
                params["tools"] = tools
            
            if not is_reasoning_model and temperature:
                params["temperature"] = temperature
            
            if extra_body:
                params["extra_body"] = extra_body
            response = client.chat.completions.create(**params)
            
            # Validate response
            msg = response.choices[0].message
            has_content = msg.content and msg.content.strip()
            has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
            
            if not has_content and not has_tool_calls:
                raise ValueError("Model returned an empty response without tool calls")
            
            return response
            
        except Exception as e:
            last_err = e
            
            if attempt == max_retries - 1:
                raise
            
            wait_time = backoff
            print(f"  ⚠️  LLM API error (attempt {attempt + 1}/{max_retries}): {e}")
            print(f"     Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    raise last_err if last_err else RuntimeError("LLM API call failed")
