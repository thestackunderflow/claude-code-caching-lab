"""Reading a response's usage fields: hit or miss, hit ratio, what the input cost, and the break-even arithmetic.
Prices (USD per million tokens) from https://platform.claude.com/docs/en/about-claude/pricing, read 19 Oct 2026.
Multipliers from https://platform.claude.com/docs/en/build-with-claude/prompt-caching, same date."""
import math

# base input price; read multiplier (footnotes: 0.05x Opus/Sonnet 5.5, 0.025x Fable/Mythos 5.1, else 0.1x)
PRICES = {
    'claude-haiku-5-5': {'input': 0.10, 'read': 0.10, 'long_over': 100_000, 'long_input': 0.50},
    'claude-haiku-4-5': {'input': 1.00, 'read': 0.10},
    'claude-sonnet-5-5': {'input': 2.00, 'read': 0.05},
    'claude-opus-5-5': {'input': 4.00, 'read': 0.05},
    'claude-fable-5-1': {'input': 10.00, 'read': 0.025},
}
WRITE_5M, WRITE_1H = 1.25, 2.00


def _f(r, k):
    return int(r.get(k) or 0)


def total_input(r):
    """total_input_tokens = cache_read + cache_creation + input_tokens (platform docs)."""
    return _f(r, 'input_tokens') + _f(r, 'cache_creation_input_tokens') + _f(r, 'cache_read_input_tokens')


def hit_ratio(r):
    t = total_input(r)
    return _f(r, 'cache_read_input_tokens') / t if t else 0.0


def classify(r):
    """'hit' (reads at least 90% of input), 'miss' (writes, reads nothing), 'partial' (reads some, rewrites a lot),
    'uncached' (neither: below the minimum length, or caching off)."""
    read, write = _f(r, 'cache_read_input_tokens'), _f(r, 'cache_creation_input_tokens')
    if read == 0 and write == 0:
        return 'uncached'
    if read == 0:
        return 'miss'
    return 'hit' if hit_ratio(r) >= 0.9 else 'partial'


def read_multiplier(model):
    return PRICES[model]['read']


def input_cost(model, r):
    """USD for the input side of one request. 1-hour writes cost 2x, 5-minute writes 1.25x."""
    p = PRICES[model]
    base = p['input']
    if 'long_over' in p and total_input(r) > p['long_over']:
        base = p['long_input']
    write = _f(r, 'cache_creation_input_tokens')
    cc = r.get('cache_creation') or {}
    w1h = int(cc.get('ephemeral_1h_input_tokens') or 0)
    w5m = write - w1h
    units = _f(r, 'input_tokens') + w5m * WRITE_5M + w1h * WRITE_1H + _f(r, 'cache_read_input_tokens') * p['read']
    return units * base / 1e6


def reads_to_break_even(write_mult, read_mult):
    """Smallest whole number of reuses n for which caching is cheaper: write + n*read < (n + 1) uncached."""
    n = (write_mult - 1) / (1 - read_mult)
    return math.floor(n) + 1
