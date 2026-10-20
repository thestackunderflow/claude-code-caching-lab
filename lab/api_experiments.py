"""Messages API experiments on Claude Haiku 5.5 (paid, about a cent): what a cache write, a read, and each kind of miss
look like in the usage fields. Writes evidence/api/<name>.json (request, timing, usage, request id). Never logs the key.
Run inside the container: python -m lab.api_experiments [--skip-wait]"""
import json, os, sys, time
from datetime import datetime, timezone
import anthropic
from lab import usage as u

MODEL = 'claude-haiku-5-5'
OUT = '/lab/evidence/api'
CAP_USD = 2.0
client = anthropic.Anthropic()
spent = 0.0


def big_text(name):
    # a real, stable ~5k-token text: a Python standard library module inside the container
    import textwrap, inspect
    src = inspect.getsource(textwrap)
    return f'You are a careful code reviewer for the project "{name}". Reference material follows.\n\n' + src


TOOLS = [
    {'name': 'read_file', 'description': 'Read a file from the repository and return its text.',
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']}},
    {'name': 'run_tests', 'description': 'Run the test suite and return the summary line.',
     'input_schema': {'type': 'object', 'properties': {}}},
]


def call(name, system, tools=TOOLS, messages=None, tool_choice=None, note=''):
    global spent
    messages = messages or [{'role': 'user', 'content': 'Reply with only the word: ok'}]
    kw = dict(model=MODEL, max_tokens=20, system=system, tools=tools, messages=messages)
    if tool_choice:
        kw['tool_choice'] = tool_choice
    t0 = time.time()
    r = client.messages.with_raw_response.create(**kw)
    msg = r.parse()
    us = msg.usage.model_dump()
    cost = u.input_cost(MODEL, us) + (us.get('output_tokens') or 0) * 0.50 / 1e6
    spent += cost
    rec = {'name': name, 'note': note, 'model': MODEL, 'at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
           'seconds': round(time.time() - t0, 2), 'request_id': r.headers.get('request-id'), 'usage': us,
           'class': u.classify(us), 'hit_ratio': round(u.hit_ratio(us), 4), 'cost_usd': round(cost, 6),
           'tool_choice': tool_choice, 'tool_descriptions': [t['description'] for t in tools]}
    json.dump(rec, open(f'{OUT}/{name}.json', 'w'), indent=2)
    print(f"{name:28s} {rec['class']:8s} read={us.get('cache_read_input_tokens')} write={us.get('cache_creation_input_tokens')} "
          f"in={us.get('input_tokens')} ${cost:.6f}")
    if spent > CAP_USD:
        sys.exit(f'stopping: spent ${spent:.4f} over the ${CAP_USD} cap')
    return rec


def sys_block(text, ttl=None):
    cc = {'type': 'ephemeral'}
    if ttl:
        cc['ttl'] = ttl
    return [{'type': 'text', 'text': text, 'cache_control': cc}]


def main():
    os.makedirs(OUT, exist_ok=True)
    skip_wait = '--skip-wait' in sys.argv
    s5 = sys_block(big_text('caching-lab-5m'))
    call('a1-cold', s5, note='first request: the prefix is written to the cache')
    call('a2-same-again', s5, note='identical request seconds later: read from the cache')
    changed = [dict(TOOLS[0], description=TOOLS[0]['description'] + ' Paths are relative to the repo root.'), TOOLS[1]]
    call('a3-tool-description-changed', s5, tools=changed, note='one word added to one tool description')
    # two breakpoints (system, last user message) so the messages layer can be seen separately
    msgs = [{'role': 'user', 'content': [{'type': 'text', 'text': 'Here is the task log.\n' + ('step ok\n' * 400),
                                          'cache_control': {'type': 'ephemeral'}}]}]
    call('a4a-two-breakpoints-warm', s5, messages=msgs, tool_choice={'type': 'auto'}, note='warm both layers')
    call('a4b-two-breakpoints-again', s5, messages=msgs, tool_choice={'type': 'auto'}, note='same again: both read')
    call('a4c-tool-choice-changed', s5, messages=msgs, tool_choice={'type': 'any'},
         note='only tool_choice changed: docs say only the messages layer is invalidated')
    call('a5-below-minimum', sys_block('You are terse. Reply briefly.'), tools=[],
         note='a prompt shorter than the 512-token minimum for Haiku 5.5: no caching, no error')
    s1h = sys_block(big_text('caching-lab-1h'), ttl='1h')
    call('a6-warm-1h', s1h, note='a 1-hour cache write (2x)')
    call('a7-warm-5m', s5, note='refresh the 5-minute entry just before the wait')
    if skip_wait:
        return
    print('waiting 6 minutes ...', flush=True)
    time.sleep(360)
    call('a8-5m-after-6-minutes', s5, note='6 minutes idle: the 5-minute entry has expired')
    call('a9-1h-after-6-minutes', s1h, note='6 minutes idle: the 1-hour entry is still there')
    print(f'total ${spent:.6f}')


if __name__ == '__main__':
    main()
