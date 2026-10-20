"""Checks on the saved evidence: each claim the video makes, against what the lab recorded. Skips when the evidence
is missing (fresh clone before a paid run). Expectations come from the prompt caching docs; a failure here means
the lab disagrees with the docs, and the video must say what the lab saw."""
import glob, json, os
import pytest
from lab import cc_report, usage as u

E = '/lab/evidence'
CC = f'{E}/claude-code'


def turn(name):
    f = f'{CC}/{name}.jsonl'
    if not os.path.exists(f):
        pytest.skip(f'no evidence {name}')
    t = cc_report.parse_turn(open(f, encoding='utf8').read())
    assert t['requests'], f'{name}: no API request recorded'
    return t['requests'][0]['usage']


def api(name):
    f = f'{E}/api/{name}.json'
    if not os.path.exists(f):
        pytest.skip(f'no evidence {name}')
    return json.load(open(f))['usage']


def reads(us):
    return us.get('cache_read_input_tokens') or 0


def test_second_turn_reads_the_cache():
    assert reads(turn('c02-same-again')) > 10_000


def test_editing_claude_md_mid_session_keeps_the_cache():
    us = turn('c03-after-claude-md-edit')
    assert reads(us) > 10_000 and (us.get('cache_creation_input_tokens') or 0) < 1_000


def test_switching_model_reads_nothing_from_the_cache():
    assert reads(turn('c04-model-switched')) == 0


def test_switching_back_within_five_minutes_reads_the_old_cache():
    assert reads(turn('c05-model-switched-back')) > 10_000


def test_mcp_server_added_or_removed_keeps_the_cache_with_tool_search_on():
    assert reads(turn('c06-mcp-server-added')) > 10_000
    assert reads(turn('c07-mcp-server-removed')) > 10_000


def test_mcp_server_added_with_tool_search_off_is_a_full_miss():
    assert reads(turn('c09-toolsearch-off-again')) > 10_000      # warm before the change
    assert reads(turn('c10-toolsearch-off-mcp-added')) == 0


def test_new_session_in_the_same_folder_reads_most_of_the_prefix():
    assert reads(turn('c11-new-session-same-dir')) > 10_000


def test_one_hour_setting_writes_one_hour_entries():
    us = turn('c12-1h-first')
    assert (us.get('cache_creation') or {}).get('ephemeral_1h_input_tokens', 0) > 0


def test_five_minute_cache_is_gone_after_six_minutes():
    # Measured 19 Oct (the first version of this test expected under half of c13's read, and failed): after 6 idle
    # minutes the session's own part was written again, but 11,352 tokens (exactly what turn 1 found cached) were still
    # read. Why that part survived is not observed. The raw API run (a8, a prompt only our script used) shows 0.
    c14, c01, c13 = turn('c14-after-6-minutes'), turn('c01-first-turn'), turn('c13-before-wait')
    assert reads(c14) <= reads(c01)                                  # nothing of this session's own part survived
    assert c14['cache_creation_input_tokens'] > 20 * c13['cache_creation_input_tokens']


def test_one_hour_cache_survives_six_minutes():
    assert reads(turn('c15-1h-after-6-minutes')) > 10_000


def test_api_layer_rule():
    assert reads(api('a2-same-again')) > 0
    assert reads(api('a3-tool-description-changed')) == 0                 # tools: everything after is re-read
    a4c = api('a4c-tool-choice-changed')
    assert reads(a4c) == reads(api('a2-same-again')) and a4c['cache_creation_input_tokens'] > 0   # only messages rewritten


def test_api_below_minimum_is_uncached_without_error():
    assert u.classify(api('a5-below-minimum')) == 'uncached'


def test_api_ttl_after_six_minutes():
    assert reads(api('a8-5m-after-6-minutes')) == 0
    assert reads(api('a9-1h-after-6-minutes')) > 0


def test_no_api_key_in_any_evidence_file():
    for f in glob.glob(f'{E}/**/*', recursive=True):
        if os.path.isfile(f):
            assert 'sk-ant-' not in open(f, encoding='utf8', errors='ignore').read(), f


def test_in_session_claude_md_edit_keeps_the_cache_and_does_not_apply():
    # one running claude process (stream-json in), CLAUDE.md edited between its two messages (claude-run/insession.py)
    f = f'{CC}/insession.jsonl'
    if not os.path.exists(f):
        pytest.skip('no in-session evidence')
    t = cc_report.parse_turn(open(f, encoding='utf8').read())
    second = t['requests'][-1]
    assert reads(second['usage']) > 15_000 and second['usage']['cache_creation_input_tokens'] < 1_000
    assert second['miss_reason'] is None
    results = [json.loads(l).get('result', '') for l in open(f, encoding='utf8') if '"type":"result"' in l]
    assert 'Prefer small commits' not in results[-1] and 'Keep answers short' in results[-1]
