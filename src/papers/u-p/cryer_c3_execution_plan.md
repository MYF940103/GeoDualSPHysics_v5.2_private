# Cryer C3 Execution Plan

Date: 2026-05-12

## C3-A: Reduced Cryer Manual-Run Workflow

Goal: use the C1 baseline XML/BAT to produce a qualitative Cryer-like run and
center-pressure history without claiming strict analytical reproduction.

Scope:

- no source changes;
- use `CaseCryer_PR_Baseline_Def.xml`;
- use the existing example-style CPU/GPU Release BATs;
- user manually runs GenCase -> DualSPHysics -> PartVTK when ready;
- add or refine center-pressure extraction after output exists;
- report qualitative pressure response, stability, and visualization.

Recommended next concrete task:

- prepare a strict-ready center-pressure extraction script that can read future
  complete output, but do not run the case automatically.

Advantages:

- fast;
- preserves the current workflow;
- useful for debugging output and visualization.

Limitations:

- reduced geometry;
- no all-around traction;
- no verified analytical comparison.

## C3-B: Strict Cryer Setup Preparation

Goal: prepare an actual Cryer benchmark candidate.

Required before running:

- verified analytical/reference implementation;
- chosen sphere radius `a` and particle spacing;
- full-sphere or documented axisymmetric geometry route;
- all-around normal traction route;
- drained curved boundary strategy;
- center-pressure postprocessing;
- Poisson-ratio sweep plan.

Potential source needs:

- curved drained boundary operator;
- traction/loading support if native XML routes are insufficient;
- optional CPU-only boundary experiment before any GPU port.

Advantages:

- can become a true paper benchmark;
- directly targets Figure 7B behavior.

Risks:

- higher implementation cost;
- source changes may be required;
- GPU should wait until CPU strict setup is credible.

## Recommendation

If the immediate goal is momentum and manual reproducibility, use C3-A:
prepare center-pressure extraction for the reduced baseline, then let the user
run it manually.

If the immediate goal is strict paper reproduction, use C3-B:
first recover the analytical series and exact geometry/normalization, then
decide whether a new CPU boundary/loading implementation is needed.

Do not enter GPU-specific Cryer development until the CPU reference and
geometry are settled.
