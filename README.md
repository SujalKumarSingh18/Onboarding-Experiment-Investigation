# Onboarding Experiment Investigation

## Project overview

This project investigates an A/B test of a new onboarding flow. Its central question is whether the new flow improved conversion, and, crucially, whether the apparent overall improvement can be trusted once acquisition-channel differences are considered.

The supplied assignment asks for an investigation rather than a simple topline readout. The implementation finds that the unadjusted result is substantially distorted by an uneven treatment/control split across user segments. The defensible result is a strong improvement for `app_store` users, not evidence to roll the flow out to every segment.

## Original problem statement and objective

The assignment PDF describes an onboarding-flow experiment with users assigned to either the existing flow (`control`) or new flow (`treatment`). It asks the analyst to investigate the conversion result across five questions:

1. Calculate the naive, overall conversion lift.
2. Break results down by user segment and identify a segment result that should not be trusted.
3. Calculate a mix-adjusted overall lift using each segment's share of all users.
4. Identify whether any segment has a meaningful positive effect.
5. As a bonus, check whether treatment/control assignment proportions are balanced across segments.

The intended decision is therefore not merely “which aggregate rate is larger?” It is whether the new flow genuinely works, for whom it works, and whether the experimental assignment makes the aggregate comparison reliable.

## Dataset

The source dataset is `experiment_results.csv`. It contains **14,000 rows**, one per user, and the implemented hygiene checks found **14,000 unique `user_id` values**, no blank segment or variant fields, and only `0` and `1` values in `converted`.

| Column | Meaning |
|---|---|
| `user_id` | Unique user identifier. It is used for uniqueness checks and a pseudo-random parity robustness split; it is not a timestamp or an experimental variable. |
| `segment` | User/acquisition segment: `paid_search`, `organic`, `referral`, `app_store`, or `influencer`. These groups have materially different baseline conversion rates. |
| `variant` | Experiment arm: `control` is the existing onboarding flow; `treatment` is the new onboarding flow. |
| `converted` | Binary outcome: `1` means the user converted and `0` means they did not. Conversion rate is the sum of this field divided by the number of users. |

The input CSV and assignment PDF were supplied from outside the repository. The analysis scripts accept a CSV path as an argument; their default filename assumes a copy named `experiment_results.csv` in the project directory, but that copy is not currently present here.

## Investigation approach

The actual implementation follows this sequence:

1. Load the CSV with Python's standard-library `csv.DictReader`; trim segment/variant strings and convert `converted` to an integer.
2. Validate row count, unique IDs, segments, variants, binary outcomes, and blank fields.
3. Compute control and treatment conversion rates overall, their percentage-point difference, and a pooled two-proportion z-test.
4. Tabulate users and conversions for every segment and arm; calculate segment conversion rates, lifts, two-sided z-test p-values, and unpooled 95% confidence intervals for the difference.
5. Standardize the segment effects to the total-population segment mix. This answers the assignment's mix-adjusted question and removes the effect of each arm receiving different proportions of segments.
6. Examine assignment proportions by segment and calculate a chi-square statistic for homogeneous treatment exposure.
7. Run supplementary robustness checks, including pseudo-random half splits, alternative standardization weights, and several exploratory checks that were retained as documented dead ends.

### Core calculations

Let \(CR_{v,s}=\frac{\text{conversions}_{v,s}}{n_{v,s}}\), where \(v\) is an arm and \(s\) is a segment.

- **Naive overall lift:** \(CR_{treatment}-CR_{control}\), using all users in each arm.
- **Segment lift:** \(CR_{treatment,s}-CR_{control,s}\), reported in percentage points (pp).
- **Mix-adjusted lift:** \(\sum_s w_s\,(CR_{treatment,s}-CR_{control,s})\), where \(w_s=\frac{n_s}{14,000}\), the segment's share of the full dataset.
- **Statistical checks:** `analyze.py` uses a pooled two-proportion z-test for p-values and an unpooled standard error for 95% confidence intervals on segment rate differences.

## Results and findings

### Q1 — naive overall conversion lift

| Variant | Users | Conversions | Conversion rate |
|---|---:|---:|---:|
| Control | 7,136 | 1,414 | 19.82% |
| Treatment | 6,864 | 1,814 | 26.43% |
| Difference |  |  | **+6.6127 pp** (rounded **+6.61 pp**) |

