# TIERS reassessment after Phase 2

Reviewed commit `d093983` against the earlier repository review. The working tree was clean when review began. This document is the only source-tree addition made during this reassessment.

## Overall assessment

The changes address most of the original data and evaluation defects. The repository now has a coherent event/state distinction, dated system membership, shared evaluation targets, weighted metrics, baselines, dependency locking, and meaningful tests. The next priorities are historical information timing and bringing calibration into agreement with evaluation. The current default-prior model still trails simple baselines on the principal tasks.

## What the changes resolved

| Earlier concern | Current status and verification |
|---|---|
| Escalation confused with non-peace; ongoing wars counted as onsets | Fixed in the main v27/v28 evaluation. `evaluation.extract_target` conditions onset on T0 and sums strictly above the current tier for escalation. Forward `P_any_esc` also uses the correct definition. |
| Lower tiers kept during duplicate removal | Fixed in the active pipeline. `build_dyad_states.resolve_states` resolves maximum directed and shared tiers while retaining contributing events. Pakistan→India in 1947 and Israel→Egypt in 1948 are now T5. Contracts check the entire built state table against its events. |
| States appearing before they existed | Fixed for the active grid through `state_system` and member-year joins. South Sudan first appears in 2011. Contracts verify membership and completeness of the member-pair grid. |
| Capability shares and duration/year gaps | Fixed in the inspected artifacts. Shares sum to one, missingness is flagged, durations restart across gaps, and targets join the following calendar year. |
| Enriched samples scored without weights | Fixed for the tier-specific evaluator's ordinary negative-sampling path; it now defaults to full population, samples dyad-years after averaging directions, and passes inclusion probabilities into metrics. See the separate headline sampler regression below. |
| Ambiguous T2 taxonomy | Improved substantially: MID threats/displays now map to T1, and T2 comes from sanctions. Source contracts check this. |
| Rivalry direction, history boundary, cutoff | Redesigned deliberately as directed rivalry with mirrored actor fields, history starting in 1900, and a stated end-of-year forecast origin. This replaces the old accidental one-sided implementation; see the remaining retrospective-severity issue below. |
| Untracked migration, broken environment, no tests | Migration is committed; `.python-version`, `uv.lock`, and pinned requirements exist. The environment at `~/.venvs/tiers` works. All 53 pytest tests pass, including artifact contracts. CI is still absent. |
| Mixed/stale results | Improved: the current report identifies its feature hash, parameters, sample, and evaluation unit; README presents corrected results. I checked the grid hash and independently reproduced the TIERS full-test headline point estimates. |

Coverage is only partly resolved. Next-year labels are masked when a whole tier lacks a source, but the code explicitly takes the starting tier as recorded, and source availability remains year-level rather than dyad-level. In particular, EUSANCT covers US/EU senders and T3 covers troop support rather than every form of proxy support. These limitations are disclosed; the evaluated outcomes should be described as outcomes observable from these sources, rather than exhaustive conflict states.

## Findings requiring follow-up

### P1 — Calibration ignores the coverage masks used by evaluation

Locations: `scripts/model/calibrate_tiers_v28_engine.py:188–192,288–291`; `scripts/model/calibrate_tiers_v28.py:283–287`.

The calibrators now load `unobserved_next`, but select training data by current tier and construct outcomes directly from `uiw_tier_next`. They never apply the target-specific coverage mask. The baseline/evaluation path does apply it. Unknown sanctions therefore become negative outcomes in calibration even though evaluation refuses those same labels.

Under the engine calibrator's default trade-observed, through-1989 filter:

| Block | Directed training rows selected | Rows eligible under evaluator coverage rules |
|---|---:|---:|
| T0→T1+ | 495,290 | 34,392 |
| T1→T2+ | 2,558 | 136 |

The excluded portions contain 2,108 and 150 recorded positives respectively; this is not merely a redundant set of negative rows. The fitting population differs materially from the evaluated one.

Fix: reuse shared target eligibility in every fitting path, before positive counts, sampling, objectives, and diagnostics. Also make engine calibration optimize the same dyad-year forecast aggregation as evaluation, rather than separately fitting both orientations. Refit parameters only after the historical timing issue below is resolved. Current published results use default priors, so this finding does not imply they were produced using these fitted parameters.

### P1 — Historical MID features still use future dispute severity

Locations: `scripts/build/build_mid_dyads.py:82–89,110–139`; `scripts/build/build_rivalry.py:76–85`.

The builder assigns a participant's maximum hostility across its entire spell to every overlapping year. Incident pairing also takes the maximum across a whole dispute without retaining incident dates. Rivalry consumes these retrospective annual events. Consequently, declaring a forecast origin at the end of year T does not ensure that its inputs only use information available by T.

I joined emitted force/war events to the earliest force-level MIDIP incident for the same dispute and ordered pair. There are **72 emitted rows from 1992 onward dated before the first force incident against that target**. For example, dispute 3552 emits Iraq→United States and Iraq→United Kingdom at T4 in 1992, while the first such force incidents in MIDIP are dated 1993.

