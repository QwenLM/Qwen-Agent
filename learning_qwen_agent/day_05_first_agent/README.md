# Day 5: Your First Agent - Building Custom AI Agents

## 📚 Overview

Welcome to Day 5 - a major milestone! Today you'll learn how to build **custom AI agents from scratch**. You'll understand the Agent architecture, create simple agents, and learn the patterns for building specialized AI assistants.

## 🎯 Learning Objectives

By the end of this day, you will:

1. **Understand the Agent hierarchy** - How Agent, FnCallAgent, and Assistant relate
2. **Explore the base Agent class** - The foundation of all agents
3. **Create custom agents** - EchoAgent, TranslatorAgent, and more
4. **Master the `_run()` method** - The heart of every agent
5. **Understand FnCallAgent** - Agents that can use tools
6. **Build tool-using agents** - Combining LLM capabilities with functions
7. **Apply practical patterns** - Specialist, Validator, and Tutor agents

## 🏗️ The Agent Hierarchy

Qwen-Agent has a clear inheritance structure:

```
Agent (Abstract Base Class)
  ├── FnCallAgent (Adds tool-calling ability)
  │   ├── Assistant (General-purpose with RAG)
  │   ├── ReActChat (ReAct prompting)
  │   └── ParallelDocQA (Document Q&A)
  └── Your Custom Agent
```

### What Each Level Provides

| Class | Capabilities | When to Use |
|-------|-------------|-------------|
| **Agent** | Basic LLM integration, message handling | Simple conversational agents |
| **FnCallAgent** | Tool calling, function execution loop | Agents that need to DO things |
| **Assistant** | RAG, file handling, memory management | Full-featured assistants |

**Key Insight:** Start simple with **Agent**, add **FnCallAgent** when you need tools, use **Assistant** when you need the complete suite.

## 🔑 Core Concepts

### The Agent Base Class

The `Agent` class is an **Abstract Base Class (ABC)** that defines:

```python
class Agent(ABC):
    def __init__(self, llm, function_list, system_message, name, description):
        self.llm = ...              # The LLM model
        self.function_map = ...     # Available tools
        self.system_message = ...   # System prompt
        self.name = ...             # Agent name
        self.description = ...      # What this agent does

    @abstractmethod
    def _run(self, messages, **kwargs) -> Iterator[List[Message]]:
        """MUST be implemented by subclasses"""
        pass

    def run(self, messages, **kwargs):
        """Public interface - calls _run()"""
        pass
```

### Key Methods

#### `run(messages)` - Public Interface
- Handles type conversions (dict ↔ Message)
- Adds system message automatically
- Calls your `_run()` implementation
- **You call this method**

#### `_run(messages)` - Private Implementation
- Core agent logic goes here
- Yields responses as `List[Message]`
- Must return an Iterator for streaming
- **You override this method**

## 🚀 Creating Your First Agent

### Example 1: EchoAgent (No LLM)

The simplest possible agent that echoes back user input:

```python
from qwen_agent import Agent
from qwen_agent.llm.schema import Message
from typing import List, Iterator

class EchoAgent(Agent):
    """A simple agent that echoes back what you say"""

    def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
        # Get the last user message
        last_message = messages[-1]
        user_content = last_message.content

        # Create and yield response
        response = Message(
            role='assistant',
            content=f"You said: {user_content}"
        )
        yield [response]

# Usage
echo_bot = EchoAgent(name='EchoBot')
for response in echo_bot.run([{'role': 'user', 'content': 'Hello!'}]):
    print(response[0]['content'])
# Output: You said: Hello!
```

**Key Points:**
- Inherit from `Agent`
- Implement `_run()` method
- Yield responses as `List[Message]`
- No LLM needed for simple logic

### Example 2: TranslatorAgent (With LLM)

An agent that uses the LLM to translate text:

