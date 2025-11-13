# Qwen-Agent Learning Materials

## Welcome! 🎓

This directory contains a complete, hands-on curriculum for learning Qwen-Agent from scratch.

### What's Inside:

```
learning_qwen_agent/
├── README.md                          ← You are here!
├── MASTER_LEARNING_PLAN.md            ← Complete 12-day overview
├── IMPLEMENTATION_PLAN.md             ← Detailed teaching plans for days 3-12
│
├── day_01_prerequisites/
│   └── day_01_notebook.ipynb          ← Environment setup & first agent
│
├── day_02_message_schema/
│   └── day_02_notebook.ipynb          ← Message structure & communication
│
├── day_03_llm_integration/            ← [To be created based on IMPLEMENTATION_PLAN.md]
├── day_04_built_in_tools/             ← [To be created]
├── day_05_first_agent/                ← [To be created]
├── day_06_function_calling/           ← [To be created]
├── day_07_custom_tools/               ← [To be created]
├── day_08_assistant_agent/            ← [To be created]
├── day_09_rag_systems/                ← [To be created]
├── day_10_multi_agent/                ← [To be created]
├── day_11_advanced_patterns/          ← [To be created]
└── day_12_gui_development/            ← [To be created]
```

---

## 🚀 Quick Start

### Step 1: Prerequisites

