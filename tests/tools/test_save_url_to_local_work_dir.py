import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from qwen_agent.utils.utils import save_url_to_local_work_dir


class DownloadHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/success.txt':
            body = b'new content'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_args):
        pass


class SaveUrlTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)

    def test_copy_from_same_path_preserves_file(self):
        source = self.directory / 'report.txt'
        source.write_text('original', encoding='utf-8')

        result = save_url_to_local_work_dir(str(source), str(self.directory))

        self.assertEqual(Path(result), source)
        self.assertEqual(source.read_text(encoding='utf-8'), 'original')

    def test_directory_source_is_rejected(self):
        directory = self.directory / 'nested'
        directory.mkdir()

        with self.assertRaises((IsADirectoryError, PermissionError)):
            save_url_to_local_work_dir(str(directory), str(self.directory))

        self.assertTrue(directory.is_dir())

    def test_local_copy_replaces_destination(self):
        source = self.directory / 'source' / 'report.txt'
        source.parent.mkdir()
        source.write_text('new content', encoding='utf-8')
        destination = self.directory / 'report.txt'
        destination.write_text('old content', encoding='utf-8')

        result = save_url_to_local_work_dir(str(source), str(self.directory))

        self.assertEqual(Path(result), destination)
        self.assertEqual(destination.read_text(encoding='utf-8'), 'new content')

    def test_missing_local_source_preserves_destination(self):
        destination = self.directory / 'report.txt'
        destination.write_text('old content', encoding='utf-8')

        with self.assertRaises(FileNotFoundError):
            save_url_to_local_work_dir(str(self.directory / 'missing' / 'report.txt'), str(self.directory))

        self.assertEqual(destination.read_text(encoding='utf-8'), 'old content')

    def start_server(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), DownloadHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def test_http_failure_preserves_destination(self):
        server = self.start_server()
        destination = self.directory / 'failed.txt'
        destination.write_text('old content', encoding='utf-8')
        with self.assertRaises(ValueError):
            save_url_to_local_work_dir(f'http://127.0.0.1:{server.server_port}/failed.txt', str(self.directory))
        self.assertEqual(destination.read_text(encoding='utf-8'), 'old content')

    def test_http_success_replaces_destination(self):
        server = self.start_server()
        destination = self.directory / 'success.txt'
        destination.write_text('old content', encoding='utf-8')
        result = save_url_to_local_work_dir(f'http://127.0.0.1:{server.server_port}/success.txt', str(self.directory))
        self.assertEqual(Path(result), destination)
        self.assertEqual(destination.read_text(encoding='utf-8'), 'new content')


if __name__ == '__main__':
    unittest.main()
