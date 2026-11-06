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

from qwen_server.utils import read_history, save_history


def test_history_does_not_collide_for_urls_with_same_basename(tmp_path):
    history_dir = str(tmp_path)
    url_a = 'https://a.example.com/index.html'
    url_b = 'https://b.example.com/index.html'
    history_a = [[url_a, 'page A']]
    history_b = [[url_b, 'page B']]

    save_history(history_a, url_a, history_dir)
    save_history(history_b, url_b, history_dir)

    assert read_history(url_a, history_dir) == history_a
    assert read_history(url_b, history_dir) == history_b
