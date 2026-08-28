"""Ground-truth tests for the verdicts `validate_markov.py` renders.

The template previously shipped `validate_markov.py` with **no test of any kind**. It renders
human-readable judgements, and this programme's evidence is that a verdict function is exactly
where a wrong answer fails to announce itself: `validation.py` shipped two wrong verdict rules and
nobody noticed until real data contradicted the output. A template propagates that blind spot into
every experiment scaffolded from it, which is why these live here rather than only upstream.

Scope, deliberately narrow. The two verdict *rules* belong to `agent_control_theory` and are tested
there against ground truth. What the template can and must own is different:

  1. that its imports resolve to the canonical package rather than the deprecated shim, so the
     migration cannot silently regress; and
  2. that the *installed* library is new enough to contain the corrected rules — because the
     template cannot fix them, and an older library would silently reintroduce them while every
     other test still passed.

(3) is end-to-end ground truth through this template's own taxonomy: known-benign data in, benign
verdict out.

**Which of these actually discriminate, verified rather than assumed.** Run against a library
checkout predating the corrections, (2) and (3) FAIL and (1) and (4) PASS. So (2) and (3) are real
gates; (4) is a benign-behaviour regression check, not a fix detector — the old stationarity rule
does not fire on this data shape at any sample size tried, and the gate that does discriminate for
it lives in the library's own suite. (4) is kept because it would still catch a future regression
that calls homogeneous data non-stationary; it is labelled so nobody mistakes it for proof the
stationarity fix is installed. Test (2) is what covers that.

Run:  pytest scripts/tests/test_validate_markov.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agent_control_theory.validation import run_second_order_test, run_stationarity_test

# This template's taxonomy. Kept local so the test does not depend on the analysis driver
# importing cleanly, which needs duckdb and a results/ tree.
STATES = ["EXPLORE", "READ_KB", "BUILD", "FIX", "WRITE", "JAR", "TEST", "PLAN", "DONE"]
N = len(STATES)


def _first_order_matrix(seed: int = 0) -> np.ndarray:
    """A realistic first-order chain: heavy self-loops and a long thin tail.

    The thin tail is the point. It produces many sparsely-observed (prev, curr) pairs, and the
    plug-in KL estimator's bias on those pairs is what drove the old, wrong verdict.
    """
    rng = np.random.default_rng(seed)
    P = np.zeros((N, N))
    for i in range(N):
        row = rng.dirichlet(np.full(N, 0.35))
        row[i] += 2.5 if i == 0 else 0.8
        P[i] = row / row.sum()
    return P


def _simulate_first_order(P, n_traces, length, seed, variant="a") -> pd.DataFrame:
    """Traces from a PERFECT first-order chain — by construction, order 1 is adequate."""
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_traces):
        s = 0
        for k in range(length):
            rows.append({"variant": variant, "trace_id": f"{variant}-t{t}", "item_id": "item",
                         "global_seq": k, "semantic_state": STATES[s]})
            s = int(rng.choice(N, p=P[s]))
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def first_order_traces() -> pd.DataFrame:
    return _simulate_first_order(_first_order_matrix(), n_traces=10, length=100, seed=1)


def test_imports_resolve_to_the_canonical_package_not_the_shim():
    """`markov_agent_analysis` is a back-compat shim that aliases the real modules.

    Importing through it works, so a regression here is invisible at runtime — the shim will keep
    resolving until the library drops it, and then every scaffolded experiment breaks at once.
    """
    import agent_control_theory.validation as canonical

    assert run_second_order_test.__module__.startswith("agent_control_theory")
    assert run_stationarity_test.__module__.startswith("agent_control_theory")
    assert canonical.run_second_order_test is run_second_order_test


def test_installed_library_contains_the_corrected_second_order_rule(first_order_traces):
    """The template cannot fix the verdict rules; it can refuse to run against a library without them.

    `mean_kl_corrected` is the observable signature of the bias correction. A library predating it
    returns the old uncorrected shape, and the end-to-end tests below could then pass or fail for
    reasons unrelated to this template.
    """
    result = run_second_order_test(first_order_traces, STATES)
    assert "mean_kl_corrected" in result, (
        "installed agent-control-theory predates the second-order bias correction; "
        "reinstall the library before trusting any verdict this template renders"
    )
    assert "lr_pvalue" in result


def test_perfect_first_order_data_is_not_called_second_order(first_order_traces):
    """Ground truth: the data IS first-order, so the verdict must not claim otherwise.

    The pre-fix rule returned "SIGNIFICANT SECOND-ORDER DEPENDENCE" on exactly this input, at every
    sample size tried — the alarming answer on data containing nothing to be alarmed about.
    """
    result = run_second_order_test(first_order_traces, STATES)
    assert "SECOND-ORDER" not in result["verdict"].upper() or "NO" in result["verdict"].upper(), (
        f"first-order data produced verdict {result['verdict']!r} "
        f"(lr_pvalue={result.get('lr_pvalue')!r})"
    )


def test_two_samples_of_one_homogeneous_chain_are_called_stationary():
    """Ground truth: both variants are drawn from the SAME chain, so there is nothing to detect.

    NOT a fix detector. Verified against a pre-correction library: this passes there too, because
    the old rule's Frobenius trigger does not fire on this data shape at any sample size tried
    (8x80 through 30x200). The discriminating stationarity gates live in the library's own suite.
    Kept as a regression check — it would still catch a future rule that calls homogeneous data
    non-stationary.
    """
    P = _first_order_matrix()
    a = _simulate_first_order(P, n_traces=8, length=80, seed=2, variant="a")
    b = _simulate_first_order(P, n_traces=8, length=80, seed=3, variant="b")
    result = run_stationarity_test(pd.concat([a, b], ignore_index=True), STATES)
    assert "NON-STATIONARY" not in result["verdict"].upper(), (
        f"one homogeneous chain produced verdict {result['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# CT7 — start-state comparability. The half that 0.3.0 does NOT fix.
#
# "On the v4 data CT6 changes nothing and CT7 flips the sign." V is a vector; N[0] is expected
# steps FROM STATES[0]. Reading it as "the" trajectory length assumes every trajectory starts
# there. These tests are written to FAIL on mismatched start states -- a guard that passes on
# everything available is theatre.
# ---------------------------------------------------------------------------

def _traces(start_state: str, n_traces: int, length: int, variant: str) -> pd.DataFrame:
    rows = []
    for t in range(n_traces):
        for k in range(length):
            rows.append({"variant": variant, "trace_id": f"{variant}-t{t}", "item_id": "item",
                         "global_seq": k, "semantic_state": start_state if k == 0 else "BUILD"})
    return pd.DataFrame(rows)


def _load_validate_markov():
    """Import the template's analysis module without running its __main__ path."""
    import importlib.util, sys, pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("validate_markov", root / "validate_markov.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_markov"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_start_state_index_points_at_where_traces_actually_start():
    """The row V must be read from. Backed by agent_control_theory.comparability, not a local copy."""
    vm = _load_validate_markov()
    df = _traces("READ_KB", 5, 10, "a")
    assert vm.start_state_index(df, "a") == vm.STATES.index("READ_KB")
    assert vm.start_state_index(df, "a") != 0, "STATES[0] is EXPLORE; reading row 0 here is CT7"


def test_differencing_across_mismatched_start_states_is_refused():
    """THE CT7 GATE, now enforced by the library so a correction there reaches this template."""
    from agent_control_theory.comparability import assert_start_states_comparable
    df = pd.concat([_traces("EXPLORE", 5, 10, "a"), _traces("READ_KB", 5, 10, "b")],
                   ignore_index=True)
    with pytest.raises(AssertionError):
        assert_start_states_comparable(df, ["a", "b"], item_id_col="trace_id")


def test_matched_start_states_are_permitted():
    """The guard must not simply refuse everything -- that would be its own kind of theatre."""
    from agent_control_theory.comparability import assert_start_states_comparable
    df = pd.concat([_traces("EXPLORE", 5, 10, "a"), _traces("EXPLORE", 5, 12, "b")],
                   ignore_index=True)
    assert_start_states_comparable(df, ["a", "b"], item_id_col="trace_id")


def test_no_local_copies_of_library_guards():
    """The CT1 lesson applied to CT7's own fix: import the guards, do not redefine them.

    A local copy that was right once is how CT1 survived a library fix. If these are defined here
    again, a correction in agent_control_theory will not reach this template.
    """
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent.parent / "validate_markov.py").read_text()
    for banned in ("def check_v_matches_observed", "def assert_start_states_comparable",
                   "def empirical_start_distribution", "def effect_with_ci"):
        assert banned not in src, f"{banned} is redefined locally; import it instead"
    assert "from agent_control_theory.comparability import" in src


