# Day 8: Assistant Agent - Your Production-Ready AI Partner

## 📚 Overview

The **Assistant** is the most complete and production-ready agent in Qwen-Agent. It brings together everything you've learned into a powerful, easy-to-use package.

**What Makes Assistant Special:**
- ✅ **Automatic tool orchestration** - Manages function calling loop for you
- ✅ **Built-in RAG** - Just provide files, get instant document Q&A
- ✅ **File handling** - Supports PDF, DOCX, PPT, Excel, HTML, URLs
- ✅ **Error handling** - Graceful recovery from failures
- ✅ **Streaming responses** - Real-time output for better UX
- ✅ **Conversation memory** - Maintains context automatically

## 🎯 Learning Objectives

By the end of this day, you will:

1. **Master all initialization parameters** - llm, function_list, files, system_message
2. **Implement RAG with files parameter** - Instant document knowledge
3. **Engineer effective system messages** - Control behavior and personality
4. **Configure tools flexibly** - Built-in, custom, and mixed
5. **Build production patterns** - Error handling, memory, streaming
6. **Create real-world assistants** - Customer support, code helper, analyst

## 🔑 Complete Parameter Reference

```python
Assistant(
    llm,                  # Required: LLM config or model object
    function_list=None,   # Optional: Tools the agent can use
    name=None,            # Optional: Agent's name (for logging)
    description=None,     # Optional: What the agent does
    system_message=None,  # Optional: Behavior instructions
    files=None            # Optional: Documents for RAG
)
```

### Parameter Guide

| Parameter | Required? | Type | Purpose |
|-----------|-----------|------|---------|
| `llm` | ✅ Yes | Dict or BaseChatModel | The AI brain |
| `function_list` | ❌ No | List | Tools (by name, class, or instance) |
| `name` | ❌ No | String | Agent identity |
| `description` | ❌ No | String | Agent purpose |
| `system_message` | ❌ No | String | Behavior/personality |
| `files` | ❌ No | List[str] | Documents for RAG |

## 🚀 Quick Start Examples

### Minimal Assistant

```python
from qwen_agent.agents import Assistant

# Just LLM - simplest possible
bot = Assistant(llm=llm_cfg)

messages = [{'role': 'user', 'content': 'Hello!'}]
for response in bot.run(messages):
    print(response[-1]['content'])
```

### Assistant with Tools

```python
# With code execution capability
code_bot = Assistant(
    llm=llm_cfg,
    function_list=['code_interpreter'],
    system_message='You are a helpful coding assistant'
)

messages = [{'role': 'user', 'content': 'Calculate factorial of 20'}]
for response in code_bot.run(messages):
    print(response[-1]['content'])
```

### Assistant with RAG

```python
# With document knowledge
doc_bot = Assistant(
    llm=llm_cfg,
    files=['company_handbook.pdf'],
    system_message='You are an HR assistant. Answer based on the handbook.'
)

messages = [{'role': 'user', 'content': 'What is the vacation policy?'}]
for response in doc_bot.run(messages):
    print(response[-1]['content'])
```

## 🎨 System Message Engineering

The `system_message` parameter controls your assistant's behavior, personality, and output format.

### Pattern 1: Role-Playing

```python
Assistant(
    llm=llm_cfg,
    system_message="""You are a friendly pirate captain who teaches programming.
Always:
- Talk like a pirate (arr, matey, ye)
- Use sailing analogies
- Be enthusiastic and encouraging
- Maintain technical accuracy"""
)
```

### Pattern 2: Output Formatting

```python
Assistant(
    llm=llm_cfg,
    system_message="""You are a data extraction assistant.
ALWAYS respond in this JSON format:
{
  "summary": "brief summary",
  "key_points": ["point 1", "point 2"],
  "confidence": 0.95
}
No text outside the JSON."""
)
```

### Pattern 3: Expert Persona

```python
Assistant(
    llm=llm_cfg,
    system_message="""You are a senior software architect.
Guidelines:
- Provide best practices and design patterns
- Consider scalability and maintainability
- Cite industry standards
- Be concise but thorough
Format: Problem → Solution → Rationale"""
)
```

### Pattern 4: Behavioral Rules

```python
Assistant(
    llm=llm_cfg,
    system_message="""You are a customer support agent.
Rules:
1. Always be polite and empathetic
2. Use the FAQ to answer questions
3. If answer not in FAQ, offer to escalate
4. Keep responses under 100 words
5. End with "Is there anything else I can help with?"
Tone: Professional yet warm"""
)
```

## 📄 The files Parameter - Automatic RAG

### What is RAG?

**RAG (Retrieval-Augmented Generation)** means the agent can answer questions based on your documents.

**How it works:**
1. You provide files
2. Agent automatically processes and indexes them
3. When user asks a question, relevant parts are retrieved
4. Agent uses those parts to generate accurate answers

**It's that simple!**

### Supported File Types

