import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from qwen_agent.utils.utils import save_url_to_local_work_dir


class _FileHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/missing.txt':
            self.send_response(404)
            self.end_headers()
            return
        body = b'downloaded'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def file_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _FileHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_save_url_keeps_existing_file_when_download_fails(tmp_path, file_server):
    dest = tmp_path / 'a.txt'
    dest.write_text('old content', encoding='utf-8')

    with pytest.raises(ValueError):
        save_url_to_local_work_dir(
            f'{file_server}/missing.txt', str(tmp_path), 'a.txt')

    assert dest.read_text(encoding='utf-8') == 'old content'
    assert not (tmp_path / 'a.txt.part').exists()


def test_save_url_creates_missing_dir_and_writes_file(tmp_path, file_server):
    save_dir = tmp_path / 'nested' / 'dir'

    path = save_url_to_local_work_dir(
        f'{file_server}/a.txt', str(save_dir), 'a.txt')

    assert path == str(save_dir / 'a.txt')
    assert (save_dir / 'a.txt').read_bytes() == b'downloaded'
    assert not (save_dir / 'a.txt.part').exists()
