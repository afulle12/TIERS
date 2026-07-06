"""UN General Assembly voting country dyad alignment.

For every country pair in the UN voting record, computes the share of jointly
observed resolutions on which the two countries cast the same sign of vote
(Y, N, or A). Non-voting (X) and absent rows are excluded from the
denominator for that pair.

Inputs:
  data/raw/UN Voting Record/2026_02_06_ga_voting.csv

Outputs:
  output/analysis/un_voting_dyads.csv
    Columns: ccode1, name1, ccode2, name2, shared_resolutions,
             agreements, alignment
    Sorted by alignment descending, then shared_resolutions descending.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(
    ROOT, "data", "raw", "UN Voting Record", "2026_02_06_ga_voting.csv"
)
OUT_PATH = os.path.join(ROOT, "output", "analysis", "un_voting_dyads.csv")

VOTE_TO_CODE = {"Y": 1, "A": 0, "N": -1}


def main() -> None:
    needed = ["undl_id", "ms_code", "ms_name", "ms_vote"]
    df = pd.read_csv(CSV_PATH, usecols=needed, low_memory=False)
    df = df[df["ms_vote"].isin(VOTE_TO_CODE)].copy()
    df["vote_code"] = df["ms_vote"].map(VOTE_TO_CODE).astype(np.int8)

    countries = (
        df[["ms_code", "ms_name"]]
        .drop_duplicates(subset=["ms_code"])
        .sort_values("ms_code")
        .reset_index(drop=True)
    )
    n_c = len(countries)
    code_to_idx = {c: i for i, c in enumerate(countries["ms_code"])}

    resolutions = (
        pd.Series(df["undl_id"].unique()).sort_values().reset_index(drop=True)
    )
    n_r = len(resolutions)
    res_to_idx = {int(r): i for i, r in enumerate(resolutions)}

    c_idx = df["ms_code"].map(code_to_idx).to_numpy()
    r_idx = df["undl_id"].map(res_to_idx).to_numpy()
    v_idx = (df["vote_code"].to_numpy() + 1).astype(np.int8)

    M = np.zeros((n_c, n_r, 3), dtype=np.int16)
    np.add.at(M, (c_idx, r_idx, v_idx), 1)

    agree = np.zeros((n_c, n_c), dtype=np.int32)
    for k in range(3):
        # M[:,:,k] is int16 -> matmul yields int64; cast to int32 to save memory.
        agree += M[:, :, k].astype(np.int32) @ M[:, :, k].T.astype(np.int32)

    # numpy 2.x: bool @ bool returns bool, truncating counts to 0/1.
    # Use int counts directly to keep the integer matrix product.
    votes_per_resolution = M.sum(axis=2).astype(np.int32)  # (n_c, n_r)
    shared = votes_per_resolution @ votes_per_resolution.T  # (n_c, n_c) int32

    iu, ju = np.triu_indices(n_c, k=1)
    out = pd.DataFrame(
        {
            "ccode1": countries["ms_code"].values[iu],
            "name1": countries["ms_name"].values[iu],
            "ccode2": countries["ms_code"].values[ju],
            "name2": countries["ms_name"].values[ju],
            "shared_resolutions": shared[iu, ju],
            "agreements": agree[iu, ju],
        }
    )
    out["alignment"] = out["agreements"] / out["shared_resolutions"]
    out = out.sort_values(
        ["alignment", "shared_resolutions"], ascending=[False, False]
    ).reset_index(drop=True)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    n_dyads = len(out)
    expected = n_c * (n_c - 1) // 2
    print(f"Countries: {n_c}")
    print(f"Resolutions with at least one valid vote: {n_r}")
    print(f"Dyads written: {n_dyads} (expected {expected})")
    print(f"Pairs with no shared resolutions: {(out['shared_resolutions'] == 0).sum()}")
    print(f"Median shared_resolutions: {int(out['shared_resolutions'].median())}")
    print(f"Median alignment (over pairs with shared >= 50): "
          f"{out.loc[out['shared_resolutions'] >= 50, 'alignment'].median():.3f}")
    print("\nTop 15 dyads by alignment:")
    print(out.head(15).to_string(index=False))
    print("\nBottom 5 dyads by alignment (with >= 100 shared resolutions):")
    bot = out[out["shared_resolutions"] >= 100].tail(5)
    print(bot.to_string(index=False))


if __name__ == "__main__":
    main()