- 📄 PDF (`.pdf`)
- 📝 Word (`.docx`)
- 📊 PowerPoint (`.pptx`)
- 📈 Excel (`.xlsx`)
- 🌐 HTML (`.html`)
- 📋 Text (`.txt`, `.md`)
- 🔗 URLs (`https://...`)

### Example: Company Policy Bot

```python
# Create policy document
policy_content = """ACME Corp Employee Handbook

Vacation Policy:
- 20 days per year
- Must request 2 weeks in advance
- Carries over up to 5 days

Remote Work:
- 3 days/week allowed
- Core hours 10 AM - 3 PM required
- Monthly in-office meetings mandatory

Professional Development:
- $2000 annual budget
- Must be job-related
- Time off granted for attendance
"""

with open('policy.txt', 'w') as f:
    f.write(policy_content)

# Create RAG assistant
hr_bot = Assistant(
    llm=llm_cfg,
    files=['policy.txt'],
    system_message="""You are an HR assistant.
- Answer based on company policy document
- Cite specific sections
- Be helpful and friendly
- If info not in document, say so"""
)

# Use it
messages = [{'role': 'user', 'content': 'How many vacation days do I get?'}]
for response in hr_bot.run(messages):
    print(response[-1]['content'])
# Output: "According to the vacation policy, you receive 20 vacation days per year..."
```

### Files from URLs

```python
# Research paper assistant
research_bot = Assistant(
    llm=llm_cfg,
    files=['https://arxiv.org/pdf/1706.03762.pdf'],  # "Attention Is All You Need"
    system_message='Help researchers understand this paper'
)

messages = [{'role': 'user', 'content': 'What is the main contribution?'}]
for response in research_bot.run(messages):
    print(response[-1]['content'])
```

### Files in Messages (Alternative)

```python
# Pass files dynamically
bot = Assistant(llm=llm_cfg)

messages = [{
    'role': 'user',
    'content': [
        {'text': 'Summarize this document'},
        {'file': '/path/to/document.pdf'}
    ]
}]

for response in bot.run(messages):
    print(response[-1]['content'])
```

## 🛠️ The function_list Parameter

### Five Ways to Provide Tools

```python
# 1. Built-in tool by name (string)
Assistant(function_list=['code_interpreter'])

# 2. Custom tool by name (registered)
Assistant(function_list=['my_custom_tool'])

# 3. Tool by class
Assistant(function_list=[MyToolClass])

# 4. Tool by instance (with config)
Assistant(function_list=[MyTool(config='value')])

# 5. Mixed (recommended for flexibility)
Assistant(function_list=[
    'code_interpreter',      # Built-in
    'my_image_gen',          # Custom registered
    WeatherTool(),           # Custom instance
])
```

### Example: Multi-Tool Assistant

```python
# Versatile assistant with multiple capabilities
multi_bot = Assistant(
    llm=llm_cfg,
    function_list=[
        'code_interpreter',  # For calculations/analysis
        'my_image_gen',      # For image generation
    ],
    system_message='You are a versatile assistant. Use appropriate tools for each task.'
)

# Test with calculation
messages = [{'role': 'user', 'content': 'Calculate 2^1000'}]
for response in multi_bot.run(messages):
    if response[-1].get('content'):
        print(response[-1]['content'])

# Test with image generation
messages = [{'role': 'user', 'content': 'Generate an image of a sunset'}]
for response in multi_bot.run(messages):
    if response[-1].get('content'):
        print(response[-1]['content'])
```

## 💼 Production Patterns

### Pattern 1: Error Handling with Retries

```python
def safe_assistant_call(bot, user_message, max_retries=3):
    """Call assistant with error handling"""
    messages = [{'role': 'user', 'content': user_message}]

    for attempt in range(max_retries):
        try:
            responses = []
            for response in bot.run(messages):
                responses = response
            return responses
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return [{'role': 'assistant', 'content': f'Error: {str(e)}'}]

    return [{'role': 'assistant', 'content': 'Service unavailable'}]
```

### Pattern 2: Conversation Memory

```python
# Multi-turn conversation
conversation_history = []

bot = Assistant(llm=llm_cfg)

def chat(user_message):
    conversation_history.append({'role': 'user', 'content': user_message})

    for response in bot.run(conversation_history):
        if response:
            conversation_history.extend(response)
            return response[-1].get('content')

# Usage
chat("My name is Alice")
chat("I'm learning Python")
answer = chat("What was my name?")
print(answer)  # "Your name is Alice"
```

### Pattern 3: Streaming with Type Writer Effect

```python
from qwen_agent.utils.output_beautify import typewriter_print

bot = Assistant(llm=llm_cfg)
messages = [{'role': 'user', 'content': 'Explain quantum computing'}]

response_text = ''
for response in bot.run(messages):
    response_text = typewriter_print(response, response_text)
```

## 🌟 Real-World Example: Customer Support Bot

