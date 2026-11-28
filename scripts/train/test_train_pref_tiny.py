"""CPU test of train_pref.py on a tiny random Gemma 4 in the 31B's int4 scheme (make_tiny_gemma.py).

    data/venv_train/bin/python scripts/train/test_train_pref_tiny.py <tiny_checkpoint_dir> <work_dir>

Synthetic data: every segment = a random prompt + a trained reply; 'good' replies follow pattern A (a fixed token cycle),
'bad' replies pattern B; 8 tasks, 2 of them held out (val). Checks:
1. step 0: the policy equals the reference (validation margin ~0, r ~0);
2. after training: the validation margin r_good - r_bad grew clearly (> 0.05) and the passes' NLL fell;
3. no NaN / inf anywhere in the history; adapters saved in PEFT format (best, final);
4. a run stopped by --max-steps resumes from its checkpoint and finishes the same plan.
"""
import json
import subprocess
import sys
from pathlib import Path

import torch

CKPT, WORK = sys.argv[1], Path(sys.argv[2])
WORK.mkdir(parents=True, exist_ok=True)
PY = sys.executable
TRAIN = str(Path(__file__).resolve().parent / "train_pref.py")
g = torch.Generator().manual_seed(0)
A = torch.arange(100, 132)
B = torch.arange(300, 332)
samples = []
for t in range(8):
    task = f"task{t}"
    split = "val" if t >= 6 else "train"
    for label, pat in (("good", A), ("bad", B)):
        for k in range(3):
            prompt = torch.randint(3, 1000, (40,), generator=g)
            off = int(torch.randint(0, 32, (1,), generator=g))
            reply = pat.roll(off)[:24]
            ids = torch.cat([prompt, reply]).to(torch.int32)
            mask = torch.cat([torch.zeros(40, dtype=torch.bool), torch.ones(24, dtype=torch.bool)])
            samples.append({"episode_id": f"{task}#a{k}{label}", "split": split, "label": label, "task": task, "decision": k == 0,
                            "segment": 0, "n_segments": 1, "replies": 1, "input_ids": ids, "labels_mask": mask})
torch.save(samples, WORK / "samples.pt")


def run(out, *extra):
    cmd = [PY, TRAIN, "--model", CKPT, "--samples", str(WORK / "samples.pt"), "--out", str(out), "--attn", "eager",
           "--lr", "3e-3", "--warmup", "2", "--epochs", "4", "--accum", "4", "--r", "4", "--alpha", "8", "--beta", "5",
           "--evals", "3", "--save-every", "2", *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout[-3000:])
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads((Path(out) / "history.json").read_text())


h = run(WORK / "full")
dec = [x for x in h if x["type"] == "val" and x.get("margin_decision") is not None]
print(f"0. decision-moment margin reported at {len(dec)} validations, final {dec[-1]['margin_decision']:+.4f}")
assert dec and dec[-1]["margin_decision"] > 0.05
vals = [x for x in h if x["type"] == "val"]
start, final = vals[0], vals[-1]
print(f"1. start: margin {start['margin']:+.5f} r_good {start['r_good']:+.5f} r_bad {start['r_bad']:+.5f}")
assert abs(start["margin"]) < 1e-3 and abs(start["r_good"]) < 1e-3, "policy != reference at step 0"
print(f"2. final: margin {final['margin']:+.4f} (r good {final['r_good']:+.4f}, bad {final['r_bad']:+.4f}); passes' NLL "
      f"{start['nll_good']:.4f} -> {final['nll_good']:.4f}")
assert final["margin"] > 0.05 and final["nll_good"] < start["nll_good"]
bad = [x for x in h for k, v in x.items() if isinstance(v, float) and (v != v or abs(v) == float("inf"))]
files = sorted(p.name for p in (WORK / "full" / "final").iterdir())
print(f"3. NaN/inf entries {len(bad)}; final adapter files {files}; best saved {(WORK / 'full' / 'best').exists()}")
assert not bad and "adapter_model.safetensors" in files and "adapter_config.json" in files

h1 = run(WORK / "resume", "--max-steps", "3")
steps1 = [x["step"] for x in h1 if x["type"] == "train"]
h2 = run(WORK / "resume")
steps2 = [x["step"] for x in h2 if x["type"] == "train"]
total = max(x["step"] for x in h if x["type"] == "train")
print(f"4. first run stopped at step {max(steps1)}; resumed run trained steps {sorted(set(steps2) - set(steps1))[:3]}... "
      f"to {max(steps2)} (uninterrupted run: {total})")
