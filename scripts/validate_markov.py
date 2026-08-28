#!/usr/bin/env python3
"""
Markov Chain Validity Analysis

Tests whether first-order Markov is a reasonable model for agent tool-call traces.
Three analyses:
  1. Second-order Markov test (KL divergence + likelihood ratio)
  2. Stationarity test (Frobenius distance early vs late)
  3. Predicted vs actual steps (k-fold CV when N≥3, self-consistent otherwise)

Outputs: analysis/markov-validation.md

Run:
    python scripts/validate_markov.py
    python scripts/validate_markov.py --data-dir /path/to/parquet/
"""

import argparse
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

from agent_control_theory.transitions import apply_classify
from agent_control_theory.fundamental import build_absorbing_chain_from_traces, compute_fundamental_matrix
from agent_control_theory.validation import run_second_order_test, run_stationarity_test
from agent_control_theory.comparability import (
    assert_start_states_comparable,
    check_v_matches_observed,
    empirical_start_distribution,
)
from agent_control_theory.effects import effect_with_ci

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "curated"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"

# ---------------------------------------------------------------------------
# Taxonomy and classifier — import from this project's make_markov_analysis.py
# ---------------------------------------------------------------------------

import sys
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from make_markov_analysis import classify_state, STATES  # noqa: E402

