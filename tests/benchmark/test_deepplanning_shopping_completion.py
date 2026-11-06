# SPDX-License-Identifier: Apache-2.0

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestShoppingCompletion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.database = self.root / 'database'
        self.database.mkdir()
        self.output = self.root / 'reports'
        project = Path(__file__).resolve().parents[2]
        self.script = project / 'benchmark/deepplanning/shoppingplanning/evaluation/evaluation_pipeline.py'

    def run_evaluation(self, traces):
        for name, messages in traces.items():
            case = self.database / name
            case.mkdir()
            (case / 'cart.json').write_text(json.dumps({'items': [{'product_id': 'item-1'}]}), encoding='utf-8')
            (case / 'validation_cases.json').write_text(json.dumps({
                'ground_truth_products': [{
                    'product_id': 'item-1'
                }],
                'ground_truth_coupons': {},
            }),
                                                        encoding='utf-8')
            if messages is not None:
                (case / 'messages.json').write_text(json.dumps({'messages': messages}), encoding='utf-8')
        result = subprocess.run(
            [
                sys.executable, '-X', 'utf8', '-B',
                str(self.script), '--database_dir',
                str(self.database), '--output_dir',
                str(self.output)
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((self.output / 'summary_report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['overall_statistics']['total_cases'], len(traces))
        # Completion changes must not alter the independent cart match score.
        self.assertTrue(all(case['score'] == 1.0 and case['case_score'] == 1.0 for case in report['case_results']))
        return report

    def test_only_final_assistant_messages_complete_a_case(self):
        traces = {
            # ShoppingFnAgent saves the initial user turn before calling the provider.
            'case_initial_user': [{
                'role': 'system',
                'content': 'Shop'
            }, {
                'role': 'user',
                'content': 'Buy an item'
            }],
            'case_system': [{
                'role': 'system',
                'content': 'Shop'
            }],
            'case_followup_user': [{
                'role': 'assistant',
                'content': 'Done'
            }, {
                'role': 'user',
                'content': 'Continue'
            }],
            'case_tool': [{
                'role': 'tool',
                'content': 'Tool result'
            }],
            'case_pending_calls': [{
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call-1'
                }]
            }],
            'case_empty': [],
            'case_missing': None,
            'case_final': [{
                'role': 'assistant',
                'content': 'Done',
                'tool_calls': []
            }],
            'case_final_empty_content': [{
                'role': 'assistant',
                'content': '',
                'tool_calls': None
            }],
            'case_final_absent_content': [{
                'role': 'assistant'
            }],
        }
        report = self.run_evaluation(traces)
        expected = {name: name.startswith('case_final') for name in traces}
        self.assertEqual({case['case_name']: case['is_completed'] for case in report['case_results']}, expected)
        self.assertEqual(report['overall_statistics']['incomplete_cases'], 7)
        self.assertAlmostEqual(report['overall_statistics']['incomplete_rate'], 0.7)
        self.assertFalse(report['overall_statistics']['valid'])

    def test_exactly_ten_percent_incomplete_is_valid(self):
        traces = {f'case_{index}': [{'role': 'assistant', 'content': 'Done'}] for index in range(10)}
        traces['case_0'] = [{'role': 'user', 'content': 'Buy an item'}]
        report = self.run_evaluation(traces)
        self.assertEqual(report['overall_statistics']['incomplete_cases'], 1)
        self.assertAlmostEqual(report['overall_statistics']['incomplete_rate'], 0.1)
        self.assertTrue(report['overall_statistics']['valid'])

    def test_more_than_ten_percent_incomplete_is_invalid(self):
        traces = {f'case_{index}': [{'role': 'assistant', 'content': 'Done'}] for index in range(10)}
        traces['case_0'] = [{'role': 'user', 'content': 'Buy an item'}]
        traces['case_1'] = [{'role': 'system', 'content': 'Shop'}]
        report = self.run_evaluation(traces)
        self.assertEqual(report['overall_statistics']['incomplete_cases'], 2)
        self.assertAlmostEqual(report['overall_statistics']['incomplete_rate'], 0.2)
        self.assertFalse(report['overall_statistics']['valid'])


if __name__ == '__main__':
    unittest.main()
