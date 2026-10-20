"""Unit tests (no network) for lab/usage.py, written before the code (red, then green).
Run: ./run.sh test"""
import pytest
from lab import usage as u


def test_a_request_that_only_writes_is_a_miss():
    r = {'input_tokens': 20, 'cache_creation_input_tokens': 3000, 'cache_read_input_tokens': 0, 'output_tokens': 3}
    assert u.classify(r) == 'miss'


def test_a_request_that_reads_most_of_its_prefix_is_a_hit():
    r = {'input_tokens': 20, 'cache_creation_input_tokens': 40, 'cache_read_input_tokens': 3000, 'output_tokens': 3}
    assert u.classify(r) == 'hit'


def test_a_request_with_no_cache_activity_is_uncached():
    r = {'input_tokens': 300, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'output_tokens': 3}
    assert u.classify(r) == 'uncached'


def test_partial_read_with_a_large_rewrite_is_a_partial_miss():
    # e.g. tool_choice changed: the system part still reads, the messages part is rewritten
    r = {'input_tokens': 10, 'cache_creation_input_tokens': 1500, 'cache_read_input_tokens': 3000, 'output_tokens': 3}
    assert u.classify(r) == 'partial'


def test_hit_ratio_is_reads_over_all_input():
    r = {'input_tokens': 100, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 800}
    assert u.hit_ratio(r) == pytest.approx(0.8)


def test_total_input_is_the_sum_of_the_three_fields():
    # platform docs: total_input_tokens = cache_read + cache_creation + input_tokens
    assert u.total_input({'input_tokens': 1, 'cache_creation_input_tokens': 2, 'cache_read_input_tokens': 3}) == 6


def test_haiku_5_5_input_cost_uses_its_own_prices():
    r = {'input_tokens': 10_000, 'cache_creation_input_tokens': 10_000, 'cache_read_input_tokens': 10_000}
    # under the 100K tier: $0.10 input + $0.125 5m write + $0.01 read, per MTok (pricing page, 19 Oct 2026)
    assert u.input_cost('claude-haiku-5-5', r) == pytest.approx(10_000 * (0.10 + 0.125 + 0.01) / 1e6)


def test_haiku_5_5_over_100k_prompt_uses_the_long_tier():
    r = {'input_tokens': 0, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 200_000}
    assert u.input_cost('claude-haiku-5-5', r) == pytest.approx(200_000 * 0.05 / 1e6)


def test_one_hour_writes_are_priced_at_2x():
    r = {'input_tokens': 0, 'cache_creation_input_tokens': 1_000_000, 'cache_read_input_tokens': 0,
         'cache_creation': {'ephemeral_1h_input_tokens': 1_000_000, 'ephemeral_5m_input_tokens': 0}}
    assert u.input_cost('claude-haiku-4-5', r) == pytest.approx(2.00)


def test_read_multiplier_differs_by_model():
    assert u.read_multiplier('claude-haiku-5-5') == pytest.approx(0.10)
    assert u.read_multiplier('claude-opus-5-5') == pytest.approx(0.05)
    assert u.read_multiplier('claude-sonnet-5-5') == pytest.approx(0.05)
    assert u.read_multiplier('claude-fable-5-1') == pytest.approx(0.025)


def test_break_even_is_one_read_for_5m_and_two_for_1h():
    # a 5m write (1.25x) plus one read (0.1x) = 1.35x, less than 2x uncached
    assert u.reads_to_break_even(1.25, 0.10) == 1
    assert u.reads_to_break_even(2.00, 0.10) == 2


def test_episode_5_claim_of_1_5_reads_is_not_the_break_even():
    assert u.reads_to_break_even(1.25, 0.10) != 1.5
