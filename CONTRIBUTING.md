# Contributing to Qwen-Agent

Thank you for your interest in contributing to Qwen-Agent! This is Alibaba Qwen team's open-source LLM Agent framework.

## Development Setup

```bash
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ".[dev]"
```

### Prerequisites
- Python 3.x
- An LLM API key (DashScope, OpenAI-compatible, Azure, etc.)

## Code Style

We follow PEP 8 with these tools:
- **ruff** for linting and formatting
- Type hints on public functions

## Running Tests

```bash
pytest
```

Tests are located in `tests/`. Please ensure existing tests pass and add tests for new functionality.

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following code style
4. Add tests for new functionality
5. Run `pytest` to ensure all tests pass
6. Submit a PR to the `main` branch

### PR Title Format
Use clear, descriptive titles:
- `fix:` for bug fixes
- `feat:` for new features
- `docs:` for documentation
- `test:` for test additions
- `refactor:` for code refactoring

### PR Description
Include:
- **What** does this PR do?
- **Why** is this change needed?
- **How** was it tested?

## Types of Contributions

### Bug Fixes
Check [Issues](https://github.com/QwenLM/Qwen-Agent/issues) for reported bugs.

### New LLM Providers
Add new providers in `qwen_agent/llm/`. See existing providers like `oai.py` or `azure.py` as examples. Register with `@register_llm('provider_name')`.

### New Tools
Add tools in `qwen_agent/tools/` extending `BaseTool`. Include tests in `tests/tools/`.

### Documentation
We welcome doc improvements:
- Adding missing docstrings
- Translating docs (especially Chinese ↔ English)
- Writing tutorials and examples
- Fixing typos

### Tests
We especially need tests for:
- GUI components
- MCP Manager
- GroupChat
- Utility functions

## Documentation Site

The documentation site is in `qwen-agent-docs/` (Next.js + MDX). Currently English-only. Chinese translations are very welcome!

## Community

- Report bugs via [GitHub Issues](https://github.com/QwenLM/Qwen-Agent/issues)
- Tag issues appropriately: `bug`, `enhancement`, `documentation`, `Work in Progress`

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