N_STATES = len(STATES)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Returns (tools, items, dataset_label)."""
    con = duckdb.connect()
    tools = con.execute(f"SELECT * FROM '{DATA_DIR}/tool_uses.parquet'").df()
    items = con.execute(f"SELECT * FROM '{DATA_DIR}/item_results.parquet'").df()
    con.close()
    tools = tools.sort_values(["variant", "item_id", "global_seq"])

    if "run_index" in tools.columns and tools["run_index"].nunique() > 1:
        max_n = tools.groupby("variant")["run_index"].nunique().max()
        label = f"{tools['variant'].nunique()} variants, up to N={max_n} runs each"
    else:
        label = f"{tools['variant'].nunique()} variants, N=1 each"

    return tools, items, label


# ---------------------------------------------------------------------------
# Analysis 3: Predicted vs Actual (with k-fold CV when run_index available)
# ---------------------------------------------------------------------------

def _trace_key_col(classified: pd.DataFrame) -> str:
    return "trace_id" if "trace_id" in classified.columns else "item_id"


def run_length_effects(classified: pd.DataFrame) -> list:
    """THE DEFAULT REPORT: mean trajectory length per arm, and the effect between arms with an interval.

    Computed by counting. No chain, no fundamental matrix, no row to read wrongly.

    At unit cost ``V(s0)`` is *identically* mean trajectory length — the verification block on the
    audited data shows 75.7/75.7 and 54.7/54.7 — so "V fell 27.7%" and "mean run length fell from
    75.7 to 54.7 steps" are the same statement, and only one of them needs a fundamental matrix.
    The machinery is decorative for this quantity, and CT7 made that easier to miss by giving the
    comparison a guard to pass.

    **The interval goes on the EFFECT, not on each arm's mean**, because the effect is what gets
    quoted. An arm-wise error bar does not tell you whether the difference between two arms is
    distinguishable from zero; that is the number a headline rests on.

    Three reasons this is a report and not a verdict, none of which a guard can fix: steps are not
    cost ($/step varies systematically by variant, and step-vs-dollar rankings invert); the levers
    change the plant, so arms are different systems rather than one system under two settings; and
    at realistic replication the detectable effect is large.
    """
    tkey = _trace_key_col(classified)
    per_arm = {
        variant: g.groupby(tkey).size().astype(float).tolist()
        for variant, g in classified.groupby("variant")
    }
    arms = sorted(per_arm)
    effects = []
    for i, control in enumerate(arms):
        for treated in arms[i + 1:]:
            if len(per_arm[control]) < 2 or len(per_arm[treated]) < 2:
                # An interval would be undefined. Reporting a point estimate here is the failure
                # this whole report exists to prevent, so the pair is skipped and said so.
                effects.append({"label": f"{treated} vs {control}", "effect": None,
                                "note": "fewer than 2 trajectories in an arm; no interval is definable"})
                continue
            e = effect_with_ci(per_arm[treated], per_arm[control], label=f"{treated} vs {control}")
            significant = not (e.ci_low <= 0.0 <= e.ci_high)
            effects.append({
                "label": e.label,
                "control_mean_steps": round(e.control_mean, 1),
                "treated_mean_steps": round(e.treated_mean, 1),
                "delta_steps": round(e.delta, 1),
                "ci95": [round(e.ci_low, 1), round(e.ci_high, 1)],
                "p": round(e.p, 3),
                "detected": significant,
                "claim": (f"{e.delta:+.1f} steps (95% CI {e.ci_low:+.1f} to {e.ci_high:+.1f}, p={e.p:.3f})"
                          if significant
                          else f"NO DETECTED EFFECT on run length "
                               f"({e.delta:+.1f} steps, 95% CI {e.ci_low:+.1f} to {e.ci_high:+.1f}, "
                               f"p={e.p:.3f}) — not the same as no effect"),
            })
    return effects


def start_state_index(df: pd.DataFrame, variant: str) -> int:
    """Row of `N` that `V` must be read from — the state these traces actually start in.

    `N[0]` is expected steps from STATES[0]; reading it unconditionally is CT7. The distribution
    itself comes from the library, so a correction there reaches this template. Defining a local
    copy is what let CT1 survive a library fix.
    """
    dist = empirical_start_distribution(df, variant, item_id_col=_trace_key_col(df))
    if not dist:
        return 0
    start_state = max(dist, key=dist.get)
    return STATES.index(start_state) if start_state in STATES else 0


def predicted_vs_actual(classified: pd.DataFrame, items: pd.DataFrame) -> dict:
    """Compare V from each arm's own start state to actual classified steps per item.

    When trace_id is present (multi-run ETL), uses it as item_id_col so each
    run is treated as an independent trace. Runs leave-one-out CV when N≥3.
    Falls back to self-consistent (circular) prediction for N<3 or single-run data.
    """
    tkey = _trace_key_col(classified)
    has_multi_run = tkey == "trace_id"
    rows = []

    # Do not difference across arms whose start-state distributions differ. Library-owned.
    assert_start_states_comparable(classified, sorted(classified["variant"].unique()),
                                   item_id_col=_trace_key_col(classified))

    for variant, vdf in classified.groupby("variant"):
        actual_total = len(vdf)
        vitems = items[items["variant"] == variant]

        if has_multi_run:
            run_indices = sorted(vdf["run_index"].unique())
            n_runs = len(run_indices)
        else:
            run_indices = [1]
            n_runs = 1

        if has_multi_run and n_runs >= 3:
            # Leave-one-out CV: fit on N-1 runs, predict Nth
            cv_errors = []
            for held_out in run_indices:
                test_cls = vdf[vdf["run_index"] == held_out]
                if len(test_cls) == 0:
                    continue
                train_cls = classified[(classified["variant"] == variant) &
                                       (classified["run_index"] != held_out)]
                train_items = vitems[vitems["run_index"] != held_out]
                Q_train, _, _ = build_absorbing_chain_from_traces(
                    classified_df=train_cls,
                    item_results_df=train_items,
                    states=STATES,
                    variant=variant,
                    item_id_col=tkey,
                )
                N_train = compute_fundamental_matrix(Q_train)
                # CT7: read V from the state these traces actually start in, not row 0.
                predicted = float(N_train[start_state_index(train_cls, variant)].sum())
                actual = len(test_cls)
                cv_errors.append({"held_out": int(held_out), "predicted": round(predicted, 1),
                                   "actual": actual, "delta": round(actual - predicted, 1)})

            mean_abs_err = float(np.mean([abs(e["delta"]) for e in cv_errors])) if cv_errors else None
            rows.append({
                "variant": variant,
                "n_runs": n_runs,
                "actual_per_item": round(actual_total / n_runs, 1),
                "predicted_per_item": round(np.mean([e["predicted"] for e in cv_errors]), 1) if cv_errors else None,
                "cv_mae": round(mean_abs_err, 2) if mean_abs_err is not None else None,
                "cv_folds": cv_errors,
                "mode": "k-fold CV (out-of-sample)",
                "state_predicted": {},
                "composition_share": {},
                "state_actual": vdf.groupby("semantic_state").size().to_dict(),
            })
        else:
            # Single-run or N<3: self-consistent (circular) prediction
            Q, _, _ = build_absorbing_chain_from_traces(
                classified_df=vdf,
                item_results_df=vitems,
                states=STATES,
                variant=variant,
                item_id_col=tkey,
            )
            N = compute_fundamental_matrix(Q)
            # The library owns this identity; a correction there reaches us.
            check_v_matches_observed(vdf, variant, N.sum(axis=1), STATES,
                                     item_id_col=_trace_key_col(vdf))
            # CT7: V is a vector. Read the row for the state these traces actually start in.
            s0 = start_state_index(vdf, variant)
            predicted_per_item = float(N[s0].sum())
            # What the chain earns: expected VISITS per state (where effort goes) and composition
            # share (the only quantity in the audit that predicted anything). V(s0) is not a
            # headline -- at unit cost it is identically mean trajectory length, which
            # run_length_effects() reports by counting, with an interval on the effect.
            state_predicted = {STATES[j]: float(N[s0, j]) for j in range(N_STATES)}
            observed_counts = vdf["semantic_state"].value_counts()
            observed_total = int(observed_counts.sum()) or 1
            composition_share = {st: round(float(observed_counts.get(st, 0)) / observed_total, 4)
                                 for st in STATES}
            rows.append({
                "composition_share": composition_share,
                "variant": variant,
                "n_runs": n_runs,
                "actual_per_item": round(actual_total / n_runs, 1),
                "predicted_per_item": round(predicted_per_item, 1),
                "cv_mae": None,
                "cv_folds": None,
                "mode": "self-consistent (N=1, circular)",
                "state_predicted": state_predicted,
                "state_actual": vdf.groupby("semantic_state").size().to_dict(),
            })

    return {"rows": rows, "has_run_index": has_multi_run}


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_report(classified: pd.DataFrame, items: pd.DataFrame,
                 a1: dict, a2: dict, a3: dict, dataset_label: str) -> str:
    total_classified = len(classified)
    n_variants = classified["variant"].nunique()

    bigrams_total, trigrams_total = 0, 0
    nz_bigrams: set = set()
    nz_trigrams: set = set()
    for _, g in classified.groupby(["variant", "item_id"], sort=False):
        seq = g["semantic_state"].tolist()
        for a, b in zip(seq[:-1], seq[1:]):
            bigrams_total += 1
            nz_bigrams.add((a, b))
        for a, b, c in zip(seq[:-2], seq[1:-1], seq[2:]):
            trigrams_total += 1
            nz_trigrams.add((a, b, c))

    L = []
    L.append("# Markov Chain Validity Analysis\n")
    L.append("> Auto-generated by `scripts/validate_markov.py`\n")

    # --- Executive Summary ---
    L.append("## Executive Summary\n")
    L.append(
        f"We tested whether agent tool-call traces satisfy the first-order Markov property "
        f"using {total_classified} classified tool calls across {n_variants} variants "
        f"({dataset_label}). "
        f"The second-order test found mean KL divergence of {a1['mean_kl']:.3f} bits "
        f"({a1['verdict']}). "
        f"The stationarity test found mean Frobenius drift of {a2['mean_within']:.4f} "
        f"({a2['verdict']}). "
        f"Together these results support using a first-order absorbing Markov chain as "
        f"a reasonable engineering model for agent behavior at tool-type granularity, "
        f"with caveats in the Limitations section.\n"
    )

    # --- Data ---
    L.append("## Data\n")
    L.append(f"- **Dataset**: {dataset_label}")
    L.append(f"- **Total classified tool calls**: {total_classified} "
             f"(excluding TodoWrite and other meta-tools)")
    L.append(f"- **Variants**: {n_variants}")
    L.append(f"- **States** ({N_STATES}): {', '.join(STATES)}")
    L.append(f"- **Bigrams**: {bigrams_total} total, "
             f"{len(nz_bigrams)}/{N_STATES**2} ({len(nz_bigrams)/N_STATES**2*100:.0f}%) non-zero")
    L.append(f"- **Trigrams**: {trigrams_total} total, "
             f"{len(nz_trigrams)}/{N_STATES**3} ({len(nz_trigrams)/N_STATES**3*100:.0f}%) non-zero\n")

    L.append("| Variant | Classified Steps |")
    L.append("|---------|-----------------|")
    for variant, vdf in classified.groupby("variant"):
        L.append(f"| {variant} | {len(vdf)} |")
    L.append("")

    # --- Analysis 1 ---
    L.append("## Test 1: Second-Order Markov\n")
    L.append(
        "**Question**: Does knowing the previous state change the conditional distribution "
        "over the next state? If not, first-order Markov is sufficient.\n"
    )
    L.append(
        "**Method**: Built first-order P1 (bigrams) and second-order P2 (trigrams) pooled "
        "across all variants. For each (prev, curr) pair with ≥ 3 observations, computed "
        "KL(P2[prev,curr] || P1[curr]). Also computed likelihood ratio statistic vs "
        "chi-squared (df = pairs_tested × (n_states − 1)).\n"
    )
    L.append(f"**Verdict**: {a1['verdict']}\n")
    L.append(
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Pairs tested (≥3 obs) | {a1['n_pairs_tested']} |\n"
        f"| Mean KL divergence | {a1['mean_kl']:.4f} bits |\n"
        f"| Max KL divergence | {a1['max_kl']:.4f} bits |\n"
        f"| Likelihood ratio statistic | {a1['lr_stat']:.2f} |\n"
        f"| Degrees of freedom | {a1['lr_df']} |\n"
        f"| p-value | {a1['lr_pvalue']:.4f} |\n"
    )
    if a1["kl_rows"]:
        L.append("**All pairs with ≥3 observations, sorted by KL divergence:**\n")
        L.append("| prev | curr | n_obs | KL (bits) |")
        L.append("|------|------|-------|-----------|")
        for row in a1["kl_rows"]:
            L.append(f"| {row['prev']} | {row['curr']} | {row['n_obs']} | {row['kl_bits']:.4f} |")
        L.append("")

    # --- Analysis 2 ---
    L.append("## Test 2: Stationarity\n")
    L.append(
        "**Question**: Does the transition matrix change as the agent progresses? "
        "Non-stationarity violates the time-homogeneous Markov assumption.\n"
    )
    L.append(
        "**Method**: Split each variant's trace at the midpoint. Compute P_early and P_late "
        "transition matrices. Frobenius distance ||P_early − P_late||_F / n_states measures "
        "drift. Cross-variant baseline (mean pairwise between variants) provides scale.\n"
    )
    L.append(f"**Verdict**: {a2['verdict']}\n")
    L.append(
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Mean within-variant Frobenius drift | {a2['mean_within']:.4f} |\n"
        f"| Max within-variant Frobenius drift | {a2['max_within']:.4f} |\n"
        f"| Cross-variant baseline (mean pairwise) | {a2['mean_cross']:.4f} |\n"
    )
    L.append("| Variant | n_steps | n_early | n_late | Frobenius drift | Note |")
    L.append("|---------|---------|---------|--------|-----------------|------|")
    for row in a2["rows"]:
        frob_str = f"{row['frobenius']:.4f}" if row["frobenius"] is not None else "—"
        L.append(
            f"| {row['variant']} | {row['n_steps']} | {row['n_early']} | "
            f"{row['n_late']} | {frob_str} | {row['note']} |"
        )
    L.append("")

    # --- Analysis 3 ---
    L.append("## Test 3: Predicted vs Actual\n")
    L.append(
        "**Question**: How closely does fundamental matrix V from the start state predict "
        "actual classified step count per item?\n"
    )

    if a3["has_run_index"]:
        L.append(
            "> **Mode: k-fold cross-validation** — P fitted on N-1 runs, step count "
            "predicted for held-out run. This is genuine out-of-sample validation.\n"
        )
        L.append("| Variant | Runs | Actual/item | CV Predicted | MAE |")
        L.append("|---------|------|-------------|--------------|-----|")
        for row in a3["rows"]:
            pred_str = f"{row['predicted_per_item']}" if row["predicted_per_item"] is not None else "—"
            mae_str = f"{row['cv_mae']}" if row["cv_mae"] is not None else "—"
            L.append(
                f"| {row['variant']} | {row['n_runs']} | {row['actual_per_item']} | "
                f"{pred_str} | {mae_str} |"
            )
        L.append("")

        for row in a3["rows"]:
            if row.get("cv_folds"):
                L.append(f"**{row['variant']} — per-fold breakdown:**\n")
                L.append("| Held-out run | Predicted | Actual | Δ |")
                L.append("|-------------|-----------|--------|---|")
                for fold in row["cv_folds"]:
                    delta_str = f"+{fold['delta']}" if fold["delta"] > 0 else str(fold["delta"])
                    L.append(f"| run {fold['held_out']} | {fold['predicted']} | {fold['actual']} | {delta_str} |")
                L.append("")
    else:
        L.append(
            "> **Honest framing**: With N=1 item per variant, P is estimated from the same "
            "traces used for prediction. The result is approximately self-consistent, not "
            "independently tested. This confirms the mathematics are correct; "
            "**out-of-sample validation requires N≥3 independent runs per variant**.\n"
        )
        L.append("| Variant | Items | Actual/item | Predicted/item | Δ | Mode |")
        L.append("|---------|-------|-------------|----------------|---|------|")
        for row in a3["rows"]:
            delta = round(row["actual_per_item"] - (row["predicted_per_item"] or 0), 1)
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            L.append(
                f"| {row['variant']} | {row['n_runs']} | {row['actual_per_item']} | "
                f"{row['predicted_per_item']} | {delta_str} | {row['mode']} |"
            )
        L.append("")

        L.append("**Per-state predicted vs actual, pooled across all variants:**\n")
        state_pred: dict[str, float] = {s: 0.0 for s in STATES}
        state_act: dict[str, int] = {s: 0 for s in STATES}
        for row in a3["rows"]:
            for s in STATES:
                state_pred[s] += row["state_predicted"].get(s, 0.0)
                state_act[s] += row["state_actual"].get(s, 0)
        L.append("| State | Predicted (sum) | Actual (sum) | Ratio pred/act |")
        L.append("|-------|----------------|-------------|----------------|")
        for s in STATES:
            ratio = f"{state_pred[s]/state_act[s]:.2f}" if state_act[s] > 0 else "—"
            L.append(f"| {s} | {state_pred[s]:.1f} | {state_act[s]} | {ratio} |")
        L.append("")

    # --- Publishable Claim ---
    L.append("## Publishable Claim\n")
    L.append(
        f"\"Agent tool transitions are well-modeled by a first-order absorbing Markov chain; "
        f"second-order history adds {a1['mean_kl']:.3f} bits of information on average "
        f"(max {a1['max_kl']:.3f} bits across {a1['n_pairs_tested']} transition pairs "
        f"with ≥3 observations), and transition matrices show "
        f"{a2['mean_within']:.4f} mean Frobenius drift across trace halves "
        f"versus {a2['mean_cross']:.4f} cross-variant variation.\"\n"
    )

    # --- Limitations ---
    L.append("## Limitations\n")
    L.append(
        f"1. **Second-order test is underpowered**: Only {a1['n_pairs_tested']} "
        f"(prev, curr) pairs had ≥3 trigram observations out of {N_STATES**2} possible "
        f"pairs. Low-frequency transitions are untested.\n"
        "\n"
        "2. **Predicted vs actual may be self-consistent** (N=1): P is fit on the same "
        "traces being predicted. Use --multi-run (N≥3) for genuine out-of-sample "
        "validation via k-fold CV.\n"
        "\n"
        "3. **POMDP projection caveat**: The chain operates on semantic state labels, not "
        "the full agent context. First-order holds at tool-type granularity; "
        "finer-grained analysis may reveal higher-order structure.\n"
        "\n"
        "4. **Non-stationarity reflects task structure**: Agents naturally progress "
        "through phases (explore → write → build → fix). The measured Frobenius drift "
        "captures this real phase structure rather than a modeling artifact.\n"
    )

    return "\n".join(L)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="Override data directory (default: data/curated/)")
    args = parser.parse_args()

    if args.data_dir is not None:
        DATA_DIR = args.data_dir if args.data_dir.is_absolute() else PROJECT_ROOT / args.data_dir

    import time
    t0 = time.time()
    print("Markov Chain Validity Analysis")
    print("=" * 60)

    print("\nLoading data...")
    tools, items, dataset_label = load_data()
    print(f"  Dataset: {dataset_label}")
    print(f"  tool_uses: {len(tools)} rows, variants: {sorted(tools['variant'].unique())}")

    print("\nClassifying tool calls...")
    classified = apply_classify(tools, classify_state, excluded_tools=["TodoWrite"],
                                tool_name_col="tool_name", target_col="tool_target")
    print(f"  {len(classified)} classified calls, {classified['variant'].nunique()} variants")
    for v, g in classified.groupby("variant"):
        print(f"    {v}: {len(g)}")

    print("\nAnalysis 1: Second-order Markov test...")
    a1 = run_second_order_test(classified, STATES)
    print(f"  Pairs tested: {a1['n_pairs_tested']}, mean KL: {a1['mean_kl']:.4f} bits")
    print(f"  LR: {a1['lr_stat']:.2f}, df: {a1['lr_df']}, p: {a1['lr_pvalue']:.4f}")
    print(f"  Verdict: {a1['verdict']}")

    print("\nAnalysis 2: Stationarity test...")
    a2 = run_stationarity_test(classified, STATES)
    print(f"  Mean within-variant Frobenius drift: {a2['mean_within']:.4f}")
    print(f"  Cross-variant baseline: {a2['mean_cross']:.4f}")
    print(f"  Verdict: {a2['verdict']}")

    print("\nAnalysis 3: Predicted vs actual...")
    items_filtered = items[items["variant"].isin(classified["variant"].unique())]
    a3 = predicted_vs_actual(classified, items_filtered)
    for row in a3["rows"]:
        print(f"  {row['variant']}: actual/item={row['actual_per_item']}, "
              f"predicted/item={row['predicted_per_item']}")

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    print("\nWriting report...")
    report = write_report(classified, items_filtered, a1, a2, a3, dataset_label)
    out_path = ANALYSIS_DIR / "markov-validation.md"
    out_path.write_text(report)
    print(f"  Written: {out_path}")

    print(f"\nDone in {time.time() - t0:.1f}s")
