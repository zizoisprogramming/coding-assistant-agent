"""LoRA SFT of the competition's 4-bit Gemma on stage B samples (build_samples.py), data-parallel over GPUs.

    torchrun --nproc_per_node <ranks> train_sft.py --model <ckpt> --samples samples.pt --out <dir> [options]
    python train_sft.py --model <ckpt> --samples samples.pt --out <dir> --probe   # memory/speed test, one rank

Each rank holds its own copy of the model (int4 weights + LoRA, scripts/train/int4_lora.py) on --gpus-per-rank GPUs
(1 if the 12B fits on one L4 at our longest segment; else 2, split by layers). One optimizer step = ranks x --accum
segments; the loss is the mean over every trained token of the step (all ranks), so long and short segments weigh
by their tokens. LoRA gradients are summed across ranks before clipping, so all copies stay identical.

Verbose by design (user): one line per step (loss, running average, lr, grad norm, tokens/s, GPU memory, ETA),
validation loss before training, at every --eval-every and at the end; adapters saved at those points (PEFT format,
same as the scorer-tested one) plus a resumable trainer state. Re-running resumes from the last saved step.
"""
import argparse
import datetime
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
from int4_lora import (Int4LoRALinear, add_lora, load_int4_model, masked_lm_loss, save_adapter,  # noqa: E402
                       text_hidden_states)


def log(msg, rank=0, me=None):
    if me is None or me == rank:
        print(msg, flush=True)


def setup():
    if "RANK" in os.environ:
        backend = "nccl" if torch.cuda.is_available() else "gloo"
        # a hang (copies waiting on different collectives) becomes an error after 40 min instead of burning quota;
        # the notebook then resumes from the last checkpoint
        dist.init_process_group(backend, timeout=datetime.timedelta(minutes=40))
        return dist.get_rank(), dist.get_world_size()
    return 0, 1


def all_sum(x, dev):
    t = torch.tensor(x, dtype=torch.float64, device=dev)
    if dist.is_initialized():
        dist.all_reduce(t)
    return t.item()


def from_rank0(x, dev):
    """Every copy takes rank 0's value: decisions that change the loop must be identical on all copies."""
    t = torch.tensor(x, dtype=torch.float64, device=dev)
    if dist.is_initialized():
        dist.broadcast(t, 0)
    return t.item()


def all_max(x, dev):
    t = torch.tensor(x, dtype=torch.float64, device=dev)
    if dist.is_initialized():
        dist.all_reduce(t, op=dist.ReduceOp.MAX)
    return t.item()


def load_model(args, rank):
    if torch.cuda.is_available():
        gpus = list(range(rank * args.gpus_per_rank, (rank + 1) * args.gpus_per_rank))
        if len(gpus) == 1:
            device_map, max_memory = {"": gpus[0]}, None
        else:
            device_map = "balanced"
            max_memory = {g: f"{int(torch.cuda.get_device_properties(g).total_memory / 2**30 * 0.45)}GiB" for g in gpus}
    else:
        gpus, device_map, max_memory = [], None, None
    model = load_int4_model(args.model, device_map=device_map, max_memory=max_memory, attn_implementation=args.attn)
    torch.manual_seed(args.seed)  # same LoRA init on every rank (also broadcast below)
    add_lora(model, r=args.r, alpha=args.alpha, dropout=args.dropout)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.config.use_cache = False
    model.train()
    return model, gpus


def lora_params(model):
    ps = []
    for _, mod in model.named_modules():
        if isinstance(mod, Int4LoRALinear) and mod.r:
            ps += [mod.lora_A, mod.lora_B]
    return ps


def load_adapter_weights(model, adapter_dir):
    """Put a saved PEFT adapter's LoRA weights into our model (to score an earlier adapter, e.g. v1)."""
    from safetensors.torch import load_file
    sd = load_file(str(Path(adapter_dir) / "adapter_model.safetensors"))
    n = 0
    for name, mod in model.named_modules():
        if isinstance(mod, Int4LoRALinear) and mod.r:
            mod.lora_A.data.copy_(sd[f"base_model.model.{name}.lora_A.weight"].to(mod.lora_A.device, torch.float32))
            mod.lora_B.data.copy_(sd[f"base_model.model.{name}.lora_B.weight"].to(mod.lora_B.device, torch.float32))
            n += 1
    return n


