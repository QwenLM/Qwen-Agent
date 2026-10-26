"""Offline regressions for explicit document cache refresh through RAG."""
import copy
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from qwen_agent.agents import Assistant
from qwen_agent.llm.qwenvl_oai import QwenVLChatAtOAI
from qwen_agent.tools import doc_parser, extract_doc_vocabulary, simple_doc_parser
from qwen_agent.tools.doc_parser import DocParser
from qwen_agent.tools.retrieval import Retrieval
from qwen_agent.tools.simple_doc_parser import DocParserError, SimpleDocParser

OLD = 'cobalt thermostat eco target is 26 degrees.'
NEW = 'amber thermostat eco target is 24 degrees.'
FILLER = '\n\nMaintenance: inspect the sensor and clean the housing.' * 150


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for module in [doc_parser, simple_doc_parser, extract_doc_vocabulary]:
        monkeypatch.setattr(module, 'DEFAULT_WORKSPACE', str(tmp_path / 'cache'))


def _text(record):
    return '\n'.join(chunk['content'] for chunk in record['raw'])


@pytest.mark.parametrize('structured', [False, True])
def test_simple_parser_refresh_is_opt_in_and_persists(tmp_path, structured):
    path = tmp_path / 'manual.txt'
    path.write_text(OLD, encoding='utf-8')
    tool = SimpleDocParser({'structured_doc': structured})
    original = tool.call({'url': str(path)})
    path.write_text(NEW, encoding='utf-8')
    assert tool.call({'url': str(path)}) == original
    assert tool.call({'url': str(path)}, force_refresh=False) == original
    fresh = tool.call({'url': str(path)}, force_refresh=True)
    assert NEW in json.dumps(fresh) and OLD not in json.dumps(fresh)
    restarted = SimpleDocParser({'structured_doc': structured})
    assert restarted.call({'url': str(path)}) == fresh
    path.write_text('third version', encoding='utf-8')
    assert restarted.call({'url': str(path)}) == fresh


@pytest.mark.parametrize('new_filler', ['', FILLER], ids=['shrunk', 'chunked'])
def test_refresh_invalidates_other_chunk_sizes_and_preserves_other_documents(tmp_path, new_filler):
    path = tmp_path / 'manual.txt'
    other = tmp_path / 'other.txt'
    path.write_text(OLD + FILLER, encoding='utf-8')
    other.write_text('untouched document' + FILLER, encoding='utf-8')
    tool = DocParser({'max_ref_token': 64})
    originals = {size: tool.call({'url': str(path)}, parser_page_size=size) for size in [500, 800]}
    other_record = tool.call({'url': str(other)})
    path.write_text(NEW + new_filler, encoding='utf-8')
    other.write_text('changed but not explicitly refreshed', encoding='utf-8')
    assert tool.call({'url': str(path)}, parser_page_size=500) == originals[500]
    refreshed = tool.call({'url': str(path)}, force_refresh=True)
    assert NEW in _text(refreshed) and OLD not in _text(refreshed)
    # New instances and other previously populated chunk sizes must not resurrect old text.
    restarted = DocParser({'max_ref_token': 64})
    for size in [500, 800]:
        result = restarted.call({'url': str(path)}, parser_page_size=size)
        assert NEW in _text(result) and OLD not in _text(result)
    assert restarted.call({'url': str(other)}) == other_record


def test_failed_parse_does_not_discard_previous_cache(monkeypatch, tmp_path):
    path = tmp_path / 'manual.txt'
    path.write_text(OLD + FILLER, encoding='utf-8')
    tool = DocParser({'max_ref_token': 64})
    original = tool.call({'url': str(path)})
    raw_original = tool.doc_extractor.call({'url': str(path)})

    def fail_parse(path):
        raise ValueError('Unreadable replacement')

    monkeypatch.setattr(simple_doc_parser, 'parse_txt', fail_parse)
    with pytest.raises(DocParserError, match='Unreadable replacement'):
        tool.call({'url': str(path)}, force_refresh=True)
    assert tool.call({'url': str(path)}) == original
    assert tool.doc_extractor.call({'url': str(path)}) == raw_original


def test_retrieval_returns_updated_content_after_refresh(tmp_path):
    path = tmp_path / 'manual.txt'
    path.write_text(OLD + FILLER, encoding='utf-8')
    tool = Retrieval({'max_ref_token': 64})
    params = {'query': 'thermostat', 'files': [str(path)]}
    original = tool.call(params)
    path.write_text(NEW + FILLER, encoding='utf-8')
    assert tool.call(params) == original
    fresh = tool.call(params, force_refresh=True)
    assert NEW in json.dumps(fresh) and OLD not in json.dumps(fresh)
    assert Retrieval({'max_ref_token': 64}).call(params) == fresh


