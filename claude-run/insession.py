"""Inside the lab container, PAID (Claude Haiku 5.5, about a cent): ONE running Claude Code process (stream-json in and
out), CLAUDE.md edited between its two messages. Measures the cache and asks Claude which rules it was given, to see
whether the edit reached the running session. Writes /out/insession.jsonl (+ .at, .stderr).
Run: python /run/insession.py"""
import json, os, subprocess, time, uuid
from datetime import datetime, timezone

OUT = '/out'
os.makedirs('/work', exist_ok=True)
os.chdir('/work')
subprocess.run('git init -q && git config user.email lab@example.com && git config user.name lab', shell=True, check=True)
open('CLAUDE.md', 'w').write('# Project rules\n- Keep answers short.\n')
subprocess.run('git add -A && git commit -qm init', shell=True, check=True)
ASK = ('Without using any tool, quote every bullet in the project rules from CLAUDE.md that you were given, '
       'one per line, nothing else.')
cmd = ['claude', '-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose',
       '--model', 'claude-haiku-5-5', '--setting-sources', 'project,local', '--strict-mcp-config',
       '--mcp-config', '{"mcpServers":{}}', '--permission-mode', 'dontAsk', '--max-budget-usd', '0.30',
       '--session-id', str(uuid.uuid4())]
out = open(f'{OUT}/insession.jsonl', 'w')
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(f'{OUT}/insession.stderr', 'w'), text=True)


def send(text):
    p.stdin.write(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': text}}) + '\n')
    p.stdin.flush()
    for line in p.stdout:
        out.write(line)
        out.flush()
        if json.loads(line).get('type') == 'result':
            return


stamps = {}
stamps['m1'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
send(ASK)
with open('CLAUDE.md', 'a') as f:            # the edit, while the same process is still running
    f.write('- Prefer small commits.\n')
stamps['edited'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
time.sleep(2)
stamps['m2'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
send(ASK)
p.stdin.close()
p.wait(timeout=120)
json.dump(stamps, open(f'{OUT}/insession.at', 'w'))
print('done')
