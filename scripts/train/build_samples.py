"""Training samples from stage B's request logs: one token sequence per segment of an episode, loss only on what the
model wrote.

    python build_samples.py --stage-b <stage_b_out dir> [...] --tokenizer-dir <model dir> --out samples.pt

An episode's model calls form segments: inside a segment every prompt is exactly the previous prompt + the previous
reply + the tool output (checked character for character), so the LAST call's prompt + its reply contains every
reply of the segment. A compaction starts a new segment (the prompt then begins with the summary). Each segment
becomes one sequence; its labels are the token positions of the model's replies: thinking, tool calls and the stop
token it emits (<|tool_response> after a tool call, <turn|> after the final message). Prompt, tool outputs and the
compaction summary are context only. ADK's summary calls themselves are not trained on.

Only attempts whose status.jsonl row says ok are used (crash-safe stage B: unfinished attempts are ignored).
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from render_traces import load_template, render, request_to_template_inputs  # noqa: E402


def reply_message(rec):
    """The model's reply as an assistant message, prepared the way vLLM prepares history (arguments as dicts)."""
    m = rec["reply"]["message"]
    out = {"role": "assistant"}
    if m.get("content"):
        out["content"] = m["content"]
    if m.get("tool_calls"):
        out["tool_calls"] = [dict(c, function=dict(c["function"], arguments=json.loads(c["function"]["arguments"] or "{}")
                                                   if isinstance(c["function"]["arguments"], str)
                                                   else c["function"]["arguments"]))
                             for c in m["tool_calls"]]
    thought = m.get("reasoning_content") or m.get("reasoning")
    if thought:
        out["reasoning_content"] = out["reasoning"] = thought
    return out


def episode_segments(records, tmpl, bos, problems):
    """[(text, [(start, end) char spans of replies])] for one episode's records (time order)."""
    segs, cur, summary_seen = [], None, False
    for rec in records:
        if not rec["request"].get("tools"):  # ADK compaction summary
            summary_seen = True
            continue
        msgs, tools, think = request_to_template_inputs(rec)
        prompt = render(tmpl, bos, msgs, tools, enable_thinking=think)
        full = render(tmpl, bos, msgs + [reply_message(rec)], tools, enable_thinking=think, add_generation_prompt=False)
        if not full.startswith(prompt):
            problems["reply does not extend the prompt"] += 1
            return None
        end = len(full) - 1 if full.endswith("<turn|>\n") else len(full)  # the newline is template layout
        if cur is not None and prompt.startswith(cur["text"]):
            cur["text"], cur["spans"] = full, cur["spans"] + [(len(prompt), end)]
        else:
            if cur is not None and not summary_seen:
                problems["new segment without a compaction"] += 1
                return None
            cur = {"text": full, "spans": [(len(prompt), end)]}
            segs.append(cur)
        summary_seen = False
    return [(s["text"], s["spans"]) for s in segs]


def tokenize_segment(tok, text, spans):
    enc = tok.encode(text, add_special_tokens=False)
    ids = enc.ids
    starts = {a for a, _ in spans}
    lab = []
    for i, (a, b) in enumerate(enc.offsets):
        inside = any(x <= a and b <= y for x, y in spans)
        lab.append(inside)
    # every reply must start exactly on a token boundary (they start with a special token)
    token_starts = {a for a, _ in enc.offsets}
    assert starts <= token_starts, "a reply does not start on a token boundary"
    return ids, lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-b", nargs="+", required=True, help="stage_b_out folder(s): requests_*.jsonl + status.jsonl")
    ap.add_argument("--tokenizer-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-len", type=int, default=32768)
    a = ap.parse_args()
    import torch
    from tokenizers import Tokenizer
    tmpl, bos = load_template(a.tokenizer_dir)
    tok = Tokenizer.from_file(str(Path(a.tokenizer_dir) / "tokenizer.json"))

    ok = {}
    for d in a.stage_b:
        for line in (Path(d) / "status.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["status"] == "ok":
                ok[(r["id"], r["attempt"])] = r
    print(f"stage B episodes ok: {len(ok)}", flush=True)
    recs = defaultdict(list)
    for d in a.stage_b:
        for f in sorted(Path(d).glob("requests_*.jsonl")):
            with open(f) as fh:
                for line in fh:
                    r = json.loads(line)
                    if (r.get("episode_id"), r.get("attempt")) in ok:
                        recs[(r["episode_id"], r["attempt"])].append(r)
    problems = Counter()
    samples = []
    for n, (key, rs) in enumerate(sorted(recs.items())):
        rs.sort(key=lambda r: r["t"])
        meta = ok[key]
        try:  # one odd episode is skipped and counted, never stops the build
            segs = episode_segments(rs, tmpl, bos, problems)
            tokenized = None if segs is None else [tokenize_segment(tok, text, spans) for text, spans in segs]
        except Exception as e:  # noqa: BLE001
            problems[f"error {type(e).__name__}"] += 1
            segs = None
            print(f"  skip {key[0]}: {e!r}"[:300], flush=True)
        if segs is None:
            continue
        for k, ((text, spans), (ids, lab)) in enumerate(zip(segs, tokenized)):
            if len(ids) > a.max_len:
                problems["segment longer than max-len"] += 1
                continue
            samples.append({"episode_id": key[0], "split": meta["split"], "category": meta.get("category"),
                            "teacher": meta.get("teacher"), "segment": k, "n_segments": len(segs),
                            "replies": len(spans), "input_ids": torch.tensor(ids, dtype=torch.int32),
                            "labels_mask": torch.tensor(lab, dtype=torch.bool)})
        if (n + 1) % 50 == 0 or n + 1 == len(recs):
            print(f"  {n + 1}/{len(recs)} episodes -> {len(samples)} segments", flush=True)
    missing = len(ok) - len(recs)
    torch.save(samples, a.out)
    print(f"\nwrote {len(samples)} segments -> {a.out}; episodes without records {missing}; problems {dict(problems)}")
    for split in ("train", "val"):
        s = [x for x in samples if x["split"] == split]
        if not s:
            continue
        lens = sorted(len(x["input_ids"]) for x in s)
        labs = [int(x["labels_mask"].sum()) for x in s]
        print(f"{split}: {len({x['episode_id'] for x in s})} episodes, {len(s)} segments, "
              f"{sum(lens) / 1e6:.2f}M tokens (trained on {sum(labs) / 1e6:.2f}M = {100 * sum(labs) / sum(lens):.1f}%), "
              f"length median {lens[len(lens) // 2]} p90 {lens[int(len(lens) * .9)]} max {lens[-1]}, "
              f"segments per episode {dict(Counter(x['n_segments'] for x in s if x['segment'] == 0))}")


if __name__ == "__main__":
    main()
