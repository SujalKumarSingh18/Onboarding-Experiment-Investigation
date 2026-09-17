#!/usr/bin/env python3
"""
Supplementary robustness checks referenced in ANSWERS.md (including the dead ends).

Stdlib only. Usage:
    python checks.py path/to/experiment_results.csv
"""

import csv
import math
import sys
from collections import defaultdict

PATH = sys.argv[1] if len(sys.argv) > 1 else "experiment_results.csv"

rows = list(csv.DictReader(open(PATH, newline="", encoding="utf-8-sig")))
for r in rows:
    r["converted"] = int(r["converted"])
    r["uid"] = int(r["user_id"])

SEGMENTS = sorted({r["segment"] for r in rows})


def ztest(c1, n1, c2, n2):
    """Two-sided pooled z-test on p1 - p2. Returns (diff_pp, z, p)."""
    p1, p2 = c1 / n1, c2 / n2
    pp = (c1 + c2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    return (p1 - p2) * 100, z, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def split(subset):
    c = [r for r in subset if r["variant"] == "control"]
    t = [r for r in subset if r["variant"] == "treatment"]
    return c, t


def lift_of(subset):
    c, t = split(subset)
    return ztest(sum(x["converted"] for x in t), len(t),
                 sum(x["converted"] for x in c), len(c)), len(c), len(t)


# ---- Check 1 (DEAD END): does user_id encode signup order / time-of-month?
print("== check 1: is there a time/order signal hidden in user_id? (dead end) ==")
print("uid range overall:", min(r['uid'] for r in rows), "-", max(r['uid'] for r in rows))
for v in ("control", "treatment"):
    s = [r["uid"] for r in rows if r["variant"] == v]
    print(f"  {v:<10} min={min(s)} max={max(s)} mean={sum(s)/len(s):.0f}")
for seg in SEGMENTS:
    s = [r["uid"] for r in rows if r["segment"] == seg]
    print(f"  {seg:<12} mean uid={sum(s)/len(s):.0f}  n={len(s)}")
print("  -> both variants and all segments span the same id range with the same mean:")
print("     user_id is a plain unique key, no ramp/time structure to exploit.\n")

# ---- Check 2: is the app_store effect stable, or driven by a sub-slice?
print("== check 2: app_store lift split into two pseudo-random halves (uid parity) ==")
for half in (0, 1):
    sub = [r for r in rows if r["segment"] == "app_store" and r["uid"] % 2 == half]
    (lift, _, p), n_c, n_t = lift_of(sub)
    print(f"  uid%2=={half}: n_c={n_c} n_t={n_t}  lift={lift:+.2f} pp  p={p:.3g}")
print("  -> positive and significant in both halves; not a single odd sub-slice.\n")

# ---- Check 3 (DEAD END): just drop app_store -- does the topline lift go away?
print("== check 3: pooled lift with app_store removed (dead end) ==")
(lift, _, p), n_c, n_t = lift_of([r for r in rows if r["segment"] != "app_store"])
print(f"  lift={lift:+.2f} pp  p={p:.3g}  n_c={n_c} n_t={n_t}")
print("  -> still ~+6 pp, because the segment-mix imbalance (not app_store) drives the")
print("     topline. Dropping a segment does not fix confounding; standardizing does.\n")

# ---- Check 4: sensitivity of the mix-adjusted number to the choice of weights
tab = defaultdict(lambda: {"control": [0, 0], "treatment": [0, 0]})
for r in rows:
    cell = tab[r["segment"]][r["variant"]]
    cell[0] += 1
    cell[1] += r["converted"]
tot = len(rows)
tot_c = sum(d["control"][0] for d in tab.values())
tot_t = sum(d["treatment"][0] for d in tab.values())

print("== check 4: mix-adjusted lift under different standardization weights ==")
for wname in ("total", "control", "treatment"):
    mix = 0.0
    for seg, d in tab.items():
        n_c, c_c = d["control"]
        n_t, c_t = d["treatment"]
        w = {"total": (n_c + n_t) / tot, "control": n_c / tot_c, "treatment": n_t / tot_t}[wname]
        mix += w * ((c_t / n_t) - (c_c / n_c)) * 100
    print(f"  weights = {wname:<10} {mix:+.4f} pp")
print("  -> +1.5 to +1.8 pp whichever population we standardize to; the assignment")
print("     asks for total-population weights, i.e. +1.63 pp.\n")

# ---- Check 5: direct standardization of each arm's conversion rate
print("== check 5: directly standardized conversion rates (total-population mix) ==")
std = {}
for v in ("control", "treatment"):
    std[v] = sum(((d["control"][0] + d["treatment"][0]) / tot) * (d[v][1] / d[v][0])
                 for d in tab.values()) * 100
    print(f"  {v:<10} {std[v]:.2f}%")
print(f"  difference = {std['treatment'] - std['control']:+.2f} pp"
      "  (matches the Q3 weighted-lift sum, as it must)\n")

# ---- Check 6: how fragile is the influencer number?
print("== check 6: fragility of the small segments ==")
for seg in ("influencer", "app_store"):
    n_c, c_c = tab[seg]["control"]
    n_t, c_t = tab[seg]["treatment"]
    print(f"  {seg:<11} {c_c}/{n_c} = {c_c/n_c*100:.2f}%  ->  {c_t}/{n_t} = {c_t/n_t*100:.2f}%"
          f"   relative {((c_t/n_t)/(c_c/n_c)-1)*100:+.1f}%")
    print(f"              5 conversions either way in treatment moves it {500/n_t:.1f} pp")

# ---- Check 7 (DEAD END): are the flat segments hiding offsetting subgroups?
print("\n== check 7: flat segments re-split by uid parity (dead end) ==")
for seg in ("paid_search", "organic", "referral"):
    for half in (0, 1):
        sub = [r for r in rows if r["segment"] == seg and r["uid"] % 2 == half]
        (lift, _, p), n_c, n_t = lift_of(sub)
        print(f"  {seg:<12} uid%2=={half}: n_c={n_c:5d} n_t={n_t:5d}"
              f"  lift={lift:+7.2f} pp  p={p:.3g}")
print("  -> every half is flat and non-significant; no masked win hiding in the big")
print("     segments, they really are unaffected by the new flow.")

# ---- Check 8: segment mix inside each arm (the source of the Simpson's paradox)
print("\n== check 8: segment mix within each arm ==")
arm_n = {v: sum(d[v][0] for d in tab.values()) for v in ("control", "treatment")}
print(f"  {'segment':<13}{'% of control':>14}{'% of treatment':>16}{'CR (pooled)':>13}")
for seg in SEGMENTS:
    d = tab[seg]
    cr = (d["control"][1] + d["treatment"][1]) / (d["control"][0] + d["treatment"][0]) * 100
    print(f"  {seg:<13}{d['control'][0]/arm_n['control']*100:13.2f}%"
          f"{d['treatment'][0]/arm_n['treatment']*100:15.2f}%{cr:12.2f}%")
print("  -> treatment is loaded with organic (best-converting) and starved of paid_search")
print("     (worst-converting); that composition gap is what inflates the topline.")
