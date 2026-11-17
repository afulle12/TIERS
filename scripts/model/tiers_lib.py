"""Importable module: TIERS dyadic model v2.1."""
from dataclasses import dataclass, fields
from typing import Dict
import copy

C_b = 0.95


@dataclass
class State:
    name: str = "X"
    N_pub: float = 0.9
    beta: float = 0.02
    dP: float = 0.0
    R_d: float = 0.0
    A_div: float = 0.0
    P_v: float = 0.0
    V_p: float = 0.0
    V_t: float = 0.0
    C_T: float = 0.5
    W_v: float = 0.0
    B: float = 0.0
    R_h: float = 0.0
    I_s: float = 0.0
    I_a: float = 0.5
    C_p: float = 0.3
    I_i: float = 0.3
    C_i: float = 0.5
    C_d_sup: float = 0.0
    C_d_opp: float = 0.0
    E_n_sup: float = 0.0
    E_n_opp: float = 0.0
    S_p_sup: float = 0.0
    S_p_opp: float = 0.0


def p_init(A: State, B: State) -> float:
    M = max((A.dP + A.R_d + A.A_div) / 3.0, A.P_v)
    O = max(A.V_p, A.V_t) * (1.0 - B.C_T * (1.0 - A.W_v))
    O = max(0.0, O)
    S = (A.B + A.R_h + A.I_s) / 3.0
    C_p_star = 1.0 if A.V_t > A.V_p else A.C_p
    F = 1.0 - (1.0 - A.I_a) * (1.0 - C_p_star) * (1.0 - A.I_i)
    return A.beta * M * O * S * F


def p_direct(A: State, B: State) -> float:
    return (1.0 - A.N_pub) * p_init(A, B)


def treaty_triggers(A: State):
    delta_opp = 1.0 if A.C_d_opp > 0.5 else 0.0
    delta_sup = 1.0 if A.C_d_sup > 0.5 else 0.0
    Ci_sup = max(A.C_i, 1.0 - A.N_pub) + delta_opp * C_b
    Ci_opp = max(A.C_i, 1.0 - A.N_pub) + delta_sup * C_b
    T_sup = A.C_d_sup**2 / (A.C_d_sup**2 + Ci_sup**2) if (A.C_d_sup**2 + Ci_sup**2) > 0 else 0.0
    T_opp = A.C_d_opp**2 / (A.C_d_opp**2 + Ci_opp**2) if (A.C_d_opp**2 + Ci_opp**2) > 0 else 0.0
    return T_sup, T_opp


def p_join(A: State, side: str, W_sev: float) -> float:
    T_sup, T_opp = treaty_triggers(A)
    if side == "sup":
        T, E_n, S_p = T_sup, A.E_n_sup, A.S_p_sup
    else:
        T, E_n, S_p = T_opp, A.E_n_opp, A.S_p_opp
    pull = 1.0 - A.N_pub
    return 1.0 - (1.0 - T) * (1.0 - E_n * W_sev * pull) * (1.0 - S_p * W_sev * pull)


def dyadic(A, B, W_sev_A=0.0, W_sev_B=0.0) -> Dict[str, float]:
    pdAB = p_direct(A, B); pdBA = p_direct(B, A)
    pjoAB = p_join(A, "opp", W_sev_A) if W_sev_A > 0 else 0.0
    pjoBA = p_join(B, "opp", W_sev_B) if W_sev_B > 0 else 0.0
    pjsAB = p_join(A, "sup", W_sev_A) if W_sev_A > 0 else 0.0
    pjsBA = p_join(B, "sup", W_sev_B) if W_sev_B > 0 else 0.0
    P_dyad = 1 - (1 - pdAB) * (1 - pdBA) * (1 - pjoAB) * (1 - pjoBA)
    P_co = 1 - (1 - pjsAB) * (1 - pjsBA)
    return {"pdAB": pdAB, "pdBA": pdBA, "pjoAB": pjoAB, "pjoBA": pjoBA,
            "pjsAB": pjsAB, "pjsBA": pjsBA, "P_dyad": P_dyad, "P_co": P_co}


PARAM_NAMES = [f.name for f in fields(State) if f.name != "name"]
