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
"""RAG with verifiable citations for the Assistant.

This example answers a recurring question (issue #375, "Is it possible to have
citations for RAG"): how to make ``Assistant`` cite its RAG sources, and — more
importantly — how to catch citations that are *not* actually supported by the
retrieved text before they reach a user.

``Assistant`` already injects each retrieved chunk into the system prompt tagged
with its source (see ``format_knowledge_to_source_and_content`` in
``qwen_agent/agents/assistant.py``, which turns the retrieval output
``[{'url': ..., 'text': [chunk, ...]}]`` into ``[{'source': ..., 'content': ...}]``
under a ``# Knowledge Base`` section). So the model *can* attribute an answer to a
source. What is missing is the other half: verifying that a quote the model
attributes to a source is really there, and really supports the claim.

The pattern here is "cheap deterministic detector -> expensive judge":

1. ``verify_citations`` — a 0-token, no-API-key gate that checks each cited quote
   appears **verbatim** (whitespace-normalized) in the content of the source it is
   attributed to. It separates four outcomes: ``supported`` (verbatim in the cited
   source), ``misattributed`` (verbatim, but in a *different* source), ``frankenquote``
   (two real fragments stitched into a quote that never appears contiguously), and
   ``fabricated`` (not present anywhere). This alone rejects the most common RAG
   citation failures and runs fully offline.

2. ``judge_support`` — an optional LLM judge, over Qwen via the framework's own
   ``get_chat_model``, that decides whether a *verbatim, correctly-attributed* quote
   actually **supports** the claim (a right quote can still be the wrong evidence).
   The burden of proof is on the citation: default to "unrelated", outside knowledge
   is inadmissible, and it fails closed. This step needs a model, so it is gated
   behind an API key and is not run in CI.

``test()`` runs only the deterministic gate on a small built-in knowledge base with
planted failures, so it needs no API key. ``run_live()`` shows the end-to-end flow
with a real ``Assistant`` over a real document and needs ``DASHSCOPE_API_KEY``.

Credit: issue #375 by @allanxenon; the "carry the source/chunk id through" idea in
that thread by @ScottDeng114514.
"""
import os
import re
from typing import Dict, List

from qwen_agent.agents import Assistant
from qwen_agent.agents.assistant import format_knowledge_to_source_and_content
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message

# A citation is a (source, quote, claim) triple: the source the model attributes the
# quote to, the verbatim span it lifts from that source, and the claim it supports.
Citation = Dict[str, str]
# Knowledge is Qwen-Agent's own retrieval-to-prompt shape: [{'source', 'content'}].
Knowledge = List[Dict[str, str]]

