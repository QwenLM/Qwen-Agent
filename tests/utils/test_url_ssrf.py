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
import tempfile

from qwen_agent.utils import utils

INTERNAL_URLS = [
    'http://127.0.0.1:9876/internal/secret',
    'http://localhost:9876/internal/secret',
    'http://169.254.169.254/latest/meta-data/iam/security-credentials/',
    'http://10.0.0.5/admin',
    'http://192.168.1.1/admin',
]


def test_internal_urls_are_rejected():
    os.environ.pop(utils._ALLOW_PRIVATE_URL_ENV, None)
    with tempfile.TemporaryDirectory() as work_dir:
        for url in INTERNAL_URLS:
            try:
                utils.save_url_to_local_work_dir(url, work_dir)
            except ValueError as e:
                assert 'non-public' in str(e), f'{url} was rejected for the wrong reason: {e}'
            else:
                raise AssertionError(f'{url} should have been rejected')


def test_internal_urls_are_allowed_when_opted_in():
    os.environ[utils._ALLOW_PRIVATE_URL_ENV] = '1'
    try:
        # The guard must not fire; the request itself is expected to fail because nothing is listening.
        utils._assert_downloadable_url('http://127.0.0.1:9876/internal/secret')
    finally:
        os.environ.pop(utils._ALLOW_PRIVATE_URL_ENV, None)


def test_redirect_to_internal_address_is_rejected():
    os.environ.pop(utils._ALLOW_PRIVATE_URL_ENV, None)
    requested = []

    class _RedirectingResponse:

        def __init__(self, location):
            self.headers = {'location': location}
            self.is_redirect = True

    def _fake_get(url, headers=None, allow_redirects=True):
        requested.append(url)
        return _RedirectingResponse('http://169.254.169.254/latest/meta-data/')

    original_get = utils.requests.get
    utils.requests.get = _fake_get
    try:
        utils._download_public_url('http://public.example.com/doc.pdf', headers={})
    except ValueError as e:
        assert 'non-public' in str(e), f'redirect was rejected for the wrong reason: {e}'
    else:
        raise AssertionError('a redirect to the metadata endpoint should have been rejected')
    finally:
        utils.requests.get = original_get

    # The redirect target must never be fetched.
    assert requested == ['http://public.example.com/doc.pdf'], requested


if __name__ == '__main__':
    test_internal_urls_are_rejected()
    test_internal_urls_are_allowed_when_opted_in()
    test_redirect_to_internal_address_is_rejected()