def _assistant(monkeypatch, strategy, constructor_files, max_ref_token=64):
    llm = QwenVLChatAtOAI({'model': 'offline-vision', 'api_key': 'unused'})
    requests = []

    def fake_create(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        answer = '{"keywords_en": ["thermostat"], "information": ["thermostat"]}'
        return iter([SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=answer))])])

    monkeypatch.setattr(llm, '_chat_complete_create', fake_create)
    rag_cfg = {'rag_keygen_strategy': strategy}
    if max_ref_token is not None:
        rag_cfg['max_ref_token'] = max_ref_token
    bot = Assistant(llm=llm, files=['manual.txt'] if constructor_files else None, rag_cfg=rag_cfg)
    content = 'What is the thermostat target?'
    if not constructor_files:
        content = [{'text': content}, {'file': 'manual.txt'}]
    messages = [{'role': 'user', 'content': content}]
    return bot, messages, requests


def _request_text(request):
    return '\n'.join(p['text'] for msg in request['messages'] for p in msg['content'] if p['type'] == 'text')


@pytest.mark.parametrize('constructor_files', [False, True])
@pytest.mark.parametrize('strategy',
                         ['none', 'GenKeyword', 'GenKeywordWithKnowledge', 'SplitQueryThenGenKeywordWithKnowledge'])
def test_assistant_refresh_reaches_model_context(monkeypatch, tmp_path, strategy, constructor_files):
    if 'WithKnowledge' in strategy:
        pytest.importorskip('sklearn')
    path = tmp_path / 'manual.txt'
    path.write_text(OLD + FILLER, encoding='utf-8')
    bot, messages, requests = _assistant(monkeypatch, strategy, constructor_files)
    before = copy.deepcopy(messages)
    list(bot.run(messages))
    assert OLD in _request_text(requests[-1])
    path.write_text(NEW + FILLER, encoding='utf-8')
    list(bot.run(messages))
    assert OLD in _request_text(requests[-1])
    requests.clear()
    list(bot.run(messages, force_refresh=True))
    assert NEW in _request_text(requests[-1]) and OLD not in _request_text(requests[-1])
    if 'WithKnowledge' in strategy:
        keyword_request = requests[-2]
        assert 'amber' in _request_text(keyword_request)
        assert 'cobalt' not in _request_text(keyword_request)
    # A later ordinary run uses the refreshed cache, including on a new Assistant instance.
    restarted, _, later_requests = _assistant(monkeypatch, strategy, constructor_files)
    list(restarted.run(messages))
    assert NEW in _request_text(later_requests[-1])
    assert messages == before
    assert all('force_refresh' not in request for request in requests + later_requests)


def test_http_document_is_downloaded_again_only_on_refresh(tmp_path):
    path = tmp_path / 'manual.txt'
    path.write_text(OLD, encoding='utf-8')
    hits = []

    class Handler(SimpleHTTPRequestHandler):

        def do_GET(self):
            hits.append(self.path)
            super().do_GET()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f'http://127.0.0.1:{server.server_port}/manual.txt'
        tool = DocParser()
        original = tool.call({'url': url})
        first_hits = len(hits)
        assert first_hits > 0
        path.write_text(NEW, encoding='utf-8')
        assert tool.call({'url': url}) == original
        assert len(hits) == first_hits
        result = tool.call({'url': url}, force_refresh=True)
        assert NEW in _text(result) and OLD not in _text(result)
        refreshed_hits = len(hits)
        assert refreshed_hits > first_hits
        assert tool.call({'url': url}) == result
        assert len(hits) == refreshed_hits
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.parametrize('filler', ['', FILLER * 20], ids=['whole_document', 'chunked_document'])
def test_assistant_refresh_with_default_rag_budget(monkeypatch, tmp_path, filler):
    path = tmp_path / 'manual.txt'
    path.write_text(OLD + filler, encoding='utf-8')
    bot, messages, requests = _assistant(monkeypatch, 'none', True, max_ref_token=None)
    list(bot.run(messages))
    path.write_text(NEW + filler, encoding='utf-8')
    list(bot.run(messages))
    assert OLD in _request_text(requests[-1])
    list(bot.run(messages, force_refresh=True))
    assert NEW in _request_text(requests[-1]) and OLD not in _request_text(requests[-1])
    list(bot.run(messages))
    assert NEW in _request_text(requests[-1]) and OLD not in _request_text(requests[-1])
