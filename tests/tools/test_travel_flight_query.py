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

import csv
import json
import socket

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):

    def reject_network(*args, **kwargs):
        raise AssertionError('Travel query tests must not access the network')

    monkeypatch.setattr(socket.socket, 'connect', reject_network)
    monkeypatch.setattr(socket.socket, 'connect_ex', reject_network)


@pytest.fixture
def flight_tool(tmp_path):
    from benchmark.deepplanning.travelplanning.tools.flight_query_tool import FlightQueryTool

    row = {
        'origin_city': 'Shanghai',
        'destination_city': 'Beijing',
        'dep_date': '2026-01-01',
        'seat_class': 'Economy',
        'route_index': '1',
        'segment_index': '1',
        'seat_status': '',
        'arr_station_code': 'PEK',
        'arr_station_name': 'Capital Airport',
        'dep_station_code': 'SHA',
        'dep_station_name': 'Hongqiao Airport',
        'duration': '120',
        'arr_datetime': '2026-01-01 10:00',
        'dep_datetime': '2026-01-01 08:00',
        'airline': 'Example Airline',
        'flight_no': 'EX123',
        'equip_size': 'Medium',
        'equip_type': 'A320',
        'manufacturer': 'Airbus',
        'price': '500',
    }
    path = tmp_path / 'flights.csv'
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)

    def make_tool(language):
        return FlightQueryTool({'database_path': str(path), 'language': language})

    return make_tool


@pytest.mark.parametrize('language', ['en', 'zh'])
@pytest.mark.parametrize('encode', [dict, json.dumps], ids=['dict', 'json'])
@pytest.mark.parametrize('override', [
    {
        'origin': 'Missing City'
    },
    {
        'depDate': '2026-01-02'
    },
    {
        'seatClassName': 'Business'
    },
],
                         ids=['route', 'date', 'seat'])
def test_flight_query_no_results(flight_tool, language, encode, override):
    tool = flight_tool(language)
    params = {'origin': 'Shanghai', 'destination': 'Beijing', 'depDate': '2026-01-01', **override}

    result = tool.call(encode(params))

    if language == 'en':
        expected = f"No flight information found from {params['origin']} to Beijing on {params['depDate']}"
    else:
        expected = f"未找到从 {params['origin']} 到 Beijing 在 {params['depDate']} 的航班信息"
    assert result == expected


@pytest.mark.parametrize('language', ['en', 'zh'])
@pytest.mark.parametrize('seat', ['', 'Economy'])
def test_flight_query_matching_result(flight_tool, language, seat):
    tool = flight_tool(language)
    params = {'origin': 'Shanghai', 'destination': 'Beijing', 'depDate': '2026-01-01'}
    if seat:
        params['seatClassName'] = seat

    result = json.loads(tool.call(params))

    segment = result[0]['Segment 1' if language == 'en' else '第1段']
    assert segment['marketingTransportNo'] == 'EX123'
    assert segment['seatClassName'] == 'Economy'
    assert segment['Remaining Seats' if language == 'en' else '剩余票数量'] == ('Available' if language == 'en' else '充足')
    assert result[0]['price'] == 500


@pytest.mark.parametrize('language,expected', [('en', 'No information found, please check input parameters'),
                                               ('zh', '未查询到信息，请检查输入参数')])
def test_flight_query_without_database(language, expected):
    from benchmark.deepplanning.travelplanning.tools.flight_query_tool import FlightQueryTool

    tool = FlightQueryTool({'language': language})
    assert tool.call({'origin': 'Shanghai', 'destination': 'Beijing', 'depDate': '2026-01-01'}) == expected
