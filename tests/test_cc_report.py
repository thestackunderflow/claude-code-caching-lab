"""Unit tests (no network) for lab/cc_report.py: one Claude Code -p turn's stream-json -> its API requests' usage."""
import json
from lab import cc_report as r

LINES = [
    {'type': 'system', 'subtype': 'init', 'model': 'claude-haiku-5-5', 'claude_code_version': '2.1.303'},
    {'type': 'assistant', 'message': {'id': 'msg_1', 'model': 'claude-haiku-5-5', 'content': [{'type': 'text', 'text': 'ok'}],
     'usage': {'input_tokens': 3, 'cache_creation_input_tokens': 120, 'cache_read_input_tokens': 18000, 'output_tokens': 2}}},
    # the same message can be streamed in more than one event: count it once
    {'type': 'assistant', 'message': {'id': 'msg_1', 'model': 'claude-haiku-5-5', 'content': [{'type': 'text', 'text': 'ok'}],
     'usage': {'input_tokens': 3, 'cache_creation_input_tokens': 120, 'cache_read_input_tokens': 18000, 'output_tokens': 2}}},
    {'type': 'result', 'subtype': 'success', 'total_cost_usd': 0.0012, 'result': 'ok',
     'usage': {'input_tokens': 3, 'cache_creation_input_tokens': 120, 'cache_read_input_tokens': 18000, 'output_tokens': 2}},
]


def text():
    return '\n'.join(json.dumps(x) for x in LINES) + '\nnot json\n'


def test_one_request_per_message_id():
    t = r.parse_turn(text())
    assert len(t['requests']) == 1
    assert t['requests'][0]['usage']['cache_read_input_tokens'] == 18000


def test_turn_summary_has_model_version_cost_and_class():
    t = r.parse_turn(text())
    assert t['model'] == 'claude-haiku-5-5'
    assert t['version'] == '2.1.303'
    assert t['cost_usd'] == 0.0012
    assert t['class'] == 'hit'
    assert t['result'] == 'ok'


def test_a_turn_with_no_assistant_message_is_reported_not_crashed():
    t = r.parse_turn(json.dumps({'type': 'result', 'subtype': 'error_max_budget_usd', 'is_error': True}))
    assert t['requests'] == [] and t['class'] == 'none'


def test_session_cost_is_the_last_cumulative_value_not_a_sum():
    # total_cost_usd in a resumed -p turn is the session's running total (seen in the lab, 19 Oct)
    rows = [{'session': 's1', 'cost_usd': 0.001}, {'session': 's1', 'cost_usd': 0.003},
            {'session': 's2', 'cost_usd': 0.002}]
    assert r.total_cost(rows) == 0.005


def test_turn_records_its_session_id():
    lines = [{'type': 'system', 'subtype': 'init', 'session_id': 'abc', 'model': 'm', 'claude_code_version': 'v'}]
    assert r.parse_turn('\n'.join(json.dumps(x) for x in lines))['session'] == 'abc'


def test_turn_records_the_apis_own_cache_miss_reason():
    # Claude Code 2.1.303 responses carry diagnostics.cache_miss_reason (cache-diagnostics docs); null = nothing changed
    m = {'id': 'm1', 'usage': {'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 9},
         'diagnostics': {'cache_miss_reason': {'type': 'model_changed', 'cache_missed_input_tokens': 5}}}
    t = r.parse_turn(json.dumps({'type': 'assistant', 'message': m}))
    assert t['miss_reason'] == 'model_changed'
    m2 = dict(m, id='m2', diagnostics=None)
    assert r.parse_turn(json.dumps({'type': 'assistant', 'message': m2}))['miss_reason'] is None