def first_device(model):
    return model.get_input_embeddings().weight.device


def segment_loss(model, sample, dev):
    ids = sample["input_ids"].long().unsqueeze(0).to(dev)
    labels = torch.where(sample["labels_mask"].unsqueeze(0).to(dev), ids, torch.full_like(ids, -100))
    hidden = text_hidden_states(model, ids)
    mean, n = masked_lm_loss(model, hidden, labels)
    return mean * n, n


def gpu_mem_gib(gpus):
    return max((torch.cuda.max_memory_allocated(g) / 2**30 for g in gpus), default=0.0)


def batches(items, world, accum, seed, epoch):
    """Global batches of world*accum segments; inside a batch, lengths are dealt so every rank gets a similar load."""
    order = list(range(len(items)))
    random.Random(seed * 1000 + epoch).shuffle(order)
    size = world * accum
    out = []
    for i in range(0, len(order), size):
        b = sorted(order[i:i + size], key=lambda j: -len(items[j]["input_ids"]))
        out.append([b[r::world] for r in range(world)])
    return out


def evaluate(model, val, rank, world, dev):
    model.eval()
    mine = sorted(range(len(val)), key=lambda j: -len(val[j]["input_ids"]))[rank::world]
    tot = n = 0.0
    with torch.no_grad():
        for j in mine:
            s, k = segment_loss(model, val[j], first_device(model))
            tot, n = tot + s.item(), n + k
    model.train()
    tot, n = all_sum(tot, dev), all_sum(n, dev)
    return tot / max(n, 1), int(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--samples", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-name", default="gemma-4-12b-it-qat-w4a16-ct")
    ap.add_argument("--gpus-per-rank", type=int, default=1)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--accum", type=int, default=2, help="segments per rank per optimizer step")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--min-lr-ratio", type=float, default=0.1)
    ap.add_argument("--warmup", type=int, default=8)
    ap.add_argument("--clip", type=float, default=1.0)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--dropout", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--attn", default="sdpa")
    ap.add_argument("--eval-every", type=int, default=0, help="steps between validation runs (0: --evals per run)")
    ap.add_argument("--evals", type=int, default=4, help="mid-run validations per run (when --eval-every is 0)")
    ap.add_argument("--early-stop-patience", type=int, default=0, help="stop when the mid-run validation loss has not "
                    "improved by --min-delta for this many validations in a row (0: off)")
    ap.add_argument("--min-delta", type=float, default=0.005)
    ap.add_argument("--val-max", type=int, default=24, help="validation segments used mid-run (0: all); start and "
                    "final always use all")
    ap.add_argument("--save-every", type=int, default=10, help="steps between resumable checkpoints")
    ap.add_argument("--max-hours", type=float, default=0, help="stop training in time (schedule re-planned to fit)")
    ap.add_argument("--extra-val", nargs="*", default=[], help="more samples files (e.g. Gemma's own runs): each split "
                    "in them is scored separately at the start and at the end")
    ap.add_argument("--score-adapter", default=None, help="adapter folder to score on every validation set before "
                    "training (e.g. v1), then training starts from a fresh LoRA")
    ap.add_argument("--probe", action="store_true", help="one rank: fwd+bwd on the longest train segment, report memory")
    ap.add_argument("--max-steps", type=int, default=0, help="tests: stop after this many steps")
    args = ap.parse_args()
    t_start = time.time()
    rank, world = setup()
    out = Path(args.out)
    if rank == 0:
        out.mkdir(parents=True, exist_ok=True)
    samples = torch.load(args.samples)
    train = [s for s in samples if s["split"] == "train"]
    val = [s for s in samples if s["split"] == "val"]
    extra = {}
    for f in args.extra_val:
        for s in torch.load(f):
            extra.setdefault(s["split"], []).append(s)
    log(f"ranks {world} x {args.gpus_per_rank} GPU(s) | train {len(train)} segments "
        f"{sum(len(s['input_ids']) for s in train) / 1e6:.2f}M tokens ({sum(int(s['labels_mask'].sum()) for s in train) / 1e6:.2f}M trained) "
        f"| val {len(val)} segments", 0, rank)

    t0 = time.time()
    model, gpus = load_model(args, rank)
    dev = first_device(model)
    params = lora_params(model)
    log(f"model loaded in {time.time() - t0:.0f}s on GPUs {gpus or 'cpu'}; LoRA r={args.r} alpha={args.alpha}: "
        f"{sum(p.numel() for p in params) / 1e6:.1f}M trainable params in {len(params)} tensors", 0, rank)

    if args.probe:
        s = max(train, key=lambda x: len(x["input_ids"]))
        if torch.cuda.is_available():
            for g in gpus:
                torch.cuda.reset_peak_memory_stats(g)
        t0 = time.time()
        loss_sum, n = segment_loss(model, s, dev)
        (loss_sum / n).backward()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        secs = time.time() - t0
        res = {"ok": True, "tokens": len(s["input_ids"]), "seconds": round(secs, 1),
               "tokens_per_s": round(len(s["input_ids"]) / secs, 1), "loss": round((loss_sum / n).item(), 4),
               "peak_gib": round(gpu_mem_gib(gpus), 2), "gpus_per_rank": args.gpus_per_rank}
        print("PROBE", json.dumps(res), flush=True)
        (out / f"probe_g{args.gpus_per_rank}.json").write_text(json.dumps(res))
        return

    if dist.is_initialized():  # identical start on every rank
        for p in params:
            t = p.data.to(dev)
            dist.broadcast(t, 0)
            p.data.copy_(t.to(p.device))
    opt = torch.optim.AdamW(params, lr=args.lr, betas=(0.9, 0.999), weight_decay=0.0)
    per_epoch = math.ceil(len(train) / (world * args.accum))
    plan = {"total": max(1, int(per_epoch * args.epochs))}

    def lr_at(step):  # linear warmup, cosine to min_lr_ratio over the (possibly re-planned) total
        if step < args.warmup:
            return args.lr * (step + 1) / args.warmup
        prog = min(1.0, (step - args.warmup) / max(1, plan["total"] - args.warmup))
        return args.lr * (args.min_lr_ratio + (1 - args.min_lr_ratio) * 0.5 * (1 + math.cos(math.pi * prog)))

    step, history = 0, []
    state_path = out / "last" / "trainer_state.pt"
    if state_path.exists():  # resume
        st = torch.load(state_path, map_location="cpu")
        for p, v in zip(params, st["lora"]):
            p.data.copy_(v.to(p.device))
        opt.load_state_dict(st["opt"])
        step, plan, history = st["step"], st["plan"], st["history"]
        log(f"RESUMED at step {step}/{plan['total']}", 0, rank)
    plan.setdefault("best", None)
    plan.setdefault("bad", 0)
    eval_every = args.eval_every or max(1, plan["total"] // (args.evals + 1))
    log(f"plan: {plan['total']} optimizer steps ({per_epoch}/epoch x {args.epochs} epochs), "
        f"{world * args.accum} segments per step, lr {args.lr} warmup {args.warmup} cosine->{args.min_lr_ratio}, "
        f"validation every {eval_every} steps", 0, rank)

    def save_state():  # resumable checkpoint (rank 0 only; no collectives)
        if rank != 0:
            return
        save_adapter(model, out / "last", args.base_name)
        torch.save({"lora": [p.detach().cpu() for p in params], "opt": opt.state_dict(), "step": step, "plan": plan,
                    "history": history}, str(state_path) + ".tmp")
        os.replace(str(state_path) + ".tmp", state_path)  # never a half-written checkpoint
        log(f"  checkpoint at step {step}", 0, rank)

    def save(tag):
        if rank != 0:
            return
        save_adapter(model, out / tag, args.base_name)
        save_adapter(model, out / "last", args.base_name)
        torch.save({"lora": [p.detach().cpu() for p in params], "opt": opt.state_dict(), "step": step, "plan": plan,
                    "history": history}, str(state_path) + ".tmp")
        os.replace(str(state_path) + ".tmp", state_path)  # never a half-written checkpoint
        (out / "history.json").write_text(json.dumps(history, indent=1))
        log(f"  saved adapter {out / tag}", 0, rank)

    eval_secs = {}

    def run_eval(tag):
        t0 = time.time()
        vs = sorted(val, key=lambda x: len(x["input_ids"]))
        if args.val_max and tag not in ("start", "final"):
            vs = vs[::max(1, len(vs) // args.val_max)][:args.val_max]
        loss, n = evaluate(model, vs, rank, world, dev)
        history.append({"type": "val", "tag": tag, "step": step, "val_loss": round(loss, 4), "val_tokens": n,
                        "segments": len(vs), "seconds": round(time.time() - t0)})
        eval_secs[tag] = (time.time() - t0, len(vs))
        log(f"VAL [{tag}] step {step}: loss {loss:.4f} over {n} trained tokens in {len(vs)} segments "
            f"({time.time() - t0:.0f}s)", 0, rank)
        return loss

    def run_extra(tag):  # the extra validation sets (Gemma's resolved / failed runs), full each time
        for split, segs in sorted(extra.items()):
            t0 = time.time()
            loss, n = evaluate(model, segs, rank, world, dev)
            history.append({"type": "val", "set": split, "tag": tag, "step": step, "val_loss": round(loss, 4),
                            "val_tokens": n, "segments": len(segs), "seconds": round(time.time() - t0)})
            log(f"VAL [{tag}] {split}: loss {loss:.4f} over {n} trained tokens in {len(segs)} segments "
                f"({time.time() - t0:.0f}s)", 0, rank)

    if step == 0 and args.score_adapter:  # score an earlier adapter on the same sets, then start fresh
        fresh = [p.detach().clone() for p in params]
        k = load_adapter_weights(model, args.score_adapter)
        log(f"scoring adapter {args.score_adapter} ({k} LoRA modules loaded)", 0, rank)
        if val:
            loss, n = evaluate(model, val, rank, world, dev)
            history.append({"type": "val", "set": "val", "tag": "scored_adapter", "step": 0, "val_loss": round(loss, 4),
                            "val_tokens": n, "segments": len(val)})
            log(f"VAL [scored_adapter] val: loss {loss:.4f} over {n} trained tokens in {len(val)} segments", 0, rank)
        run_extra("scored_adapter")
        for p, v in zip(params, fresh):
            p.data.copy_(v)
    if step == 0 and val:
        run_eval("start")
    if step == 0:
        run_extra("start")
    all_batches = [b for e in range(math.ceil(args.epochs)) for b in batches(train, world, args.accum, args.seed, e)]
    ema, t_train, steps_timed = None, time.time(), 0
    while step < plan["total"] and step < len(all_batches):
        if args.max_steps and step >= args.max_steps:
            break
        t0 = time.time()
        mine = [train[j] for j in all_batches[step][rank]]
        my_lab = sum(int(s["labels_mask"].sum()) for s in mine)
        g_lab = all_sum(my_lab, dev)
        for g in gpus:
            torch.cuda.reset_peak_memory_stats(g)
        tot = 0.0
        for s in mine:
            loss_sum, _ = segment_loss(model, s, dev)
            (loss_sum / g_lab).backward()
            tot += loss_sum.item()
        flat = torch.cat([(p.grad if p.grad is not None else torch.zeros_like(p)).flatten().to(dev) for p in params])
        if dist.is_initialized():
            dist.all_reduce(flat)
        gnorm = flat.norm().item()
        if args.clip and gnorm > args.clip:
            flat.mul_(args.clip / (gnorm + 1e-6))
        i = 0
        for p in params:
            k = p.numel()
            p.grad = flat[i:i + k].view_as(p).to(p.device)
            i += k
        lr = lr_at(step)
        for gr in opt.param_groups:
            gr["lr"] = lr
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        loss = all_sum(tot, dev) / max(g_lab, 1)
        toks = all_sum(sum(len(s["input_ids"]) for s in mine), dev)
        mem = all_max(gpu_mem_gib(gpus), dev)
        secs = time.time() - t0
        ema = loss if ema is None else 0.9 * ema + 0.1 * loss
        steps_timed += 1
        avg_step = (time.time() - t_train) / steps_timed
        if args.max_hours and steps_timed == 3:  # re-plan once the speed is known (rank 0 decides for everyone)
            full = eval_secs.get("start", (0.0, max(len(val), 1)))
            per_seg = full[0] / max(full[1], 1)
            n_mid = min(args.val_max or len(val), len(val))
            evals = per_seg * (len(val) + args.evals * n_mid + sum(len(v) for v in extra.values())) + 120  # final+mid+extra
            left = args.max_hours * 3600 - (time.time() - t_start) - evals
            fit = int(from_rank0(step + max(0, int(left / avg_step)), dev))
            if fit < plan["total"]:
                log(f"TIME BUDGET: {plan['total']} steps would take {plan['total'] * avg_step / 3600:.1f}h; "
                    f"re-planned to {fit} steps to finish within {args.max_hours}h", 0, rank)
                plan["total"] = fit
                eval_every = args.eval_every or max(1, fit // (args.evals + 1))
        eta = (plan["total"] - step) * avg_step
        history.append({"type": "train", "step": step, "loss": round(loss, 4), "ema": round(ema, 4), "lr": lr,
                        "grad_norm": round(gnorm, 4), "tokens": int(toks), "trained_tokens": int(g_lab),
                        "seconds": round(secs, 1), "mem_gib": round(mem, 2)})
        log(f"step {step:4}/{plan['total']} | loss {loss:.4f} (avg {ema:.4f}) | lr {lr:.2e} | grad {gnorm:.3f} | "
            f"{int(toks):6} tok ({int(g_lab)} trained) {toks / secs:6.0f} tok/s | mem {mem:.1f} GiB | "
            f"{secs:5.1f}s | ETA {eta / 60:5.1f} min", 0, rank)
        if step % eval_every == 0 and step < plan["total"]:
            stop = False
            if val:
                loss_v = run_eval(f"step{step}")  # the same 24-segment subset every time: comparable across steps
                if plan["best"] is None or loss_v < plan["best"] - args.min_delta:
                    plan["best"], plan["bad"] = loss_v, 0
                    save("best")
                    log(f"  new best mid-run validation loss {loss_v:.4f} -> saved as best", 0, rank)
                else:
                    plan["bad"] += 1
                    log(f"  no improvement over best {plan['best']:.4f} (by {args.min_delta}) for {plan['bad']} "
                        f"validation(s)", 0, rank)
                    stop = bool(args.early_stop_patience) and plan["bad"] >= args.early_stop_patience
            save(f"step_{step}")
            if from_rank0(1.0 if stop else 0.0, dev) > 0.5:  # rank 0 decides for every copy
                log(f"EARLY STOP at step {step}: validation loss plateaued ({plan['bad']} validations without "
                    f"improvement); final validation + save next", 0, rank)
                break
        elif step % args.save_every == 0:
            save_state()
    if val:
        run_eval("final")
    run_extra("final")
    save("final")
    if rank == 0:
        vals = [h for h in history if h["type"] == "val"]
        log("\nVALIDATION LOSS: " + " | ".join(f"{h.get('set', 'val')}@{h['tag']} {h['val_loss']}" for h in vals), 0, rank)
        log(f"done: {step} steps in {(time.time() - t_start) / 3600:.2f}h -> {out / 'final'}", 0, rank)
    if dist.is_initialized():
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