```python
# Create FAQ document
faq = """SmartWatch Pro FAQ

Q: Battery life?
A: Up to 7 days normal use, 3 days with GPS

Q: Waterproof?
A: Yes, IP68 rated. Safe for swimming.

Q: Compatible phones?
A: iPhone (iOS 13+), Android (8.0+)

Q: Return policy?
A: 30-day money-back guarantee
"""

with open('faq.txt', 'w') as f:
    f.write(faq)

# Build comprehensive support bot
support_bot = Assistant(
    llm=llm_cfg,
    name='SmartWatch Support',
    description='Customer support for SmartWatch Pro',
    system_message="""You are a friendly customer support agent.

Guidelines:
1. Be polite and empathetic
2. Use FAQ to answer questions
3. Use code_interpreter for calculations (discounts, totals)
4. If answer not in FAQ, offer to escalate
5. Keep responses concise
6. End with "Anything else I can help with?"

Tone: Professional yet warm""",
    function_list=['code_interpreter'],
    files=['faq.txt']
)

# Test scenarios
questions = [
    "Is it waterproof?",
    "3 watches at $299 each with 15% discount - what's my total?",
    "What's the return policy?"
]

for question in questions:
    print(f"\nCustomer: {question}")
    messages = [{'role': 'user', 'content': question}]
    for response in support_bot.run(messages):
        if response[-1].get('content'):
            print(f"Support: {response[-1]['content']}\n")
```

## 📊 Common Use Cases

### 1. Code Helper

```python
code_helper = Assistant(
    llm=llm_cfg,
    function_list=['code_interpreter'],
    system_message='You are a coding tutor. Run code examples to demonstrate concepts.'
)
```

### 2. Data Analyst

```python
data_analyst = Assistant(
    llm=llm_cfg,
    function_list=['code_interpreter'],
    system_message='You analyze data and create visualizations. Use pandas, matplotlib, etc.'
)
```

### 3. Document Q&A

```python
doc_qa = Assistant(
    llm=llm_cfg,
    files=['report.pdf', 'presentation.pptx'],
    system_message='Answer questions about the provided documents. Cite sources.'
)
```

### 4. Research Assistant

```python
researcher = Assistant(
    llm=llm_cfg,
    files=['https://arxiv.org/pdf/paper.pdf'],
    system_message='Explain research papers in simple terms. Be technically accurate.'
)
```

## 💡 Best Practices

### 1. Clear System Messages

```python
# ✅ Good - specific and actionable
system_message="""You are an email assistant.
- Keep emails under 200 words
- Use professional tone
- Include greeting and signature
- Proofread for grammar"""

# ❌ Bad - vague
system_message="Help with emails"
```

### 2. Appropriate Tool Selection

```python
# ✅ Good - only tools you need
function_list=['code_interpreter']

# ❌ Bad - all tools (slower, more expensive)
function_list=['code_interpreter', 'doc_parser', 'image_gen', ...]
```

### 3. Document Organization

```python
# ✅ Good - relevant documents
files=['product_manual.pdf', 'faq.txt']

# ❌ Bad - too many documents (slow, less accurate)
files=['doc1.pdf', 'doc2.pdf', ..., 'doc100.pdf']
```

### 4. Error Messages

```python
# ✅ Good - handle errors gracefully
try:
    for response in bot.run(messages):
        pass
except Exception as e:
    return "I'm having trouble right now. Please try again."

# ❌ Bad - expose technical errors
# Just let exception propagate
```

## 🔗 Related Resources

### Official Documentation
- [Agent Source Code](/qwen_agent/agent.py)
- [Assistant Implementation](/qwen_agent/agents/assistant.py)
- [RAG Documentation](/docs/rag.md)

### Examples
- [Basic Assistant](/examples/assistant_basic.py)
- [Custom Tool Assistant](/examples/assistant_add_custom_tool.py)
- [Multi-Agent](/examples/multi_agent_router.py)

### Next Steps
- **Day 9**: RAG Systems Deep Dive
- **Day 10**: Multi-Agent Orchestration
- **Day 11**: Advanced Patterns

## 💡 Key Takeaways

1. **Assistant is production-ready** - Handles tools, files, errors automatically
2. **system_message is powerful** - Controls behavior, format, personality
3. **files = instant RAG** - No manual setup needed
4. **Mix and match tools** - Built-in, custom, configured
5. **Conversation memory matters** - Maintain context for better UX
6. **Test incrementally** - Start simple, add complexity
7. **Handle errors gracefully** - Retries and fallbacks for reliability

---

**🎉 Congratulations!**

You've mastered the Assistant agent - the most versatile tool in Qwen-Agent!

You can now build production-ready AI assistants that:
- ✅ Use tools intelligently
- ✅ Learn from documents
- ✅ Follow your instructions
- ✅ Handle errors gracefully
- ✅ Maintain conversations
- ✅ Stream responses
- ✅ Scale to production

**You're ready for advanced topics!** 🚀

