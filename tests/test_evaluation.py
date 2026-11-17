"""Regression tests for scripts/model/evaluation.py and vectorized scoring."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import (  # noqa: E402
    attach_next_year_tier,
    compute_metrics,
    deescalation_probability,
    escalation_probability,
    extract_target,
    fit_transition_matrix,
    reliability_table,
    score_transition_matrix,
    weighted_avg_precision,
    weighted_roc_auc,
)
from tiers_lib_v27 import (  # noqa: E402
    ActorState,
    DyadState,
    InputState,
    Priors as V27Priors,
    score_dataframe_v27,
    score_dyad_year as score_dyad_year_v27,
)
from tiers_lib_v28 import (  # noqa: E402
    Priors as V28Priors,
    score_dataframe_v28,
    score_dyad_year as score_dyad_year_v28,
)


def _ten_row_fixture() -> tuple[pd.DataFrame, np.ndarray]:
    """10-row synthetic fixture covering persistence, escalation, de-escalation, T0/T5 boundaries, and a year gap."""
    raw_rows = [
        ("A", "B", 2000, 0),  # 0->0 persistence at T0 boundary
        ("A", "B", 2001, 0),  # 0->5 war onset from T0
        ("A", "B", 2002, 5),  # 5->5 persistence at T5 boundary
        ("A", "B", 2003, 5),  # 5->1 de-escalation from T5
        ("A", "B", 2004, 1),  # terminal
        ("C", "D", 2000, 0),  # 0->4 force onset from T0
        ("C", "D", 2001, 4),  # 4->2 de-escalation from T4
        ("C", "D", 2002, 2),  # gap: 2003 missing -> MUST NOT join to 2004!
        ("C", "D", 2004, 3),  # 3->5 escalation from T3
        ("C", "D", 2005, 5),  # terminal
    ]
    assert len(raw_rows) == 10
    df = pd.DataFrame(raw_rows, columns=["initiator", "target", "year", "uiw_tier"])
    pis = np.array([
        [0.70, 0.10, 0.05, 0.05, 0.05, 0.05],  # A->B 2000 (cur=0)
        [0.60, 0.10, 0.05, 0.05, 0.10, 0.10],  # A->B 2001 (cur=0)
        [0.10, 0.10, 0.10, 0.10, 0.10, 0.50],  # A->B 2002 (cur=5)
        [0.05, 0.20, 0.05, 0.10, 0.10, 0.50],  # A->B 2003 (cur=5)
        [0.65, 0.05, 0.05, 0.05, 0.10, 0.10],  # C->D 2000 (cur=0)
        [0.10, 0.10, 0.20, 0.10, 0.40, 0.10],  # C->D 2001 (cur=4)
        [0.05, 0.05, 0.10, 0.50, 0.15, 0.15],  # C->D 2004 (cur=3)
    ], dtype=float)
    return df, pis


def test_ten_row_fixture_join_and_targets():
    raw_df, pis = _ten_row_fixture()
    joined, n_dup = attach_next_year_tier(raw_df)
    assert n_dup == 0
    # 10 rows -> 2 terminal (2004 A->B, 2005 C->D) and 1 gap (2002 C->D) dropped -> 7 rows
    assert len(joined) == 7
    assert not ((joined["initiator"] == "C") & (joined["year"] == 2002)).any()

    cur = joined["uiw_tier"].to_numpy()
    nxt = joined["uiw_tier_next"].to_numpy()

    # Onset, war: ONLY cur == 0 eligible (3 rows: A-2000, A-2001, C-2000).
    # A-2002 (5->5) and C-2004 (3->5) MUST NOT appear!
    m_war, y_war, p_war = extract_target(cur, nxt, pis, "Onset, war")
    assert m_war.sum() == 3
    assert y_war.tolist() == [0, 1, 0]
    assert np.allclose(p_war, [0.05, 0.10, 0.10])

    # Onset, force: cur == 0, nxt >= 4 -> A-2001 (5) and C-2000 (4)
    m_frc, y_frc, p_frc = extract_target(cur, nxt, pis, "Onset, force")
    assert m_frc.sum() == 3
    assert y_frc.tolist() == [0, 1, 1]
    assert np.allclose(p_frc, [0.10, 0.20, 0.20])

    # Onset, any: cur == 0, nxt >= 1 -> A-2001 (5) and C-2000 (4)
    m_any, y_any, p_any = extract_target(cur, nxt, pis, "Onset, any")
    assert m_any.sum() == 3
    assert y_any.tolist() == [0, 1, 1]
    assert np.allclose(p_any, [0.30, 0.40, 0.35])

    # Escalation: cur in 0..4 (excludes A-2002 cur=5 and A-2003 cur=5 -> 5 rows)
    m_esc, y_esc, p_esc = extract_target(cur, nxt, pis, "Escalation")
    assert m_esc.sum() == 5
    # Eligible rows: A-2000(0->0:0), A-2001(0->5:1), C-2000(0->4:1), C-2001(4->2:0), C-2004(3->5:1)
    assert y_esc.tolist() == [0, 1, 1, 0, 1]
    # Scores: sum above cur -> for C-2001 (cur=4) must be pi[5]=0.10, NOT 1-pi[0]=0.90!
    assert np.allclose(p_esc, [0.30, 0.40, 0.35, 0.10, 0.30])

    # De-escalation: cur in 1..5 (excludes the 3 cur==0 rows -> 4 rows)
    m_de, y_de, p_de = extract_target(cur, nxt, pis, "De-escalation")
    assert m_de.sum() == 4
    # Eligible rows: A-2002(5->5:0), A-2003(5->1:1), C-2001(4->2:1), C-2004(3->5:0)
    assert y_de.tolist() == [0, 1, 1, 0]
    assert np.allclose(p_de, [0.50, 0.50, 0.50, 0.20])


def test_escalation_probability_not_one_minus_t0():
    pis = np.array([[0.10, 0.10, 0.50, 0.15, 0.10, 0.05]])
    assert escalation_probability(pis, np.array([2]))[0] == pytest.approx(0.30)
    assert escalation_probability(pis, np.array([5]))[0] == pytest.approx(0.0)
    assert deescalation_probability(pis, np.array([2]))[0] == pytest.approx(0.20)
    assert deescalation_probability(pis, np.array([0]))[0] == pytest.approx(0.0)


def test_suppression_below_min_positives():
    rng = np.random.default_rng(7)
    y = np.zeros(100, dtype=int)
    y[:19] = 1
    p = rng.uniform(0.0, 1.0, size=100)
    res = compute_metrics(y, p, n_boot=0, min_positives=20)
    assert res["suppressed"] is True
    assert res["n_sample_pos"] == 19
    assert np.isnan(res["roc_auc"])
    assert np.isnan(res["avg_precision"])
    assert np.isnan(res["brier"])

    y[19] = 1
    res_ok = compute_metrics(y, p, n_boot=0, min_positives=20)
    assert res_ok["suppressed"] is False
    assert np.isfinite(res_ok["roc_auc"])


def test_inclusion_weights_recover_population_brier():
    # Reproduces the enrichment check from repository_review_2026-11-16.md:
    # 100 positives, 9900 negatives -> 1% population rate; constant 0.01 forecast has Brier 0.0099.
    # Keeping all 100 positives (inc=1.0) and sampling 900 negatives (inc=900/9900) yields 10% sample.
    y_sample = np.array([1] * 100 + [0] * 900, dtype=int)
    p_sample = np.full(1000, 0.01)
    inc = np.array([1.0] * 100 + [900.0 / 9900.0] * 900)

    unweighted = compute_metrics(y_sample, p_sample, inclusion_prob=None, n_boot=0)
    weighted = compute_metrics(y_sample, p_sample, inclusion_prob=inc, n_boot=0)
    assert unweighted["brier"] == pytest.approx(0.0981, abs=1e-4)
    assert weighted["brier"] == pytest.approx(0.0099, abs=1e-4)
    assert weighted["n_pop_pos"] == pytest.approx(100.0)
    assert weighted["n_pop_neg"] == pytest.approx(9900.0)


def test_weighted_auc_and_ap_match_sklearn_with_ties():
    rng = np.random.default_rng(123)
    y = rng.integers(0, 2, size=250)
    # Include ties by rounding scores to 1 decimal place
    p = np.round(rng.uniform(0.0, 1.0, size=250), 1)
    inc = rng.uniform(0.2, 1.0, size=250)
    w = 1.0 / inc
    assert weighted_roc_auc(y, p, w) == pytest.approx(roc_auc_score(y, p, sample_weight=w), abs=1e-12)
    assert weighted_avg_precision(y, p, w) == pytest.approx(
        average_precision_score(y, p, sample_weight=w), abs=1e-12
    )
    m = compute_metrics(y, p, inclusion_prob=inc, ref_rate=0.4, n_boot=0)
    assert m["brier"] == pytest.approx(brier_score_loss(y, p, sample_weight=w), abs=1e-12)
    assert m["log_loss"] == pytest.approx(
        log_loss(y, np.clip(p, 1e-15, 1.0 - 1e-15), sample_weight=w), abs=1e-12
    )


def test_transition_matrix_and_reliability_table():
    cur = np.array([0, 0, 0, 1, 1])
    nxt = np.array([0, 0, 1, 0, 2])
    mat = fit_transition_matrix(cur, nxt)
    assert mat[0, 0] == pytest.approx(2.0 / 3.0)
    assert mat[0, 1] == pytest.approx(1.0 / 3.0)
    assert mat[1, 0] == pytest.approx(0.5)
    assert mat[1, 2] == pytest.approx(0.5)
    assert mat[5, 5] == pytest.approx(1.0)
    pis = score_transition_matrix(mat, np.array([0, 1]))
    assert pis.shape == (2, 6)
    rel = reliability_table(np.array([0, 1, 0, 1]), np.array([0.1, 0.8, 0.2, 0.9]), n_bins=2)
    assert rel["n_rows"].sum() == 4


def test_vectorized_v27_v28_parity():
    df = pd.DataFrame([
        {
            "uiw_tier": 0, "d_k_years": 2.0, "contiguity_xi": 1.0, "rivalry_omega": 0.4,
            "fma": 0.2, "cap_a_to_b": 0.6, "cap_b_to_a": 0.3,
            "closing_window_a": 0.7, "closing_window_b": 0.4,
            "n_pub_a": 0.8, "n_pub_b": 0.5, "c_t_ab": 0.7, "c_t_ba": 0.3, "attribution": 0.1,
            "trade_source": "BACI", "trade_surface_norm_ab": 0.5, "mutual_trade_dependence_ab": 0.2,
            "dep_a_on_b": 0.1, "dep_b_on_a": 0.3,
            "import_leverage_a_over_b": 0.2, "export_leverage_a_over_b": 0.1, "trade_leverage_a_over_b": 0.2,
            "import_dep_a_on_b": 0.1, "import_dep_b_on_a": 0.3, "export_dep_a_on_b": 0.2, "export_dep_b_on_a": 0.1,
        },
        {
            "uiw_tier": 3, "d_k_years": 4.0, "contiguity_xi": 0.0, "rivalry_omega": 0.7,
            "fma": 0.3, "cap_a_to_b": 0.2, "cap_b_to_a": 0.1,
            "closing_window_a": 0.6, "closing_window_b": 0.2,
            "n_pub_a": 0.9, "n_pub_b": 0.4, "c_t_ab": 0.4, "c_t_ba": 0.6, "attribution": 0.8,
            "trade_source": "NONE", "trade_surface_norm_ab": 0.0, "mutual_trade_dependence_ab": 0.0,
            "dep_a_on_b": 0.0, "dep_b_on_a": 0.0,
            "import_leverage_a_over_b": 0.0, "export_leverage_a_over_b": 0.0, "trade_leverage_a_over_b": 0.0,
            "import_dep_a_on_b": 0.0, "import_dep_b_on_a": 0.0, "export_dep_a_on_b": 0.0, "export_dep_b_on_a": 0.0,
        },
    ])
    v27 = score_dataframe_v27(df, V27Priors())
    v28 = score_dataframe_v28(df, V28Priors())

    for idx, row in df.iterrows():
        sym = DyadState(
            current_tier=int(row["uiw_tier"]), duration=row["d_k_years"],
            contiguity=row["contiguity_xi"], rivalry=row["rivalry_omega"],
            state_current_tier=InputState.OBSERVED, state_duration=InputState.OBSERVED,
            state_contiguity=InputState.OBSERVED, state_rivalry=InputState.OBSERVED,
        )
        tstate = InputState.OBSERVED if row["trade_source"] != "NONE" else InputState.ABSENT
        a = ActorState(
            n_pub=row["n_pub_a"], capability_share=row["c_t_ab"],
            closing_window=row["closing_window_a"], fma=row["fma"],
            cap_proxy=row["cap_a_to_b"], attribution=row["attribution"], stakes=0.5,
            state_b_econ=InputState.ABSENT, state_b_blood=InputState.ABSENT, state_v_i=InputState.ABSENT,
            state_fma=InputState.OBSERVED, state_closing_window=InputState.OBSERVED,
            state_cap=InputState.OBSERVED, state_attribution=InputState.OBSERVED,
            state_integration=tstate,
        )
        b = ActorState(
            n_pub=row["n_pub_b"], capability_share=row["c_t_ba"],
            closing_window=row["closing_window_b"], fma=row["fma"],
            cap_proxy=row["cap_b_to_a"], attribution=0.0, stakes=0.5,
            state_b_econ=InputState.ABSENT, state_b_blood=InputState.ABSENT, state_v_i=InputState.ABSENT,
            state_fma=InputState.OBSERVED, state_closing_window=InputState.OBSERVED,
            state_cap=InputState.OBSERVED, state_attribution=InputState.DEFAULTED,
            state_integration=tstate,
        )
        r27 = score_dyad_year_v27(a, b, sym, V27Priors())
        assert np.allclose(v27["pi_ab"][idx], r27["pi_ab"], atol=1e-13)
        assert np.allclose(v27["pi_ba"][idx], r27["pi_ba"], atol=1e-13)

        a.trade_surface_norm = row["trade_surface_norm_ab"]
        a.dep_on_target = row["dep_a_on_b"]
        a.mutual_trade_dependence = row["mutual_trade_dependence_ab"]
        a.import_leverage = row["import_leverage_a_over_b"]
        a.export_leverage = row["export_leverage_a_over_b"]
        a.trade_leverage = row["trade_leverage_a_over_b"]
        b.trade_surface_norm = row["trade_surface_norm_ab"]
        b.dep_on_target = row["dep_b_on_a"]
        b.mutual_trade_dependence = row["mutual_trade_dependence_ab"]
        b.import_leverage = max(row["import_dep_a_on_b"] - row["import_dep_b_on_a"], 0.0)
        b.export_leverage = max(row["export_dep_a_on_b"] - row["export_dep_b_on_a"], 0.0)
        b.trade_leverage = max(b.import_leverage, b.export_leverage)
        r28 = score_dyad_year_v28(a, b, sym, V28Priors())
        assert np.allclose(v28["pi_ab"][idx], r28["pi_ab"], atol=1e-13)
        assert np.allclose(v28["pi_ba"][idx], r28["pi_ba"], atol=1e-13)
