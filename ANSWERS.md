# Onboarding Experiment Investigation — Answers

**Data:** `experiment_results.csv`, 14,000 rows, 14,000 unique `user_id` (no duplicates, no
blank segments/variants, `converted` only ever 0 or 1).

**Code:** `analyze.py` produces every number in Q1–Q5 and writes `answers.json`.
`checks.py` holds the robustness checks and dead ends described at the bottom.

```
python analyze.py path/to/experiment_results.csv
python checks.py  path/to/experiment_results.csv
```

**Headline:** the topline +6.61 pp is mostly a mix artifact. Treatment was handed a much
better pool of users than control. After adjusting for that, the flow is worth about
+1.63 pp overall, and essentially all of it comes from one segment, `app_store`.

---

## Q1 — Naive overall difference

| variant | users | conversions | conversion rate |
|---|---|---|---|
| control | 7,136 | 1,414 | 19.82% |
| treatment | 6,864 | 1,814 | 26.43% |
| **difference** | | | **+6.61 pp** (6.6127 pp) |

Two-proportion z-test: z = 9.29, p < 1e-19. So the topline gap is real as a *description*
of the two groups — it just isn't an effect of the flow, as Q3 shows.

Method: count rows and sum `converted` per variant, take the difference of the two rates.

## Q2 — By segment

Segments ordered by share of total users. Lift = treatment rate − control rate, in
percentage points. CI is an unpooled 95% interval on the difference; p is a two-sided
two-proportion z-test.

| segment | n control | CR control | n treatment | CR treatment | lift (pp) | 95% CI (pp) | p | % of all users | % of segment in treatment |
|---|---|---|---|---|---|---|---|---|---|
| paid_search | 3,353 | 15.18% | 1,459 | 14.39% | −0.79 | [−2.96, +1.39] | 0.48 | 34.37% | 30.3% |
| organic | 1,298 | 35.29% | 2,917 | 35.07% | −0.21 | [−3.34, +2.91] | 0.89 | 30.11% | 69.2% |
| referral | 1,441 | 23.46% | 1,397 | 26.27% | +2.81 | [−0.37, +5.99] | 0.083 | 20.27% | 49.2% |
| app_store | 925 | 8.76% | 960 | 20.00% | **+11.24** | [+8.13, +14.36] | 4.1e-12 | 13.46% | 50.9% |
| influencer | 119 | 23.53% | 131 | 16.79% | −6.74 | [−16.69, +3.22] | 0.18 | 1.79% | 52.4% |

The first thing to notice: in three of five segments the new flow does nothing
(`paid_search` and `organic` are flat to slightly negative, `referral` is positive but not
significant). Yet the pooled number is +6.61 pp. That mismatch is the whole story, and Q3
explains it.

**The segment I would not trust: `influencer`.** Its lift is the second largest in the
table by absolute size (−6.74 pp, a −29% relative swing), and it is worth nothing:

- The whole segment is 250 users — 1.79% of the file — split 119 control / 131 treatment.
- That's 28 conversions in control and 22 in treatment. Five conversions either way moves
  the treatment rate by ~3.8 pp, so a handful of coin flips would flip the sign.
- The 95% CI is [−16.69, +3.22] pp, i.e. 20 points wide and straddling zero (p = 0.18).
  The data are consistent with anything from a large harm to a moderate gain.

It happened to land negative here, but the point is symmetric: had the same noise come out
+6.7 pp, someone would be quoting `influencer` as a second success story, and it would be
just as meaningless. `referral` (+2.81 pp, p = 0.083) is the other one I'd hold loosely —
directionally encouraging, not yet decision-grade, and worth more exposure before calling it.

## Q3 — Mix-adjusted overall lift

Each segment's own lift, weighted by that segment's share of **all 14,000 users**
(direct standardization to the total population):

