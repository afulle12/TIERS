# TIERS repository review — November 16, 2026

## Assessment

The immediate priority is to make the historical labels and evaluation reliable before adding model complexity or interpreting the published AUCs as evidence of early-warning performance. The current code contains concrete errors in both areas. Passing probability invariants does not establish that the targets, eligible population, or reported metrics are correct.

This review covers the existing working tree, including the uncommitted TIERS/v28 migration. No model, data, or configuration files were changed. Numerical data audits below used `data/processed/dyads_with_features_v28.csv` (2,101,408 rows, 1946–2014); the backtest prefers Parquet, so these counts should also be checked against that artifact during remediation.

## 1. Correct the headline evaluation targets and forecast output — high priority

Locations: `scripts/model/backtest_tiers_v28.py:110–120,142–162`; `scripts/model/tiers_score_v28.py:32–46`.

- “Any esc” uses `1 - P(T0)`, which measures next-year non-peace. For a dyad currently at T2, this includes T1 de-escalation and T2 persistence. Correct escalation probability is `sum(pi[k+1:])` for current tier `k`.
- The same error appears in forward output as `P_any_esc`.
- “T0->T5” evaluates every row with next tier T5, including current T5. In the inspected CSV's test period, 196 rows end at T5: 156 already start at T5, and only 29 start at T0. This is predominantly a different task from forecasting peace-to-war transitions.
- “T0->T1+” marks non-T0 rows negative while assigning them non-peace probabilities. “T0->T4+” includes starting tiers 1–3 in its positives and also scores already-military rows as negatives. The metric names, eligibility masks, targets, and scores must agree.

Fix: define each task once, including its starting-state eligibility and target, and reuse it across models, baselines, backtests, and forecast exports. Recompute README results afterward. Add small regression examples covering persistence, de-escalation, escalation, and the T0/T5 boundaries.

## 2. Resolve simultaneous event tiers before deduplicating — high priority

Locations: `scripts/build/build_t0_dyads.py:77–78`; `scripts/build/build_features_v27.py:64–77`.

The full table is sorted by ascending tier. The feature builder then deduplicates on dyad-year with `keep="first"`. Simultaneous events at different tiers are treated as duplicate records, selecting the lower tier.

Within 1946–2014, the combined event CSV contains 1,132 name-keyed dyad-years with multiple tiers. The v28 feature CSV selects a tier below the maximum recorded event for 1,126 of them. Examples:

| Dyad-year | Recorded tiers | Selected tier |
|---|---|---|
| Pakistan → India, 1947 | T1, T5 | T1 |
| Israel → Egypt, 1948 | T4, T5 | T4 |
| United Kingdom → Argentina, 1947 | T1, T4 | T1 |

Fix: adopt an explicit state-resolution rule, such as the highest active tier where appropriate to the model definition. Preserve all contributing events and source provenance separately. Assert one canonical state per numeric dyad-year key, rebuild downstream features and durations, and then recalibrate. Do not mechanically remove duplicates without resolving their meaning.

## 3. Build the eligible population from country-year membership and source coverage — high priority

Location: `scripts/build/build_t0_dyads.py:30–63`.

The peace grid crosses all countries seen anywhere in the event data with all years, instead of checking whether both states existed in that year. The current v28 CSV includes South Sudan, Slovakia, and the Czech Republic from 1946. Country inclusion also depends on appearing in the event table, which can omit states with no recorded conflict.

Furthermore, “no event found” is assigned T0 without an explicit source-coverage mask. Missing observation and observed peace need distinct treatment, especially when sources have different periods and tier coverage.

Fix: define the population from an appropriate dated state-membership registry, resolve historical codes and aliases by year, and attach observation coverage by tier/source. Exclude ineligible dyad-years and retain unknown outcomes where coverage is insufficient.

Additional audit results: 783,975 feature rows have `c_t_ab + c_t_ba != 1`. The feature builder uses different missing-value substitutions in the numerator and denominator (`build_features.py:162–164`). Coverage is printed after imputation, which obscures missingness. There are also 37 target pairs whose next observation is not the following calendar year; loaders currently use `shift(-1)` without checking that year difference is one.

## 4. Correct sampling weights in tier-specific evaluation — high priority

Location: `scripts/model/backtest_tiers_v28_by_tier.py:57–66,79–99`.

The sampler keeps every escalation and subsamples non-escalations. Brier score and log loss are then computed without correcting for selection probabilities. They describe an artificially enriched sample rather than population calibration. Exact-transition AUC can also change because sampling is defined by the cumulative target, changing the composition of exact-target negatives.

Reproduction using the existing sampler: a population with 100 positives and 9,900 negatives has 1% prevalence. A 1,000-row sample has 10% prevalence. For a constant 1% forecast, true Brier score is 0.0099; the unweighted sample reports 0.0981.

Fix: evaluate all rows where feasible, or retain inclusion probabilities and use suitable weights for every reported metric. Report population and sample counts separately. Use identical eligible populations for model comparisons. Add precision-recall metrics, reliability plots, and dyad/time-aware uncertainty intervals after repairing the evaluation definitions.

## 5. Repair rivalry symmetry and historical timing — medium priority

