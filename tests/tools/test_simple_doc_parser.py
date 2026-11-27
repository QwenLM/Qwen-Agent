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

import pytest
from qwen_agent.tools import SimpleDocParser


def test_simple_doc_parser():
    tool = SimpleDocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


if __name__ == '__main__':
    test_simple_doc_parser()


@pytest.mark.parametrize('fail_extraction', [False, True])
def test_parse_pdf_closes_document(tmp_path, monkeypatch, fail_extraction):
    import pdfminer.high_level
    import pdfplumber
    from qwen_agent.tools.simple_doc_parser import parse_pdf
    from reportlab.pdfgen import canvas

    path = tmp_path / 'lesson.pdf'
    pdf = canvas.Canvas(str(path))
    pdf.drawString(50, 700, 'Lesson experiment')
    pdf.save()
    opened = []
    real_open = pdfplumber.open

    def track_open(*args, **kwargs):
        document = real_open(*args, **kwargs)
        opened.append(document)
        return document

    def fail(*args, **kwargs):
        raise RuntimeError('layout failure')

    monkeypatch.setattr(pdfplumber, 'open', track_open)
    if fail_extraction:
        monkeypatch.setattr(pdfminer.high_level, 'extract_pages', fail)
    try:
        if fail_extraction:
            with pytest.raises(RuntimeError, match='layout failure'):
                parse_pdf(str(path))
        else:
            result = parse_pdf(str(path))
            assert 'Lesson experiment' in result[0]['content'][0]['text']
        assert len(opened) == 1
        assert opened[0].stream.closed
    finally:
        for document in opened:
            document.close()
