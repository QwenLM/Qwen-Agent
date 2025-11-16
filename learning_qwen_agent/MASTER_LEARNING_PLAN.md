# Qwen-Agent Master Learning Plan
## Complete Day-by-Day Curriculum

**Repository:** Qwen-Agent by QwenLM
**Learning Approach:** Hands-on, executable notebooks with gradual complexity increase
**Duration:** 12 days (can be extended based on pace)
**Prerequisites:** Basic Python knowledge

---

## 📚 Learning Philosophy

This curriculum is designed to:
1. **Start from zero** - No prior agent framework knowledge required
2. **Build incrementally** - Each day builds on previous concepts
3. **Hands-on practice** - Every concept has executable code examples
4. **Real examples** - All code comes from the actual Qwen-Agent repository
5. **No hallucination** - Only use documented features and patterns

---

## 🎯 Learning Objectives

By the end of this curriculum, you will be able to:
- Understand the core architecture of Qwen-Agent
- Create basic and advanced agents
- Develop custom tools
- Implement RAG (Retrieval-Augmented Generation) systems
- Build multi-agent collaborative systems
- Deploy agents with web interfaces
- Apply agent patterns to real-world problems

---

## 📅 Daily Breakdown

### **Week 1: Foundations**

#### Day 1: Prerequisites & Setup
**Location:** `day_01_prerequisites/`
**Focus:** Environment setup and fundamental concepts

**What you'll learn:**
- What are LLM agents and why use them?
- Qwen-Agent architecture overview
- Setting up your development environment
- Understanding API keys and model services (DashScope)
- Basic Python async patterns for streaming responses

**Key Concepts:**
- Agent frameworks vs. direct LLM usage
- Streaming vs. non-streaming outputs
- Message-based communication

**Hands-on:**
- Install Qwen-Agent with all dependencies
- Configure API keys
- Run your first "Hello World" agent
- Test streaming vs. non-streaming modes

---

#### Day 2: Message Schema & Communication
**Location:** `day_02_message_schema/`
**Focus:** Understanding the Message abstraction

**What you'll learn:**
- The `Message` class structure
- Role types: user, assistant, system, function
- Content types: text, images, audio, video
- ContentItem for multimodal content
- Message flow through an agent

**Key Concepts:**
- Why messages are lists, not strings
- How context is maintained
- System messages vs. user messages
- Function call messages

**Hands-on:**
- Create messages programmatically
- Build conversation histories
- Work with multimodal content (text + images)
- Parse agent responses

**Files Referenced:**
- `/qwen_agent/llm/schema.py` (lines 1-200)

---

#### Day 3: LLM Integration
**Location:** `day_03_llm_integration/`
**Focus:** Understanding how Qwen-Agent talks to language models

**What you'll learn:**
- BaseChatModel interface
- Supported model services (DashScope, OpenAI-compatible, local)
- LLM configuration options
- Generation parameters (temperature, top_p, etc.)
- Model-specific features (reasoning models like QwQ)

**Key Concepts:**
- Model abstraction layer
- API vs. local models
- Token management
- Streaming responses from LLMs

**Hands-on:**
- Configure different LLM backends
- Call LLMs directly (without agents)
- Experiment with generation parameters
- Compare streaming vs. non-streaming

**Files Referenced:**
- `/qwen_agent/llm/base.py`
- `/qwen_agent/llm/qwen_dashscope.py`
- `/examples/function_calling.py`

---

#### Day 4: Built-in Tools Overview
**Location:** `day_04_built_in_tools/`
**Focus:** Exploring Qwen-Agent's tool ecosystem

**What you'll learn:**
- What are tools and why agents need them?
- BaseTool interface
- Built-in tools catalog:
  - code_interpreter (Python execution)
  - doc_parser (PDF/DOCX parsing)
  - retrieval (RAG search)
  - image_gen (image generation)
  - web_search
- Tool parameters and return values

**Key Concepts:**
- Tool as function abstraction
- Tool registration system
- Tool execution safety

**Hands-on:**
- Call tools directly (without agents)
- Explore code_interpreter with Python code
- Parse documents with doc_parser
- Search the web with web_search

**Files Referenced:**
- `/qwen_agent/tools/base.py`
- `/qwen_agent/tools/code_interpreter.py`
- `/qwen_agent/tools/doc_parser.py`

---

#### Day 5: Creating Your First Agent
**Location:** `day_05_first_agent/`
**Focus:** Agent base class and simple agent creation

**What you'll learn:**
- The `Agent` abstract base class
- Agent lifecycle: initialization → run → yield results
- The `run()` and `run_nonstream()` methods
- Creating a basic custom agent
- When to use BasicAgent vs. custom agents

**Key Concepts:**
- Iterator pattern for streaming
- Message processing pipeline
- Agent state management