assert max(steps1) == 3 and min(set(steps2) - set(steps1)) == 4 and max(steps2) == total
sys.path.insert(0, str(Path(TRAIN).parent))
from train_pref import select_budget  # noqa: E402
tr = [s for s in samples if s["split"] == "train"]
sel = select_budget(tr, 10 * 64, 1)
labs = [s["label"] for s in sel]
print(f"5. token budget 640 of {sum(len(s['input_ids']) for s in tr)}: {len(sel)} segments, good {labs.count('good')} bad "
      f"{labs.count('bad')}, tasks {len({s['task'] for s in sel})}; no budget keeps all {len(select_budget(tr, 0, 1))}")
assert len(sel) == 10 and labs.count("good") == 5 and len({s["task"] for s in sel}) >= 5 and len(select_budget(tr, 0, 1)) == len(tr)

# 6-7. adapters P and O (pref_episodes --mode p / o, build_samples' copy / kto flags)
P_samples = [dict(s, copy=True, kto=False, episode_id=s["episode_id"] + "#copy") for s in samples if s["label"] == "good"]
torch.save(P_samples, WORK / "samples_p.pt")
O_samples = P_samples + [dict(s, copy=False, kto=True, weight=0.5) for s in samples]
torch.save(O_samples, WORK / "samples_o.pt")


def run_on(f, out, *extra):
    cmd = [PY, TRAIN, "--model", CKPT, "--samples", str(WORK / f), "--out", str(out), "--attn", "eager",
           "--lr", "3e-3", "--warmup", "2", "--epochs", "4", "--accum", "4", "--r", "4", "--alpha", "8", "--beta", "5",
           "--evals", "3", "--save-every", "2", *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads((Path(out) / "history.json").read_text()), p.stdout + p.stderr


hp, logp = run_on("samples_p.pt", WORK / "p")
vp = [x for x in hp if x["type"] == "val"]
tp = [x for x in hp if x["type"] == "train"]
print(f"6. P: '{'no reference pass' if 'no reference pass' in logp else 'REFERENCE PASS RAN'}' | passes' NLL "
      f"{vp[0]['nll_good']:.4f} -> {vp[-1]['nll_good']:.4f} | KTO part max {max(abs(x['kto']) for x in tp):.4f} | best saved "
      f"{(WORK / 'p' / 'best').exists()} ({'by passes NLL' if 'passes NLL (copy only)' in logp else 'NOT by NLL'})")
assert "no reference pass" in logp and vp[-1]["nll_good"] < vp[0]["nll_good"] and max(abs(x["kto"]) for x in tp) == 0
assert (WORK / "p" / "best" / "adapter_model.safetensors").exists() and "passes NLL (copy only)" in logp

ho, logo = run_on("samples_o.pt", WORK / "o")
vo = [x for x in ho if x["type"] == "val"]
copy_line = next(l for l in logo.splitlines() if "copy " in l and "KTO " in l and "segments" in l)
print(f"7. O: margin {vo[0]['margin']:+.4f} -> {vo[-1]['margin']:+.4f} | passes' NLL {vo[0]['nll_good']:.4f} -> "
      f"{vo[-1]['nll_good']:.4f} | {copy_line.split('trained;')[1].split(')')[0].strip()}")
assert abs(vo[0]["margin"]) < 1e-3 and vo[-1]["margin"] > 0.05 and vo[-1]["nll_good"] < vo[0]["nll_good"]
n_copy_tr = sum(1 for s in O_samples if s["copy"] and s["split"] == "train")
n_kto_tr = sum(1 for s in O_samples if s["kto"] and s["split"] == "train")
assert f"copy {n_copy_tr}, KTO {n_kto_tr}" in copy_line, copy_line
fp = lambda log: next(l for l in log.splitlines() if "copy segments selected" in l).split("fingerprint ")[1].split()[0]
hp2, logp2 = run_on("samples_p.pt", WORK / "p_budget", "--copy-tokens", "500", "--max-steps", "1")
ho2, logo2 = run_on("samples_o.pt", WORK / "o_budget", "--copy-tokens", "500", "--train-tokens", "700", "--max-steps", "1")
print(f"8. copy budget 500 tokens: P fingerprint {fp(logp2)} | O fingerprint {fp(logo2)}")
assert fp(logp2) == fp(logo2), "P and O must copy the same segments"
print("OK")
