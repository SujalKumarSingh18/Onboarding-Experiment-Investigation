#!/usr/bin/env python3
"""
Onboarding A/B test investigation.

Stdlib only (csv + math). Usage:
    python analyze.py [path/to/experiment_results.csv]

Prints every number quoted in ANSWERS.md and writes answers.json.
"""

import csv
import json
import math
import os
import sys
from collections import defaultdict

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "experiment_results.csv"
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "answers.json")

VARIANTS = ("control", "treatment")


# ---------------------------------------------------------------- load + hygiene
def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["segment"] = r["segment"].strip()
        r["variant"] = r["variant"].strip()
        r["converted"] = int(r["converted"])
    return rows


def hygiene(rows):
    ids = [r["user_id"] for r in rows]
    print("== data hygiene ==")
    print(f"rows                : {len(rows)}")
    print(f"unique user_id      : {len(set(ids))}  (dupes: {len(ids) - len(set(ids))})")
    print(f"segments            : {sorted({r['segment'] for r in rows})}")
    print(f"variants            : {sorted({r['variant'] for r in rows})}")
    print(f"converted values    : {sorted({r['converted'] for r in rows})}")
    blanks = sum(1 for r in rows if not r["segment"] or not r["variant"])
    print(f"blank segment/variant: {blanks}")
    print()


# ---------------------------------------------------------------- stats helpers
def rate(conv, n):
    return conv / n if n else float("nan")


