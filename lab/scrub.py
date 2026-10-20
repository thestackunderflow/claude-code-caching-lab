"""Scrub run logs and API records before they are published.

Host paths become <lab> (this folder) or <home> (a user's home folder); API keys and account fields
(email, organization, account ids) become <redacted>. Container paths (/work, /root, /lab, /tmp) and every number
are left exactly as they are. run.sh calls this after every paid run.

    python -m lab.scrub evidence      # rewrites the files in place
"""
import os, re, sys

LAB = re.compile(r"""(?:[A-Za-z]:[\\/]|/[A-Za-z]/|/home/|/Users/)[^\s"'<>|]*?claude-code-caching-lab(?![\w-])""")
HOME = [
    re.compile(r"""[A-Za-z]:(?:\\\\|\\|/)Users(?:\\\\|\\|/)[^\\/\s"']+"""),
    re.compile(r"""(?:/[A-Za-z])?/(?:Users|home)/[^\\/\s"']+"""),
]
KEYS = re.compile(r"\bsk-ant-[A-Za-z0-9_-]+|\bsk-[A-Za-z0-9]{20,}|\bghp_[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b"
                  r"|\bhf_[A-Za-z0-9]{20,}|(?i:\bbearer\s+[A-Za-z0-9._-]{20,})")
FIELDS = re.compile(r'"((?i:e-?mail[A-Za-z_]*|organi[sz]ation[A-Za-z_]*|org_?id|account[A-Za-z_]*))"\s*:\s*"[^"]*"')


def scrub_text(text: str) -> str:
    text = LAB.sub('<lab>', text)
    for h in HOME:
        text = h.sub('<home>', text)
    text = KEYS.sub('<redacted>', text)
    return FIELDS.sub(lambda m: '"%s":"<redacted>"' % m.group(1), text)


def scrub_dir(path: str) -> int:
    """Rewrite every text file under path; returns how many changed."""
    changed = 0
    for root, _, names in os.walk(path):
        for n in names:
            f = os.path.join(root, n)
            try:
                with open(f, encoding='utf8', newline='') as fh:
                    t = fh.read()
            except UnicodeDecodeError:
                continue
            s = scrub_text(t)
            if s != t:
                with open(f, 'w', encoding='utf8', newline='') as fh:
                    fh.write(s)
                changed += 1
    return changed


if __name__ == '__main__':
    for p in sys.argv[1:] or ['evidence']:
        print(p, 'files changed:', scrub_dir(p))
