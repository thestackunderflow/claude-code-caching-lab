#!/usr/bin/env bash
# Inside the lab container, PAID (Claude Haiku 5.5, a few cents): one real Claude Code session, resumed turn by turn
# with -p, changing one thing before each turn. Every turn's stream-json (per-request usage) goes to /out/cNN-*.jsonl.
# Auth: ANTHROPIC_API_KEY (so the default cache lifetime is 5 minutes). No user settings, no MCP unless a turn adds it.
set -uo pipefail
OUT=/out; mkdir -p $OUT /work && cd /work
git init -q && git config user.email lab@example.com && git config user.name lab
printf '# Project rules\n- Keep answers short.\n' > CLAUDE.md && git add -A && git commit -qm init
claude --version > $OUT/claude-version.txt
SID=$(python -c 'import uuid; print(uuid.uuid4())'); echo "$SID" > $OUT/session-id.txt
GIT='{"mcpServers":{"git":{"command":"/opt/mcpgit/bin/mcp-server-git","args":["--repository","/work"]}}}'
NONE='{"mcpServers":{}}'
base() { claude --setting-sources project,local --permission-mode dontAsk --output-format stream-json --verbose \
  --max-budget-usd 0.50 "$@" < /dev/null; }
turn() {  # turn <name> <model> <mcp-json> [extra env...]
  local name=$1 model=$2 mcp=$3; shift 3
  date -u +%FT%TZ > $OUT/$name.at
  env "$@" bash -c "$(declare -f base); base --model $model --mcp-config '$mcp' --strict-mcp-config $FLAG -p 'Reply with only the word: ok'" \
    > $OUT/$name.jsonl 2> $OUT/$name.stderr
}
FLAG="--session-id $SID"; turn c01-first-turn claude-haiku-5-5 "$NONE"
FLAG="--resume $SID"
turn c02-same-again claude-haiku-5-5 "$NONE"
printf -- '- Prefer small commits.\n' >> CLAUDE.md          # edit CLAUDE.md mid-session (not committed)
turn c03-after-claude-md-edit claude-haiku-5-5 "$NONE"
turn c04-model-switched claude-haiku-4-5 "$NONE"
turn c05-model-switched-back claude-haiku-5-5 "$NONE"
turn c06-mcp-server-added claude-haiku-5-5 "$GIT"                     # tool search on (default)
turn c07-mcp-server-removed claude-haiku-5-5 "$NONE"
# a second session with tool search off, so MCP tools load upfront
SID2=$(python -c 'import uuid; print(uuid.uuid4())'); echo "$SID2" > $OUT/session2-id.txt
FLAG="--session-id $SID2"; turn c08-toolsearch-off-first claude-haiku-5-5 "$NONE" ENABLE_TOOL_SEARCH=false
FLAG="--resume $SID2"
turn c09-toolsearch-off-again claude-haiku-5-5 "$NONE" ENABLE_TOOL_SEARCH=false
turn c10-toolsearch-off-mcp-added claude-haiku-5-5 "$GIT" ENABLE_TOOL_SEARCH=false
# a brand-new session in the same directory and git state
SID3=$(python -c 'import uuid; print(uuid.uuid4())'); echo "$SID3" > $OUT/session3-id.txt
FLAG="--session-id $SID3"; turn c11-new-session-same-dir claude-haiku-5-5 "$NONE"
# a session on the 1-hour lifetime, warmed now, read after the wait
SID4=$(python -c 'import uuid; print(uuid.uuid4())'); echo "$SID4" > $OUT/session4-id.txt
FLAG="--session-id $SID4"; turn c12-1h-first claude-haiku-5-5 "$NONE" CLAUDE_CODE_PROMPT_CACHE_TTL=1h
FLAG="--resume $SID"; turn c13-before-wait claude-haiku-5-5 "$NONE"
echo "waiting 6 minutes"; sleep 360
FLAG="--resume $SID"; turn c14-after-6-minutes claude-haiku-5-5 "$NONE"
FLAG="--resume $SID4"; turn c15-1h-after-6-minutes claude-haiku-5-5 "$NONE" CLAUDE_CODE_PROMPT_CACHE_TTL=1h
echo done
