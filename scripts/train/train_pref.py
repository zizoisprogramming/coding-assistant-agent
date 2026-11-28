"""LoRA plan B: learn from the SAME agent's passes vs fails (user 2026-11-25: 'go with B' -> 'yes write the training code
while they run'). Unpaired, KTO-style (Ethayarajh et al. 2024, arXiv 2402.01306) + a copy (SFT) term on passes, on the
competition's 4-bit Gemma with our int4 LoRA (scripts/train/int4_lora.py, the adapter format the scorer served in the
2026-10-24 serve check).

    torchrun --nproc_per_node <ranks> train_pref.py --model <ckpt> --samples samples.pt --out <dir> [options]

Samples: build_samples.py output of pref_episodes.py episodes: one sequence per segment, loss only on the model's own
tokens (thinking, tool calls, replies; never tool outputs), each with label 'good' (a solved run, cut at its first
submit) or 'bad' (a failed run of a task that was also solved).

Per segment s:  r(s) = mean over its trained tokens of [log p_policy - log p_ref]  (= ref NLL - policy NLL; per-token
mean, not KTO's sum, so 300-token and 9,000-token segments weigh alike). The reference is the base model: LoRA B starts
at 0, so the policy at step 0 IS the reference; its NLL per segment is computed once before training and cached.
  good:  w_good * (1 - sigmoid(beta * (r - z0)))  +  sft_weight * policy NLL     (raise passes, keep copying them)
  bad:   w_bad  * (1 - sigmoid(beta * (z0 - r)))                                  (lower fails, relative to the reference)
z0 (KTO's reference point, how far the policy has moved overall): --z0 kto = detached, clamped >= 0 running mean of r over
recent batches (all ranks); --z0 zero = 0 (APO-zero, unpaired). w_good / w_bad balance the label counts (KTO: desirable
weight x n_good ~= undesirable weight x n_bad). Habits that passes and fails share push both ways and cancel; what
separates them is what moves.

Logged every step: loss, its KTO and copy parts, mean r of the step's good and bad segments, z0, lr, grad norm, tokens/s,
memory, ETA. Validation (held-out TASKS): mean r good / bad, the margin r_good - r_bad (should grow), KTO loss, the
passes' NLL (should not rise much: the copy term guards the base behaviour). Best checkpoint = lowest validation KTO loss
with the passes' NLL within --max-nll-rise of the start. Resumable; --session-hours pauses inside a Kaggle session.
"""
import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch
import torch.distributed as dist

sys.path.insert(0, str(Path(__file__).resolve().parent))
from int4_lora import masked_lm_loss, save_adapter, text_hidden_states  # noqa: E402
from train_sft import (all_max, all_sum, batches, first_device, from_rank0, gpu_mem_gib, load_model, log,  # noqa: E402
                       lora_params, setup)


def nll(model, s, dev):
    """Mean NLL over the segment's trained tokens (a tensor with grad when training) and their count."""
    ids = s["input_ids"].long().unsqueeze(0).to(dev)
    labels = torch.where(s["labels_mask"].unsqueeze(0).to(dev), ids, torch.full_like(ids, -100))
    mean, n = masked_lm_loss(model, text_hidden_states(model, ids), labels)
    return mean, n


def reference_nll(model, items, rank, world, dev, cache):
    """Per-segment NLL of the reference (= the model with LoRA B = 0), computed once, split over ranks, cached."""
    if cache.exists():
        ref = torch.load(cache)
        if len(ref) == len(items):
            return ref
    model.eval()
    ref = torch.zeros(len(items), dtype=torch.float64, device=dev)
    mine = sorted(range(len(items)), key=lambda j: -len(items[j]["input_ids"]))[rank::world]
    t0 = time.time()
    with torch.no_grad():
        for k, j in enumerate(mine):
            m, _ = nll(model, items[j], dev)
            ref[j] = m.item()
            if rank == 0 and (k + 1) % 20 == 0:
                log(f"  reference NLL {k + 1}/{len(mine)} segments on rank 0 ({time.time() - t0:.0f}s)")
    if dist.is_initialized():
        dist.all_reduce(ref)
    model.train()
    ref = ref.cpu()
    if rank == 0:
        torch.save(ref, cache)
    return ref