**Hands-on:**
- Create a simple echo agent
- Build a sentiment analysis agent
- Implement a summarization agent
- Chain multiple agent calls

**Files Referenced:**
- `/qwen_agent/agent.py`
- `/qwen_agent/agents/basic.py`
- `/docs/agent.md`

---

### **Week 2: Practical Applications**

#### Day 6: Function Calling (Tool Use)
**Location:** `day_06_function_calling/`
**Focus:** How agents decide when and how to use tools

**What you'll learn:**
- Function calling workflow
- How LLMs generate function calls
- Function call detection and parsing
- Parallel function calling
- Tool choice strategies

**Key Concepts:**
- Function schemas and parameters
- The ReAct pattern (Reasoning + Acting)
- Tool call templates (Qwen vs. Nous formats)
- Error handling in tool execution

**Hands-on:**
- Build a weather query bot
- Implement parallel tool execution
- Handle tool errors gracefully
- Create a math problem solver

**Files Referenced:**
- `/examples/function_calling.py`
- `/examples/function_calling_in_parallel.py`
- `/qwen_agent/llm/function_calling.py`
- `/qwen_agent/llm/fncall_prompts/`

---

#### Day 7: Custom Tool Development
**Location:** `day_07_custom_tools/`
**Focus:** Building your own tools for agents

**What you'll learn:**
- Tool development pattern
- @register_tool decorator
- Defining tool descriptions and parameters
- Parameter validation
- Return value formatting
- Tool configuration options

**Key Concepts:**
- Tool discoverability
- Parameter schemas (JSON Schema)
- Registered vs. unregistered tools
- Tool testing strategies

**Hands-on:**
- Create a currency converter tool
- Build a database query tool
- Develop a custom API wrapper tool
- Integrate third-party services

**Files Referenced:**
- `/docs/tool.md`
- `/examples/assistant_add_custom_tool.py`
- `/qwen_agent/tools/base.py`

---

#### Day 8: The Assistant Agent - Deep Dive
**Location:** `day_08_assistant_agent/`
**Focus:** Understanding and using the most powerful built-in agent

**What you'll learn:**
- Assistant agent capabilities
- Role-playing with system messages
- Automatic planning and tool orchestration
- File handling and document processing
- Memory management
- Conversation state

**Key Concepts:**
- System message engineering
- Automatic vs. manual tool selection
- Context window management
- Multi-turn conversations

**Hands-on:**
- Build a personal assistant
- Create a code helper bot
- Implement a research assistant
- Add file upload capabilities

**Files Referenced:**
- `/qwen_agent/agents/assistant.py`
- `/examples/assistant_qwen3.py`
- `/examples/assistant_weather_bot.py`

---

#### Day 9: RAG (Retrieval-Augmented Generation)
**Location:** `day_09_rag_systems/`
**Focus:** Building knowledge-enhanced agents

**What you'll learn:**
- What is RAG and why it matters?
- Document chunking strategies
- Embedding and retrieval
- RAG workflow in Qwen-Agent
- RAG strategy agents (SplitQuery, GenKeyword)
- Handling super-long documents (1M+ tokens)

**Key Concepts:**
- Vector search vs. keyword search
- Retrieval quality vs. quantity
- Context injection patterns
- ParallelDocQA for long documents

**Hands-on:**
- Build a document Q&A system
- Create a knowledge base chatbot
- Implement multi-document search
- Test with 100-page PDFs

**Files Referenced:**
- `/examples/assistant_rag.py`
- `/examples/parallel_doc_qa.py`
- `/qwen_agent/agents/doc_qa/`
- `/qwen_agent/tools/retrieval.py`

---

#### Day 10: Multi-Agent Systems
**Location:** `day_10_multi_agent/`
**Focus:** Coordinating multiple agents for complex tasks

**What you'll learn:**
- GroupChat class architecture
- Agent coordination patterns
- Human-in-the-loop design
- Turn-taking and interruption
- Agent routing strategies

**Key Concepts:**
- Multi-agent collaboration
- Role specialization
- Message routing
- Consensus building

**Hands-on:**
- Create a debate simulation
- Build a collaborative writing system
- Implement the Gomoku (chess) example
- Design a research team of agents

**Files Referenced:**
- `/qwen_agent/agents/group_chat.py`
- `/examples/group_chat_demo.py`
- `/examples/group_chat_chess.py`
- `/examples/multi_agent_router.py`

---

#### Day 11: Advanced Agent Patterns
**Location:** `day_11_advanced_patterns/`
**Focus:** Complex workflows and specialized agents

**What you'll learn:**
- ReAct pattern implementation
- Tool-Integrated Reasoning (TIR)
- Nested agent development
- Vision-language agents
- Reasoning models (QwQ-32B)
- MCP (Model Context Protocol) integration

