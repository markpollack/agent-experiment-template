"""The pre-flight power check must be demonstrably capable of saying NO.

A check that always answers "yes, that is enough" is the same theatre as a guard that never fires,
so every claim below is paired with its opposite:

  refuses an underpowered design, AND names the replicates it would need
  passes an adequate one, so it is not simply refusing everything
  makes UNDECLARED loud, so skipping the declaration is not silently equivalent to declaring
  carries the sigma SOURCE into the rendered verdict, so a power claim cannot be quoted without it

The arithmetic itself is agent_control_theory's and is not re-tested here; what is tested is that
this script's answers are consistent with it.
"""

from __future__ import annotations

import json

import pytest

from agent_control_theory.effects import minimum_detectable_effect, n_for_target_mde

from preflight_power import SIGMA_SOURCES, Verdict, evaluate, main


def _design(**over):
    base = {
        "response": "run_length_steps",
        "factors": {"prompt": ["simple", "hardened"], "handoff": ["on", "off"]},
        "replicates": 3,
        "targetEffect": {"value": 19.0, "unit": "percent", "baseline": 62.0},
        "sigmaSource": {"kind": "PRIOR_SWEEP", "value": 11.0},
    }
    base.update(over)
    return base


# --- must say NO ------------------------------------------------------------

def test_a_v4_shaped_design_is_refused():
    """THE GATE. 2x2 at 3 replicates chasing ~19% is the shape that produced "undetected" results."""
    verdict = evaluate(_design())
    assert verdict.status == "UNDERPOWERED"
    assert all(not d["adequate"] for d in verdict.per_factor.values())


def test_refusal_names_the_replicates_required():
    """"Underpowered" without a number is a complaint. The experimenter needs the decision."""
    verdict = evaluate(_design())
    detail = verdict.per_factor["prompt"]
    assert detail["required_replicates"] > verdict.replicates
    assert f"needs {detail['required_replicates']} replicate(s)" in verdict.render()


def test_required_n_actually_achieves_the_target_and_is_minimal():
    """Checked against the arithmetic rather than merely produced."""
    verdict = evaluate(_design())
    detail = verdict.per_factor["prompt"]
    required = detail["required_n_per_side"]
    assert minimum_detectable_effect(verdict.sigma, required) <= verdict.target
    assert minimum_detectable_effect(verdict.sigma, required - 1) > verdict.target


# --- must also say YES ------------------------------------------------------

def test_an_adequately_powered_design_passes():
    """Or the check refuses everything and is theatre in the other direction."""
    verdict = evaluate(_design(replicates=40))
    assert verdict.status == "ADEQUATE"


def test_the_factorial_itself_buys_power():
    """Declaring the design is not bookkeeping -- pooling cells at each level changes the answer."""
    factorial = evaluate(_design(replicates=8))
    flat = evaluate(_design(replicates=8, factors={}))
    assert factorial.per_factor["prompt"]["n_per_side"] > flat.per_factor["(single comparison)"]["n_per_side"]
    assert factorial.per_factor["prompt"]["mde"] < flat.per_factor["(single comparison)"]["mde"]


# --- undeclared must be loud ------------------------------------------------

def test_undeclared_is_not_silent():
    assert main(["--none"]) == 2


def test_undeclared_says_why_it_matters():
    text = Verdict(status="UNDECLARED").render()
    assert "UNDECLARED" in text
    assert "cannot be distinguished from 'no effect'" in text


# --- the sigma source is load-bearing --------------------------------------

@pytest.mark.parametrize("kind", sorted(SIGMA_SOURCES))
def test_every_verdict_carries_where_its_sigma_came_from(kind):
    """A power claim that can be quoted without its sigma source is the optional map again."""
    verdict = evaluate(_design(sigmaSource={"kind": kind, "value": 11.0}))
    rendered = verdict.render()
    assert kind in rendered
    assert SIGMA_SOURCES[kind] in rendered


def test_an_unknown_sigma_source_is_refused():
    verdict = evaluate(_design(sigmaSource={"kind": "VIBES", "value": 11.0}))
    assert verdict.status == "MALFORMED"


def test_a_percentage_target_without_a_baseline_is_refused():
    """A percentage is not an effect size without the mean it is a percentage of."""
    verdict = evaluate(_design(targetEffect={"value": 19.0, "unit": "percent"}))
    assert verdict.status == "MALFORMED"
    assert "not an effect size" in " ".join(verdict.reasons)


def test_exit_codes_distinguish_the_four_states(tmp_path):
    good = tmp_path / "d.json"
    good.write_text(json.dumps(_design(replicates=40)), encoding="utf-8")
    bad = tmp_path / "b.json"
    bad.write_text(json.dumps(_design()), encoding="utf-8")
    broken = tmp_path / "x.json"
    broken.write_text("{not json", encoding="utf-8")
    assert main([str(good)]) == 0
    assert main([str(bad)]) == 1
    assert main(["--none"]) == 2
    assert main([str(broken)]) == 3
