"""One Claude Code -p turn (stream-json) -> the API requests it made and their cache usage. Also: a table over all turns.
Run inside the container: python -m lab.cc_report  (reads evidence/claude-code/*.jsonl, writes evidence/cc-summary.json)"""
import glob, json, os
from lab import usage as u


def parse_turn(text):
    requests, seen, out = [], set(), {'model': None, 'version': None, 'cost_usd': None, 'result': None}
    for line in text.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get('type') == 'system' and ev.get('subtype') == 'init':
            out['model'] = ev.get('model')
            out['version'] = ev.get('claude_code_version')
            out['session'] = ev.get('session_id')
        elif ev.get('type') == 'assistant':
            m = ev.get('message') or {}
            if m.get('id') in seen or 'usage' not in m:
                continue
            seen.add(m.get('id'))
            d = (m.get('diagnostics') or {}).get('cache_miss_reason') or {}
            requests.append({'id': m.get('id'), 'model': m.get('model'), 'usage': m['usage'], 'miss_reason': d.get('type')})
        elif ev.get('type') == 'result':
            out['cost_usd'] = ev.get('total_cost_usd')
            out['result'] = ev.get('result')
            out['subtype'] = ev.get('subtype')
    out['requests'] = requests
    out['class'] = u.classify(requests[0]['usage']) if requests else 'none'
    out['miss_reason'] = requests[0]['miss_reason'] if requests else None
    return out


def total_cost(rows):
    """total_cost_usd of a -p turn is the session's running total, so take each session's largest value."""
    last = {}
    for row in rows:
        last[row['session']] = max(last.get(row['session'], 0), row['cost_usd'] or 0)
    return round(sum(last.values()), 6)


def main(folder='/lab/evidence/claude-code'):
    rows = []
    for f in sorted(glob.glob(f'{folder}/c*.jsonl')):
        t = parse_turn(open(f, encoding='utf8').read())
        first = t['requests'][0]['usage'] if t['requests'] else {}
        at = f[:-6] + '.at'
        rows.append({'turn': os.path.basename(f)[:-6], 'session': t['session'], 'at': open(at).read().strip() if os.path.exists(at) else None,
                     'model': t['model'], 'version': t['version'], 'class': t['class'], 'requests': len(t['requests']),
                     'read': first.get('cache_read_input_tokens'), 'write': first.get('cache_creation_input_tokens'),
                     'input': first.get('input_tokens'), 'write_1h': (first.get('cache_creation') or {}).get('ephemeral_1h_input_tokens'),
                     'session_cost_so_far_usd': t['cost_usd'], 'cost_usd': t['cost_usd'], 'result': t['result'], 'miss_reason': t['miss_reason']})
    json.dump(rows, open('/lab/evidence/cc-summary.json', 'w'), indent=2)
    for r in rows:
        print(f"{r['turn']:32s} {r['class']:8s} read={r['read']} write={r['write']} in={r['input']} 1h={r['write_1h']} why={r['miss_reason']} ${r['cost_usd']}")
    print('total $%.4f (each session counted once)' % total_cost(rows))


if __name__ == '__main__':
    main()