Location: `scripts/build/build_rivalry.py:54–82,85–119,129–132`.

The function documents a symmetric rivalry feature, but emits only side-A → side-B pairs. A two-participant synthetic dispute produces `(2, 200)` and no `(200, 2)`. Reverse rows can consequently default to zero despite the same shared history.

The documented formula uses events strictly before year T; implementation includes events at T. Dispute participant hostility/fatality summaries also require an availability audit before they can be treated as information known at forecast time. The runner discards all pre-1946 events, resetting historical rivalry at the evaluation window boundary.

Fix: emit both orientations, define the forecast information cutoff explicitly, retain needed pre-window history, and test symmetry, lagging, decay, and boundary behavior on a tiny history.

## 6. Separate missing trade inputs from wholesale engine fallback — medium priority

Location: `scripts/model/tiers_lib_v28.py:256–259`; v28 draft §14.

Any dyad with both trade states absent immediately uses the v27 engine, even when structural features needed for v28 non-trade hazards are present. The draft distinguishes absent trade from absent *all* v28-specific features: absent trade should retain edge-specific non-trade hazards.

In a synthetic T2 case with zero trade fields, changing only the integration state from observed to absent changes reconciled escalation probability from 0.040152 to 0.328161. In the inspected CSV, 967,519 rows have trade source `NONE`, so this choice affects a large part of the evaluation.

Fix: implement and test the intended nested members explicitly. Report evaluation by active engine and trade source. Distinguish observed zero trade from unobserved trade.

## 7. Make operational scoring use current, versioned inputs and fitted parameters — medium priority

Locations: `scripts/model/tiers_score_v28.py:20–32,74–80`; `scripts/build/build_features_v27.py:50,71,275–280`.

The “live” scorer defaults to the latest year in the structural grid, which is 2014 in the inspected data. It constructs `Priors()` unconditionally and has no calibrated-prior argument, although calibration scripts already produce parameter JSON files and backtesting can load them.

Fix: establish an explicit forecast origin, feature availability dates, and output horizon. Allow the scorer to load the same versioned parameters as evaluation. Label historical scores accurately, and report input age and active-member coverage. Updating trade alone cannot make a grid capped at 2014 current.

## 8. Establish a reproducible development and research workflow — medium priority

- The last commit is July 6, 2026. The active build directory, v28 scripts/specification, and TIERS replacements are untracked; older Eirene files are deleted in the working tree. A fresh clone of HEAD does not reproduce this working copy. Review and checkpoint the migration in coherent commits.
- `pyproject.toml` points pytest at `tests/`, but that directory is absent. No `.github/` CI directory exists. Move or wrap the valuable invariant tests into normal discovery and add data/metric regressions plus a tiny fixture-driven pipeline check.
- The supplied `.venv` executables lack execute permission and reference Python 3.13, while the host Python is 3.14. Recreate the environment from declared dependencies and record a tested dependency resolution. A separate bundled Python 3.12 runtime was used for the successful checks below.
- Feature/rivalry builders return early when output files exist, without checking whether source data, code, or parameters changed. Add explicit rebuild controls and input/code/config fingerprints so stale artifacts cannot silently survive fixes.
- README model equations, results, and limitations mix generations. The README's 200k-sample metrics differ from the existing summary's 50k-sample metrics. Calibration code and parameter artifacts exist despite broad statements that calibration is pending. Store the command, source hashes, commit, parameters, sample, and metrics together for each experiment, then generate documentation from a named run.
- Review the T2 construct: the combined labels include legacy `T2-Economic/Display`, whereas v28 calls T2 economic coercion. A documented source-to-taxonomy crosswalk is needed before interpreting economic-hazard coefficients.
- Ruff reports 527 findings across `scripts/`, predominantly style/naming and cleanup. These are lower priority than label and evaluation correctness. It also identifies repeated country-dictionary keys that deserve a targeted audit.

## Verification performed

- Parsed all 70 Python files under `scripts/`: no syntax errors.
- Ran the v27 invariant script: all 9 checks passed, including 2,000 random probability-bound cases.
- Ran the v28 invariant script: all 4 checks passed, including 1,000 random dyads.
- Ran Ruff read-only and audited the full v28 feature CSV with selected-column and streamed checks.
- Reproduced the tier-sampling distortion, missing-trade engine switch, and one-sided rivalry expansion with small examples.
- Did not rerun the full backtests, coefficient fitting, raw-data rebuild, or LLM Wikipedia pipeline. Full scientific-stack execution was unavailable in the existing environment; the alternate runtime had NumPy/Pandas but lacked scikit-learn, SciPy, PyArrow, and pytest. Existing historical AUCs were not independently regenerated.

## Recommended implementation order

1. Checkpoint the migration and recreate a working environment.
2. Fix state resolution, country-year eligibility, coverage/missingness, capability imputation, rivalry, and consecutive-year targets; add regression fixtures and rebuild features.
3. Unify evaluation tasks, repair escalation scores and sampling weights, and rerun simple baselines on exactly the same population.
4. Recalibrate v28, assess uncertainty and calibration by transition/source/member, and refresh the documentation from a reproducible run.
5. Update the operational input pipeline and parameter loading before presenting scores as current forecasts.
