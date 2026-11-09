import copy
import tempfile
import unittest
from pathlib import Path

from benchmark.deepplanning.travelplanning.evaluation.constraints_commonsense import (check_budget_accuracy,
                                                                                      eval_commonsense_with_dimensions)


class TravelBudgetTest(unittest.TestCase):

    def make_plan(self, total, cost=100):
        return {
            'budget_summary': {
                'total_estimated_budget': total
            },
            'daily_plans': [{
                'current_city':
                    'Test City',
                'activities': [{
                    'type': 'meal',
                    'time_slot': '12:00-13:00',
                    'details': {
                        'restaurant_name': 'Test Restaurant',
                        'cost': cost
                    }
                }]
            }]
        }

    def check_budget(self, total, cost=100):
        plan = self.make_plan(total, cost)
        original = copy.deepcopy(plan)
        result = check_budget_accuracy(plan, plan['daily_plans'], {'people_number': 1})
        self.assertEqual(plan, original)
        return result

    def test_negative_totals_fail(self):
        for total in (-1, -100, -0.01, '-1', '-100', '-0.01'):
            with self.subTest(total=total):
                passed, reason = self.check_budget(total)
                self.assertFalse(passed)
                self.assertIsNotNone(reason)

    def test_negative_total_with_no_cost_still_fails(self):
        self.assertFalse(self.check_budget(-1, cost=0)[0])

    def test_zero_and_positive_controls(self):
        for total, cost, expected in ((0, 0, True), (-0.0, 0, True), (0, 100, False), (100, 100, True),
                                      ('100', 100, True), (100, 110, True), (100, 111, False)):
            with self.subTest(total=total, cost=cost):
                self.assertEqual(self.check_budget(total, cost)[0], expected)

    def test_invalid_total_controls(self):
        for total in (None, 'not a number', float('nan'), float('inf'), float('-inf')):
            with self.subTest(total=total):
                self.assertFalse(self.check_budget(total)[0])

    def test_dimension_scoring_rejects_negative_total(self):
        plan = self.make_plan(-100)
        original = copy.deepcopy(plan)
        with tempfile.TemporaryDirectory() as directory:
            result = eval_commonsense_with_dimensions(plan, {'days': 1, 'people_number': 1}, Path(directory))
        self.assertFalse(result['check_results']['cost_calculation_correctness'][0])
        self.assertEqual(result['dimension_scores']['Cost Calculation Accuracy'], 0.0)
        self.assertEqual(result['dimension_details']['Cost Calculation Accuracy']['weighted_score'], 0.0)
        self.assertEqual(plan, original)


if __name__ == '__main__':
    unittest.main()
