"""Flag episodes whose teacher did something that cannot work (or is forbidden) in the competition sandbox, so
training never teaches it. Nothing is deleted: this writes one row per flagged episode; selection skips them.

    python sandbox_check.py --episodes <dir> [<dir> ...] --out flags.jsonl.gz

The harness tells the agent: offline, all dependencies pre-installed, do not pip install, do not search outside
/workspace (e.g. /usr/, /wheels/, site-packages). Rules below follow that.
"""
import argparse
import gzip
import json
import re
from pathlib import Path

CMD = r"(?:^|[;&|(\n]|&&|\|\||\$\()\s*(?:sudo\s+)?"  # command position: start of line / after ; && || | ( $(
RULES = {
    # installing / managing packages (offline sandbox; the task prompt forbids it)
    "package_install": re.compile(
        CMD + r"(?:pip3?|python3?\s+-m\s+pip|uv\s+pip|conda|mamba|apt(?:-get)?|apk|yum|brew|poetry|pipenv|npm|yarn|"
        r"pnpm|gem|cargo)\s+(?:install|add|update|upgrade|sync|remove|uninstall)\b"),
    # network access by the shell (URLs inside scripts or test data are not counted)
    "network": re.compile(CMD + r"(?:curl|wget|ssh|scp|rsync|nc|telnet|ping)\s|"
                          + CMD + r"git\s+(?:clone|fetch|pull|push|ls-remote)\s+\S*(?:https?://|git@)"),
    # looking outside the repository at installed packages / system directories
    "outside_workspace": re.compile(r"(?:site-packages|dist-packages|/usr/(?:local/)?lib/python|/opt/conda|"
                                    r"(?<![\w.])/root/|(?<![\w.])/home/\w)|" + CMD + r"pip3?\s+(?:show|list|freeze)\b"),
    # privileged / environment-changing
    "privileged": re.compile(CMD + r"(?:sudo|su|docker|systemctl|service)\s"),
}
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\b", re.S)


def shell_part(cmd):
    """The command without the bodies of files it writes (heredocs): those are file contents, not actions."""
    return HEREDOC.sub("<<HEREDOC", cmd)


# write_file / edit_file targets must stay inside the repository (or /tmp for scratch files)
BAD_WRITE_PATH = re.compile(r"^/(?!tmp/|workspace/)")


def check(ep):
    hits = {}
    for s in ep["steps"]:
        for c in s["calls"]:
            a = c["args"]
            if c["tool"] == "run_command":
                cmd = shell_part(a.get("command", ""))
                for name, rx in RULES.items():
                    if rx.search(cmd):
                        hits.setdefault(name, cmd[:200])
            elif c["tool"] in ("write_file", "edit_file", "read_file"):
                p = a.get("filepath", "")
                if BAD_WRITE_PATH.match(p) or "site-packages" in p:
                    hits.setdefault("outside_workspace", p[:200])
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n = flagged = 0
    counts = {}
    with gzip.open(a.out, "wt") as fh:
        for f in sorted(f for d in a.episodes for f in Path(d).rglob("episodes_*.jsonl")):
            for line in open(f):
                ep = json.loads(line)
                n += 1
                hits = check(ep)
                if hits:
                    flagged += 1
                    for k in hits:
                        counts[k] = counts.get(k, 0) + 1
                    fh.write(json.dumps({"id": ep["id"], "instance_id": ep["instance_id"], "hits": hits}) + "\n")
    print(f"{n} episodes, {flagged} flagged ({100 * flagged / max(n, 1):.1f}%), by rule {counts} -> {a.out}")


if __name__ == "__main__":
    main()
