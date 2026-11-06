# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestDeepPlanningAggregation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.project = self.root / 'deepplanning'
        self.project.mkdir()
        self.model_name = 'test-model'
        # Keep the complete CLI and its __file__-relative output paths temporary.
        source = Path(__file__).resolve().parents[2] / 'benchmark' / 'deepplanning' / 'aggregate_results.py'
        self.script = self.project / 'aggregate_results.py'
        shutil.copyfile(source, self.script)

    def write_travel_results(self, results_dir, zh_score, en_score):
        expected = {}
        for lang, score in [('zh', zh_score), ('en', en_score)]:
            summary = results_dir / f'{self.model_name}_{lang}' / 'evaluation' / 'evaluation_summary.json'
            summary.parent.mkdir(parents=True, exist_ok=True)
            metrics = {
                'composite_score': score,
                'case_acc': score,
                'commonsense_score': score,
                'personalized_score': score,
            }
            summary.write_text(json.dumps({
                'metrics': metrics,
                'total_test_samples': 4,
                'evaluation_success_count': 3,
            }),
                               encoding='utf-8')
            expected[lang] = dict(metrics, total_test_samples=4, evaluation_success_count=3)
        return expected

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, '-X', 'utf8',
             str(self.script), '--model_name', self.model_name, *args],
            cwd=self.project,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )

    def read_aggregate(self):
        output = self.project / 'aggregated_results' / f'{self.model_name}_aggregated.json'
        return json.loads(output.read_text(encoding='utf-8'))

    def assert_travel_results(self, aggregate, expected):
        travel = aggregate['domains']['travel']
        self.assertEqual(travel['language_details'], expected)
        self.assertEqual(travel['languages_completed'], ['zh', 'en'])
        self.assertEqual(travel['total_cases'], 8)
        self.assertEqual(travel['successful_cases'], 6)
        for metric in ['composite_score', 'case_acc', 'commonsense_score', 'personalized_score']:
            average = sum(value[metric] for value in expected.values()) / 2
            self.assertAlmostEqual(travel[metric], average)
            self.assertAlmostEqual(aggregate['overall'][f'travel_{metric}'], average)

    def test_custom_directory_overrides_stale_default_results(self):
        self.write_travel_results(self.project / 'travelplanning' / 'results', 0.1, 0.2)
        custom_dir = self.root / 'custom travel results'
        expected = self.write_travel_results(custom_dir, 0.8, 0.6)
        for relative in [False, True]:
            with self.subTest(relative=relative):
                directory = os.path.relpath(custom_dir, self.project) if relative else str(custom_dir)
                result = self.run_cli('--travel-output-dir', directory)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_travel_results(self.read_aggregate(), expected)

    def test_custom_directory_works_without_default_results(self):
        custom_dir = self.root / 'custom travel results'
        expected = self.write_travel_results(custom_dir, 0.8, 0.6)
        result = self.run_cli('--travel-output-dir', str(custom_dir))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_travel_results(self.read_aggregate(), expected)

    def test_default_directory_and_shopping_aggregation_are_preserved(self):
        expected = self.write_travel_results(self.project / 'travelplanning' / 'results', 0.25, 0.5)
        report = self.project / 'shoppingplanning' / 'result_report' / f'{self.model_name}_statistics.json'
        report.parent.mkdir(parents=True)
        report.write_text(json.dumps({
            'total': {
                'total_cases': 2,
                'successful_cases': 2,
                'successful_rate': 1.0,
                'match_rate': 0.5,
                'weighted_average_case_score': 0.75,
                'valid': True,
                'levels_completed': [1],
            },
        }),
                          encoding='utf-8')
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        aggregate = self.read_aggregate()
        self.assert_travel_results(aggregate, expected)
        self.assertEqual(aggregate['overall']['domains_completed'], ['shopping', 'travel'])
        self.assertEqual(aggregate['overall']['total_cases'], 10)
        self.assertAlmostEqual(aggregate['overall']['avg_acc'], (0.75 + 0.375) / 2)

    def test_missing_custom_directory_does_not_fall_back_to_default_results(self):
        self.write_travel_results(self.project / 'travelplanning' / 'results', 0.1, 0.2)
        result = self.run_cli('--travel-output-dir', str(self.root / 'missing'))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse((self.project / 'aggregated_results').exists())


if __name__ == '__main__':
    unittest.main()