Before starting, ensure you have:
- Python 3.10+ installed
- Jupyter notebook/lab
- A code editor (VS Code recommended)
- DashScope API key (get it from https://dashscope.console.aliyun.com/)

### Step 2: Installation

```bash
# Install Qwen-Agent with all features
pip install -U "qwen-agent[gui,rag,code_interpreter,mcp]"

# Verify installation
python -c "import qwen_agent; print('Qwen-Agent installed successfully!')"
```

### Step 3: Configure API Key

```bash
# Set environment variable (Linux/Mac)
export DASHSCOPE_API_KEY='your-api-key-here'

# Or Windows
set DASHSCOPE_API_KEY=your-api-key-here

# Or create a .env file in this directory
echo "DASHSCOPE_API_KEY=your-api-key-here" > .env
```

### Step 4: Start Learning!

```bash
# Open the first notebook
jupyter notebook day_01_prerequisites/day_01_notebook.ipynb

# Or use JupyterLab
jupyter lab
```

---

## 📚 Learning Path

### Beginner Track (Days 1-5)
Master the fundamentals:
- ✅ Day 1: Environment setup and first agent
- ✅ Day 2: Understanding message structure
- 📝 Day 3: LLM integration and configuration
- 📝 Day 4: Built-in tools overview
- 📝 Day 5: Creating custom agents

**Time commitment:** ~1.5-2 hours per day

### Intermediate Track (Days 6-9)
Build practical applications:
- 📝 Day 6: Function calling (tool use)
- 📝 Day 7: Custom tool development
- 📝 Day 8: Assistant agent deep dive
- 📝 Day 9: RAG systems

**Time commitment:** ~2-3 hours per day

### Advanced Track (Days 10-12)
Master complex patterns:
- 📝 Day 10: Multi-agent systems
- 📝 Day 11: Advanced agent patterns
- 📝 Day 12: GUI development & deployment

**Time commitment:** ~2-3 hours per day

---

## 🎯 Learning Approach

Each day follows the same structure:

1. **Concept Introduction** (Markdown cells)
   - What you'll learn
   - Why it matters
   - How it fits in the bigger picture

2. **Hands-On Examples** (Code cells)
   - Runnable, tested code
   - Taken from actual Qwen-Agent repository
   - Progressively increasing complexity

3. **Practice Exercises** (Code cells with TODOs)
   - Reinforce understanding
   - Build real skills
   - Vary in difficulty

4. **Key Takeaways** (Summary section)
   - Recap main concepts
   - Common patterns
   - What's next

---

## 📖 How to Use These Materials

### For Self-Study:

1. **Follow the order** - Days build on each other
2. **Run every cell** - Don't just read, execute!
3. **Complete exercises** - Practice is essential
4. **Take notes** - Write down confusing parts
5. **Experiment** - Modify code and see what happens

### For Instructors:

1. **Review IMPLEMENTATION_PLAN.md** - Detailed teaching guide
2. **Adapt to your pace** - Can extend to multiple sessions per day
3. **Add your examples** - Supplement with domain-specific use cases
4. **Encourage questions** - Build a learning community
5. **Provide solutions** - Create solution notebooks separately

### For Teams:

1. **Group sessions** - Work through notebooks together
2. **Pair programming** - Collaborate on exercises
3. **Code reviews** - Review each other's solutions
4. **Share learnings** - Discuss interesting discoveries
5. **Build projects** - Apply concepts to real work

---

## 🛠️ Troubleshooting

### Common Issues:

**Import Error: qwen_agent not found**
```bash
# Solution: Install Qwen-Agent
pip install -U "qwen-agent[gui,rag,code_interpreter,mcp]"
```

**API Key Not Found**
```bash
# Solution: Set environment variable
export DASHSCOPE_API_KEY='your-key'
```

**Jupyter Kernel Crashes**
```bash
# Solution: Restart kernel
# In Jupyter: Kernel → Restart
```

**Code Examples Don't Work**
- Check Python version (need 3.10+ for GUI)
- Verify Qwen-Agent version matches course
- Read error messages carefully
- Check official docs for API changes

---

## 📋 Progress Tracker

Mark your progress:

### Week 1: Foundations
- [ ] Day 1: Prerequisites & Setup
- [ ] Day 2: Message Schema
- [ ] Day 3: LLM Integration
- [ ] Day 4: Built-in Tools
- [ ] Day 5: First Agent

### Week 2: Applications
- [ ] Day 6: Function Calling
- [ ] Day 7: Custom Tools
- [ ] Day 8: Assistant Agent
- [ ] Day 9: RAG Systems
- [ ] Day 10: Multi-Agent
- [ ] Day 11: Advanced Patterns
- [ ] Day 12: GUI Development

---

## 🎓 After Completion

Once you've finished all 12 days, you'll be able to:

✅ Build agents from scratch
✅ Create custom tools
✅ Implement RAG systems
✅ Coordinate multiple agents
✅ Deploy production-ready UIs
✅ Apply agent patterns to real problems

### Next Steps:

1. **Build a project** - Apply your skills
2. **Contribute to Qwen-Agent** - Give back to the community
3. **Teach others** - Share your knowledge
4. **Stay updated** - Follow Qwen-Agent releases

---

## 🌟 Additional Resources

### Official Documentation:
- [Qwen-Agent GitHub](https://github.com/QwenLM/Qwen-Agent)
- [Qwen Models Documentation](https://qwen.readthedocs.io/)
- [DashScope API Docs](https://help.aliyun.com/zh/dashscope/)

### Community:
- [GitHub Issues](https://github.com/QwenLM/Qwen-Agent/issues) - Ask questions
- [Discord](https://discord.gg/yPEP2vHTu4) - Chat with community
- [Qwen Blog](https://qwenlm.github.io/) - Latest updates

### Related Learning:
- [LangChain Documentation](https://python.langchain.com/) - Similar framework
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - Better prompts
- [RAG Tutorial](https://www.pinecone.io/learn/retrieval-augmented-generation/) - Deep dive

---

## 📝 Contributing to This Curriculum

Found an issue? Want to add content?

1. **Report bugs** - Create GitHub issue
2. **Suggest improvements** - Pull requests welcome
3. **Add examples** - Share your use cases
4. **Translate** - Help with i18n
5. **Create exercises** - More practice = better learning

---

## 📜 License

This curriculum follows the same license as Qwen-Agent: **Apache 2.0**

Feel free to:
- Use for personal learning
- Use for teaching (credit appreciated)
- Modify and extend
- Share with others

---

## 🙏 Acknowledgments

- **Qwen Team** - For creating Qwen-Agent and excellent documentation
- **Community Contributors** - For examples and feedback
- **You** - For investing time in learning!

---

## ✉️ Questions?

- Check the official docs first
- Search GitHub issues
- Ask in Discord
- Create a new issue

---

**Happy Learning! Let's build amazing AI agents together! 🚀**

---

## Quick Reference Card

### Running Notebooks:
```bash
# Start Jupyter
jupyter notebook

# Or JupyterLab
jupyter lab
```

### Creating an Agent (Template):
```python
from qwen_agent.agents import Assistant

bot = Assistant(
    llm={'model': 'qwen-max-latest'},
    function_list=['tool1', 'tool2'],
    system_message='Instructions...'
)

messages = [{'role': 'user', 'content': 'Query'}]
response = bot.run_nonstream(messages)
```

### Creating a Tool (Template):
```python
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('my_tool')
class MyTool(BaseTool):
    description = 'What it does'
    parameters = [{
        'name': 'param1',
        'type': 'string',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # Implementation
        return result
```

### Launching GUI (Template):
```python
from qwen_agent.gui import WebUI

WebUI(bot).run()
```

---

*Last updated: 2025 | Qwen-Agent v0.0.31*
