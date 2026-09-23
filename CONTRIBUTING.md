# Contributing to Qwen-Agent

Thank you for your interest in contributing to Qwen-Agent! This is Alibaba Qwen team's open-source LLM Agent framework.

## Development Setup

```bash
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -e ./"[gui,rag,code_interpreter,mcp]"
# Or `pip install -e ./` for the minimal requirements.
```

There is no `[dev]` extra. `setup.py` declares five extras — `gui`, `rag`,
`code_interpreter`, `mcp` and `python_executor` — so install only the ones you need;
`pip install -e ./"[mcp,python_executor]"` covers most tool work.

The tests and the lint hooks are not covered by any extra, so install them yourself:

```bash
pip install pytest pre-commit
pre-commit install
```

### Prerequisites
- Python — the `gui` extra requires Python 3.10 or higher. `setup.py` declares no
  `python_requires`, so the core package imposes no floor of its own.
- An LLM API key (DashScope, OpenAI-compatible, Azure, etc.)

## Code Style

Style is enforced by the hooks configured in `.pre-commit-config.yaml`:

| Hook | Tool | Configuration |
| ---- | ---- | ------------- |
| Lint | flake8 | `--max-line-length=300`, ignoring `E231,E702,E251,W604` |
| Import order | isort | `--line-length 120` |
| Format | yapf | Google style, `column_limit: 120` |
| Hygiene | pre-commit-hooks | trailing whitespace, EOF newline, LF endings, `check-yaml`, ... |

Run `pre-commit run --all-files` before pushing. The flake8 limit is still 300 columns,
but new code should stay within 120 where practical — `.pre-commit-config.yaml` carries
an open TODO to tighten it to 120 and reformat the tree. Type hints on public functions
are appreciated, though no hook checks them.

## Running Tests

```bash
pytest
```

Tests live in `tests/` (22 files, grouped by area: `tests/agents`, `tests/llm`,
`tests/tools`, `tests/memory`, `tests/qwen_server`, `tests/examples`). Most of them call
a live model service instead of a mock, so export an API key first — the default
`qwen-max` configuration reads `DASHSCOPE_API_KEY`. Please ensure existing tests pass and
add tests for new functionality.

Note that the repository's only GitHub Actions workflow is `deploy-docs.yml`; the test
suite is not run in CI, so run it locally before opening a PR.

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following code style
4. Add tests for new functionality
5. Run `pytest` to ensure all tests pass
6. Submit a PR to the `main` branch

### PR Title Format
Use a clear, descriptive title. The repository does not enforce a prefix convention: the
history mixes plain subjects ("support streamable-http for mcp") with prefixed ones
(`fix:`, `bugfix:`, `docs:`), so pick whichever reads best.

### PR Description
Include:
- **What** does this PR do?
- **Why** is this change needed?
- **How** was it tested?

## Types of Contributions

### Bug Fixes
Check [Issues](https://github.com/QwenLM/Qwen-Agent/issues) for reported bugs.

### New LLM Providers
Add new providers in `qwen_agent/llm/`. See existing providers like `oai.py` or `azure.py` as examples. Register with `@register_llm('provider_name')` (defined in `qwen_agent/llm/base.py`).

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

The documentation site is in `qwen-agent-docs/website/` (Next.js + Nextra + MDX). Content
currently only exists under `qwen-agent-docs/website/content/en/`, so it is English-only;
the `app/[lang]/` route already handles a language prefix, which makes Chinese
translations very welcome!

## Community

- Report bugs via [GitHub Issues](https://github.com/QwenLM/Qwen-Agent/issues)
- Tag issues with one of the repository's existing labels: `Bug`, `Documentation`,
  `Work in Progress`, `Bad Case`. There is no `enhancement` label, and no
  beginner-friendly label yet.

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
