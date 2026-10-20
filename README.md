# claude-code-caching lab

Companion lab for "Claude Code Prompt Caching, Measured: What Breaks the Cache" (The Hidden Cost of AI Coding #9).
Everything runs in Docker; nothing is installed on the host.

## What it measures

1. **Claude Code, one real session, one change per turn** (`claude-run/cc.sh`, Claude Code 2.1.303, Claude Haiku 5.5,
   signed in with an API key, so the default cache lifetime is 5 minutes). Each turn is `claude -p "Reply with only the
   word: ok"` resumed on the same session, after changing one thing: edit CLAUDE.md, switch model, switch back, add an
   MCP server, remove it, turn tool search off, start a new session, wait 6 minutes, use the 1-hour lifetime. Every
   turn's `--output-format stream-json` is saved; `lab/cc_report.py` reads each API request's `usage`
   (`cache_read_input_tokens`, `cache_creation_input_tokens`, `input_tokens`).
2. **The Messages API directly** (`lab/api_experiments.py`, Claude Haiku 5.5): a cold write, a read, a changed tool
   description, a changed `tool_choice` with two breakpoints (system and messages), a prompt under the 512-token minimum,
   and 5-minute vs 1-hour entries after 6 idle minutes.
3. **Arithmetic** (`lab/usage.py`): per-model prices and read multipliers from the pricing page (19 Oct 2026), and the
   break-even rule: a 5-minute write pays off after 1 read, a 1-hour write after 2.

## What we saw (19 Oct 2026, `evidence/`)

| Change before the turn | Cache read | Cache write | Verdict |
|---|---:|---:|---|
| Edit CLAUDE.md, same running process (`insession.jsonl`) | 17,478 | 184 | kept (and the edit does not apply until /clear, /compact or a restart) |
| Switch model (c04) | 0 | 14,086 | broken: each model has its own cache |
| Add an MCP server, tool search on (c06) | 18,580 | 286 | kept |
| Add an MCP server, tool search off (c10) | 0 | 33,846 | broken: tools are the bottom of the prompt |
| Wait 6 minutes on an API key, 5-minute lifetime (c14) | 11,352 | 7,918 | the session's own part expired |
| Messages API, prompt under the 512-token minimum (a5) | 0 | 0 | nothing cached, no error |

Full per-turn numbers: `evidence/cc-summary.json`, `evidence/cc-run.log`, `evidence/api-run.log`.

## Run

Needs Docker and bash (Git Bash works on Windows).

```
./run.sh test                        # unit tests (offline) + checks on the saved evidence; no key, no cost
ANTHROPIC_API_KEY=... ./run.sh api        # paid, about $0.01
ANTHROPIC_API_KEY=... ./run.sh cc         # paid, about $0.05; refuses to overwrite saved evidence
ANTHROPIC_API_KEY=... ./run.sh insession  # paid, about $0.01; one running process, CLAUDE.md edited between messages
```

The key is passed into the container as an environment variable and never written to disk. Each Claude Code turn runs
with `--max-budget-usd 0.50`; the API script stops at $2. After every paid run, `lab/scrub.py` rewrites the new
evidence so host paths, API keys and account fields (email, organization, account ids) never reach a commit; numbers
are never changed. To rerun `cc` or `insession`, move the saved evidence out of `evidence/claude-code/` first.

## Files

- `lab/usage.py` hit/miss classification, hit ratio, input cost, break-even (pure, tested).
- `lab/cc_report.py` stream-json to per-request usage; `evidence/cc-summary.json`.
- `lab/api_experiments.py` API experiments; `evidence/api/*.json` (usage, request id, timing).
- `claude-run/cc.sh` the Claude Code session; `evidence/claude-code/c*.jsonl`.
- `claude-run/insession.py` one running Claude Code process, CLAUDE.md edited between two messages; `evidence/claude-code/insession.jsonl`.
- `lab/scrub.py` removes host paths, keys and account fields from run logs (tested; run.sh calls it after paid runs).
- `make_primer.py` optional: writes the video script JSON from the evidence (for the channel's video engine, not
  needed for the lab). `python make_primer.py [output dir]`.
- `tests/` unit tests (red-phase.log, green-phase.log) and evidence tests.

## License

Apache-2.0, see `LICENSE`.
