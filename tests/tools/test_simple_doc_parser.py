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

from qwen_agent.tools import SimpleDocParser


def test_simple_doc_parser():
    tool = SimpleDocParser()
    res = tool.call({'url': 'https://qianwen-res.oss-cn-beijing.aliyuncs.com/QWEN_TECHNICAL_REPORT.pdf'})
    print(res)


if __name__ == '__main__':
    test_simple_doc_parser()


def test_parse_ppt_reads_nested_groups_in_slide_order(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches
    from qwen_agent.tools.simple_doc_parser import parse_ppt

    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.shapes.add_textbox(0, 0, Inches(2), Inches(1)).text = 'Lesson opening'
    group = slide.shapes.add_group_shape()
    group.shapes.add_textbox(0, 0, Inches(2), Inches(1)).text = 'Photosynthesis'
    nested = group.shapes.add_group_shape()
    nested.shapes.add_textbox(0, 0, Inches(2), Inches(1)).text = 'Chloroplast experiment'
    table = slide.shapes.add_table(1, 1, 0, 0, Inches(2), Inches(1))
    table.table.cell(0, 0).text = 'Light intensity'
    group.element.append(table.element)
    slide.shapes.add_textbox(0, 0, Inches(2), Inches(1)).text = 'Lesson summary'
    deck.slides.add_slide(deck.slide_layouts[6])
    path = tmp_path / 'lesson.pptx'
    deck.save(path)

    assert parse_ppt(str(path)) == [
        {
            'page_num':
                1,
            'content': [
                {
                    'text': 'Lesson opening'
                },
                {
                    'text': 'Photosynthesis'
                },
                {
                    'text': 'Chloroplast experiment'
                },
                {
                    'table': '|Light intensity|'
                },
                {
                    'text': 'Lesson summary'
                },
            ]
        },
        {
            'page_num': 2,
            'content': []
        },
    ]

    tool = SimpleDocParser({'path': str(tmp_path / 'cache')})
    text = tool.call({'url': str(path)})
    assert text == 'Lesson opening\nPhotosynthesis\nChloroplast experiment\n|Light intensity|\nLesson summary'
    assert tool.call({'url': str(path)}) == text