The pooled two-proportion test reports **z = 9.29** and **p < 1e-19**. This establishes that the observed arm-level difference is large, but does not establish that it was caused by the new flow: the arm populations are not comparably composed by segment.

### Q2 — segment-level results and reliability

| Segment | Control n | Control CR | Treatment n | Treatment CR | Lift | 95% CI (pp) | p-value | Share of all users | Treatment share within segment |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `paid_search` | 3,353 | 15.18% | 1,459 | 14.39% | -0.79 pp | [-2.96, +1.39] | 0.48 | 34.37% | 30.3% |
| `organic` | 1,298 | 35.29% | 2,917 | 35.07% | -0.21 pp | [-3.34, +2.91] | 0.89 | 30.11% | 69.2% |
| `referral` | 1,441 | 23.46% | 1,397 | 26.27% | +2.81 pp | [-0.37, +5.99] | 0.083 | 20.27% | 49.2% |
| `app_store` | 925 | 8.76% | 960 | 20.00% | **+11.24 pp** | [+8.13, +14.36] | 4.1e-12 | 13.46% | 50.9% |
| `influencer` | 119 | 23.53% | 131 | 16.79% | -6.74 pp | [-16.69, +3.22] | 0.18 | 1.79% | 52.4% |

The implementation identifies **`influencer`** as the result not to trust. It has only 250 users (119 control and 131 treatment), a wide confidence interval spanning zero, and p = 0.18. Its treatment rate would move by about **3.8 pp** if five treatment conversions changed, so its apparent -6.74 pp effect is too fragile for a product conclusion.

`referral` is directionally positive (+2.81 pp) but is also not statistically significant at the conventional 0.05 threshold. `paid_search` and `organic` are effectively flat within their intervals.

### Q3 — mix-adjusted overall lift

The required standardization weights every within-segment lift by that segment's share of all 14,000 users.

| Segment | Population share | Segment lift | Contribution to adjusted lift |
|---|---:|---:|---:|
| `paid_search` | 4,812 / 14,000 = 0.343714 | -0.7870 pp | -0.2705 pp |
| `organic` | 4,215 / 14,000 = 0.301071 | -0.2148 pp | -0.0647 pp |
| `referral` | 2,838 / 14,000 = 0.202714 | +2.8146 pp | +0.5706 pp |
| `app_store` | 1,885 / 14,000 = 0.134643 | +11.2432 pp | +1.5138 pp |
| `influencer` | 250 / 14,000 = 0.017857 | -6.7355 pp | -0.1203 pp |
| **Total** | **1.000000** |  | **+1.6289 pp** |

The **mix-adjusted lift is +1.63 pp**, not +6.61 pp. Direct standardization independently yields **22.20% control** versus **23.82% treatment**, which is the same +1.63 pp difference.

The gap is explained by segment composition: `paid_search`, the lowest-converting large segment, is 47% of control but 21% of treatment, while `organic`, the highest-converting segment, is 18% of control but 42% of treatment. This is a Simpson's-paradox-style aggregation problem: the pooled comparison blends the flow effect with who happened to be in each arm.

### Q4 — meaningful positive effect

**`app_store` is the only segment with a clearly supported positive effect.** Its conversion rate rises from **8.76% to 20.00%**: **+11.24 pp** (a +128% relative improvement), with 95% CI **[+8.13, +14.36] pp** and p = **4.1e-12**. It contributes **+1.51 pp** of the total **+1.63 pp** adjusted lift—about 93%—despite representing only 13.46% of users.

As an additional check, splitting `app_store` users by `user_id` parity produced +8.56 pp (p = 0.0001) and +13.94 pp (p = 4e-9). These are pseudo-random diagnostic splits, not new independent experiments, but both support the direction and stability of the segment result.

### Q5 — treatment/control assignment balance

Overall, 6,864 / 14,000 = **49.03%** of users are in treatment. This aggregate figure masks severe segment imbalance.

| Segment | Total n | Control share | Treatment share | Expected treatment count at 49.03% | Actual treatment count |
|---|---:|---:|---:|---:|---:|
| `paid_search` | 4,812 | 69.68% | **30.32%** | 2,359 | 1,459 |
| `organic` | 4,215 | 30.79% | **69.21%** | 2,067 | 2,917 |
| `referral` | 2,838 | 50.78% | 49.22% | 1,391 | 1,397 |
| `app_store` | 1,885 | 49.07% | 50.93% | 924 | 960 |
| `influencer` | 250 | 47.60% | 52.40% | 123 | 131 |