This establishes a timing mismatch between the event construction and incident chronology; it is not a claim that every earlier year is known to have been peaceful. The participant-peak limitation is already documented in the builder, but it affects both annual targets and forecast inputs and needs to qualify interpretation of early-warning performance.

Fix: preserve incident dates and derive annual/as-of severity where incident coverage permits. For earlier spells, explicitly distinguish retrospective episode coding from forecast-time observations and run sensitivity analyses or restrict the strongest prospective claims to adequately dated data. Add a multi-year fixture where force first occurs after the forecast origin.

### P2 — The optional headline sampler changes the forecast being evaluated

Locations: `scripts/model/backtest_tiers_v28.py:133–138,295–321`; `scripts/model/evaluation.py:391–403`.

`--sample` samples directed rows before `collapse_directions`. If the canonical orientation is selected without its reverse, it retains its own score rather than the mean of both scores. If only the reverse is selected, it is discarded. The inclusion weights cannot reconstruct the missing orientation's prediction.

Reproduction using the actual helpers: an A↔B pair with directed target probabilities 0.1 and 0.9 has a full-pair forecast of 0.5. Sampling one direction with seed 1 evaluates 0.1. This is a different prediction, not just a smaller sample of the full evaluation task.

This is not limited to invented asymmetric predictions: in the current feature grid, 1,372 of 2,162 T3 directed rows have score vectors differing from their pair mean by more than 1e-8; the largest single-component difference is 0.096255.

Fix: select unordered dyad-years and keep both directions together before scoring, or average the full predictions before sampling, as the tier-specific evaluator already does. Default `--sample 0` full-population results are unaffected by this specific issue.

## Earlier concerns that remain

- **Missing trade still switches wholesale to v27.** Both scalar and vectorized scoring retain this branch (`tiers_lib_v28.py:267–268,497–503`). Draft §14 still calls for edge-specific non-trade hazards when trade alone is absent. This needs either an implementation change or an explicit specification change and validation of the chosen behavior.
- **The scoring CLI is still historical and cannot load fitted parameters.** The current grid ends in 2014. `score_year` now accepts a `Priors` object, which is progress, but `main` exposes no `--priors` option and calls it without one (`tiers_score_v28.py:81–94`). It still prints “live” directed pairs. Exported directional scores also need to be distinguished from the mean-over-directions forecast evaluated in the report.
- **No CI workflow exists.** Tests are now valuable enough to automate. On a fresh checkout, artifact tests skip when generated data is absent; fixture tests should run unconditionally in CI, with a separate artifact-validation job where the required datasets are available.
- **Some build reproducibility remains conditional.** The active builders mostly rebuild rather than silently returning early. The pipeline can still reuse existing geography when Shapely is unavailable and existing trade with `--skip-trade`; record hashes/configuration for those reused inputs. Shapely is imported by geography but is not declared in project dependencies.

## Current performance and verification

The current Parquet grid has **1,388,704 directed rows, 1946–2014**, SHA-256 prefix `3a5030bdc2618305`, matching the saved evaluation report. Consecutive-year evaluation naturally stops at 2013 as a forecast-origin year.

I independently rescored the full test split using default priors and reproduced these point estimates:

| Target | Positive dyad-years | TIERS AUC | Brier skill versus training base rate |
|---|---:|---:|---:|
| Onset, any | 3,027 | 0.563748 | -1.157717 |
| Onset, force | 258 | 0.824578 | 0.001595 |
| Onset, war | 14 | suppressed | suppressed |
| Escalation | 3,533 | 0.587049 | -1.021684 |
| De-escalation | 2,755 | 0.557702 | 0.082610 |

Negative Brier skill means worse squared probability error than the training-base-rate forecast. The saved report's logistic baseline has onset AUC 0.7340 and force-onset AUC 0.9113; those logistic fits were inspected in code/report but not refitted during this reassessment. The old roughly 0.93 “peace-to-war” headline should not be carried forward: the corrected test has only 14 genuine peace-to-war outcomes and appropriately suppresses discrimination metrics.

Checks run:

- Complete pytest suite: **53 passed**, with the built-data contracts executing rather than skipping.
- Standalone v27 and v28 invariant suites: **9 and 4 passed**.
- Scalar/vectorized score comparison on 120 current-grid rows, including directed-rivalry inputs: maximum absolute probability difference **2.22e-16**.
- Full-test TIERS headline point-estimate recomputation; no output files overwritten.
- Current Parquet state examples, membership, coverage eligibility, source/hash, raw incident chronology, and a synthetic headline-sampling reproduction.

I did not rerun the complete raw-data pipeline, refit model/logistic coefficients, or regenerate bootstrap intervals. Model code and data were not changed during review.

## Recommended next step

Resolve historical as-of severity first, then make calibration use the same masked targets and dyad-year unit as evaluation. Repair the optional headline sampler and missing-trade model selection, then recalibrate and compare against the existing baselines. Updating operational inputs should follow those checks.
