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

import pytest

from qwen_agent.utils.utils import get_basename_from_url


@pytest.mark.parametrize('path_or_url, expected', [
    ('/mnt/a/b/c', 'c'),
    ('https://github.com/here?k=v', 'here'),
    ('https://github.com/', 'github.com'),
    ('https://github.com', 'github.com'),
    ('https://github.com/?k=v', 'github.com'),
    ('https://github.com/#frag', 'github.com'),
    ('https://github.com/?k=v#frag', 'github.com'),
    ('', ''),
    ('/', ''),
    ('C:\\a\\b\\c', 'c'),
])
def test_get_basename_from_url(path_or_url, expected):
    assert get_basename_from_url(path_or_url) == expected


def test_get_basename_from_url_never_returns_an_absolute_path():
    # Callers join the result onto a directory, so an absolute basename would
    # silently discard that directory.
    for path_or_url in ('', '/', 'https://github.com/', 'https://github.com/?k=v'):
        basename = get_basename_from_url(path_or_url)
        assert not os.path.isabs(basename)
        assert os.path.join('/safe/root/hash', basename).startswith('/safe/root/hash')