| segment | population share | segment lift (pp) | contribution (pp) |
|---|---|---|---|
| paid_search | 4,812 / 14,000 = 0.343714 | −0.7870 | −0.2705 |
| organic | 4,215 / 14,000 = 0.301071 | −0.2148 | −0.0647 |
| referral | 2,838 / 14,000 = 0.202714 | +2.8146 | +0.5706 |
| app_store | 1,885 / 14,000 = 0.134643 | +11.2432 | +1.5138 |
| influencer | 250 / 14,000 = 0.017857 | −6.7355 | −0.1203 |
| **total** | 1.000000 | | **+1.6289** |

**Mix-adjusted overall lift = +1.63 pp** (vs +6.61 pp naive).

Equivalently, standardizing each arm's conversion rate to the total-population segment
mix gives control 22.20% and treatment 23.82%, a difference of +1.63 pp — the same number
from the other direction (`checks.py`, check 5).

**Why it differs from Q1.** The variants were not given the same kind of users, so the
naive comparison is measuring the mix as much as the flow. `paid_search`, the worst-
converting segment at ~15%, makes up 47% of control but only 21% of treatment; `organic`,
the best-converting at ~35%, is 18% of control and 42% of treatment. Treatment's pool is
therefore loaded with users who were always going to convert more, which inflates its
overall rate no matter what the flow does. Weighting every segment by its share of the
whole population removes that difference in composition and leaves roughly a quarter of the
apparent gain. This is a straight Simpson's paradox: the pooled direction (+6.6 pp) is not
the direction of the within-segment effects, three of which are flat or negative.

## Q4 — Where the flow has a real effect

**`app_store`** — that is the one segment I'd defend, and it's the only one.

- Effect size: 8.76% → 20.00%, **+11.24 pp**, a +128% relative improvement. That's large
  enough to matter commercially, not just statistically.
- Precision: n = 1,885 (925 / 960), 95% CI [+8.13, +14.36] pp, p = 4.1e-12. The entire
  interval is far from zero, and the lower bound alone (+8 pp) would justify shipping.
- It is not a mix artifact: `app_store` is split 50.9% / 49.1% between the arms, the most
  balanced segment in the file apart from `referral`, so no reweighting is needed to
  believe it.
- It survives slicing. Splitting the segment into two pseudo-random halves by `user_id`
  parity gives +8.56 pp (p = 0.0001) and +13.94 pp (p = 4e-9). Both halves agree in
  direction and significance, so the result isn't one strange sub-slice.
- It accounts for +1.51 pp of the +1.63 pp mix-adjusted total, i.e. 93% of the whole
  adjusted gain, despite being only 13.5% of users.

The story is also plausible: app-store installs likely hit the most friction in the old
flow (8.76% was the worst baseline of any segment by a wide margin), so that's where a
better onboarding has the most room to work.

Everything else is either flat (`paid_search` −0.79 pp, `organic` −0.21 pp, both
comfortably inside noise) or too thin to call (`referral`, `influencer`).

**Recommendation:** ship the new flow to `app_store` and keep it there. Don't roll out to
everyone on the strength of +6.61 pp — that number is mostly composition. Fix the
assignment problem in Q5, then run a clean test on `referral` to settle its +2.81 pp.

## Q5 — Bonus: how users were assigned

Overall 6,864 / 14,000 = 49.03% of users are in treatment, which looks like a clean 50/50
until you split by segment:

| segment | n | in control | in treatment | expected @ 49.03% | actual treatment |
|---|---|---|---|---|---|
| paid_search | 4,812 | 69.68% | **30.32%** | 2,359 | 1,459 |
| organic | 4,215 | 30.79% | **69.21%** | 2,067 | 2,917 |
| referral | 2,838 | 50.78% | 49.22% | 1,391 | 1,397 |
| app_store | 1,885 | 49.07% | 50.93% | 924 | 960 |
| influencer | 250 | 47.60% | 52.40% | 123 | 131 |

Yes, this is broken. `referral`, `app_store` and `influencer` sit within a couple of points
of 50/50, exactly as a random split should. `paid_search` and `organic` do not:
`paid_search` got 30% treatment and `organic` got 69%, in opposite directions and by ~19-20
points each. A chi-square test of whether the treatment share is homogeneous across
segments gives χ² ≈ 1,364 on 4 df, which is not something randomization produces — for
context, a fair split would put χ² around 4.