def two_prop_z(c1, n1, c2, n2):
    """Two-sided z-test for p1 - p2 (pooled). Returns (diff_pp, z, p_value)."""
    if not n1 or not n2:
        return float("nan"), float("nan"), float("nan")
    p1, p2 = c1 / n1, c2 / n2
    p_pool = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return (p1 - p2) * 100, float("nan"), float("nan")
    z = (p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return (p1 - p2) * 100, z, p


def diff_ci95(c1, n1, c2, n2):
    """Unpooled 95% CI on p1 - p2, in percentage points."""
    p1, p2 = c1 / n1, c2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = (p1 - p2) * 100
    return d - 1.96 * se * 100, d + 1.96 * se * 100


# ---------------------------------------------------------------- tabulation
def tabulate(rows):
    """seg -> variant -> {'n': int, 'conv': int}"""
    t = defaultdict(lambda: {v: {"n": 0, "conv": 0} for v in VARIANTS})
    for r in rows:
        cell = t[r["segment"]][r["variant"]]
        cell["n"] += 1
        cell["conv"] += r["converted"]
    return t


def main():
    rows = load(CSV_PATH)
    hygiene(rows)
    tab = tabulate(rows)
    # order segments largest-population first, for readability
    segments = sorted(tab, key=lambda s: -(tab[s]["control"]["n"] + tab[s]["treatment"]["n"]))
    total_n = len(rows)

    # ---------------- Q1: naive overall
    tot = {v: {"n": 0, "conv": 0} for v in VARIANTS}
    for s in segments:
        for v in VARIANTS:
            tot[v]["n"] += tab[s][v]["n"]
            tot[v]["conv"] += tab[s][v]["conv"]

    n_c, n_t = tot["control"]["n"], tot["treatment"]["n"]
    cr_c = rate(tot["control"]["conv"], n_c)
    cr_t = rate(tot["treatment"]["conv"], n_t)
    naive_pp = (cr_t - cr_c) * 100
    _, z_all, p_all = two_prop_z(tot["treatment"]["conv"], n_t, tot["control"]["conv"], n_c)

    print("== Q1: naive overall ==")
    print(f"control   : n={n_c:6d}  conv={tot['control']['conv']:5d}  cr={cr_c*100:6.2f}%")
    print(f"treatment : n={n_t:6d}  conv={tot['treatment']['conv']:5d}  cr={cr_t*100:6.2f}%")
    print(f"naive lift: {naive_pp:+.4f} pp  (rounded {naive_pp:+.2f} pp)   z={z_all:.2f}  p={p_all:.3g}")
    print()

    # ---------------- Q2: by segment
    print("== Q2: by segment ==")
    hdr = (f"{'segment':<13}{'n_ctrl':>7}{'cr_ctrl':>9}{'n_trt':>7}{'cr_trt':>9}"
           f"{'lift_pp':>10}{'95% CI (pp)':>22}{'p':>10}{'pop_share':>11}{'%_in_trt':>10}")
    print(hdr)
    print("-" * len(hdr))
    seg_stats = {}
    for s in segments:
        c, t = tab[s]["control"], tab[s]["treatment"]
        seg_n = c["n"] + t["n"]
        lift, z, p = two_prop_z(t["conv"], t["n"], c["conv"], c["n"])
        lo, hi = diff_ci95(t["conv"], t["n"], c["conv"], c["n"])
        share = seg_n / total_n
        pct_trt = t["n"] / seg_n * 100
        seg_stats[s] = {
            "n_control": c["n"], "n_treatment": t["n"], "n_total": seg_n,
            "conv_control": c["conv"], "conv_treatment": t["conv"],
            "cr_control_pct": rate(c["conv"], c["n"]) * 100,
            "cr_treatment_pct": rate(t["conv"], t["n"]) * 100,
            "lift_pp": lift, "ci95_lo_pp": lo, "ci95_hi_pp": hi,
            "z": z, "p_value": p,
            "pop_share": share, "pct_in_treatment": pct_trt,
        }
        print(f"{s:<13}{c['n']:>7}{rate(c['conv'], c['n'])*100:>8.2f}%{t['n']:>7}"
              f"{rate(t['conv'], t['n'])*100:>8.2f}%{lift:>+10.2f}"
              f"{f'[{lo:+.2f}, {hi:+.2f}]':>22}{p:>10.3g}{share*100:>10.2f}%{pct_trt:>9.1f}%")
    print()

    # ---------------- Q3: mix-adjusted (standardized) lift
    print("== Q3: mix-adjusted lift (weight each segment's lift by its share of TOTAL users) ==")
    mix = 0.0
    for s in segments:
        st = seg_stats[s]
        contrib = st["pop_share"] * st["lift_pp"]
        mix += contrib
        print(f"{s:<13} share={st['pop_share']:.6f} x lift={st['lift_pp']:+8.4f} pp"
              f" = {contrib:+8.4f} pp")
    print(f"{'TOTAL':<13} mix-adjusted lift = {mix:+.4f} pp  ->  {mix:+.2f} pp")
    print(f"Q1 naive = {naive_pp:+.2f} pp ; gap = {naive_pp - mix:+.2f} pp")
    print()

    # ---------------- Q5: assignment balance
    print("== Q5: assignment balance ==")
    overall_trt_share = n_t / total_n
    print(f"overall share in treatment: {overall_trt_share*100:.2f}%")
    chi2 = 0.0
    for s in segments:
        st = seg_stats[s]
        exp_t = st["n_total"] * overall_trt_share
        exp_c = st["n_total"] * (1 - overall_trt_share)
        chi2 += (st["n_treatment"] - exp_t) ** 2 / exp_t + (st["n_control"] - exp_c) ** 2 / exp_c
        print(f"{s:<13} n={st['n_total']:>6}  in_treatment={st['pct_in_treatment']:>6.2f}%"
              f"  (expected {overall_trt_share*100:.2f}% -> {exp_t:8.1f} vs actual {st['n_treatment']})")
    print(f"chi-square (homogeneity of treatment share across segments) = {chi2:.1f}, df={len(segments)-1}")
    print()

    # ---------------- Q2/Q4 picks, derived from the numbers rather than hand-typed
    # untrustworthy: biggest absolute lift among segments that are small / not significant
    untrusted = max(
        (s for s in segments if seg_stats[s]["p_value"] > 0.05 or seg_stats[s]["n_total"] / total_n < 0.05),
        key=lambda s: abs(seg_stats[s]["lift_pp"]),
    )
    # real effect: significant positive lift, largest by population contribution
    real_candidates = [s for s in segments
                       if seg_stats[s]["lift_pp"] > 0
                       and seg_stats[s]["p_value"] < 0.05
                       and seg_stats[s]["ci95_lo_pp"] > 0]
    real = max(real_candidates, key=lambda s: seg_stats[s]["pop_share"] * seg_stats[s]["lift_pp"]) \
        if real_candidates else "none"

    print("== derived picks ==")
    print(f"Q2 untrustworthy segment : {untrusted}")
    print(f"Q4 real-effect segment   : {real}  (candidates: {real_candidates or 'none'})")
    print()

    answers = {
        "q1_naive_lift_pp": round(naive_pp, 2),
        "q1_n_control": n_c,
        "q1_n_treatment": n_t,
        "q2_untrustworthy_segment": untrusted,
        "q3_mix_adjusted_lift_pp": round(mix, 2),
        "q4_real_effect_segment": real,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(answers, fh, indent=2)
        fh.write("\n")
    print("wrote", OUT_JSON)
    print(json.dumps(answers, indent=2))


if __name__ == "__main__":
    main()