# ---------------------------------------------------------------------------
# The default report: counting, with the interval on the EFFECT
# ---------------------------------------------------------------------------

def _arm(variant, lengths):
    rows = []
    for t, length in enumerate(lengths):
        for k in range(length):
            rows.append({"variant": variant, "trace_id": f"{variant}-t{t}", "item_id": "item",
                         "global_seq": k, "semantic_state": "EXPLORE" if k == 0 else "BUILD"})
    return rows


def test_a_noisy_effect_is_reported_as_not_detected():
    """THE GATE on the interval. A CI that never crosses zero on real-shaped data is theatre."""
    vm = _load_validate_markov()
    df = pd.DataFrame(_arm("simple", [55, 62, 69]) + _arm("handoff", [44, 51, 59]))
    effect = vm.run_length_effects(df)[0]
    assert effect["detected"] is False
    assert "NO DETECTED EFFECT" in effect["claim"]
    assert "not the same as no effect" in effect["claim"]


def test_a_large_tight_effect_is_still_detected():
    """And it must not refuse everything, or it is theatre in the other direction."""
    vm = _load_validate_markov()
    df = pd.DataFrame(_arm("a", [100, 101, 99, 100]) + _arm("b", [40, 41, 39, 40]))
    effect = vm.run_length_effects(df)[0]
    assert effect["detected"] is True