So assignment was not random with respect to `segment`. Two conclusions follow:

1. **The topline number is unusable as it stands.** Treatment is overweighted toward the
   high-converting `organic` segment and underweighted on the low-converting
   `paid_search`, which manufactures most of the +6.61 pp. Any pooled metric from this
   test — conversion, and likely revenue or retention too — carries the same bias.
2. **Something conditioned the bucketing on acquisition channel.** The pattern (two
   channels badly skewed in opposite directions, three clean) smells like a hashing or
   targeting bug, e.g. the channel string feeding the bucketing hash, a rollout rule that
   excluded paid traffic, or separate paid/organic landing paths each with their own
   assignment. Worth checking before anyone trusts another readout from this framework.

The within-segment comparisons are still usable, since the imbalance is *between*
segments — inside `app_store` the 50.9/49.1 split looks random, so its +11.24 pp stands.
But I'd want to know the cause before extending that trust further; whatever skewed the
split on channel could have skewed it on something we can't see in this file.

---

## Investigation process

- Loaded the CSV with the stdlib `csv` module and checked hygiene first: 14,000 rows,
  14,000 distinct `user_id`, five segments, two variants, `converted` strictly 0/1, no
  blanks. Nothing to clean, so no cleaning decisions to defend.
- Computed the naive topline (+6.61 pp, p < 1e-19) and treated the tiny p-value as a
  warning rather than a result — a gap that large on 14k users usually means the groups
  differ in more than the treatment.
- Cut by segment. Three of five segments flat or negative while the pooled number was
  strongly positive is the signature of Simpson's paradox, so the next question was the mix
  rather than the effect.
- Checked exposure by segment and found it: 30% treatment in `paid_search` vs 69% in
  `organic`, and those are the lowest- and highest-converting segments respectively. That
  single fact explains the topline.
- Standardized to the total-population mix for Q3 (+1.63 pp) and confirmed it two ways:
  as a weighted sum of segment lifts, and as the difference of two directly standardized
  arm rates (22.20% vs 23.82%). Both give +1.63 pp, which they must.
- Tested how much the choice of weights matters: total-population +1.63 pp, control-mix
  +1.50 pp, treatment-mix +1.76 pp. The conclusion holds regardless, so the answer isn't
  an artifact of the weighting scheme the assignment happened to specify.
- Attached CIs and z-tests to every segment before ranking them, so "impressive" and
  "trustworthy" were decided by interval width and sample size instead of by eyeballing
  the lift column. That's what separates `app_store` (+11.24, CI [+8.13, +14.36]) from
  `influencer` (−6.74, CI [−16.69, +3.22]).
- Stress-tested the `app_store` result by splitting it into `user_id`-parity halves; both
  halves came back positive and significant, so I stopped worrying it was one odd slice.
- Quantified the `influencer` fragility rather than asserting it: with 131 treatment users,
  five conversions either way is 3.8 pp, so a 6.7 pp swing is within coin-flip range.
- **Dead end 1:** looked for a time or ramp signal hidden in `user_id` (a staged rollout
  would explain the skew and change the analysis). Both arms span 100,001–114,000 with
  means of 107,002 and 106,999, and every segment's mean id is within ~250 of the others.
  It's a plain unique key with no ordering to exploit.
- **Dead end 2:** tried simply dropping `app_store` to see whether the topline lift was
  "just" that segment. It stayed at +6.01 pp (p = 1.4e-14), because the driver is the
  `paid_search`/`organic` imbalance, not `app_store`. Removing a segment doesn't fix
  confounding; standardizing does. Worth having tried, since it rules out the
  one-segment-carries-everything explanation for the *naive* number specifically.
- **Dead end 3:** checked whether the flat segments were hiding offsetting subgroups by
  re-splitting `paid_search` and `organic` on `user_id` parity. Both halves were flat too,
  so there's no masked win in the big segments — they really are unaffected.
