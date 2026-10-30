import json
from threading import Lock

import pytest

from benchmark.deepplanning.travelplanning.evaluation.constraints_commonsense import (calculate_dimension_scores,
                                                                                      check_attraction_necessity,
                                                                                      eval_commonsense,
                                                                                      get_all_check_names)
from benchmark.deepplanning.travelplanning.evaluation.eval_converted import (calculate_weighted_score,
                                                                             process_single_evaluation)


def attraction(start='06:08', end='10:08', **fields):
    return {'type': 'attraction', 'start_time': start, 'end_time': end, 'details': {'name': 'Museum'}, **fields}


def day(activities):
    return {'current_city': 'Beijing', 'activities': activities}


@pytest.mark.parametrize('start,end', [('06:08', '10:08'), ('08:01', '12:01'), ('10:03', '14:03'), ('20:08', '00:08')])
@pytest.mark.parametrize('use_time_slot', [False, True])
def test_exact_four_hours_satisfy_attraction_necessity(start, end, use_time_slot):
    activity = attraction(start, end)
    if use_time_slot:
        activity.pop('start_time')
        activity.pop('end_time')
        activity['time_slot'] = f'{start}-{end}'
    assert check_attraction_necessity([day([activity])], {'org': 'Beijing'}) == (True, None)


def test_travel_and_visit_minutes_sum_to_four_hours():
    activities = [
        {
            'type': 'travel_city',
            'start_time': '08:00',
            'end_time': '09:12',
            'details': {
                'from': 'Hotel',
                'to': 'Museum'
            }
        },
        attraction('09:12', '12:00'),
    ]
    assert check_attraction_necessity([day(activities)], {'org': 'Beijing'}) == (True, None)


@pytest.mark.parametrize('start,end', [('06:08', '10:07'), ('20:08', '00:07'), ('08:00', '08:00'), ('bad', '10:08'),
                                       ('', '')])
def test_insufficient_or_invalid_duration_is_rejected(start, end):
    passed, reason = check_attraction_necessity([day([attraction(start, end)])], {'org': 'Beijing'})
    assert passed is False
    assert 'requires attraction-related duration' in reason


def test_two_attractions_remain_an_alternative_to_four_hours():
    activities = [attraction('08:00', '08:30'), attraction('09:00', '09:30')]
    assert check_attraction_necessity([day(activities)], {'org': 'Beijing'}) == (True, None)


def test_travel_unrelated_to_attraction_is_not_counted():
    activities = [
        attraction('08:00', '09:00'),
        {
            'type': 'travel_city',
            'start_time': '09:00',
            'end_time': '12:00',
            'details': {
                'from': 'Hotel',
                'to': 'Airport'
            }
        },
    ]
    assert check_attraction_necessity([day(activities)], {'org': 'Beijing'})[0] is False


def test_missing_origin_remains_an_error():
    assert check_attraction_necessity([day([attraction()])],
                                      {}) == (False, 'Missing org info, cannot determine attraction necessity')


@pytest.mark.parametrize('end,expected', [('10:08', 1.0), ('10:07', 0.0)])
def test_native_evaluation_persists_correct_itinerary_score(tmp_path, end, expected):
    database = tmp_path / 'database'
    (database / 'id_0').mkdir(parents=True)
    output = tmp_path / 'scores'
    output.mkdir()
    plan_file = tmp_path / 'id_0_converted.json'
    activities = [
        attraction(end=end),
        {
            'type': 'meal',
            'start_time': '12:00',
            'end_time': '13:00',
            'details': {
                'name': 'Lunch'
            }
        },
        {
            'type': 'meal',
            'start_time': '18:00',
            'end_time': '19:00',
            'details': {
                'name': 'Dinner'
            }
        },
    ]
    plan_file.write_text(json.dumps({'daily_plans': [day(activities)]}), encoding='utf-8')
    samples = [{'id': 0, 'meta_info': {'org': 'Beijing', 'days': 1}}]
    process_single_evaluation(plan_file, samples, output, database, Lock())
    saved = json.loads((output / 'id_0_score.json').read_text(encoding='utf-8'))
    assert saved['commonsense_dimension_scores']['Itinerary Structure'] == expected
    detail = saved['commonsense_dimension_details']['Itinerary Structure']
    assert detail['total'] == 4
    assert detail['passed'] == 3 + int(expected)
    assert detail['weighted_score'] == expected * 0.125


def test_missing_itinerary_still_fails_all_evaluator_checks():
    result = eval_commonsense({}, {'org': 'Beijing'})
    assert result['essential_attraction_coverage'] == (False, 'Missing daily_plans')
    assert all(value == (False, 'Missing daily_plans') for value in result.values())
    assert calculate_weighted_score(result)['total_weighted_score'] == 0.0


def test_score_aggregation_retains_dimension_veto():
    results = {name: (True, None) for name in get_all_check_names()}
    assert calculate_weighted_score(results)['total_weighted_score'] == 1.0
    results['essential_attraction_coverage'] = (False, 'Insufficient duration')
    for score in [calculate_weighted_score(results), calculate_dimension_scores(results)]:
        assert score['total_weighted_score'] == 0.875
        assert score['dimension_scores']['Itinerary Structure'] == 0.0