def test_a_single_trajectory_arm_yields_no_interval_rather_than_a_point_estimate():
    vm = _load_validate_markov()
    df = pd.DataFrame(_arm("a", [50]) + _arm("b", [40]))
    effect = vm.run_length_effects(df)[0]
    assert effect["effect"] is None
    assert "no interval is definable" in effect["note"]

def test_v_identity_guard_still_fires_on_a_wrong_row():
    """Kept live deliberately: the default report no longer computes V, so nothing else calls this.

    An imported-and-never-invoked guard rots silently. V returns the moment per-state cost is not 1
    -- V = N.c is then expected remaining COST rather than steps -- and on that day someone needs to
    know these still work. This test is what keeps them exercised in between.
    """
    from agent_control_theory.comparability import check_v_matches_observed
    vm = _load_validate_markov()
    df = _traces("READ_KB", 5, 10, "a")
    # V claiming far more steps from the true start state than were observed.
    v_per_state = np.full(len(vm.STATES), 99.0)
    with pytest.raises(AssertionError):
        check_v_matches_observed(df, "a", v_per_state, vm.STATES, item_id_col="trace_id")


def test_v_identity_guard_passes_when_v_matches_observation():
    """And it must not fire on correct data, or it is theatre in the other direction."""
    from agent_control_theory.comparability import check_v_matches_observed
    vm = _load_validate_markov()
    df = _traces("READ_KB", 5, 10, "a")
    v_per_state = np.full(len(vm.STATES), 10.0)  # matches the observed mean length
    check_v_matches_observed(df, "a", v_per_state, vm.STATES, item_id_col="trace_id")
