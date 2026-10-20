#!/usr/bin/env bash
# ./run.sh test | api | cc | insession   (api, cc and insession are paid, a few cents on Claude Haiku 5.5; need ANTHROPIC_API_KEY)
# After every paid run, lab/scrub.py removes host paths, keys and account fields from evidence/ before you commit it.
set -euo pipefail
cd "$(dirname "$0")"
docker build -q -t claude-code-caching-lab . >/dev/null
here=$(pwd -W 2>/dev/null || pwd)
scrub() { MSYS_NO_PATHCONV=1 docker run --rm -v "$here/evidence:/lab/evidence" claude-code-caching-lab python -m lab.scrub /lab/evidence; }
case "${1:-test}" in
  test) MSYS_NO_PATHCONV=1 docker run --rm -v "$here/evidence:/lab/evidence:ro" claude-code-caching-lab python -m pytest -q tests ;;
  api)  : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY}"
        MSYS_NO_PATHCONV=1 docker run --rm -e ANTHROPIC_API_KEY -v "$here/evidence:/lab/evidence" claude-code-caching-lab \
          python -m lab.api_experiments
        scrub ;;
  cc)   : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY}"
        [ -e evidence/claude-code/c01-first-turn.jsonl ] && { echo "refusing: evidence exists (never overwritten)"; exit 1; }
        MSYS_NO_PATHCONV=1 docker run --rm -e ANTHROPIC_API_KEY -v "$here/claude-run:/run:ro" \
          -v "$here/evidence/claude-code:/out" claude-code-caching-lab bash /run/cc.sh
        MSYS_NO_PATHCONV=1 docker run --rm -v "$here/evidence:/lab/evidence" claude-code-caching-lab python -m lab.cc_report
        scrub ;;
  insession) : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY}"
        [ -e evidence/claude-code/insession.jsonl ] && { echo "refusing: evidence exists (never overwritten)"; exit 1; }
        MSYS_NO_PATHCONV=1 docker run --rm -e ANTHROPIC_API_KEY -v "$here/claude-run:/run:ro" \
          -v "$here/evidence/claude-code:/out" claude-code-caching-lab python /run/insession.py
        scrub ;;
  *) echo "usage: see the first line"; exit 2 ;;
esac
