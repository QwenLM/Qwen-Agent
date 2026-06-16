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

from qwen_agent.utils.utils import is_image


def test_is_image_recognizes_real_extensions():
    assert is_image('photo.jpg')
    assert is_image('photo.jpeg')
    assert is_image('photo.png')
    assert is_image('photo.webp')
    # Case-insensitive and works for URLs.
    assert is_image('https://example.com/dir/IMG.PNG?token=abc')


def test_is_image_rejects_non_images():
    assert not is_image('document.pdf')
    assert not is_image('archive.zip')


def test_is_image_requires_extension_separator():
    # A trailing extension substring without a "." separator must not count as
    # an image, e.g. a path component literally named "png" or a file whose
    # name merely ends with the extension letters.
    assert not is_image('https://example.com/png')
    assert not is_image('backup_jpg')
    assert not is_image('mockpng')


if __name__ == '__main__':
    test_is_image_recognizes_real_extensions()
    test_is_image_rejects_non_images()
    test_is_image_requires_extension_separator()
