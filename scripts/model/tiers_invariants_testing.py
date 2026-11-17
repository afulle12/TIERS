import random
import math
import os
from datetime import datetime

# =============================================================================
# 0. CONFIGURATION
# =============================================================================
MODEL_VERSION = "1.1.0"                     # v11 – all primitives bounded to [0,1]
RUN_DATE = "2026-05-06"
RUN_TIMESTAMP = datetime.now().strftime("%H%M%S")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(ROOT, "docs", "invariant_logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"invariant_test_v{MODEL_VERSION}_{RUN_DATE}_{RUN_TIMESTAMP}.txt")


# =============================================================================
# 1. VARIABLE RANGES — ALL primitives now bounded to [0,1]  (v11 spec)
# =============================================================================
# Per the v11 spec, every causal primitive (ΔP, R_d, A_div, P_v, V_p, V_t,
# C_T, W_v, B, R_h, I_s, I_a, C_p, I_i, N_pub, W_sev, E_n, S_p, C_d, C_i)
# lies in [0,1].  No more unnormalised variables.
# =============================================================================

PRIMITIVE_VARS = {
    # --- Path 1 inputs ---
    'N_pub':    (0.0, 1.0),   # public support / peace sentiment
    'beta':     (0.0, 1.0),   # calibration constant  (explicit in v11)
    'P_v':      (0.0, 1.0),   # victory probability threshold
    'V_p':      (0.0, 1.0),   # probability of victory (offensive)
    'V_t':      (0.0, 1.0),   # probability of victory (defensive / territorial)
    'C_T':      (0.0, 1.0),   # territorial conquest cost
    'W_v':      (0.0, 1.0),   # war value / utility
    'I_a':      (0.0, 1.0),   # ideological alignment
    'C_p':      (0.0, 1.0),   # cultural proximity
    'I_i':      (0.0, 1.0),   # intelligence / information
    'delta_P':  (0.0, 1.0),   # power shift  (was [0,10] before v11)
    'R_d':      (0.0, 1.0),   # resource demand
    'A_div':    (0.0, 1.0),   # diversionary incentive
    'B':        (0.0, 1.0),   # balance of power
    'R_h':      (0.0, 1.0),   # relative honour / reputation
    'I_s':      (0.0, 1.0),   # strategic interest
    # --- Path 2 inputs ---
    'W_sev':    (0.0, 1.0),   # severity of ongoing war
    'E_n_sup':  (0.0, 1.0),   # economic interdependence (support direction)
    'E_n_opp':  (0.0, 1.0),   # economic interdependence (oppose direction)
    'S_p_sup':  (0.0, 1.0),   # security pact strength (support)
    'S_p_opp':  (0.0, 1.0),   # security pact strength (oppose)
    'C_i_A':    (0.0, 1.0),   # state A's baseline intervention cost
    'C_d_sup':  (0.0, 1.0),   # formal alliance density (support direction)
    'C_d_opp':  (0.0, 1.0),   # formal alliance density (oppose direction)
}

C_b = 0.95  # betrayal penalty constant (fixed, per spec)


# =============================================================================
# 2. RANDOM INPUT GENERATION
# =============================================================================

def generate_random_params():
    """Return a dict of randomly sampled parameters, all in [0,1]."""
    return {name: random.uniform(lo, hi) for name, (lo, hi) in PRIMITIVE_VARS.items()}


# =============================================================================
# 3. MODEL COMPUTATION (v11)
# =============================================================================

def compute(params):
    """Compute all values for directed dyad A -> B under v11 spec."""
    N_pub   = params['N_pub']
    beta    = params['beta']
    delta_P = params['delta_P']
    R_d     = params['R_d']
    A_div   = params['A_div']
    P_v     = params['P_v']
    V_p     = params['V_p']
    V_t     = params['V_t']
    C_T     = params['C_T']
    W_v     = params['W_v']
    B       = params['B']
    R_h     = params['R_h']
    I_s     = params['I_s']
    I_a     = params['I_a']
    C_p     = params['C_p']
    I_i     = params['I_i']
    W_sev   = params['W_sev']
    E_n_sup = params['E_n_sup']
    E_n_opp = params['E_n_opp']
    S_p_sup = params['S_p_sup']
    S_p_opp = params['S_p_opp']
    C_i_A   = params['C_i_A']
    C_d_sup = params['C_d_sup']
    C_d_opp = params['C_d_opp']

    # ----- Path 1 -----
    # M_AB: average of three [0,1] terms, maxed with P_v → still [0,1]
    M = max((delta_P + R_d + A_div) / 3.0, P_v)
    # O_AB: both factors in [0,1] → product in [0,1]
    O = max(V_p, V_t) * (1.0 - C_T * (1.0 - W_v))
    # S_AB: average of three [0,1] terms → [0,1]
    S = (B + R_h + I_s) / 3.0
    # F_AB: complementary probability → [0,1]
    C_p_star = 1.0 if V_t > V_p else C_p
    F = 1.0 - (1.0 - I_a) * (1.0 - C_p_star) * (1.0 - I_i)

    P_init   = beta * M * O * S * F    # all factors ∈ [0,1] → P_init ∈ [0,1] ✓
    P_direct = N_pub * P_init           # product of two [0,1] values

    # ----- Path 2 -----
    one_minus_N = 1.0 - N_pub

    # Betrayal penalty flags
    delta_opp = 1.0 if C_d_opp > 0.5 else 0.0
    delta_sup = 1.0 if C_d_sup > 0.5 else 0.0

    # Effective intervention costs  (costs, not probabilities – may exceed 1)
    C_i_sup_star = max(C_i_A, one_minus_N) + delta_opp * C_b
    C_i_opp_star = max(C_i_A, one_minus_N) + delta_sup * C_b

    # Treaty triggers  (ratio of squares → [0,1])
    denom_sup = C_d_sup**2 + C_i_sup_star**2
    T_sup = C_d_sup**2 / denom_sup if denom_sup != 0 else 0.0

    denom_opp = C_d_opp**2 + C_i_opp_star**2
    T_opp = C_d_opp**2 / denom_opp if denom_opp != 0 else 0.0

    # Join probabilities  (noisy‑OR → [0,1])
    P_join_sup = 1.0 - (1.0 - T_sup) * (1.0 - E_n_sup * W_sev * one_minus_N) * (1.0 - S_p_sup * W_sev * one_minus_N)
    P_join_opp = 1.0 - (1.0 - T_opp) * (1.0 - E_n_opp * W_sev * one_minus_N) * (1.0 - S_p_opp * W_sev * one_minus_N)

    return {
        'M': M,
        'O': O,
        'S': S,
        'F': F,
        'C_p_star': C_p_star,
        'P_init': P_init,
        'P_direct': P_direct,
        'C_i_sup_star': C_i_sup_star,
        'C_i_opp_star': C_i_opp_star,
        'delta_sup': delta_sup,
        'delta_opp': delta_opp,
        'T_sup': T_sup,
        'T_opp': T_opp,
        'P_join_sup': P_join_sup,
        'P_join_opp': P_join_opp,
    }


# =============================================================================
# 4. OVERALL DYADIC AND CO‑BELLIGERENCY PROBABILITIES
# =============================================================================

def compute_overall(directed):
    P_direct   = directed['P_direct']
    P_join_opp = directed['P_join_opp']
    P_join_sup = directed['P_join_sup']

    P_dyad = 1.0 - (1.0 - P_direct)**2 * (1.0 - P_join_opp)**2
    P_co   = 1.0 - (1.0 - P_join_sup)**2

    return P_dyad, P_co


# =============================================================================
# 5. INVARIANT CHECKS (v11)
# =============================================================================
# Notes on v11 invariant policy:
#   - All probability outputs must be ∈ [0,1]
#   - Composite indices M, O, S, F must be ≥ 0
#   - C_i_sup_star, C_i_opp_star are COSTS, not probabilities → domain [0, 1+C_b]
#   - Delta indicators are exactly 0 or 1
#   - C_p_star is either 1 or the original C_p
#   - When N_pub = 1, join probabilities collapse to T_sup / T_opp
# =============================================================================

def check_invariants(params, directed, P_dyad, P_co):
    """Return a list of failure messages (empty if all pass)."""
    failures = []

    # (a) All probability quantities must be in [0,1]
    prob_names = [
        ('P_direct',     directed['P_direct']),
        ('P_init',       directed['P_init']),
        ('P_join_sup',   directed['P_join_sup']),
        ('P_join_opp',   directed['P_join_opp']),
        ('T_sup',        directed['T_sup']),
        ('T_opp',        directed['T_opp']),
        ('P_dyad',       P_dyad),
        ('P_co',         P_co),
    ]
    for name, val in prob_names:
        if not (0.0 - 1e-12 <= val <= 1.0 + 1e-12):
            failures.append(f"Probability {name} = {val} outside [0,1]")

    # (b) Costs C_i* — domain is [0, 1 + C_b] per spec  (v11 note)
    for name in ['C_i_sup_star', 'C_i_opp_star']:
        val = directed[name]
        if not (0.0 <= val <= 1.0 + C_b + 1e-12):
            failures.append(f"Cost {name} = {val} outside [0, 1+C_b]")

    # (c) All deterministic composites must be non‑negative
    nonneg_names = ['M', 'O', 'S', 'F']
    for name in nonneg_names:
        val = directed[name]
        if val < 0.0:
            failures.append(f"Composite {name} = {val} is negative")

    # (d) Delta indicators — must be exactly 0.0 or 1.0
    for key in ['delta_sup', 'delta_opp']:
        val = directed[key]
        if val not in (0.0, 1.0):
            failures.append(f"{key} = {val} not 0 or 1")

    # (e) C_p_star — must equal either 1.0 or the original C_p
    if directed['C_p_star'] != 1.0 and directed['C_p_star'] != params['C_p']:
        failures.append(f"C_p_star = {directed['C_p_star']} not 1 or original C_p")

    # (f) Edge case: N_pub = 1  →  join probabilities = treaty triggers
    if abs(params['N_pub'] - 1.0) < 1e-12:
        expected_join_sup = directed['T_sup']
        expected_join_opp = directed['T_opp']
        if abs(directed['P_join_sup'] - expected_join_sup) > 1e-9:
            failures.append("P_join_sup != T_sup when N_pub = 1")
        if abs(directed['P_join_opp'] - expected_join_opp) > 1e-9:
            failures.append("P_join_opp != T_opp when N_pub = 1")

    return failures


# =============================================================================
# 6. FORMATTING HELPERS
# =============================================================================

def format_params(params):
    lines = [f"    {k} = {v:.6f}" for k, v in sorted(params.items())]
    return "{\n" + ",\n".join(lines) + "\n}"

def format_directed(directed):
    lines = [f"    {k} = {v:.8f}" for k, v in directed.items()]
    return "{\n" + ",\n".join(lines) + "\n}"


# =============================================================================
# 7. MAIN TEST LOOP — 50 tests, single log file
# =============================================================================

def test_invariant_sweep(num_tests=50, seed=None):
    """Run invariant tests and write all results to a single timestamped file."""

    # Write header
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("====================================================\n")
        f.write(f"  Invariant Test Report\n")
        f.write(f"  Model Version : v{MODEL_VERSION}\n")
        f.write(f"  Run Date      : {RUN_DATE}\n")
        f.write(f"  Run Time      : {RUN_TIMESTAMP}\n")
        f.write(f"  Total Tests   : {num_tests}\n")
        f.write(f"  Seed          : {seed if seed is not None else 'None (random)'}\n")
        f.write(f"  All primitives ∈ [0,1]?      Yes (v11 constraint)\n")
        f.write(f"  β ∈ [0,1]?                   Yes (v11 calibration)\n")
        f.write(f"  Costs allowed ∉ [0,1]?       Yes (C_i* are costs)\n")
        f.write("====================================================\n\n")

    if seed is not None:
        random.seed(seed)

    total_tests = 0
    total_failures = 0
    failure_indices = []

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        for i in range(num_tests):
            params = generate_random_params()
            directed = compute(params)
            P_dyad, P_co = compute_overall(directed)

            failures = check_invariants(params, directed, P_dyad, P_co)

            total_tests += 1

            if failures:
                total_failures += 1
                failure_indices.append(i)

                f.write(f"\n--- FAILURE #{total_failures} (Test {i}) ---\n")
                f.write(f"Inputs:\n{format_params(params)}\n")
                f.write(f"Directed results:\n{format_directed(directed)}\n")
                f.write(f"Overall: P_dyad = {P_dyad:.8f},  P_co = {P_co:.8f}\n")
                f.write(f"Violations:\n")
                for err in failures:
                    f.write(f"  - {err}\n")
            else:
                f.write(f"\n--- SUCCESS (Test {i}) ---\n")
                f.write(f"  P_direct     = {directed['P_direct']:.6f}\n")
                f.write(f"  P_init       = {directed['P_init']:.6f}\n")
                f.write(f"  P_join_sup   = {directed['P_join_sup']:.6f}\n")
                f.write(f"  P_join_opp   = {directed['P_join_opp']:.6f}\n")
                f.write(f"  T_sup        = {directed['T_sup']:.6f}\n")
                f.write(f"  T_opp        = {directed['T_opp']:.6f}\n")
                f.write(f"  P_dyad       = {P_dyad:.6f}\n")
                f.write(f"  P_co         = {P_co:.6f}\n")

        # Write summary
        f.write("\n\n====================================================\n")
        f.write("  SUMMARY\n")
        f.write("====================================================\n")
        f.write(f"  Model Version : v{MODEL_VERSION}\n")
        f.write(f"  Total Tests   : {total_tests}\n")
        f.write(f"  Passed        : {total_tests - total_failures}\n")
        f.write(f"  Failed        : {total_failures}\n")
        f.write(f"  Success Rate  : {(total_tests - total_failures)/total_tests*100:.2f}%\n")
        if failure_indices:
            indices_str = ", ".join(str(idx) for idx in failure_indices[:20])
            suffix = "..." if len(failure_indices) > 20 else ""
            f.write(f"  Failure at test indices: [{indices_str}{suffix}]\n")
        f.write(f"  Log file      : {LOG_FILE}\n")
        f.write("====================================================\n")

    # Console output
    print(f"\n=== Invariant Testing Complete (v{MODEL_VERSION}) ===")
    print(f"  Total Tests   : {total_tests}")
    print(f"  Passed        : {total_tests - total_failures}")
    print(f"  Failed        : {total_failures}")
    print(f"  Success Rate  : {(total_tests - total_failures)/total_tests*100:.2f}%")
    print(f"\n  Log written to: {LOG_FILE}")

    return total_tests, total_failures


# =============================================================================
# 8. RUN — 50 tests with a fixed seed for reproducibility
# =============================================================================

if __name__ == "__main__":
    test_invariant_sweep(num_tests=5000, seed=42)
