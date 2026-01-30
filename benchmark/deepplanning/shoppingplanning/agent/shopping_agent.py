"""
Custom Agent implementation - Framework-independent

Uses universal LLM calling for multiple providers
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from threading import Lock

try:
    from .call_llm import call_llm
except ImportError:
    from call_llm import call_llm




class ShoppingFnAgent:
    """
    Lightweight function-calling Agent (shopping scenario):
    - Loads shopping_tool_schema.json as OpenAI Chat Completions tools
    - Dynamically loads tool classes (BaseShoppingTool subclasses) from shopping_tools directory
    - Iteratively calls LLM and executes tool_calls until final answer
    """

    def __init__(self,
                 model: str | None = None,
                 tool_schema_path: str | None = None,
                 base_url: str | None = None,
                 api_key: str | None = None,
                 sample_id: str | None = None,
                 database_base_path: str | None = None) -> None:
        """
        Initialize Agent
        
        Args:
            model: Model name (must exist in models_config.json)
            tool_schema_path: Path to tool schema JSON file
            base_url: Base URL for API (deprecated, loaded from models_config.json)
            api_key: API key (deprecated, loaded from models_config.json)
            sample_id: Sample ID for database path resolution
            database_base_path: Base path to database directory
        """
        self._load_env_from_dotenv()

        self.model = model or os.getenv("TOOLS_AGENT_MODEL", "qwen-plus")
        default_schema = Path(__file__).resolve().parent / 'tools' / 'shopping_tool_schema.json'
        self.tool_schema_path = tool_schema_path or os.getenv("SHOPPING_SCHEMA_PATH", str(default_schema))

        self.sample_id = sample_id
        if database_base_path:
            self.database_base_path = Path(database_base_path)
        else:
            # Default path: ShoppingBench/database
            project_root = Path(__file__).resolve().parent
            self.database_base_path = project_root / 'database'

        self.tool_config = self._build_tool_config()
        self.tools_schema = self._load_tool_schemas()
        self.openai_tools = self._build_openai_tools(self.tools_schema)
        self.tool_instances = self._load_tool_instances()

        if not Path(self.tool_schema_path).exists():
            raise FileNotFoundError(f"Tool schema not found: {self.tool_schema_path}")

    def _build_tool_config(self) -> Dict[str, Any]:
        """
        Build tool configuration with database path.
        All shopping tools use the same products.jsonl file, simplifying the logic.
        """
        cfg = {}
        if self.sample_id is not None:
            # Shopping scenario database path structure: database/case_{sample_id}/products.jsonl
            db_path = self.database_base_path / f'case_{self.sample_id}'
            
            if db_path.exists():
                cfg['database_path'] = str(db_path)
            else:
                if os.getenv('DEBUG_TOOLS') == '1':
                    print(f"[ShoppingFnAgent] WARN: Database not found for case {self.sample_id}: {db_path}")
        return cfg
    
    def _load_tool_instances(self) -> Dict[str, Any]:
        """
        Dynamically load tool instances from TOOL_REGISTRY.
        
        Tool registration mechanism:
        1. Tool classes use the @register_tool('tool_name') decorator
        2. The decorator executes at class definition time, registering the tool class to base_shopping_tool.TOOL_REGISTRY
        3. When importing the tools package, __init__.py imports all tool modules, triggering decorator execution
        4. Retrieve registered tool classes from TOOL_REGISTRY and instantiate them
        """
        instances: Dict[str, Any] = {}

        tools_dir = Path(__file__).resolve().parent.parent / 'tools'
        # Add tools_dir to sys.path to enable 'from base_shopping_tool import ...' in tool files
        sys.path.insert(0, str(tools_dir))
        sys.path.insert(0, str(tools_dir.parent))

        # Import tools package to trigger @register_tool decorator execution for all tool modules
        # tools/__init__.py imports all tool modules, and decorators register tool classes to TOOL_REGISTRY
        try:
            import tools  # noqa: F401
        except Exception as e:
            if os.getenv('DEBUG_TOOLS') == '1':
                print(f"[ShoppingFnAgent] WARN: import tools failed: {e}")
            return instances

        # Get TOOL_REGISTRY from base_shopping_tool module
        try:
            import base_shopping_tool  # type: ignore
            tool_registry = getattr(base_shopping_tool, 'TOOL_REGISTRY', None)
            if tool_registry is None:
                if os.getenv('DEBUG_TOOLS') == '1':
                    print("[ShoppingFnAgent] WARN: TOOL_REGISTRY not found in base_shopping_tool")
                return instances
        except Exception as e:
            if os.getenv('DEBUG_TOOLS') == '1':
                print(f"[ShoppingFnAgent] WARN: import base_shopping_tool failed: {e}")
            return instances

        if not tool_registry:
            print("[ShoppingFnAgent] WARN: TOOL_REGISTRY is empty. No tools were registered.")
            return instances

        # Create tool instances from TOOL_REGISTRY
        tool_cfg = self.tool_config
        for tool_name, tool_cls in tool_registry.items():
            try:
                inst = tool_cls(cfg=tool_cfg)
                instances[tool_name] = inst
            except Exception as e:
                if os.getenv('DEBUG_TOOLS') == '1':
                    print(f"[ShoppingFnAgent] WARN: Failed to instantiate tool '{tool_name}': {e}")
                continue

        return instances

    def _load_env_from_dotenv(self) -> None:
        """
        Load environment variables from .env file
        
        Searches for .env in the following order:
        1. Domain directory (shoppingplanning/)
        2. Project root (parent of domain)
        """
        try:
            # Try domain directory first
            domain_root = Path(__file__).resolve().parent.parent
            domain_dotenv = domain_root / '.env'
            
            # Try project root
            project_root = domain_root.parent
            project_dotenv = project_root / '.env'
            
            # Use project root .env if it exists, otherwise domain .env
            dotenv_path = project_dotenv if project_dotenv.exists() else domain_dotenv
            
            if not dotenv_path.exists():
                return
            
            for line in dotenv_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and (key not in os.environ):
                    os.environ[key] = val
        except Exception:
            pass

    def _load_tool_schemas(self) -> List[Dict[str, Any]]:
        """Load tool schemas from JSON file"""
        with open(self.tool_schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_openai_tools(self, schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build OpenAI tools format
        - If schema is already {type:function, function:{...}}, use as-is
        - Otherwise wrap as function definition
        """
        tools: List[Dict[str, Any]] = []
        for s in schemas:
            if isinstance(s, dict) and s.get('type') == 'function' and isinstance(s.get('function'), dict):
                tools.append(s)
        return tools

    def _exec_tool(self, name: str, arguments_json: str) -> str:
        """Execute tool call"""
        inst = self.tool_instances.get(name)
        if not inst:
            return json.dumps({"error": f"tool '{name}' not found"}, ensure_ascii=False)
        try:
            res = inst.call(arguments_json)  # Pass raw JSON string
            return res if isinstance(res, str) else json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _call_llm(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None):
        """Call LLM with unified handling for all models"""
        return call_llm(
            config_name=self.model,
            messages=messages,
            tools=tools
        )

    def _detect_tool_calls(self, assistant_message) -> List[Dict[str, Any]]:
        """Detect and normalize tool calls"""
        tool_calls = getattr(assistant_message, 'tool_calls', None)
        calls: List[Dict[str, Any]] = []
        if not tool_calls:
            return calls
        
        for idx, tc in enumerate(tool_calls):
            try:
                # Generate unique ID if not provided by the model
                tool_call_id = tc.id
                if tool_call_id is None or not tool_call_id:
                    tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
                
                calls.append({
                    'id': tool_call_id,
                    'name': tc.function.name,
                    'arguments': tc.function.arguments,
                })
            except Exception:
                continue
        
        return calls

    def _add_to_cart(self, history_messages: List[Any]) -> List[Any]:
        history_messages = list(history_messages)
        history_messages.append({
            "role": "user",
            "content": (
                "Check whether the items in the shopping cart meet the requirements. "
                "If not, add the required items to the cart. If there are multiple possible solutions, "
                "choose the optimal one. The final result should be based on the items in the cart. "
                "If the task is already complete, then stop."
            )
        })
        return history_messages

    def run(self, user_query: str, system_prompt: str | None = None, max_llm_calls: int = 100, save_messages: bool = True, messages_output_dir: str | None = None, sample_id: str | None = None) -> List[Any]:
        """
        Agent main loop: Call LLM → Execute tools → Repeat until final answer
        
        Args:
            user_query: User query
            system_prompt: System prompt
            max_llm_calls: Maximum LLM calls
            save_messages: Whether to save messages to file
            messages_output_dir: Output directory for messages (if sample_id not provided)
            sample_id: Sample ID for database path resolution
            
        Returns:
            Complete message history
        """
        if save_messages:
            # If sample_id exists, save to {database_base_path}/case_{sample_id}/messages.json
            # Use self.database_base_path for proper isolation when running concurrent instances
            if sample_id:
                db_case_dir = self.database_base_path / f'case_{sample_id}'
                db_case_dir.mkdir(parents=True, exist_ok=True)
                messages_file = db_case_dir / 'messages.json'
            else:
                # Otherwise fallback to result/messages
                msg_dir = Path(messages_output_dir or (Path(__file__).resolve().parent.parent / 'result' / 'messages'))
                msg_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                messages_file = msg_dir / f'messages_{ts}.json'

        messages: List[Any] = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": user_query}]
        if save_messages:
            self._save_messages(messages, messages_file, 0, "Initial messages")

        for step_count in range(1, max_llm_calls + 1):
            resp = self._call_llm(messages=messages, tools=self.openai_tools)
            msg = resp.choices[0].message
            
            # Convert message object to serializable dict
            msg_dict = {
                "role": "assistant",
                "content": msg.content or '',
            }
            
            # Preserve reasoning_content if present
            if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                msg_dict['reasoning_content'] = msg.reasoning_content
            
            calls = self._detect_tool_calls(msg)
            if calls:
                msg_dict["tool_calls"] = [
                    {
                        'id': call['id'],
                        'type': 'function',
                        'function': {
                            'name': call['name'],
                            'arguments': call['arguments']
                        }
                    }
                    for call in calls
                ]
            
            messages.append(msg_dict)
            if save_messages:
                self._save_messages(messages, messages_file, step_count, f"LLM response - {len(calls)} tool calls")
            
            if not calls:
                break

            for call in calls:
                tool_result = self._exec_tool(call['name'], call['arguments'])
                messages.append({"role": "tool", "tool_call_id": call['id'], "content": tool_result})
            if save_messages:
                self._save_messages(messages, messages_file, step_count, f"Tool execution completed - {len(calls)} tools")

        messages = self._add_to_cart(messages)
        for step_count in range(1, max_llm_calls + 1):
            resp = self._call_llm(messages=messages, tools=self.openai_tools)
            msg = resp.choices[0].message
            
            # Convert message object to serializable dict
            msg_dict = {
                "role": "assistant",
                "content": msg.content or '',
            }
            
            # Preserve reasoning_content if present
            if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                msg_dict['reasoning_content'] = msg.reasoning_content
            
            calls = self._detect_tool_calls(msg)
            if calls:
                msg_dict["tool_calls"] = [
                    {
                        'id': call['id'],
                        'type': 'function',
                        'function': {
                            'name': call['name'],
                            'arguments': call['arguments']
                        }
                    }
                    for call in calls
                ]
            
            messages.append(msg_dict)
            if save_messages:
                self._save_messages(messages, messages_file, step_count, f"LLM response - {len(calls)} tool calls")
            
            if not calls:
                return messages
            
            for call in calls:
                tool_result = self._exec_tool(call['name'], call['arguments'])
                messages.append({"role": "tool", "tool_call_id": call['id'], "content": tool_result})
            if save_messages:
                self._save_messages(messages, messages_file, step_count, f"Tool execution completed - {len(calls)} tools")

        return messages
    
    def _save_messages(self, messages: List[Any], filepath: Path, step: int, description: str):
        """Save messages to file"""
        serializable_messages = [m.model_dump() if hasattr(m, 'model_dump') else m for m in messages]
        save_data = {"step": step, "description": description, "messages": serializable_messages}
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            thread_info = threading.current_thread().name
            print(f"  💾 [{thread_info}] Step {step}: {description} - Saved {len(messages)} messages")
        except Exception as e:
            thread_info = threading.current_thread().name
            print(f"  ⚠️  [{thread_info}] Failed to save messages: {e}")