```python
class TranslatorAgent(Agent):
    """An agent that translates text to a target language"""

    def __init__(self, target_language='French', **kwargs):
        super().__init__(
            name=f'Translator-{target_language}',
            description=f'Translates text to {target_language}',
            system_message=f'You are a professional translator. Translate all user input to {target_language}. Only output the translation, nothing else.',
            **kwargs
        )
        self.target_language = target_language

    def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
        # messages already contains system message (added by parent's run())
        # Just call the LLM and yield responses
        for response in self.llm.chat(messages=messages, stream=True):
            yield response

# Usage
translator = TranslatorAgent(target_language='Spanish', llm=llm_cfg)
for response in translator.run([{'role': 'user', 'content': 'Hello!'}]):
    print(response[-1]['content'])
# Output: ¡Hola!
```

**Important:** The parent's `run()` method automatically adds your `system_message` to the beginning of the conversation, so don't add it again in `_run()`.

## 🛠️ FnCallAgent - Tool-Using Agents

When you need an agent that can use tools, extend `FnCallAgent`:

### The Function Calling Loop

FnCallAgent implements this workflow automatically:

```
1. Call LLM with function definitions
2. LLM decides: Use function or answer directly?
   ├─ Function call → Execute tool → Add result → Loop back to step 1
   └─ Direct answer → Return to user
3. Repeat up to MAX_LLM_CALL_PER_RUN times
```

### Example: SummarizerAgent

```python
from qwen_agent.agents import FnCallAgent

class SummarizerAgent(FnCallAgent):
    """An agent specialized in summarizing text"""

    def __init__(self, **kwargs):
        super().__init__(
            function_list=['code_interpreter'],  # Can use tools if needed
            system_message='You are a professional summarizer. Provide concise bullet-point summaries.',
            name='Summarizer',
            description='Summarizes text into bullet points',
            **kwargs
        )

# Usage
summarizer = SummarizerAgent(llm=llm_cfg)
messages = [{'role': 'user', 'content': 'Summarize this...'}]
for response in summarizer.run(messages):
    print(response[-1]['content'])
```

**When to use FnCallAgent:**
- Your agent needs to execute tools/functions
- You want automatic tool calling loop
- You need `_call_llm()` and `_call_tool()` helpers

## 📖 Understanding `_run()` Signature

```python
def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
```

### Why Iterator?
- Enables streaming responses
- Better UX (show partial results)
- Works with both simple and complex agents

### Why yield List[Message]?
- Agent might generate multiple messages (assistant + function call)
- Supports streaming partial updates
- Maintains conversation history

### Why messages already has system message?
- The parent's `run()` method adds it automatically (see agent.py:110-123)
- Prevents duplicate system messages
- You just use `messages` as-is

## 🎨 Practical Agent Patterns

### Pattern 1: The Specialist Agent

An agent with a narrow, well-defined purpose:

```python
class PythonTutorAgent(FnCallAgent):
    """Teaches Python by running code examples"""

    def __init__(self, **kwargs):
        super().__init__(
            function_list=['code_interpreter'],
            system_message=(
                "You are a Python programming tutor. When explaining concepts, "
                "always provide working code examples using code_interpreter. "
                "Run the code to show the output, then explain what happened."
            ),
            name='PythonTutor',
            description='Teaches Python with executable examples',
            **kwargs
        )
```

### Pattern 2: The Validator Agent

An agent that validates and corrects input:

```python
class CodeValidatorAgent(FnCallAgent):
    """Validates Python code"""

    def __init__(self, **kwargs):
        super().__init__(
            function_list=['code_interpreter'],
            system_message=(
                "You are a code validator. When given Python code:\n"
                "1. Run it with code_interpreter\n"
                "2. Report if it works or has errors\n"
                "3. If errors exist, suggest fixes\n"
                "Keep responses concise."
            ),
            name='CodeValidator',
            **kwargs
        )
```

### Pattern 3: Custom Workflow

Override `_run()` for custom multi-step logic:

```python
class StepByStepAgent(FnCallAgent):
    """Shows each step explicitly"""

    def _run(self, messages: List[Message], **kwargs) -> Iterator[List[Message]]:
        # Step 1: Call LLM
        functions = [func.function for func in self.function_map.values()]
        for llm_response in self._call_llm(messages=messages, functions=functions):
            yield llm_response

        # Step 2: Check for function call
        if llm_response[-1].get('function_call'):
            fn_name = llm_response[-1]['function_call']['name']
            fn_args = llm_response[-1]['function_call']['arguments']

            # Step 3: Execute tool
            result = self._call_tool(fn_name, fn_args, messages=messages)

            # Step 4: Call LLM again with result
            # ... (add function result and continue)
```

