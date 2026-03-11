#!/usr/bin/env python3
"""
Markov chain analysis — template wrapper.

CUSTOMIZE:
  1. Update STATES with your domain's tool-call state taxonomy
  2. Update classify_state() with your domain-specific logic
  3. Update CLUSTER_DEFINITIONS, DELTA_PAIRS, NOTE_MAP, COLORS, VARIANT_ORDER

Requires markov-agent-analysis library:
    pip install -e path/to/markov-agent-analysis[all]
    # or: uv pip install -e path/to/markov-agent-analysis[all]

Run:
    python scripts/make_markov_analysis.py
"""

from pathlib import Path
import duckdb
import matplotlib
matplotlib.use("Agg")

from markov_agent_analysis import MarkovAnalysisPipeline

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "curated"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "figures"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"

# ---------------------------------------------------------------------------
# CUSTOMIZE: State taxonomy for your domain
# ---------------------------------------------------------------------------

# Replace with your domain's semantic state names.
# These are the labels your classify_state() function returns.
STATES = [
    "EXPLORE",    # reading/searching the codebase
    "READ_KB",    # reading knowledge base files
    "WRITE",      # writing output files
    "BUILD",      # running build/test commands
    "FIX",        # editing/fixing errors
]

# CUSTOMIZE: per-state colors (optional — defaults to tab10 palette)
COLORS = {}

# CUSTOMIZE: display order for variant names in charts
VARIANT_ORDER = [
    "control",
    "variant-a",
    "variant-b",
]

# CUSTOMIZE: cluster definitions for cluster% computation
# Maps cluster label → list of state names in that cluster
CLUSTER_DEFINITIONS = {
    # "BUILD_FIX": ["BUILD", "FIX"],
}

# CUSTOMIZE: variant pairs for intervention delta heatmaps
# Format: (variant_a, variant_b, "label") — heatmap shows P_b - P_a
DELTA_PAIRS = [
    # ("control", "variant-a", "Effect of hardened prompt"),
    # ("variant-a", "variant-b", "Effect of KB"),
]

# CUSTOMIZE: human-readable labels for each variant (used in findings.md)
NOTE_MAP = {
    # "control":   "Naive baseline",
    # "variant-a": "Hardened prompt",
}

# ---------------------------------------------------------------------------
# CUSTOMIZE: Classifier — maps (tool_name, target) → state name
# ---------------------------------------------------------------------------

def classify_state(tool_name: str, target: str) -> str | None:
    """
    Map a tool call to a semantic state name.

    Return None to exclude the tool call from analysis (e.g., meta-tools).
    Return a string from STATES to classify it.

    Example for a code generation task:
        if tool_lower == "bash" and "mvn" in target_lower: return "BUILD"
        if tool_lower in ("read", "readfile"): return "EXPLORE"
        if tool_lower in ("write", "writefile"): return "WRITE"
    """
    tool_lower = tool_name.lower() if tool_name else ""
    target_lower = target.lower() if target else ""

    # CUSTOMIZE: replace with your domain logic
    if tool_lower == "bash":
        return "BUILD"
    if tool_lower in ("write", "writefile"):
        return "WRITE"
    if tool_lower in ("edit", "str_replace_editor"):
        return "FIX"
    if tool_lower in ("read", "readfile"):
        if any(kb in target_lower for kb in ["knowledge/", "/kb/", "index.md"]):
            return "READ_KB"
        return "EXPLORE"
    if tool_lower in ("glob", "grep", "find"):
        return "EXPLORE"

    return "EXPLORE"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    con = duckdb.connect()
    items = con.execute(f"SELECT * FROM '{DATA_DIR}/item_results.parquet'").df()
    tool_uses_path = DATA_DIR / "tool_uses.parquet"
    tools = (con.execute(f"SELECT * FROM '{tool_uses_path}'").df()
             if tool_uses_path.exists() else None)
    con.close()
    return items, tools

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time
    t0 = time.time()
    print("Markov Chain Analysis (domain wrapper)")
    print("=" * 50)
    print("\nLoading data...")
    items, tools = load_data()
    if tools is None or tools.empty:
        print("ERROR: No tool_uses.parquet found. Run load_results.py first.")
        raise SystemExit(1)
    print(f"  tool_uses: {len(tools)} rows")
    print(f"  item_results: {len(items)} rows")

    # NOTE: load_results.py already uses the library's expected column names:
    #   item_id (not item_slug), tool_target (not target), global_seq for ordering
    tools = tools.sort_values(["variant", "item_id", "global_seq"])

    pipeline = MarkovAnalysisPipeline(
        classify_fn=classify_state,
        states=STATES,
        output_dir=OUTPUT_DIR,
        analysis_dir=ANALYSIS_DIR,
        colors=COLORS,
        variant_order=VARIANT_ORDER,
        cluster_definitions=CLUSTER_DEFINITIONS,
        delta_pairs=DELTA_PAIRS,
        note_map=NOTE_MAP,
        enable_sankey=True,
    )
    pipeline.run(tools, items)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Figures:      {OUTPUT_DIR}")
    print(f"  Summary:      {ANALYSIS_DIR / 'markov-findings.md'}")
