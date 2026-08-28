#!/usr/bin/env python3
"""Decide whether a sweep can detect what it is looking for — BEFORE spending the runs.

An experimenter spends twelve runs and only then learns the design could never have detected the
effect they wanted. v4 is the case: n=3 gave roughly a ±19% detection threshold, so most of what it
measured came back "undetected" — which is not "no effect". Halving an interval costs 4× the runs,
and that is a decision worth making before the money is spent rather than after.

This runs between planning and dispatch. The arithmetic is NOT reimplemented here — it comes from
`agent_control_theory.effects`, because a copy that was right once is how the truncation defect
survived its own library fix.

Usage:
    python scripts/preflight_power.py sweep-design.json
    python scripts/preflight_power.py --none      # explicitly undeclared

Exit codes: 0 adequate · 1 underpowered (refuse) · 2 undeclared · 3 malformed declaration.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from agent_control_theory.effects import minimum_detectable_effect, n_for_target_mde

#: How much a σ can be trusted, strongest first. Stated here so nobody re-derives it, and carried
#: into every verdict so a power claim cannot be quoted without it.
SIGMA_SOURCES = {
    "PRIOR_SWEEP": "measured from a previous sweep's replicated cells — strongest, unavailable the first time",
    "PILOT": "measured from a pilot of this design — accurate, but costs runs to decide whether to spend runs",
    "ASSUMED": "declared by the experimenter — always available, and honest ONLY because the number is shown here",
}


@dataclass
class Verdict:
    """A power decision, with the σ it rests on attached so it cannot be quoted without one."""

    status: str  # ADEQUATE | UNDERPOWERED | UNDECLARED | MALFORMED
    response: str = ""
    sigma: float = 0.0
    sigma_source: str = ""
    replicates: int = 0
    cells: int = 1
    target: float = 0.0
    per_factor: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)

    @property
    def declared(self) -> bool:
        return self.status in ("ADEQUATE", "UNDERPOWERED")

    def render(self) -> str:
        if self.status == "UNDECLARED":
            return (
                "POWER: UNDECLARED — this sweep did not say what effect it intends to detect.\n"
                "  Any effect it reports carries no claim about what it could have detected, and an\n"
                "  'undetected' result from it cannot be distinguished from 'no effect'.\n"
                "  Declare one with a sweep design, or record this state alongside the results."
            )
        if self.status == "MALFORMED":
            return "POWER: MALFORMED DECLARATION — " + "; ".join(self.reasons)

        head = [
            f"POWER: {self.status}",
            f"  response      {self.response}",
            f"  design        {self.cells} cell(s) x {self.replicates} replicate(s)",
            # The source travels with the number, always. A σ nobody can trace is a number that
            # makes a check pass.
            f"  sigma         {self.sigma:.4g}  [{self.sigma_source}: {SIGMA_SOURCES[self.sigma_source]}]",
            f"  target        detect {self.target:.4g}",
        ]
        for factor, detail in sorted(self.per_factor.items()):
            mark = "OK " if detail["adequate"] else "NO "
            line = (f"  {mark}{factor:<12} MDE {detail['mde']:.4g} "
                    f"at n={detail['n_per_side']} per side")
            if not detail["adequate"]:
                line += (f"  -> cannot detect {self.target:.4g}; "
                         f"needs {detail['required_replicates']} replicate(s) per cell "
                         f"({detail['required_n_per_side']} per side)")
            head.append(line)
        return "\n".join(head)


def _cells(factors: dict) -> int:
    total = 1
    for levels in factors.values():
        total *= len(levels)
    return total


def evaluate(declaration: dict) -> Verdict:
    """Can this design see the effect it declared? Computed, not asserted."""
    problems = []
    for required in ("response", "replicates", "targetEffect", "sigmaSource"):
        if required not in declaration:
            problems.append(f"missing '{required}'")
    if problems:
        return Verdict(status="MALFORMED", reasons=problems)

    factors = declaration.get("factors", {}) or {}
    replicates = int(declaration["replicates"])
    source = declaration["sigmaSource"]
    kind = source.get("kind", "")
    if kind not in SIGMA_SOURCES:
        return Verdict(status="MALFORMED",
                       reasons=[f"sigmaSource.kind must be one of {sorted(SIGMA_SOURCES)}, got {kind!r}"])
    sigma = float(source["value"])

    target_spec = declaration["targetEffect"]
    target = float(target_spec["value"])
    if target_spec.get("unit") == "percent":
        baseline = target_spec.get("baseline")
        if baseline is None:
            return Verdict(status="MALFORMED",
                           reasons=["targetEffect.unit is 'percent' but no 'baseline' given; "
                                    "a percentage is not an effect size without the mean it is a "
                                    "percentage of"])
        target = abs(float(baseline)) * target / 100.0

    cells = _cells(factors)
    per_factor = {}
    # A factorial buys power: a main effect pools every cell at each level, so n per side is the
    # replicate count times the cells sharing that level. This is why declaring the design is not
    # bookkeeping -- it changes the answer.
    comparisons = {f: len(levels) for f, levels in factors.items()} or {"(single comparison)": 2}
    for factor, n_levels in comparisons.items():
        n_per_side = replicates * max(cells // max(n_levels, 1), 1)
        mde = minimum_detectable_effect(sigma, n_per_side)
        adequate = mde <= target
        required_n = None if adequate else n_for_target_mde(sigma, target)
        per_factor[factor] = {
            "mde": mde,
            "n_per_side": n_per_side,
            "adequate": adequate,
            "required_n_per_side": required_n,
            "required_replicates": (None if adequate
                                    else max(1, math.ceil(required_n / max(cells // max(n_levels, 1), 1)))),
        }

    status = "ADEQUATE" if all(d["adequate"] for d in per_factor.values()) else "UNDERPOWERED"
    return Verdict(status=status, response=str(declaration["response"]), sigma=sigma,
                   sigma_source=kind, replicates=replicates, cells=cells, target=target,
                   per_factor=per_factor)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("declaration", nargs="?", type=Path)
    parser.add_argument("--none", action="store_true",
                        help="run explicitly undeclared; exits 2 so the state is never silent")
    args = parser.parse_args(argv)

    if args.none or args.declaration is None:
        print(Verdict(status="UNDECLARED").render())
        return 2
    try:
        declaration = json.loads(args.declaration.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(Verdict(status="MALFORMED", reasons=[str(error)]).render())
        return 3

    verdict = evaluate(declaration)
    print(verdict.render())
    return {"ADEQUATE": 0, "UNDERPOWERED": 1, "UNDECLARED": 2, "MALFORMED": 3}[verdict.status]


if __name__ == "__main__":
    raise SystemExit(main())
