"""Manual route API smoke check. Creates and closes only its own test tour."""
import json
import argparse
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-version', default='1.2.6')
args = parser.parse_args()
base = 'http://127.0.0.1:18000/api/v1'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
headers, sid = {}, None
report = dict(simulated=False, phone_verified=False, checks=[])


def call(path, method='GET', data=None):
    body = json.dumps(data).encode() if data is not None else b'' if method in ('POST', 'PUT') else None
    request = urllib.request.Request(base + path, data=body, method=method,
                                    headers={'Content-Type': 'application/json', **headers})
    with opener.open(request, timeout=30) as response:
        return json.load(response)


try:
    for ids in ([12, 11, 9, 3], [12, 9, 11, 3]):
        overview = call('/tour-experience/route-preview', 'POST', dict(spot_ids=ids, pace='standard'))['data']
        assert [s['spot_id'] for s in overview['stops']] == ids and overview['complete']
        report['checks'].append(dict(route_order=ids, total_minutes=overview['total_minutes'],
                                     walking_meters=overview['walking_meters'],
                                     real_road_geometry=any(leg.get('geometry') for leg in overview['legs'])))
    params = dict(name='App route adjustment verification', guide_id=2, spot_ids='[12,11,9,3]',
                  planning=json.dumps(dict(preferences=['photography'], time_budget_minutes=180, pace='standard')))
    created = call('/tour-session/visitor-create?' + urllib.parse.urlencode(params), 'POST')['data']
    sid, headers = created['session_id'], {'X-Tour-Access': created['avatar_access_token']}
    call(f'/tour-session/start/{sid}', 'PUT')
    before = call(f'/tour-session/live-info/{sid}')['data']
    template = dict(remaining_minutes=120, pace='standard', end_area='auto', reserve_minutes=0, scenario='time',
                    strategy='highlights', required_spot_ids=[], excluded_spot_ids=[], avoid_steps=False, allow_reorder=True)
    plans = {}
    for scenario, patch in [('time', {}), ('less_walking', dict(scenario='less_walking', strategy='shortest')),
                            ('skip', dict(scenario='skip', excluded_spot_ids=[11])),
                            ('exit', dict(scenario='exit', end_area='east'))]:
        plan = call(f'/tour-session/{sid}/replan/preview', 'POST', {**template, **patch})['data']
        plans[scenario] = plan
        assert plan['feasible'] and plan['current_spot_id'] == before['current_spot_info']['spot_id']
        report['checks'].append(dict(scenario=scenario, feasible=True, total_minutes=plan['totals']['total_minutes'],
                                     next_ids=[s['spot_id'] for s in plan['next_spots']]))
    assert call(f'/tour-session/live-info/{sid}')['data']['visitor_preferences'] == before['visitor_preferences']
    report['checks'].append(dict(preview_leaves_live_route_unchanged=True))
    rejected = call(f'/tour-session/{sid}/replan/preview', 'POST',
                    {**template, 'scenario': 'exit', 'end_area': 'east', 'remaining_minutes': 1})['data']
    assert not rejected['feasible'] and not rejected['proposal_token']
    report['checks'].append(dict(impossible_budget_has_no_apply_token=True))
    plan = plans['skip']
    applied = call(f'/tour-session/{sid}/replan/apply', 'POST', dict(proposal_token=plan['proposal_token']))['data']
    actual = call(f'/tour-session/live-info/{sid}')['data']
    ids = json.loads(actual['visitor_preferences'])['spot_ids']
    assert ids == applied['spot_ids'] and 11 not in ids
    assert actual['current_spot_info']['spot_id'] == before['current_spot_info']['spot_id']
    report['checks'].append(dict(apply_updates_live_route=ids, current_stop_preserved=True))
    try:
        call(f'/tour-session/{sid}/replan/apply', 'POST', dict(proposal_token=plan['proposal_token']))
        raise AssertionError('Stale token accepted')
    except urllib.error.HTTPError as error:
        assert error.code == 409
        report['checks'].append(dict(stale_proposal_rejected=409))
    report['passed'] = True
finally:
    if sid:
        report['test_tour_closed'] = call(f'/tour-session/end/{sid}', 'PUT').get('success')
    output = Path(__file__).resolve().parents[1] / ('unpackage/main-d31183c-' + args.output_version + '/real-route-check.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
