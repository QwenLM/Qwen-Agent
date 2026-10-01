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
"""Guards against SSRF when fetching user-supplied URLs.

Tools such as ``web_extractor`` and ``simple_doc_parser`` download content
from URLs chosen by the model or the caller. Without validation, such a
request can be pointed at loopback, private or link-local addresses, which
allows reaching cloud metadata endpoints and internal services (SSRF).

``assert_safe_url`` resolves every URL host through DNS and rejects it when
any resolved address falls into a non-public range, including IPv4-mapped
IPv6 addresses. ``fetch_public_url`` applies this check to every hop of a
redirect chain. Set the environment variable
``QWEN_AGENT_ALLOW_PRIVATE_NETWORK=1`` to opt out for intranet deployments.
"""

import ipaddress
import os
import socket
import urllib.parse
from typing import Set

import requests

DEFAULT_TIMEOUT_SECONDS = 60
MAX_REDIRECTS = 5

ALLOW_PRIVATE_NETWORK_ENV = 'QWEN_AGENT_ALLOW_PRIVATE_NETWORK'

# Shared address space (RFC 6598); not covered by ipaddress.is_private.
CGNAT_NETWORK = ipaddress.ip_network('100.64.0.0/10')


class UnsafeUrlError(ValueError):
    """Raised when a URL cannot be fetched safely."""


def _allow_private_network() -> bool:
    return os.environ.get(ALLOW_PRIVATE_NETWORK_ENV, '').strip().lower() in ('1', 'true', 'yes', 'on')


def is_disallowed_ip(ip: str) -> bool:
    """Return True if the address must not be reached from a public fetch."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        # Unparseable or zone-indexed addresses fail closed.
        return True
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        # ::ffff:10.0.0.1 is a private IPv4 address in disguise.
        addr = addr.ipv4_mapped
    return (addr.is_unspecified or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved or
            addr.is_private or addr in CGNAT_NETWORK)


def _resolve_host_ips(hostname: str) -> Set[str]:
    infos = socket.getaddrinfo(hostname, None)
    return {info[4][0] for info in infos}


def assert_safe_url(url: str) -> None:
    """Raise :class:`UnsafeUrlError` unless every resolved IP is public."""
    if _allow_private_network():
        return
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise UnsafeUrlError(f'Only http(s) URLs are supported, got scheme {parsed.scheme!r} in {url!r}')
    if not parsed.hostname:
        raise UnsafeUrlError(f'URL has no host name: {url!r}')
    try:
        ips = _resolve_host_ips(parsed.hostname)
    except socket.gaierror as ex:
        raise UnsafeUrlError(f'Cannot resolve host {parsed.hostname!r}: {ex}')
    disallowed = sorted(ip for ip in ips if is_disallowed_ip(ip))
    if disallowed:
        raise UnsafeUrlError(f'Refusing to fetch {parsed.hostname!r}: it resolves to non-public '
                             f'address(es) {disallowed}, which could reach internal services (SSRF). '
                             f'To allow internal addresses, e.g. for intranet deployments, set the '
                             f'{ALLOW_PRIVATE_NETWORK_ENV} environment variable.')


def fetch_public_url(url: str, headers=None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> requests.Response:
    """Fetch ``url`` while rejecting non-public addresses on every hop.

    Redirects are followed manually so that each new target host is
    validated again before the next request is made.
    """
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        assert_safe_url(current_url)
        response = requests.get(current_url, headers=headers, timeout=timeout, allow_redirects=False)
        if response.is_redirect or response.is_permanent_redirect:
            current_url = urllib.parse.urljoin(current_url, response.headers['location'])
            continue
        return response
    raise UnsafeUrlError(f'Too many redirects (more than {MAX_REDIRECTS}) while fetching {url!r}')
