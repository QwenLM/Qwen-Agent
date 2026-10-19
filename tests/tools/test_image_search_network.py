"""Qwen-Agent imports must not change networking for the rest of the process."""

import os
import socket
import subprocess
import sys
import textwrap

import pytest


def run_fresh_process(code, *args):
    env = dict(os.environ, NO_PROXY='*', no_proxy='*')
    result = subprocess.run([sys.executable, '-c', textwrap.dedent(code), *args],
                            env=env,
                            capture_output=True,
                            text=True,
                            timeout=30)
    if result.returncode == 77:
        pytest.skip(result.stdout.strip())
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('module', ['qwen_agent', 'qwen_agent.tools.image_search'])
def test_import_preserves_system_resolver(module):
    run_fresh_process(
        '''
        import importlib
        import socket
        import sys

        resolver = socket.getaddrinfo
        importlib.import_module(sys.argv[1])
        assert socket.getaddrinfo is resolver
        ''', module)


@pytest.mark.parametrize('module', ['qwen_agent', 'qwen_agent.tools.image_search'])
@pytest.mark.parametrize('family', [socket.AF_INET, socket.AF_INET6])
def test_import_preserves_real_http_connectivity(module, family):
    run_fresh_process(
        '''
        import importlib
        import socket
        import sys
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        import requests

        family = int(sys.argv[2])
        host = '::1' if family == socket.AF_INET6 else '127.0.0.1'

        class Server(HTTPServer):
            address_family = family

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(3)

            def log_message(self, *_args):
                pass

            def do_GET(self):
                body = b'local-http-ok'
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        try:
            server = Server((host, 0), Handler)
        except OSError as error:
            if family == socket.AF_INET6:
                print('IPv6 loopback is unavailable:', error)
                sys.exit(77)
            raise
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        thread.start()
        url_host = '[::1]' if family == socket.AF_INET6 else host
        url = f'http://{url_host}:{server.server_port}/'
        try:
            with requests.Session() as session:
                session.trust_env = False
                before = session.get(url, timeout=3)
                assert before.status_code == 200
                assert before.content == b'local-http-ok'
                importlib.import_module(sys.argv[1])
                after = session.get(url, timeout=3)
                assert after.status_code == 200
                assert after.content == before.content
                assert socket.getaddrinfo(host, server.server_port, family, socket.SOCK_STREAM)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            assert not thread.is_alive()
        ''', module, str(int(family)))


def test_image_search_still_parses_a_local_http_response():
    run_fresh_process('''
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from urllib.parse import parse_qs, urlsplit

        from qwen_agent.tools import image_search

        calls = []

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(3)

            def log_message(self, *_args):
                pass

            def do_GET(self):
                calls.append(parse_qs(urlsplit(self.path).query))
                body = json.dumps({'image_results': [{
                    'position': 1, 'title': 'Local image', 'original': 'https://example.test/image.png',
                    'link': 'https://example.test/page', 'width': '640', 'height': '480',
                }]}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        thread.start()
        try:
            image_search.SERPAPI_URL = f'http://127.0.0.1:{server.server_port}/search.json'
            image_search.SERPAPI_IMAGE_SEARCH_KEY = 'local-test-key'
            result = image_search.serper_search('https://example.test/query.png', check_accessibility=False, max_retry=1)
            assert len(result) == 1
            assert result[0].title == 'Local image'
            assert result[0].imgurl == 'https://example.test/image.png'
            assert calls == [{
                'engine': ['google_reverse_image'], 'image_url': ['https://example.test/query.png'],
                'api_key': ['local-test-key'], 'hl': ['zh-CN'], 'gl': ['cn'],
            }]
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            assert not thread.is_alive()
        ''')
