import pytest

from benchmark.deepplanning.travelplanning.evaluation.constraints_commonsense import check_attraction_necessity


@pytest.mark.parametrize('use_time_slot', [False, True])
@pytest.mark.parametrize('has_attraction', [False, True])
@pytest.mark.parametrize('direction,time,required', [
    ('arrival', '11:59', True),
    ('arrival', '12:00', False),
    ('arrival', '12:01', False),
    ('arrival', '14:00', False),
    ('departure', '15:59', False),
    ('departure', '16:00', False),
    ('departure', '16:01', True),
    ('departure', '18:00', True),
])
def test_attraction_requirement_messages_match_time_boundaries(direction, time, required, has_attraction,
                                                               use_time_slot):
    activities = [{'type': 'travel_intercity_public'}]
    if direction == 'arrival':
        day = {'current_city': 'from Shanghai to Hangzhou', 'activities': activities}
        days = [day]
        start, end = '07:00', time
        expected_message = 'Arrival time earlier than 12:00'
    else:
        days = [
            {
                'current_city': 'from Shanghai to Hangzhou',
                'activities': [{
                    'type': 'travel_intercity_public',
                    'time_slot': '14:00-15:00'
                }],
            },
            {
                'current_city': 'from Hangzhou to Shanghai',
                'activities': activities
            },
        ]
        start, end = time, '20:00'
        expected_message = 'Departure time later than 16:00'
    if use_time_slot:
        activities[0]['time_slot'] = f'{start}-{end}'
    else:
        activities[0].update(start_time=start, end_time=end)
    if has_attraction:
        activities.append({'type': 'attraction', 'details': {'name': 'Lake'}})

    passed, reason = check_attraction_necessity(days, {'org': 'Shanghai'})

    if required and not has_attraction:
        assert passed is False
        assert expected_message in reason
        assert '14:00' not in reason
    else:
        assert (passed, reason) == (True, None)
