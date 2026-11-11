"""Turn data/analysis/stats_model.json into the 9 datasets of the "Run Bank Statistics" page
(https://claude.ai/artifact/Mf8mXPF6ToLNonBi5ARNpQ). Usage (repo root, after run_model.py):
    .venv/bin/python scripts/stats/export_dash.py OUT_DIR
Then upload each OUT_DIR/<name>.json as an asset of the page and point datasets/<name>.source.url at its /_blob/ url.
The luck rows leave out the whole-run totals (ALL ARMS): the chart shares one scale and per-arm rows are 0-6 solves."""
import json, os, sys

S = sys.argv[1]
os.makedirs(S, exist_ok=True)
m = json.load(open("data/analysis/stats_model.json"))
OURS = {"evidc", "evidd", "evide", "combo1", "pub024"}
r = lambda x, k=4: round(float(x), k)
agents = [dict(agent=a["agent"], runs=a["runs"], solved=a["solved"], raw_rate=r(a["raw_rate"]), dev16=r(a["dev16"]), dev16_lo=r(a["dev16_lo"]),
               dev16_hi=r(a["dev16_hi"]), dev16_runs=a["dev16_runs"], mean_agent_s=round(a["mean_agent_s"]), ours=a["agent"] in OURS) for a in m["agents"]]
tp = {(p["a"], p["b"]): p for p in m["time_pairs"]}
alt = {(p["a"], p["b"]): p for p in m.get("pairs_axt030", [])}
pairs = []
for p in m["pairs"]:
    t = tp.get((p["a"], p["b"]), {}); q = alt[(p["a"], p["b"])]
    pairs.append(dict(pair=f"{p['a']} vs {p['b']}", a=p["a"], b=p["b"], diff_pts=r(100 * p["diff"], 2), lo_pts=r(100 * p["lo"], 2), hi_pts=r(100 * p["hi"], 2),
                      p_better=r(p["p_better"], 3), same_run_pairs=p["same_run_pairs"], wins=p["plus"], losses=p["minus"], sign_p=r(p["sign_p"], 3),
                      alt_diff_pts=r(100 * q["diff"], 2), alt_lo_pts=r(100 * q["lo"], 2), alt_hi_pts=r(100 * q["hi"], 2),
                      time_diff_s=r(t.get("diff_s", 0), 1), time_lo_s=r(t.get("lo", 0), 1), time_hi_s=r(t.get("hi", 0), 1)))
short = lambda f: f.split("_", 1)[1].replace("skill_", "")
draws = [dict(draw=short(d["draw"]), date=d["draw"][:10], runs=d["runs"], solved=d["solved"], effect=r(d["effect"], 3), lo=r(d["lo"], 3), hi=r(d["hi"], 3)) for d in m["draws"]]
luck = []
for x in m["luck"]:
    if x["arm"] == "ALL ARMS":
        continue
    v = "lucky" if x["percentile"] >= 0.95 else "unlucky" if x["percentile"] <= 0.05 else "within luck"
    luck.append(dict(run=short(x["draw"]), date=x["draw"][:10], arm=x["arm"], row=f"{short(x['draw'])} · {x['arm']}", runs=x["runs"], observed=x["observed"],
                     expected=r(x["expected"], 2), lo=x["lo"], hi=x["hi"], percentile=r(x["percentile"], 3), verdict=v, scored_as=x.get("scored_as") or ""))
noise = [dict(runs_per_arm=v["runs_per_arm"], passes=int(k), band_lo=v["band90"][0], band_hi=v["band90"][1], sd=r(v["sd"], 2)) for k, v in sorted(m["noise"].items(), key=lambda kv: int(kv[0]))]
power = []
for row in m["power"]:
    for k, v in row.items():
        if k.startswith("power_"):
            n = int(k.split("_")[1])
            power.append(dict(gain_pts=row["gain_pp"], runs_per_arm=n, power=r(v, 3), needed_gap=row[f"needed_gap_{n}"]))
names = {"task": "Task difficulty", "agent": "Agent", "draw": "Draw (whole notebook run)", "agent_x_task": "Agent x task"}
variance = [dict(component=names[k], key=k, solve_share=r(m["shares"][k]), solve_sigma_logit=r(m["sigma"][k], 3), time_share=r(m["time_shares"][k]),
                 time_sigma_s=r(m["time_sigma"][k], 1)) for k in ("task", "agent", "draw", "agent_x_task")]
variance.append(dict(component="Single-run chance", key="chance", solve_share=r(m["shares"]["run-level chance"]), solve_sigma_logit=None,
                     time_share=r(m["time_shares"]["run-level"]), time_sigma_s=r(m["time_resid"], 1)))
tasks = [dict(task=t["task"], runs=t["runs"], solved=t["solved"], rate=r(t["rate"]), lo=r(t["lo"]), hi=r(t["hi"]), dev16=t["dev16"]) for t in m["tasks"]]
best = max(agents, key=lambda a: a["dev16"]); worst = min(agents, key=lambda a: a["dev16"])
model_date = max(d["draw"][:10] for d in m["draws"])
summary = [dict(n_runs=m["n_runs"], n_tasks=m["n_tasks"], n_agents=m["n_agents"], n_draws=m["n_draws"], base_dev16=r(m["base_dev16"]),
                task_share=r(m["shares"]["task"]), agent_spread_pts=r(100 * (best["dev16"] - worst["dev16"]), 1),
                band_16_runs=int(m["noise"]["1"]["band90"][1]), band_32_runs=int(m["noise"]["2"]["band90"][1]),
                pairs_clear=sum(1 for p in pairs if p["lo_pts"] > 0 or p["hi_pts"] < 0), pairs_total=len(pairs),
                runs_for_10pts=next((p["runs_per_arm"] for p in power if p["gain_pts"] == 10 and p["power"] >= 0.8), None),
                model_date=model_date)]
for name, rows in (("agents", agents), ("pairs", pairs), ("draws", draws), ("luck", luck), ("noise", noise), ("power", power), ("variance", variance),
                   ("tasks", tasks), ("summary", summary)):
    json.dump(rows, open(os.path.join(S, f"{name}.json"), "w"))
    print(name, len(rows), os.path.getsize(os.path.join(S, f"{name}.json")))
print(summary)