# A fragment must be at least this many normalized chars to count toward a frankenquote,
# so a stray shared word ('the', 'study') cannot make two unrelated quotes look stitched.
_MIN_FRAGMENT_CHARS = 12


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace so 'verbatim' ignores wrapping/spacing only."""
    return re.sub(r'\s+', ' ', text or '').strip().lower()


def _is_frankenquote(norm_quote: str, norm_content: str) -> bool:
    """True if the quote is two real fragments of `content` that are not contiguous in it.

    We split the quote at each internal space and ask whether some left+right pair are
    *both* present verbatim in the same source while the whole quote is not — the
    signature of a quote stitched from real material that was never said together.
    """
    tokens = norm_quote.split(' ')
    for i in range(1, len(tokens)):
        left = ' '.join(tokens[:i])
        right = ' '.join(tokens[i:])
        if len(left) >= _MIN_FRAGMENT_CHARS and len(right) >= _MIN_FRAGMENT_CHARS:
            if left in norm_content and right in norm_content:
                return True
    return False


def verify_citations(citations: List[Citation], knowledge: Knowledge) -> List[Dict]:
    """Deterministically check each citation's quote against the retrieved knowledge.

    Args:
        citations: List of ``{'source', 'quote', 'claim'}``. ``source`` should match a
            ``source`` field produced by ``format_knowledge_to_source_and_content``.
        knowledge: The retrieved knowledge in Qwen-Agent's ``[{'source', 'content'}]``
            shape (the output of ``format_knowledge_to_source_and_content``).

    Returns:
        One verdict dict per citation with a ``status`` field:
          - ``supported``: the quote appears verbatim in the cited source.
          - ``misattributed``: the quote appears verbatim, but in a different source.
          - ``frankenquote``: two real fragments stitched into a non-contiguous quote.
          - ``fabricated``: the quote appears in no source.
        Verdicts other than ``supported`` are the ones to block on.
    """
    by_source = {k['source']: _normalize(k['content']) for k in knowledge}
    all_content = list(by_source.items())

    verdicts = []
    for cite in citations:
        source = cite.get('source', '')
        norm_quote = _normalize(cite.get('quote', ''))
        verdict = {
            'source': source,
            'quote': cite.get('quote', ''),
            'claim': cite.get('claim', ''),
        }

        if not norm_quote:
            verdict['status'] = 'fabricated'
            verdict['detail'] = 'empty quote'
            verdicts.append(verdict)
            continue

        cited_content = by_source.get(source)
        if cited_content is not None and norm_quote in cited_content:
            verdict['status'] = 'supported'
            verdicts.append(verdict)
            continue

        # Not verbatim in the cited source. Is it verbatim in a different one?
        found_in = [src for src, content in all_content if norm_quote in content]
        if found_in:
            verdict['status'] = 'misattributed'
            verdict['detail'] = f'quote is verbatim in {found_in} but was attributed to {source!r}'
            verdicts.append(verdict)
            continue

        # Not verbatim anywhere. Is it a stitch of real fragments from any one source?
        if any(_is_frankenquote(norm_quote, content) for _, content in all_content):
            verdict['status'] = 'frankenquote'
            verdict['detail'] = 'quote is stitched from real fragments that are not contiguous in the source'
            verdicts.append(verdict)
            continue

        verdict['status'] = 'fabricated'
        verdict['detail'] = 'quote does not appear in any retrieved source'
        verdicts.append(verdict)

    return verdicts


JUDGE_SYSTEM = ('You are a strict citation auditor. You are given a CLAIM and a QUOTE that has already '
                'been verified to appear verbatim in a cited source. Decide only whether the QUOTE, on '
                'its own, establishes the CLAIM. The burden of proof is on the citation:\n'
                '- Answer with exactly one word: supports, partial, unrelated, or contradicts.\n'
                '- Use ONLY the quote. Any outside knowledge is inadmissible.\n'
                '- If the quote does not clearly and fully establish the claim, answer partial or unrelated.\n'
                '- If in doubt, do not give credit.')

_VALID_JUDGE = ('supports', 'partial', 'unrelated', 'contradicts')


def judge_support(claim: str, quote: str, llm_cfg: Dict) -> str:
    """LLM judge: does a verbatim, correctly-attributed quote actually support the claim?

    A quote can be real and still be the wrong evidence, which the deterministic gate
    cannot see. This runs over Qwen through the framework's own ``get_chat_model``.
    Fails closed: any malformed/unexpected model output is treated as ``unrelated``.
    Requires a model (API key); not run in CI.
    """
    llm = get_chat_model(llm_cfg)
    messages = [
        Message('system', JUDGE_SYSTEM),
        Message('user', f'CLAIM: {claim}\n\nQUOTE: {quote}\n\nOne word:'),
    ]
    *_, last = llm.chat(messages=messages, stream=True)
    answer = _normalize(last[-1].content) if last else ''
    for label in _VALID_JUDGE:
        if answer.startswith(label):
            return label
    return 'unrelated'  # fail closed


def build_demo_knowledge() -> Knowledge:
    """A tiny synthetic knowledge base in Qwen-Agent's retrieval-output shape.

    Built via the real ``format_knowledge_to_source_and_content`` so the gate is
    exercised on exactly the structure ``Assistant`` produces at runtime, not a mock.
    """
    retrieval_output = [
        {
            'url':
                'trial_report_A.txt',
            'text': [
                'In the ATLAS-3 trial, 1,204 adults received denavimab or placebo for 24 weeks. '
                'Denavimab reduced the annual relapse rate by 41% versus placebo (p=0.002).',
                'In the pre-specified low-risk subgroup, the reduction in relapse rate was not '
                'statistically significant.',
            ],
        },
        {
            'url':
                'safety_memo_B.txt',
            'text': [
                'Across pooled studies, the most common adverse event with denavimab was mild '
                'injection-site reaction, reported in 12% of participants.',
            ],
        },
    ]
    return format_knowledge_to_source_and_content(retrieval_output)


def test():
    """Offline gate check on a built-in knowledge base with planted failures. No API key."""
    knowledge = build_demo_knowledge()
    src_a = knowledge[0]['source']

    citations = [
        # supported: verbatim in the cited source
        {
            'claim': 'Denavimab cut the annual relapse rate.',
            'source': src_a,
            'quote': 'Denavimab reduced the annual relapse rate by 41% versus placebo',
        },
        # fabricated: plausible number that appears nowhere
        {
            'claim': 'Denavimab reduced mortality by 30%.',
            'source': src_a,
            'quote': 'Denavimab reduced all-cause mortality by 30%',
        },
        # misattributed: real quote from B, cited to A
        {
            'claim': 'The common adverse event was an injection-site reaction.',
            'source': src_a,
            'quote': 'the most common adverse event with denavimab was mild injection-site reaction',
        },
        # frankenquote: two real fragments of A stitched together
        {
            'claim': 'The relapse reduction held in the low-risk subgroup.',
            'source': src_a,
            'quote': 'reduced the annual relapse rate by 41% in the pre-specified low-risk subgroup',
        },
    ]

    verdicts = verify_citations(citations, knowledge)
    statuses = [v['status'] for v in verdicts]
    print('Citation audit:')
    for v in verdicts:
        print(f"  [{v['status']:>13}] {v['claim']}")
        if v.get('detail'):
            print(f"                  -> {v['detail']}")

    assert statuses == ['supported', 'fabricated', 'misattributed', 'frankenquote'], statuses

    unsupported = [v for v in verdicts if v['status'] != 'supported']
    assert len(unsupported) == 3
    print(f'\nBlocked {len(unsupported)} unsupported citation(s); 1 passed.')


def run_live(file: str = 'https://arxiv.org/pdf/1706.03762.pdf',
             query: str = 'What problem does the paper say recurrent models have, and what does it propose?'):
    """End-to-end: real RAG answer -> deterministic gate -> LLM judge. Needs DASHSCOPE_API_KEY."""
    if not os.getenv('DASHSCOPE_API_KEY'):
        print('run_live skipped: set DASHSCOPE_API_KEY to run the live Assistant demo.')
        return

    llm_cfg = {'model': 'qwen-plus-latest'}
    instruction = ('Answer using only the # Knowledge Base. After each sentence, cite support inline as '
                   '<<source | verbatim quote>>, copying the quote exactly from the cited source.')
    bot = Assistant(llm=llm_cfg, system_message=instruction)
    messages = [{'role': 'user', 'content': [{'text': query}, {'file': file}]}]

    answer = ''
    for rsp in bot.run(messages):
        answer = rsp[-1]['content']
    print('Answer:\n', answer, '\n')

    # Reconstruct the knowledge the Assistant retrieved, then audit the answer's citations.
    *_, mem = bot.mem.run(messages=messages)
    knowledge = format_knowledge_to_source_and_content(mem[-1]['content'])

    citations = []
    for src, quote in re.findall(r'<<\s*(.*?)\s*\|\s*(.*?)\s*>>', answer):
        citations.append({'claim': '', 'source': src, 'quote': quote})

    verdicts = verify_citations(citations, knowledge)
    for v in verdicts:
        line = f"[{v['status']}] {v['quote'][:80]}"
        if v['status'] == 'supported':
            line += f" -> judge: {judge_support(v['claim'] or answer, v['quote'], llm_cfg)}"
        print(line)


if __name__ == '__main__':
    test()
    run_live()