**Key Concepts:**
- Agent composition patterns
- Specialized vs. general agents
- State machines in agents
- Advanced prompt engineering

**Hands-on:**
- Implement a ReAct agent from scratch
- Build a vision understanding agent
- Create nested agents for complex workflows
- Integrate MCP servers

**Files Referenced:**
- `/qwen_agent/agents/react_chat.py`
- `/examples/assistant_qwq.py`
- `/examples/qwen2vl_assistant_tooluse.py`
- `/examples/assistant_mcp_sqlite_bot.py`

---

#### Day 12: GUI Development & Deployment
**Location:** `day_12_gui_development/`
**Focus:** Creating web interfaces for your agents

**What you'll learn:**
- WebUI class usage
- Gradio 5 basics
- Customizing the interface
- Chatbot configuration
- File upload handling
- Deploying to production

**Key Concepts:**
- Frontend-backend separation
- Real-time streaming in UIs
- User session management
- Security considerations

**Hands-on:**
- Create a basic chatbot UI
- Add custom styling
- Implement file upload
- Deploy locally and share publicly

**Files Referenced:**
- `/qwen_agent/gui/`
- `/examples/assistant_add_custom_tool.py` (GUI section)

---

## 🎓 Advanced Topics (Optional Extensions)

### Day 13+: Choose Your Own Adventure

**Option A: Production Deployment**
- Containerization with Docker
- API endpoints with FastAPI
- Scaling strategies
- Monitoring and logging

**Option B: Domain-Specific Agents**
- BrowserQwen deep dive
- Code generation agents
- Data analysis agents
- Writing assistants

**Option C: Research & Optimization**
- Benchmarking your agents
- Prompt optimization
- Cost reduction strategies
- Latency optimization

---

## 📖 How to Use This Curriculum

### Daily Routine:
1. **Read the markdown explanations** in each cell
2. **Run the code cells** in order
3. **Experiment** by modifying parameters
4. **Complete the exercises** at the end of each notebook
5. **Build the mini-project** to solidify understanding

### Time Commitment:
- **Reading & Understanding:** 30-45 minutes
- **Running Examples:** 15-30 minutes
- **Exercises:** 30-60 minutes
- **Total per day:** 1.5-2.5 hours

### Success Tips:
- Don't skip days - concepts build on each other
- Actually run the code, don't just read it
- Modify examples to test your understanding
- Keep notes on confusing parts
- Join the Discord/WeChat community for questions

---

## 🔧 Prerequisites Check

Before starting Day 1, ensure you have:
- [ ] Python 3.10+ installed
- [ ] Pip package manager
- [ ] Jupyter notebook/lab
- [ ] Code editor (VS Code recommended)
- [ ] DashScope API key (or OpenAI-compatible service)
- [ ] Basic understanding of:
  - Python functions and classes
  - JSON format
  - REST APIs (helpful but not required)

---

## 📚 Reference Materials

### Official Documentation:
- [Qwen-Agent GitHub](https://github.com/QwenLM/Qwen-Agent)
- [Qwen Models Documentation](https://qwen.readthedocs.io/)
- [DashScope API Docs](https://help.aliyun.com/zh/dashscope/)

### Supplementary Reading:
- "What is an AI Agent?" - foundational concepts
- "ReAct: Reasoning and Acting" - agent patterns
- "RAG Explained" - retrieval augmentation

### Community:
- GitHub Issues - troubleshooting
- Discord - real-time help
- WeChat Group - Chinese community

---

## 🎯 Learning Outcomes Assessment

After completing this curriculum, you should be able to:

**Beginner Level (Days 1-5):**
- ✅ Set up Qwen-Agent environment
- ✅ Understand message flow
- ✅ Configure LLM backends
- ✅ Use built-in tools
- ✅ Create simple agents

**Intermediate Level (Days 6-9):**
- ✅ Implement function calling
- ✅ Develop custom tools
- ✅ Build conversational agents
- ✅ Create RAG systems

**Advanced Level (Days 10-12):**
- ✅ Coordinate multi-agent systems
- ✅ Implement complex agent patterns
- ✅ Deploy production-ready UIs
- ✅ Design domain-specific solutions

---

## 🚀 Your First Step

Ready to begin? Head to `day_01_prerequisites/day_01_notebook.ipynb` and start your journey!

Remember: **The best way to learn is by doing.** Every code cell in this curriculum is designed to be executed and modified. Don't just read - experiment!

---

## 📝 Notes & Customization

Feel free to:
- Adjust the pace (take multiple days per notebook if needed)
- Skip topics you're already familiar with
- Deep dive into areas of particular interest
- Build your own projects alongside the curriculum

---

**Happy Learning! 🎉**

*This curriculum is based on Qwen-Agent version 0.0.31. Check for updates if using a newer version.*