## 📊 Agent Comparison Table

| Agent Type | Can Use LLM? | Can Use Tools? | When to Use |
|------------|-------------|----------------|-------------|
| Agent (base) | Yes | No | Simple LLM-only agents |
| FnCallAgent | Yes | Yes | Agents that need tools |
| Assistant | Yes | Yes + RAG | General assistants |
| ReActChat | Yes | Yes (ReAct) | Step-by-step reasoning |
| Custom Agent | Your choice | Your choice | Specialized workflows |

### Decision Tree

```
Need tools?
  ├─ No → Extend Agent
  └─ Yes → Need RAG/Files?
      ├─ No → Use/Extend FnCallAgent
      └─ Yes → Use Assistant (Day 8)
```

## 🎓 Practice Exercises

The notebook includes hands-on exercises:

1. **ReverseAgent** - Reverse user input without using LLM
2. **PoetAgent** - Convert input into haiku using LLM
3. **MathTutorAgent** - Solve math with code_interpreter and explain
4. **DebuggerAgent** - Multi-step: run code → detect errors → suggest fix → test fix

## 🔍 Helper Methods

### `_call_llm(messages, functions, extra_generate_cfg)`
- Calls the LLM with function definitions
- Handles streaming automatically
- Returns an iterator of responses
- **For advanced use cases**

### `_call_tool(tool_name, tool_args, **kwargs)`
- Executes a tool by name
- Handles parameter parsing
- Returns tool result as string
- **For manual tool control**

## 📝 Important Notes

### System Message Handling

**✅ CORRECT:**
```python
def _run(self, messages: List[Message], **kwargs):
    # messages already has system message
    for response in self.llm.chat(messages=messages, stream=True):
        yield response
```

**❌ INCORRECT:**
```python
def _run(self, messages: List[Message], **kwargs):
    # DON'T add system message again!
    messages_with_system = [
        Message(role='system', content=self.system_message)
    ] + messages  # This creates duplicate!
    for response in self.llm.chat(messages=messages_with_system, stream=True):
        yield response
```

### Streaming vs Non-Streaming

**Streaming (Recommended):**
```python
for response in self.llm.chat(messages=messages, stream=True):
    yield response  # Yields List[Message] incrementally
```

**Non-Streaming:**
```python
response_list = self.llm.chat(messages=messages, stream=False)
yield response_list  # response_list is already a List[Message]
```

## 🔗 Related Resources

### Official Documentation
- [Agent Base Class](/qwen_agent/agent.py)
- [FnCallAgent](/qwen_agent/agents/fncall_agent.py)
- [Message Schema](/docs/llm.md)

### Example Code
- [Function Calling Examples](/examples/function_calling.py)
- [Multi-Agent Systems](/examples/multi_agent_router.py)

### Next Steps
- **Day 6**: Advanced Function Calling (fncall_prompt_type, parallel calls)
- **Day 7**: Building Complex Custom Tools
- **Day 8**: The Assistant Agent (RAG, file handling, memory)

## 💡 Key Takeaways

1. **All agents follow the same pattern**: Extend Agent/FnCallAgent and implement `_run()`
2. **Choose the right base class**: Agent for simple, FnCallAgent for tools, Assistant for full suite
3. **System messages matter**: They define your agent's personality and behavior
4. **Yield enables streaming**: Better UX than returning complete responses
5. **Don't duplicate system messages**: Parent's `run()` adds it automatically
6. **FnCallAgent automates tool calling**: Use it when you need function execution

## 🎉 What You've Accomplished

After completing this day, you can:

- ✅ Explain the Agent hierarchy and when to use each class
- ✅ Create custom agents by extending Agent
- ✅ Implement the `_run()` method correctly
- ✅ Build tool-using agents with FnCallAgent
- ✅ Apply common agent patterns (Specialist, Validator, Multi-step)
- ✅ Understand streaming and why we yield List[Message]
- ✅ Avoid common pitfalls (duplicate system messages)

**Ready for Day 6?** Tomorrow you'll master advanced function calling patterns, parallel tool execution, and error handling!

---

**Happy Building! 🤖**