def select_budget(items, budget, seed):
    """Segments within a token budget (0: all): good and bad alternately, tasks round-robin, so the set stays balanced by
    label and spread over tasks (31B on 4 x L4 trains ~60 tok/s: the budget is the GPU time)."""
    if not budget or sum(len(s["input_ids"]) for s in items) <= budget:
        return items
    rng = random.Random(seed)
    queues = {}
    for lab in ("good", "bad"):
        by_task = {}
        for s in items:
            if s["label"] == lab:
                by_task.setdefault(s["task"], []).append(s)
        tasks = sorted(by_task)
        rng.shuffle(tasks)
        for t in tasks:
            rng.shuffle(by_task[t])
        order = []
        while any(by_task.values()):
            for t in tasks:
                if by_task[t]:
                    order.append(by_task[t].pop())
        queues[lab] = order
    out, used, lab = [], 0, "good"
    while queues["good"] or queues["bad"]:
        if not queues[lab]:
            lab = "bad" if lab == "good" else "good"
        s = queues[lab].pop(0)
        if used + len(s["input_ids"]) <= budget:
            out.append(s)
            used += len(s["input_ids"])
        lab = "bad" if lab == "good" else "good"
    return out


def kto_terms(r, label, z0, beta):
    """Per-segment KTO loss (0..1) for one segment's r."""
    if label == "good":
        return 1 - torch.sigmoid(beta * (r - z0))
    return 1 - torch.sigmoid(beta * (z0 - r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--samples", nargs="+", required=True, help="build_samples.py outputs (merged); FILE:N caps that file's train "
                    "segments to N tokens (e.g. the fastapi / rich file at ~10% of the training budget)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-name", default="google/gemma-4-31b-it-qat-w4a16-ct")
    ap.add_argument("--gpus-per-rank", type=int, default=1)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--accum", type=int, default=4, help="segments per rank per optimizer step (mixed labels)")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--min-lr-ratio", type=float, default=0.1)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--clip", type=float, default=1.0)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=16)
    ap.add_argument("--dropout", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--attn", default="sdpa")
    ap.add_argument("--beta", type=float, default=5.0, help="sharpness on the per-token log-ratio r")
    ap.add_argument("--sft-weight", type=float, default=1.0, help="copy term on passes (0: pure KTO)")
    ap.add_argument("--z0", choices=["kto", "zero"], default="kto")
    ap.add_argument("--decision-weight", type=float, default=2.0, help="weight of decision-moment segments (build_samples: the first budget warning / first a.py banner of a run); 1 = off")
    ap.add_argument("--z0-ema", type=float, default=0.9)
    ap.add_argument("--max-nll-rise", type=float, default=0.10, help="best checkpoint only if the passes' validation NLL "
                    "is at most this fraction above its start value")
    ap.add_argument("--max-len", type=int, default=16384, help="longest segment trained (31B: 24k ran out of memory)")
    ap.add_argument("--train-tokens", type=int, default=0, help="token budget of the train set (0: all); with P / O flags: of the KTO samples")
    ap.add_argument("--copy-tokens", type=int, default=0, help="P / O: token budget of the copy-only samples (0: all)")
    ap.add_argument("--val-tokens", type=int, default=0, help="token budget of the validation set (0: all)")
    ap.add_argument("--evals", type=int, default=4)
    ap.add_argument("--save-every", type=int, default=10)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--session-hours", type=float, default=0)
    args = ap.parse_args()
    t_start = time.time()
    rank, world = setup()
    out = Path(args.out)
    if rank == 0:
        out.mkdir(parents=True, exist_ok=True)
    samples = []
    for spec in args.samples:
        f, _, cap = spec.partition(":") if not Path(spec).exists() else (spec, "", "")
        part = [s for s in torch.load(f) if s.get("label") in ("good", "bad") and int(s["labels_mask"].sum()) > 0
                and float(s.get("weight", 1.0)) > 0]
        if cap:
            part = select_budget([s for s in part if s["split"] == "train"], int(cap), args.seed) + [s for s in part if s["split"] == "val"]
        log(f"samples {Path(f).name}: {len(part)} segments, {sum(len(s['input_ids']) for s in part) / 1e6:.2f}M tokens"
            f"{' (train capped at ' + cap + ' tokens)' if cap else ''}", 0, int(os.environ.get('RANK', 0)))
        samples += part
    for i, s in enumerate(samples):
        s["idx"] = i
    samples = [s for s in samples if int(s["labels_mask"].sum()) > 0 and len(s["input_ids"]) <= args.max_len
               and float(s.get("weight", 1.0)) > 0]  # weight 0 = a task every run solved (or failed): no same-task signal
    for i, s in enumerate(samples):
        s["idx"] = i
    for s in samples:  # P / O flags (build_samples.py); old files: every good sample is copied, every sample is in KTO
        s["copy"] = bool(s["copy"]) if "copy" in s else s["label"] == "good"
        s["kto"] = bool(s.get("kto", True))
    only_copy = lambda xs: [s for s in xs if s["copy"] and not s["kto"]]
    with_kto = lambda xs: [s for s in xs if s["kto"]]
    train = (select_budget(with_kto([s for s in samples if s["split"] == "train"]), args.train_tokens, args.seed) +
             select_budget(only_copy([s for s in samples if s["split"] == "train"]), args.copy_tokens, args.seed))
    val = (select_budget(with_kto([s for s in samples if s["split"] == "val"]), args.val_tokens, args.seed) +
           select_budget(only_copy([s for s in samples if s["split"] == "val"]), args.val_tokens, args.seed))
    samples = train + val  # the reference pass covers only what is used
    for i, s in enumerate(samples):
        s["idx"] = i
    kto_items = [s for s in samples if s["kto"]]
    for i, s in enumerate(kto_items):
        s["ridx"] = i
    ng = sum(float(s.get("weight", 1.0)) for s in train if s["kto"] and s["label"] == "good")
    nb = sum(float(s.get("weight", 1.0)) for s in train if s["kto"] and s["label"] == "bad")  # weighted counts: KTO class balance
    has_kto = any(s["kto"] for s in train)
    assert not has_kto or (ng and nb), f"need both labels in the KTO samples (good {ng}, bad {nb})"
    assert has_kto or any(s["copy"] for s in train), "nothing to train: no KTO and no copy samples"
    w_good, w_bad = (1.0, ng / nb) if has_kto else (1.0, 1.0)  # KTO balance: w_good * n_good == w_bad * n_bad
    log(f"ranks {world} x {args.gpus_per_rank} GPU(s) | train {len(train)} segments (weighted good {ng:.1f}, bad {nb:.1f}; "
        f"{len({s['task'] for s in train})} tasks) {sum(len(s['input_ids']) for s in train) / 1e6:.2f}M tokens "
        f"({sum(int(s['labels_mask'].sum()) for s in train) / 1e6:.2f}M trained; copy {sum(s['copy'] for s in train)}, KTO "
        f"{sum(s['kto'] for s in train)}) | val {len(val)} segments "
        f"({len({s['task'] for s in val})} tasks) | beta {args.beta} sft {args.sft_weight} z0 {args.z0} "
        f"w_good {w_good:.2f} w_bad {w_bad:.2f} | decision segments train {sum(bool(s.get('decision')) for s in train)} "
        f"(good {sum(bool(s.get('decision')) and s['label'] == 'good' for s in train)}, bad "
        f"{sum(bool(s.get('decision')) and s['label'] == 'bad' for s in train)}) x{args.decision_weight}, val "
        f"{sum(bool(s.get('decision')) for s in val)}", 0, rank)

    t0 = time.time()
    model, gpus = load_model(args, rank)
    dev = first_device(model)
    params = lora_params(model)
    log(f"model loaded in {time.time() - t0:.0f}s on GPUs {gpus or 'cpu'}; LoRA r={args.r} alpha={args.alpha}: "
        f"{sum(p.numel() for p in params) / 1e6:.1f}M trainable params", 0, rank)
    if dist.is_initialized():
        for p in params:
            t = p.data.to(dev)
            dist.broadcast(t, 0)
            p.data.copy_(t.to(p.device))
    assert all(float(p.detach().abs().max()) == 0 for p in params[1::2]), "LoRA B must start at 0 (policy == reference)"

    state_path = out / "last" / "trainer_state.pt"
    resumed = state_path.exists()
    if resumed:  # the cache was written before any step; recomputing it with a trained LoRA would be wrong
        assert (out / "ref_nll.pt").exists(), "resume without the reference cache"
    t0 = time.time()
    if kto_items:
        ref = reference_nll(model, kto_items, rank, world, dev, out / "ref_nll.pt")
        log(f"reference NLL ready for {len(ref)} KTO segments ({time.time() - t0:.0f}s): good mean "
            f"{ref[[s['ridx'] for s in kto_items if s['label'] == 'good']].mean():.4f}, bad mean "
            f"{ref[[s['ridx'] for s in kto_items if s['label'] == 'bad']].mean():.4f}", 0, rank)
    else:
        ref = torch.zeros(0, dtype=torch.float64)
        log("no KTO samples (adapter P: copy only): no reference pass", 0, rank)

    opt = torch.optim.AdamW(params, lr=args.lr, betas=(0.9, 0.999), weight_decay=0.0)
    per_epoch = math.ceil(len(train) / (world * args.accum))
    plan = {"total": max(1, int(per_epoch * args.epochs)), "best": None, "nll0": None}
    step, history, z0 = 0, [], 0.0
    if resumed:
        st = torch.load(state_path, map_location="cpu")
        for p, v in zip(params, st["lora"]):
            p.data.copy_(v.to(p.device))
        opt.load_state_dict(st["opt"])
        step, plan, history, z0 = st["step"], st["plan"], st["history"], st["z0"]
        log(f"RESUMED at step {step}/{plan['total']} (z0 {z0:.4f})", 0, rank)
    eval_every = max(1, plan["total"] // (args.evals + 1))

    def lr_at(k):
        if k < args.warmup:
            return args.lr * (k + 1) / args.warmup
        prog = min(1.0, (k - args.warmup) / max(1, plan["total"] - args.warmup))
        return args.lr * (args.min_lr_ratio + (1 - args.min_lr_ratio) * 0.5 * (1 + math.cos(math.pi * prog)))

    def save(tag):
        if rank != 0:
            return
        if tag:
            save_adapter(model, out / tag, args.base_name)
        save_adapter(model, out / "last", args.base_name)
        torch.save({"lora": [p.detach().cpu() for p in params], "opt": opt.state_dict(), "step": step, "plan": plan,
                    "history": history, "z0": z0}, str(state_path) + ".tmp")
        os.replace(str(state_path) + ".tmp", state_path)
        (out / "history.json").write_text(json.dumps(history, indent=1))
        log(f"  saved {'adapter ' + str(out / tag) if tag else 'checkpoint'} at step {step}", 0, rank)

    def validate(tag):
        model.eval()
        mine = sorted(range(len(val)), key=lambda j: -len(val[j]["input_ids"]))[rank::world]
        # r_good, n_good, r_bad, n_bad, kto (KTO samples); nll, n (copy samples = the passes' NLL); decision r_good, n, r_bad, n
        acc = torch.zeros(11, dtype=torch.float64, device=dev)
        with torch.no_grad():
            for j in mine:
                s = val[j]
                m, _ = nll(model, s, first_device(model))
                if s["copy"]:
                    acc += torch.tensor([0, 0, 0, 0, 0, m.item(), 1, 0, 0, 0, 0], dtype=torch.float64, device=dev)
                if not s["kto"]:
                    continue
                r = ref[s["ridx"]].item() - m.item()
                k = kto_terms(torch.tensor(r), s["label"], z0, args.beta).item()
                d = 1.0 if s.get("decision") else 0.0
                if s["label"] == "good":
                    acc += torch.tensor([r, 1, 0, 0, k * w_good, 0, 0, r * d, d, 0, 0], dtype=torch.float64, device=dev)
                else:
                    acc += torch.tensor([0, 0, r, 1, k * w_bad, 0, 0, 0, 0, r * d, d], dtype=torch.float64, device=dev)
        if dist.is_initialized():
            dist.all_reduce(acc)
        model.train()
        rg, ngv, rb, nbv, kt, nl, ncv, drg, dng, drb, dnb = acc.tolist()
        res = {"type": "val", "tag": tag, "step": step, "r_good": round(rg / max(ngv, 1), 5), "r_bad": round(rb / max(nbv, 1), 5),
               "margin": round(rg / max(ngv, 1) - rb / max(nbv, 1), 5), "kto": round(kt / max(ngv + nbv, 1), 5),
               "nll_good": round(nl / max(ncv, 1), 5), "segments": len(val),
               "margin_decision": round(drg / max(dng, 1) - drb / max(dnb, 1), 5) if dng and dnb else None}
        history.append(res)
        log(f"VAL [{tag}] step {step}: margin {res['margin']:+.4f} (r good {res['r_good']:+.4f}, bad {res['r_bad']:+.4f}) | "
            f"KTO {res['kto']:.4f} | passes' NLL {res['nll_good']:.4f} ({int(ncv)} copy segments) | {int(ngv)} good + {int(nbv)} bad KTO segments | decision-moment "
            f"margin {res['margin_decision'] if res['margin_decision'] is not None else '-'} ({int(dng)} good + {int(dnb)} bad)", 0, rank)
        return res

    val_kto = any(s["kto"] for s in val)
    best_key = (lambda v: v["kto"]) if val_kto else (lambda v: v["nll_good"])  # P: no KTO -> the held-out passes' NLL
    if step == 0 and val:
        v0 = validate("start")
        plan["nll0"] = v0["nll_good"]
    all_batches = [b for e in range(math.ceil(args.epochs)) for b in batches(train, world, args.accum, args.seed, e)]
    ema_loss, t_train, timed = None, time.time(), 0
    while step < plan["total"] and step < len(all_batches):
        if args.max_steps and step >= args.max_steps:
            break
        t0 = time.time()
        mine = [train[j] for j in all_batches[step][rank]]
        wt = lambda s: float(s.get("weight", 1.0)) * (args.decision_weight if s.get("decision") else 1.0)  # same-task advantage x decision
        n_glob = all_sum(sum(wt(s) for s in mine), dev)  # weighted mean over the step's segments
        for g in gpus:
            torch.cuda.reset_peak_memory_stats(g)
        stats = torch.zeros(6, dtype=torch.float64, device=dev)  # kto sum, sft sum, r_good sum, n_good, r_bad sum, n_bad
        for s in mine:
            m, _ = nll(model, s, dev)
            if s["kto"]:
                r = ref[s["ridx"]].to(m.device, m.dtype) - m
                k = kto_terms(r, s["label"], z0, args.beta) * (w_good if s["label"] == "good" else w_bad)
            else:
                r, k = torch.zeros_like(m), torch.zeros_like(m)
            sft = args.sft_weight * m if s["copy"] else torch.zeros_like(m)  # P / O: only the copied passes
            ((k + sft) * wt(s) / n_glob).backward()
            g_, b_ = s["kto"] and s["label"] == "good", s["kto"] and s["label"] == "bad"
            stats += torch.tensor([k.item() * wt(s), sft.item() * wt(s), r.item() if g_ else 0, g_,
                                   r.item() if b_ else 0, b_], dtype=torch.float64, device=dev)
        if dist.is_initialized():
            dist.all_reduce(stats)
        flat = torch.cat([(p.grad if p.grad is not None else torch.zeros_like(p)).flatten().to(dev) for p in params])
        if dist.is_initialized():
            dist.all_reduce(flat)
        gnorm = flat.norm().item()
        if not math.isfinite(gnorm):
            raise SystemExit(f"non-finite gradient at step {step}: stopping before the LoRA weights are damaged")
        if args.clip and gnorm > args.clip:
            flat.mul_(args.clip / (gnorm + 1e-6))
        i = 0
        for p in params:
            n = p.numel()
            p.grad = flat[i:i + n].view_as(p).to(p.device)
            i += n
        lr = lr_at(step)
        for gr in opt.param_groups:
            gr["lr"] = lr
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        kt, sf, rg, ngs, rb, nbs = stats.tolist()
        r_mean = (rg + rb) / max(ngs + nbs, 1)
        if args.z0 == "kto" and ngs + nbs > 0:  # how far the policy has moved overall, never negative, detached
            z0 = from_rank0(max(0.0, args.z0_ema * z0 + (1 - args.z0_ema) * r_mean), dev)
        loss = (kt + sf) / max(n_glob, 1)
        ema_loss = loss if ema_loss is None else 0.9 * ema_loss + 0.1 * loss
        toks = all_sum(sum(len(s["input_ids"]) for s in mine), dev)
        mem = all_max(gpu_mem_gib(gpus), dev)
        secs = time.time() - t0
        timed += 1
        eta = (plan["total"] - step) * (time.time() - t_train) / timed
        history.append({"type": "train", "step": step, "loss": round(loss, 5), "kto": round(kt / max(n_glob, 1), 5),
                        "sft": round(sf / max(n_glob, 1), 5), "r_good": round(rg / max(ngs, 1), 5),
                        "r_bad": round(rb / max(nbs, 1), 5), "n_good": int(ngs), "n_bad": int(nbs), "z0": round(z0, 5),
                        "lr": lr, "grad_norm": round(gnorm, 4), "tokens": int(toks), "seconds": round(secs, 1), "mem_gib": round(mem, 2)})
        log(f"step {step:4}/{plan['total']} | loss {loss:.4f} (avg {ema_loss:.4f}) = KTO {kt / max(n_glob, 1):.4f} + copy "
            f"{sf / max(n_glob, 1):.4f} | r good {rg / max(ngs, 1):+.4f} ({int(ngs)}) bad {rb / max(nbs, 1):+.4f} ({int(nbs)}) "
            f"| z0 {z0:.4f} | lr {lr:.2e} | grad {gnorm:.3f} | {int(toks):6} tok {toks / secs:6.0f} tok/s | mem {mem:.1f} GiB "
            f"| {secs:5.1f}s | ETA {eta / 60:5.1f} min", 0, rank)
        if val and step % eval_every == 0 and step < plan["total"]:
            v = validate(f"step{step}")
            ok_nll = plan["nll0"] is None or v["nll_good"] <= plan["nll0"] * (1 + args.max_nll_rise)
            if ok_nll and (plan["best"] is None or best_key(v) < plan["best"]):
                plan["best"] = best_key(v)
                save("best")
                log(f"  new best validation {'KTO' if val_kto else 'passes NLL (copy only)'} {best_key(v):.4f} -> saved as best", 0, rank)
            elif not ok_nll:
                log(f"  passes' NLL {v['nll_good']:.4f} rose more than {args.max_nll_rise:.0%} above the start "
                    f"{plan['nll0']:.4f}: not a best candidate (the copy term is losing)", 0, rank)
            save(f"step_{step}")
        elif step % args.save_every == 0:
            save(None)
        if args.session_hours and step < plan["total"] and \
                time.time() - t_start + 2 * (time.time() - t_train) / timed + 600 > args.session_hours * 3600:
            save(None)
            log(f"PAUSED at step {step}/{plan['total']} after {(time.time() - t_start) / 3600:.2f}h: attach this output to "
                f"the next session, which resumes here", 0, rank)
            if dist.is_initialized():
                dist.destroy_process_group()
            return
    if val:
        v = validate("final")
        ok_nll = plan["nll0"] is None or v["nll_good"] <= plan["nll0"] * (1 + args.max_nll_rise)
        if ok_nll and (plan["best"] is None or best_key(v) < plan["best"]):
            plan["best"] = best_key(v)
            save("best")
    save("final")
    if rank == 0:
        vals = [h for h in history if h["type"] == "val"]
        log("\nVALIDATION: " + " | ".join(f"{h['tag']} margin {h['margin']:+.4f} KTO {h['kto']:.4f} NLL {h['nll_good']:.4f}"
                                         for h in vals), 0, rank)
        log(f"done: {step} steps in {(time.time() - t_start) / 3600:.2f}h -> {out / 'final'} (best: {out / 'best'})", 0, rank)
    if dist.is_initialized():
        dist.destroy_process_group()


if __name__ == "__main__":
    random.seed(0)
    main()