def run_agent_inference(
    model: str,
    test_data_path: Path,
    database_dir: Path,
    tool_schema_path: Path,
    system_prompt: str,
    workers: int = 10,
    max_llm_calls: int = 100,
    rerun_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Run agent inference (batch processing)
    
    Args:
        model: Configuration name from models_config.json
        test_data_path: Path to test data JSON file
        database_dir: Base path to database directory
        tool_schema_path: Path to tool schema JSON file
        system_prompt: System prompt for the agent
        workers: Number of parallel workers
        max_llm_calls: Maximum LLM calls per sample
        rerun_ids: Optional list of specific IDs to rerun. If None, run all samples.
    
    Returns:
        Results summary dict
    """
    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    # Filter samples if rerun_ids is specified
    if rerun_ids is not None:
        rerun_ids_set = set(str(id) for id in rerun_ids)  # Convert to strings for comparison
        original_count = len(test_data)
        test_data = [s for s in test_data if str(s.get('id')) in rerun_ids_set]
        print(f"  🔄 Filtered {original_count} samples to {len(test_data)} samples for rerun")
        
        if len(test_data) == 0:
            print(f"  ⚠️  Warning: No samples found matching the specified IDs")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'elapsed_time': 0,
                'results': []
            }
    
    print(f"\n{'='*80}")
    print(f"Agent Inference")
    print(f"{'='*80}")
    print(f"Model: {model}")
    print(f"Samples: {len(test_data)}")
    print(f"Workers: {workers}")
    print(f"{'='*80}\n")
    
    print_lock = Lock()
    results = []
    
    def process_sample(sample):
        sample_id = sample.get('id', 'unknown')
        query = sample.get('query', '')
        
        try:
            
            agent = ShoppingFnAgent(
                model=model,
                sample_id=str(sample_id),
                database_base_path=str(database_dir),
                tool_schema_path=str(tool_schema_path)
            )
            
            start_time = time.time()
            
            messages = agent.run(
                user_query=query,
                system_prompt=system_prompt,
                save_messages=True,
                sample_id=str(sample_id),
                max_llm_calls=max_llm_calls
            )
            
            elapsed = time.time() - start_time
            
            result = {
                'id': sample_id,
                'query': query,
                'model': model,
                'messages': messages,
                'elapsed_time': elapsed,
                'success': True,
            }
            
            with print_lock:
                print(f"✅ Sample {sample_id} completed in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            with print_lock:
                print(f"❌ Sample {sample_id} failed: {e}")
                import traceback
                traceback.print_exc()
            
            return {
                'id': sample_id,
                'query': query,
                'success': False,
                'error': str(e),
            }
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_sample, sample) for sample in test_data]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    success_count = sum(1 for r in results if r['success'])
    
    return {
        'total': len(results),
        'success': success_count,
        'failed': len(results) - success_count,
        'results': results
    }


if __name__ == '__main__':
    """Simple test"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='qwen-plus', help='Configuration name from models_config.json')
    parser.add_argument('--level', type=int, default=1, choices=[1, 2, 3], help='Shopping level: 1, 2, or 3')
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent
    test_output_dir = base_dir / 'results' / 'test'
    
    # Get system prompt for the specified level
    try:
        from .prompts import prompt_lib
    except ImportError:
        from prompts import prompt_lib
    
    system_prompt = getattr(prompt_lib, f'SYSTEM_PROMPT_level{args.level}', None)
    if system_prompt is None:
        raise ValueError(f"System prompt for level {args.level} not found")
    
    result = run_agent_inference(
        model=args.model,
        test_data_path=base_dir / 'data' / f'level_{args.level}_query_meta.json',
        database_dir=base_dir / 'database',
        tool_schema_path=base_dir / 'tools' / 'shopping_tool_schema.json',
        system_prompt=system_prompt,
        workers=2,
        max_llm_calls=100,
    )
    print(f"\nTest completed: {result['success']}/{result['total']} succeeded")

