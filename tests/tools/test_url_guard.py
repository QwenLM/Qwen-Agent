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
import os
import socket

import pytest

from qwen_agent.utils.url_guard import (ALLOW_PRIVATE_NETWORK_ENV, DEFAULT_TIMEOUT_SECONDS, MAX_REDIRECTS,
                                        UnsafeUrlError, assert_safe_url, fetch_public_url, is_disallowed_ip)
from qwen_agent.utils.utils import save_url_to_local_work_dir


def _addrinfo(ip):
    family = socket.AF_INET6 if ':' in ip else socket.AF_INET
    sockaddr = (ip, 0, 0, 0) if family == socket.AF_INET6 else (ip, 0)
    return [(family, socket.SOCK_STREAM, 6, '', sockaddr)]


def _patch_resolution(monkeypatch, host_to_ips):
    """Map host names to canned getaddrinfo answers without touching DNS."""

    def fake_getaddrinfo(host, *args, **kwargs):
        if host not in host_to_ips:
            raise socket.gaierror(socket.EAI_NONAME, f'no resolution stub for {host!r}')
        ips = host_to_ips[host]
        result = []
        for ip in ips:
            result.extend(_addrinfo(ip))
        return result

    monkeypatch.setattr(socket, 'getaddrinfo', fake_getaddrinfo)


def test_is_disallowed_ip_matrix():
    disallowed = [
        '127.0.0.1',  # loopback
        '127.8.8.8',
        '10.1.2.3',  # RFC1918
        '172.16.0.1',  # RFC1918
        '172.31.255.255',
        '192.168.1.1',  # RFC1918
        '169.254.169.254',  # link-local (cloud metadata)
        '0.0.0.0',  # unspecified
        '100.64.0.1',  # CGNAT shared address space
        '224.0.0.1',  # multicast
        '240.0.0.1',  # reserved
        '::1',  # IPv6 loopback
        'fe80::1',  # IPv6 link-local
        'fc00::1',  # IPv6 ULA
        'fd12:3456::1',  # IPv6 ULA
        '::ffff:10.0.0.5',  # IPv4-mapped private IPv4
        '::ffff:127.0.0.1',  # IPv4-mapped loopback
        'fe80::1%eth0',  # zone index fails closed
        'not-an-ip',
    ]
    for ip in disallowed:
        assert is_disallowed_ip(ip), ip

    allowed = ['8.8.8.8', '1.2.3.4', '172.32.0.1', '100.128.0.1', '93.184.216.34', '2606:4700::1111']
    for ip in allowed:
        assert not is_disallowed_ip(ip), ip


def test_assert_safe_url_rejects_non_http_schemes():
    for url in ['file:///etc/passwd', 'ftp://example.com/file', 'gopher://example.com', 'example.com/file']:
        with pytest.raises(UnsafeUrlError):
            assert_safe_url(url)


def test_assert_safe_url_rejects_private_resolution(monkeypatch):
    _patch_resolution(monkeypatch, {'metadata.google.internal': ['169.254.169.254']})
    with pytest.raises(UnsafeUrlError):
        assert_safe_url('http://metadata.google.internal/latest/meta-data/')


def test_assert_safe_url_accepts_public_resolution(monkeypatch):
    _patch_resolution(monkeypatch, {'example.com': ['93.184.216.34', '2606:4700::1111']})
    assert_safe_url('http://example.com/doc.pdf')


def test_assert_safe_url_rejects_when_any_record_is_private(monkeypatch):
    # A mixed answer must fail closed: one private record poisons the host.
    _patch_resolution(monkeypatch, {'dual.example.com': ['93.184.216.34', '10.0.0.7']})
    with pytest.raises(UnsafeUrlError):
        assert_safe_url('http://dual.example.com/doc.pdf')


def test_assert_safe_url_rejects_unresolvable_host(monkeypatch):
    _patch_resolution(monkeypatch, {})
    with pytest.raises(UnsafeUrlError):
        assert_safe_url('http://no-such-host.invalid/doc.pdf')


