"""Write the video script (mcp-canvas primer + Short) from the lab's saved evidence, so every on-screen number comes
from evidence/cc-summary.json, evidence/claude-code/insession.jsonl and evidence/api/*.json.
Revision 2 (19 Oct 2026), after script reviews. The output is JSON for the channel's video engine (not part of this
repo); you do not need it to run the lab or the tests.
Run: python make_primer.py [output dir]   (default: ./primer-out)"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'primer-out')
os.makedirs(OUT, exist_ok=True)
cc = {r['turn']: r for r in json.load(open(os.path.join(HERE, 'evidence', 'cc-summary.json'), encoding='utf8'))}
api = {f[:-5]: json.load(open(os.path.join(HERE, 'evidence', 'api', f), encoding='utf8'))
       for f in os.listdir(os.path.join(HERE, 'evidence', 'api')) if f.endswith('.json')}
# the in-session run: one claude process, CLAUDE.md edited between its two messages
ins, seen, ins_results = [], set(), []
for line in open(os.path.join(HERE, 'evidence', 'claude-code', 'insession.jsonl'), encoding='utf8'):
    e = json.loads(line)
    if e.get('type') == 'assistant' and e['message']['id'] not in seen:
        seen.add(e['message']['id']); ins.append(e['message']['usage'])
    if e.get('type') == 'result':
        ins_results.append(e.get('result', ''))
INS_READ, INS_WRITE = ins[-1]['cache_read_input_tokens'], ins[-1]['cache_creation_input_tokens']
assert 'Prefer small commits' not in ins_results[-1]


def n(x):
    return f'{x:,}'


def R(t):
    return n(cc[t]['read'] or 0)


def W(t):
    return n(cc[t]['write'] or 0)


def A(k, f):
    return n(api[k]['usage'].get(f) or 0)


assert cc['c04-model-switched']['miss_reason'] == 'model_changed'
assert cc['c10-toolsearch-off-mcp-added']['miss_reason'] == 'tools_changed'
assert cc['c14-after-6-minutes']['miss_reason'] is None
switch_cost = cc['c04-model-switched']['session_cost_so_far_usd'] - cc['c03-after-claude-md-edit']['session_cost_so_far_usd']
w04 = cc['c04-model-switched']['write']
warm45 = w04 * 0.10 / 1e6   # the same tokens read from a warm cache on Haiku 4.5 ($0.10/MTok): arithmetic, not measured
VER = cc['c01-first-turn']['version']

primer = {
    'id': 'claude-code-caching',
    'title': 'Claude Code Prompt Caching, Measured: What Breaks the Cache',
    'emphasis': 'teach', 'gates': 'f2', 'legibility': 'repair',
    'nodes': [
        {'id': 'you', 'label': 'You · the traveller'},
        {'id': 'cc', 'label': 'Claude Code · packs the bag'},
        {'id': 'api', 'label': 'Claude API · the check-in desk'},
        {'id': 'cache', 'label': 'Prompt cache · the desk remembers'},
    ],
    'edges': [
        {'id': 'e_send', 'from': 'you', 'to': 'cc', 'label': 'your message'},
        {'id': 'e_turn', 'from': 'cc', 'to': 'api', 'label': 'the whole bag, every turn'},
        {'id': 'e_look', 'from': 'api', 'to': 'cache', 'label': 'same bottom layers? skip them'},
    ],
    'intro': [{
        'id': 'hook', 'title': "What breaks Claude Code's prompt cache?",
        'subtitle': f'Claude Code {VER} · Claude Haiku 5.5 · measured 19 Oct 2026',
        'body': f'Edit CLAUDE.md mid-session: kept (reused {n(INS_READ)})\n'
                f'Switch model: broken (reused 0, re-sent {W("c04-model-switched")})\n'
                'Add an MCP server: kept, while tool search is on\n'
                f'Wait 6 minutes on an API key: session\'s part gone (rewrote {W("c14-after-6-minutes")})',
        'layout': 'left',
        'narration': [
            {'say': "Claude Code's prompt cache makes repeated tokens ten times cheaper on Haiku. We measured what breaks it."},
            {'say': f'Editing CLAUDE dot M D mid-session? Kept: the next message reused {n(INS_READ)} tokens.'},
            {'say': f'Switching the model? Broken: nothing reused, and all {W("c04-model-switched")} tokens were sent again.'},
            {'say': 'Adding an M C P server? Kept, as long as tool search is on.'},
            {'say': "A six minute pause, on an A P I key? This session's part was gone. To see why, picture a bag."},
        ]}],
    'chapters': [
        {'id': 'words', 'slide': {'title': '1 · The bag, packed in layers', 'body': 'Same bottom layers, cheaper trip',
                                  'layout': 'left', 'narration': [{'say': 'One picture explains all four.'}]},
         'beats': [
             {'id': 'b_bag', 'term': 'the whole bag, every turn', 'show': ['you', 'cc', 'api'], 'edges': ['e_send', 'e_turn'],
              'callout': 'Every turn, Claude Code sends everything again, and the desk charges for what it reads',
              'narration': "Picture a trip where you check a bag at a desk on every turn of the conversation, and the desk charges "
                           "for every token it has to unpack and read. The model remembers nothing between turns, so Claude Code "
                           "packs the whole bag again each time: its instructions, its tools, your CLAUDE dot M D, and every message "
                           "so far. It's the bag from episode eight; here we watch what it costs. So how could the second trip be "
                           "cheaper? It starts with how the bag is packed."},
             {'id': 'b_layers', 'term': 'the bag is packed in layers', 'show': ['cc', 'api'], 'edges': ['e_turn'],
              'panel': {'kind': 'terminal', 'lines': ['How Claude Code packs each request (docs)', '1 bottom: system prompt + tool definitions',
                                                       '2 middle: project context, CLAUDE.md', '3 top: the conversation, every turn'],
                        'highlight': [1]},
              'narration': "It packs in the same order every time. At the bottom, the system prompt and the tool definitions. In the "
                           "middle, project context like your CLAUDE dot M D. On top, the conversation. Only the top layer grows from "
                           "turn to turn. And that order is the whole trick, because of what the desk remembers."},
             {'id': 'b_cache', 'term': 'the desk remembers the bottom', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'callout': 'The desk checks from the bottom up. At the first difference, everything above is processed again',
              'narration': "That memory is the prompt cache. The desk checks your bag from the bottom up, comparing each item with a bag "
                           "it saw a few minutes ago. While everything matches, it skips the work. Engineers call that matching start "
                           "the prefix. At the first item that's different, it stops trusting the rest, and everything above that point "
                           "is processed again, at full price. Change the top: you lose almost nothing. Change the bottom: you lose the "
                           "whole bag. So what does a skip save?"},
             {'id': 'b_prices', 'term': 'a write, then cheap reads', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'panel': {'kind': 'terminal', 'lines': ['Cache prices vs normal input (docs, 19 Oct 2026)', 'write, 5-minute memory   1.25x',
                                                       'write, 1-hour memory     2x', 'read: Haiku 5.5, Haiku 4.5    0.1x',
                                                       'read: Opus 5.5, Sonnet 5.5     0.05x'],
                        'highlight': [3]},
              'narration': "The first time, the desk writes the bag into its memory, and that costs a little extra: one and a quarter "
                           "times the normal price for a five minute memory, double for a one hour memory. Every reuse after that is a "
                           "cache read, and reads are cheap: a tenth of the price on Haiku, and less on the bigger models. So when does it pay off?"},
             {'id': 'b_even', 'statement': ['1 READ PAYS FOR', 'A 5-MINUTE WRITE', 'A 1-HOUR WRITE NEEDS 2'],
              'narration': "A five minute write plus one read costs one point three five times the normal price, against two times for "
                           "sending it twice. So one reuse already pays. A one hour write needs two. Now, what does Claude Code actually do?"},
         ]},
        {'id': 'lab', 'slide': {'title': '2 · The lab', 'body': 'One session, one change per turn',
                                'layout': 'left', 'narration': [{'say': 'Here is how we measured it.'}]},
         'beats': [
             {'id': 'b_setup', 'term': 'one change per turn', 'show': ['you', 'cc'], 'edges': ['e_send'],
              'panel': {'kind': 'terminal', 'lines': [f'Claude Code {VER} · Claude Haiku 5.5 · API key', 'claude -p "Reply with only the word: ok"',
                                                       '  a fresh run per turn, resuming the same session',
                                                       'usage per request: cache read / cache write'], 'highlight': [1]},
              'narration': "We ran Claude Code on Claude Haiku five point five, signed in with an A P I key. Each turn is a fresh claude "
                           "dash p run that resumes the same session and asks for one word, and before each turn we change exactly one "
                           "thing. For every request, Claude Code reports two numbers: tokens read from the cache, and tokens written to "
                           "it. First, the baseline."},
             {'id': 'b_base', 'term': 'the first two turns', 'show': ['cc', 'api', 'cache'], 'edges': ['e_turn', 'e_look'],
              'panel': {'kind': 'terminal', 'lines': ['turn               cache read   cache write',
                                                       f'1 first turn       {R("c01-first-turn"):>10}   {W("c01-first-turn"):>10}',
                                                       f'2 same again       {R("c02-same-again"):>10}   {W("c02-same-again"):>10}',
                                                       "turn 2, API's reason: messages_changed"],
                        'highlight': [2]},
              'narration': f"Turn one already read {R('c01-first-turn')} tokens from the cache, before this session had sent anything. Our "
                           f"lab shows that it happened, not which earlier request wrote it. Turn two read {R('c02-same-again')} and wrote "
                           f"{W('c02-same-again')}, far more than a one-word exchange; the A P I's own diagnostic said an earlier message had "
                           "changed. After that, a normal turn wrote a few hundred tokens or less. Now let's start changing things."},
         ]},
        {'id': 'keeps', 'slide': {'title': '3 · Kept the cache', 'body': 'Three things that felt risky',
                                  'layout': 'left', 'narration': [{'say': 'First, three things that kept the cache.'}]},
         'beats': [
             {'id': 'b_claudemd', 'term': 'editing CLAUDE.md mid-session', 'show': ['you', 'cc'], 'edges': ['e_send'],
              'panel': {'kind': 'terminal', 'lines': ['one running session: edit CLAUDE.md between two messages',
                                                       f'next message: cache read {n(INS_READ)} · write {n(INS_WRITE)}',
                                                       'asked to quote its rules: "- Keep answers short."',
                                                       'the new rule was not there'], 'highlight': [1, 2]},
              'narration': f"We edited CLAUDE dot M D while one Claude Code session was running, between two messages. The next message "
                           f"read {n(INS_READ)} tokens from the cache and wrote just {n(INS_WRITE)}. Kept. Then we asked Claude to quote its "
                           "project rules: it quoted only the old one. The edit hadn't reached the running session; the docs say it loads "
                           "on slash clear, slash compact, or a restart. What about M C P servers?"},
             {'id': 'b_mcp', 'term': 'adding an MCP server', 'show': ['cc', 'api', 'cache'], 'edges': ['e_turn', 'e_look'],
              'panel': {'kind': 'terminal', 'lines': ['tool search on (the default)', f'MCP server added     read {R("c06-mcp-server-added")}',
                                                       f'MCP server removed   read {R("c07-mcp-server-removed")}'], 'highlight': [1, 2]},
              'narration': f"We added a git M C P server, then took it away. Both turns still reused the cache: {R('c06-mcp-server-added')} "
                           f"tokens, then {R('c07-mcp-server-removed')}. Why? Tool search, on by default. Without it, every tool's full "
                           "instructions are packed into the bottom layer. With it, Claude Code keeps the tool list it started with, and "
                           "fetches a new tool's instructions only when it needs them, on top of the bag. So the bottom doesn't move. Hold "
                           "on to that; we'll turn it off later. One more: starting over."},
             {'id': 'b_newsession', 'term': 'a new session, same folder', 'show': ['you', 'cc'], 'edges': ['e_send'],
              'callout': f'New session, same folder and git state: read {R("c11-new-session-same-dir")}, wrote {W("c11-new-session-same-dir")}',
              'narration': f"A brand new session, same folder, same project: most of its prompt matched. It read "
                           f"{R('c11-new-session-same-dir')} tokens from the cache and wrote {W('c11-new-session-same-dir')}. The docs say a "
                           "different folder, or a different git state, changes the start of the bag. So, what does break it?"},
         ]},
        {'id': 'breaks', 'slide': {'title': '4 · Broke the cache', 'body': 'Change the bottom, process everything again',
                                   'layout': 'left', 'narration': [{'say': 'Now, the ones that broke it.'}]},
         'beats': [
             {'id': 'b_switch', 'term': 'switching the model', 'show': ['cc', 'api', 'cache'], 'edges': ['e_turn', 'e_look'],
              'panel': {'kind': 'terminal', 'lines': ['switch to Claude Haiku 4.5 on the same session',
                                                       f'cache read 0 · cache write {W("c04-model-switched")}',
                                                       "API's reason: model_changed",
                                                       f'that turn: ${switch_cost:.4f} · warm Haiku 4.5: ~${warm45:.4f} (calc.)'],
                        'highlight': [1, 2]},
              'narration': f"We switched the session to Claude Haiku four point five. That turn reused nothing and wrote all "
                           f"{W('c04-model-switched')} tokens again; the A P I's own diagnostic said: model changed. Each model has its own "
                           "desk, one that has never seen your bag. That turn cost about 1.8 cents. Read from a warm cache, the same tokens "
                           "would have cost about 0.14 cents. And when we switched back?"},
             {'id': 'b_back', 'term': 'switching back', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'callout': f'Back on Haiku 5.5 seconds later: read {R("c05-model-switched-back")}. The old memory was still warm',
              'narration': f"Back on Haiku five point five, the next turn read {R('c05-model-switched-back')} tokens. The old memory was "
                           "still there, because we came back seconds later, well inside five minutes. Now the M C P server again, with "
                           "tool search turned off."},
             {'id': 'b_toolsearch', 'term': 'MCP with tool search off', 'show': ['cc', 'api', 'cache'], 'edges': ['e_turn', 'e_look'],
              'panel': {'kind': 'terminal', 'lines': ['ENABLE_TOOL_SEARCH=false (tools load upfront)',
                                                       f'same again        read  {R("c09-toolsearch-off-again")}',
                                                       f'MCP server added  read 0 · write {W("c10-toolsearch-off-mcp-added")}',
                                                       "API's reason: tools_changed"],
                        'highlight': [2, 3]},
              'narration': f"With tool search off, every tool's instructions sit in the bottom layer. Adding the same M C P server now "
                           f"read zero from the cache and wrote {W('c10-toolsearch-off-mcp-added')} tokens. New tools at the bottom of the "
                           "bag, so everything above them is written again. The A P I's diagnostic named it: tools changed. One more thing "
                           "breaks it, and you can't see it: time."},
             {'id': 'b_pitch', 'statement': ['THE HIDDEN COST', 'OF AI CODING'],
              'narration': "Quick pause. This is The Hidden Cost of A I Coding: episode eight was the bag getting too heavy, this one is "
                           "the bag getting expensive. Subscribe, so you get the next one. Now, the clock."},
         ]},
        {'id': 'time', 'slide': {'title': '5 · The clock', 'body': '5 minutes, or 1 hour',
                                 'layout': 'left', 'narration': [{'say': 'The desk only remembers for so long.'}]},
         'beats': [
             {'id': 'b_wait', 'term': 'six minutes idle', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'panel': {'kind': 'terminal', 'lines': ['6 minutes idle, 5-minute memory (API key default)',
                                                       f'turn before the wait: read {R("c13-before-wait")} · write {W("c13-before-wait")}',
                                                       f'turn after the wait:  read {R("c14-after-6-minutes")} · write {W("c14-after-6-minutes")}',
                                                       "API's reason: none (nothing in the request changed)"],
                        'highlight': [2]},
              'narration': f"We left the session alone for six minutes, on the default five minute memory. The next turn wrote "
                           f"{W('c14-after-6-minutes')} tokens again, where the turn before the wait wrote {W('c13-before-wait')}. Only the "
                           f"first {R('c14-after-6-minutes')} tokens were still read from the cache: exactly what turn one found cached. "
                           "Why that part survived, our lab doesn't show, so we won't guess. The A P I found nothing changed in the "
                           "request: the rest had expired. And the one hour memory?"},
             {'id': 'b_hour', 'term': 'a one-hour memory', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'panel': {'kind': 'terminal', 'lines': ['6 minutes idle, 1-hour memory',
                                                       f'Claude Code: read {R("c15-1h-after-6-minutes")} · write {W("c15-1h-after-6-minutes")}',
                                                       f'Raw API, 5-minute: read {A("a8-5m-after-6-minutes", "cache_read_input_tokens")}',
                                                       f'Raw API, 1-hour:   read {A("a9-1h-after-6-minutes", "cache_read_input_tokens")}'],
                        'highlight': [1, 3]},
              'narration': f"A session set to a one hour memory read {R('c15-1h-after-6-minutes')} tokens after the same wait and wrote "
                           f"{W('c15-1h-after-6-minutes')}: the same split as turn two, which had no wait at all. On the A P I, with a "
                           f"prompt only our script used, the five minute memory read zero and the one hour memory read "
                           f"{A('a9-1h-after-6-minutes', 'cache_read_input_tokens')}. So how do you get the hour?"},
             {'id': 'b_ttl', 'term': 'choosing one hour', 'show': ['you', 'cc'], 'edges': ['e_send'],
              'panel': {'kind': 'terminal', 'lines': ['Default memory in Claude Code (docs)', 'Claude subscription, within plan: 1 hour',
                                                       'API key, usage credits, cloud: 5 minutes',
                                                       'CLAUDE_CODE_PROMPT_CACHE_TTL=1h  (v2.1.242+)'], 'highlight': [3]},
              'narration': "It depends on how you sign in. The docs say a Claude subscription gets one hour for the main conversation, "
                           "within your plan. An A P I key gets five minutes, unless you set one hour, as we did. The docs call this "
                           "lifetime the T T L, time to live. A one hour write costs double, so it pays from the second reuse. Building "
                           "your own app on the A P I? One rule decides all of this."},
         ]},
        {'id': 'rule', 'slide': {'title': '6 · The rule underneath', 'body': 'Bottom to top: tools, system, messages',
                                 'layout': 'left', 'narration': [{'say': 'The same rule, measured directly on the A P I.'}]},
         'beats': [
             {'id': 'b_api', 'term': 'the same rule, raw', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'panel': {'kind': 'terminal', 'lines': ['Claude API · Haiku 5.5 · cached system prompt',
                                                       f'same request again            read {A("a2-same-again", "cache_read_input_tokens")}',
                                                       f'one tool description edited   read 0 · write {A("a3-tool-description-changed", "cache_creation_input_tokens")}',
                                                       '+ cached last message:',
                                                       f'only tool_choice changed      read {A("a4c-tool-choice-changed", "cache_read_input_tokens")} · write {A("a4c-tool-choice-changed", "cache_creation_input_tokens")}'],
                        'highlight': [2, 4]},
              'narration': f"Inside the A P I, tools come first, then the system prompt, then messages. Same request twice: the second "
                           f"reused {A('a2-same-again', 'cache_read_input_tokens')} tokens. Add one sentence to one tool's description: "
                           "nothing reused, because tools are the very bottom. Change only tool choice, the setting that tells Claude "
                           f"which tool it must use: it lives with the messages, so the bottom still reused "
                           f"{A('a4c-tool-choice-changed', 'cache_read_input_tokens')} and only the top was written again. One last trap."},
             {'id': 'b_floor', 'term': 'too small to cache', 'show': ['api', 'cache'], 'edges': ['e_look'],
              'callout': f'A {A("a5-below-minimum", "input_tokens")}-token prompt marked for caching: nothing written, no error. Haiku 5.5 minimum: 512 tokens',
              'narration': "A tiny prompt, marked for caching, wrote nothing, and returned no error. On Haiku five point five, the docs set "
                           "the floor at five hundred twelve tokens; on Haiku four point five it's four thousand ninety-six. We covered this "
                           "trap in depth in an earlier episode, linked below. So, what should you do?"},
         ]},
        {'id': 'check', 'slide': {'title': '7 · Keep the desk remembering',
                                  'body': 'Pick the model at the start; switch between tasks\nKeep tool search on\nEdit CLAUDE.md freely: it applies after /clear, /compact or a restart\nStepping away? Consider the 1-hour TTL\nCheck /usage (v2.1.251+): "Prompt cache (main)"',
                                  'layout': 'left',
                                  'narration': [{'say': 'Pick your model at the start; switch between tasks.'},
                                                {'say': 'Keep tool search on.'},
                                                {'say': 'Edit CLAUDE dot M D freely; it applies after a clear, a compact, or a restart.'},
                                                {'say': 'Stepping away often? Consider the one hour T T L.'},
                                                {'say': 'And check slash usage for your hit ratio.'}]},
         'beats': []},
    ],
    'recap': {'narration': 'The whole picture: the desk remembers the bottom of the bag, until you change the bottom, or the memory expires.',
              'slide': {'id': 'takeaway', 'title': 'Same bottom. Same model. Back before it expires.',
                        'narration': 'Same bottom. Same model. Back before the memory expires.'}},
    'outro': [{'id': 'series', 'title': 'The Hidden Cost of AI Coding · episode 9',
               'subtitle': f'Claude Code {VER} · Claude Haiku 5.5 · Claude API · measured 19 Oct 2026',
               'body': 'Where your tokens go, measured in a lab\nNext to watch: "Prompt Is Too Long" (episode 8)\nThe lab and every measurement: linked below',
               'layout': 'center',
               'narration': [{'say': 'This is episode nine of The Hidden Cost of A I Coding.'},
                             {'say': 'For when the bag gets too heavy, watch episode eight next.'},
                             {'say': 'The lab and every measurement are linked below. Subscribe for the next one.'}]}],
}

short = [{
    'id': 'cc-01-model-switch', 'title': "Does switching models break Claude Code's cache?",
    'nodes': ['cc', 'api', 'cache'], 'labels': {'cc': 'Claude Code', 'api': 'Claude API', 'cache': 'Prompt cache'},
    'shots': [
        {'id': 'conflict', 'show': ['cc'],
         'narration': f"Does switching models break Claude Code's prompt cache? We switched mid-session: the next turn reused zero "
                      f"tokens and wrote all {W('c04-model-switched')} again.",
         'callout': f'Switched model · next turn: cache read 0, write {W("c04-model-switched")}'},
        {'id': 'answer', 'slide': {'title': "Yes. But editing CLAUDE.md doesn't",
                                   'body': f'Edit CLAUDE.md mid-session\ncache read {n(INS_READ)}: kept'},
         'narration': f"Yes: each model has its own cache. But editing CLAUDE dot M D, which feels riskier, kept it: the next message "
                      f"reused {n(INS_READ)} tokens."},
        {'id': 'bonus', 'show': ['cc', 'api', 'cache'], 'edges': ['e_turn', 'e_look'],
         'narration': "And a six minute pause, on an A P I key, lost this session's part of it too."},
        {'id': 'end', 'show': ['cc', 'api', 'cache'], 'camera': ['cc', 'cache'],
         'narration': 'Every cache breaker we measured is in episode nine of The Hidden Cost of A I Coding. Tap the link below. '
                      'Which one do you do most?'},
    ]}]

json.dump(primer, open(os.path.join(OUT, 'claude-code-caching.primer.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=2)
json.dump(short, open(os.path.join(OUT, 'claude-code-caching.shorts.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=2)
print('wrote', OUT)