The chi-square statistic for homogeneous treatment share across segments is **approximately 1,364** on **4 degrees of freedom**. Assignment is therefore not balanced with respect to segment. The repository does not identify the underlying operational cause; it suggests possible bucketing, targeting, or landing-path differences as hypotheses only.

## Conclusion

The new onboarding flow should **not** be rolled out to all users based on the naive +6.61 pp topline result. That result is mostly supported by a favorable treatment mix—too many high-converting `organic` users and too few low-converting `paid_search` users in treatment.

After the assignment-relevant adjustment, the overall estimated lift is +1.63 pp. Almost all of that adjusted gain comes from a convincing `app_store` effect (+11.24 pp). The project’s documented recommendation is to keep or ship the new flow for `app_store`, avoid a universal rollout on the topline evidence, repair or investigate assignment logic, and run a clean follow-up test for `referral` before treating its positive estimate as decision-grade.

## Implementation

The project uses only Python's standard library—`csv`, `collections`, `math`, `json`, `os`, and `sys`—with no third-party packages.

- `analyze.py` is the primary analysis. It loads and validates data, produces all Q1–Q5 calculations, writes the compact answer artifact, and implements the z-tests, confidence intervals, standardization, and chi-square calculation.
- `checks.py` contains supplementary robustness and exploratory checks.
- `answers.json` is the machine-readable summary emitted by `analyze.py`.
- `ANSWERS.md` is the detailed narrative report from the completed analysis.

Run the scripts with the supplied CSV path:

```powershell
python analyze.py "C:\path\to\experiment_results.csv"
python checks.py "C:\path\to\experiment_results.csv"
```

`analyze.py` overwrites `answers.json` in its own directory when run.

## Investigation process and non-material checks

Beyond the required questions, `checks.py` records the following work:

- It tested whether `user_id` represented signup order or a time/ramp signal. Both variants span IDs 100,001–114,000 with nearly identical means (107,002 control; 106,999 treatment), so this was a **dead end**: `user_id` acts as a unique key, not usable time information.
- It removed `app_store` from the pooled calculation to test whether that one segment explained the raw topline. The lift remained **+6.01 pp** (p = 1.4e-14), another **dead end** for explaining the naive result. The large pooled lift is driven by the `paid_search`/`organic` mix imbalance, not simply by `app_store`.
- It recomputed the adjusted lift with total-population, control-arm, and treatment-arm weights: **+1.63 pp**, **+1.50 pp**, and **+1.76 pp**, respectively. The conclusion is not sensitive to this reasonable weighting choice; the assignment-required answer uses total-population weights.
- It re-split `paid_search`, `organic`, and `referral` by `user_id` parity. The large flat segments remained flat and non-significant; no hidden positive subgroup was found by this diagnostic.
- It quantified the small-segment fragility and displayed the segment mix inside each arm, making the source of the aggregate bias explicit.

These checks increase confidence in the stated interpretation, but they do not establish the root cause of the assignment imbalance or substitute for a properly randomized follow-up experiment.

## Original requirements vs. actual implementation

All five assignment questions are implemented and answered. The main additions beyond the stated Q1–Q5 deliverables are confidence intervals and significance tests, direct-standardization verification, parity-based robustness splits, alternative weighting sensitivity, and exploratory dead-end checks.

Two practical discrepancies are worth noting:

1. The assignment PDF and CSV were provided externally and are not stored in this project directory. Consequently, the scripts’ no-argument default (`experiment_results.csv`) will not work in the current checkout unless the CSV is copied here; passing its path works.
2. `ANSWERS.md` contains character-encoding artifacts for several symbols (for example, some plus/minus and dash characters). The numeric values and logic agree with `analyze.py` and `answers.json`; this README presents those values with normal Markdown/Unicode rendering.

## Project structure

```text
.
├── README.md       # This project documentation
├── analyze.py      # Primary Q1–Q5 analysis and JSON-output generator
├── checks.py       # Supplementary robustness checks and documented dead ends
├── ANSWERS.md      # Detailed original analysis narrative and result tables
└── answers.json    # Compact generated answer summary
```

External reference materials used for the analysis:

- `Onboarding_Experiment_Assignment.pdf` — original problem statement and question set.
- `experiment_results.csv` — experiment-level user data described above.