def test_env_opt_out_allows_private_targets(monkeypatch):
    monkeypatch.setenv(ALLOW_PRIVATE_NETWORK_ENV, '1')
    assert_safe_url('http://192.168.1.10:8080/intranet-wiki')


class FakeResponse:

    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.calls = None

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307) and 'location' in self.headers

    @property
    def is_permanent_redirect(self):
        return self.status_code == 308 and 'location' in self.headers


def _patch_http(monkeypatch, responses):
    calls = []

    def fake_get(url, headers=None, timeout=None, allow_redirects=None):
        assert allow_redirects is False
        assert timeout is not None, 'a fetch without timeout can hang forever'
        calls.append({'url': url, 'timeout': timeout})
        return responses.pop(0)

    monkeypatch.setattr('qwen_agent.utils.url_guard.requests.get', fake_get)
    return calls


def test_fetch_public_url_follows_public_redirects(monkeypatch):
    _patch_resolution(monkeypatch, {'example.com': ['93.184.216.34'], 'cdn.example.com': ['8.8.8.8']})
    calls = _patch_http(monkeypatch, [
        FakeResponse(302, {'location': 'https://cdn.example.com/real.pdf'}),
        FakeResponse(200),
    ])
    response = fetch_public_url('http://example.com/doc.pdf')
    assert response.status_code == 200
    assert [call['url'] for call in calls] == [
        'http://example.com/doc.pdf',
        'https://cdn.example.com/real.pdf',
    ]
    assert calls[0]['timeout'] == DEFAULT_TIMEOUT_SECONDS


def test_fetch_public_url_rejects_redirect_to_private_host(monkeypatch):
    _patch_resolution(monkeypatch, {'example.com': ['93.184.216.34']})
    _patch_http(monkeypatch, [FakeResponse(302, {'location': 'http://metadata.google.internal/latest/meta-data/'})])
    with pytest.raises(UnsafeUrlError):
        fetch_public_url('http://example.com/doc.pdf')


def test_fetch_public_url_rejects_redirect_to_private_ip(monkeypatch):
    # Literal loopback addresses must be rejected even without DNS stubs.
    _patch_resolution(monkeypatch, {'example.com': ['93.184.216.34']})
    _patch_http(monkeypatch, [FakeResponse(302, {'location': 'http://127.0.0.1:9876/internal/secret'})])
    with pytest.raises(UnsafeUrlError):
        fetch_public_url('http://example.com/doc.pdf')


def test_fetch_public_url_limits_redirect_hops(monkeypatch):
    _patch_resolution(monkeypatch, {'example.com': ['93.184.216.34']})
    loop = [FakeResponse(302, {'location': 'http://example.com/next'})]
    calls = _patch_http(monkeypatch, loop * (MAX_REDIRECTS + 1))
    with pytest.raises(UnsafeUrlError):
        fetch_public_url('http://example.com/start')
    assert len(calls) == MAX_REDIRECTS + 1


def test_save_url_to_local_work_dir_blocks_private_url(monkeypatch, tmp_path):
    _patch_resolution(monkeypatch, {'internal.example': ['10.0.0.5']})
    with pytest.raises(UnsafeUrlError):
        save_url_to_local_work_dir('http://internal.example/doc.txt', str(tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_save_url_to_local_work_dir_keeps_local_path_behavior(tmp_path):
    # The non-http branch must keep working unchanged.
    source = tmp_path / 'local.docx'
    source.write_bytes(b'fake-docx-bytes')
    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    target = save_url_to_local_work_dir(str(source), str(out_dir))
    assert os.path.exists(target)
    with open(target, 'rb') as f:
        assert f.read() == b'fake-docx-bytes'


if __name__ == '__main__':
    test_is_disallowed_ip_matrix()
    test_assert_safe_url_rejects_non_http_schemes()
    test_save_url_to_local_work_dir_keeps_local_path_behavior()
    print('run with pytest for the full suite')
