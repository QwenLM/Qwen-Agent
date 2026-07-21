# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");

import os
import tempfile

from qwen_agent.agent import Agent
from qwen_agent.llm.schema import Message


class _DummyAgent(Agent):
    """Minimal concrete Agent for unit tests (no LLM calls)."""

    def _run(self, messages, lang: str = 'en', **kwargs):
        yield messages


def test_system_prompt_files_prepended_to_system_message(tmp_path):
    agents_md = tmp_path / 'AGENTS.md'
    soul_md = tmp_path / 'SOUL.md'
    agents_md.write_text('You are a careful coding agent.', encoding='utf-8')
    soul_md.write_text('Your name is Qwen.', encoding='utf-8')

    bot = _DummyAgent(
        system_message='Base system message.',
        system_prompt_files=[str(agents_md), str(soul_md)],
        llm=None,
    )

    assert 'You are a careful coding agent.' in bot.system_message
    assert 'Your name is Qwen.' in bot.system_message
    assert bot.system_message.endswith('Base system message.')
    # files come first, in order
    assert bot.system_message.index('careful coding agent') < bot.system_message.index('Your name is Qwen')
    assert bot.system_message.index('Your name is Qwen') < bot.system_message.index('Base system message')


def test_system_prompt_files_via_kwargs(tmp_path):
    f = tmp_path / 'PROFILE.md'
    f.write_text('Profile: research assistant', encoding='utf-8')
    # kwargs path is used when the named param is omitted (config-driven setup).
    bot = _DummyAgent(system_message='Hi', llm=None, **{'system_prompt_files': [str(f)]})
    assert 'Profile: research assistant' in bot.system_message
    assert bot.system_message.endswith('Hi')


def test_missing_system_prompt_file_is_skipped(tmp_path):
    existing = tmp_path / 'AGENTS.md'
    existing.write_text('Present rules', encoding='utf-8')
    missing = tmp_path / 'MISSING.md'
    bot = _DummyAgent(
        system_message='Base',
        system_prompt_files=[str(missing), str(existing)],
        llm=None,
    )
    assert 'Present rules' in bot.system_message
    assert 'Base' in bot.system_message
    assert 'MISSING' not in bot.system_message


def test_run_injects_combined_system_message(tmp_path):
    f = tmp_path / 'AGENTS.md'
    f.write_text('Always cite sources.', encoding='utf-8')
    bot = _DummyAgent(system_message='Be concise.', system_prompt_files=[str(f)], llm=None)
    *_, last = bot.run([Message('user', 'hello')])
    assert last[0].role == 'system'
    assert 'Always cite sources.' in last[0].content
    assert 'Be concise.' in last[0].content
