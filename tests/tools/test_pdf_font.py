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

import unittest

from pdfminer.layout import LTChar, LTTextBoxHorizontal, LTTextLineHorizontal
from pdfminer.pdfcolor import PREDEFINED_COLORSPACE
from pdfminer.pdffont import PDFType1Font
from pdfminer.pdfinterp import PDFGraphicState, PDFResourceManager
from pdfminer.psparser import LIT

from qwen_agent.tools.simple_doc_parser import get_font


def make_text_box(lines):
    box = LTTextBoxHorizontal()
    for spans in lines:
        line = LTTextLineHorizontal(word_margin=0.1)
        for font_name, font_size, count in spans:
            font = PDFType1Font(PDFResourceManager(), {'BaseFont': LIT(font_name)})
            for _ in range(count):
                line.add(
                    LTChar((1, 0, 0, 1, 0, 0), font, font_size, 1, 0, 'x', font.char_width(ord('x')),
                           font.char_disp(ord('x')), PREDEFINED_COLORSPACE['DeviceGray'], PDFGraphicState()))
        box.add(line)
    return box


class TestPDFFont(unittest.TestCase):

    def test_most_common_font_counts_repeated_characters(self):
        # Both cases have the same distinct fonts but opposite majorities.
        for spans, expected in [
            ([('Helvetica', 12, 5), ('Times-Roman', 18, 1)], ('Helvetica', 12)),
            ([('Helvetica', 12, 1), ('Times-Roman', 18, 5)], ('Times-Roman', 18)),
        ]:
            with self.subTest(expected=expected):
                self.assertEqual(get_font(make_text_box([spans])), expected)

    def test_most_common_font_counts_across_lines(self):
        box = make_text_box([
            [('Helvetica', 12, 2)],
            [('Helvetica', 12, 2)],
            [('Times-Roman', 18, 3)],
        ])
        self.assertEqual(get_font(box), ('Helvetica', 12))

    def test_empty_text_box_has_no_font(self):
        self.assertEqual(get_font(LTTextBoxHorizontal()), [])
