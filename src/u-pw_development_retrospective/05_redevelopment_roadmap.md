# Redevelopment Roadmap After Rollback

## Recommended Reset Point

Choose one clean base:

1. original pre-u-pw branch;
2. artificial-stress stable branch, if that is the desired numerical base;
3. a known clean commit before Cryer/triaxial/MCC interface expansion.

Tag the current branch first:

```powershell
git tag u-pw-pre-rollback-archive-20260514 1b1c1f8d14473b7c20c01b701a211441e6907c18
git push origin u-pw-pre-rollback-archive-20260514
```

## Phase 1: Minimal 1D PR Diffusion Gate

Cherry-pick or reimplement only:

- `PorePressureInit=3`;
- Level-1 Terzaghi analytical script;
- top drained and bottom no-flux checks;
- CPU/GPU parity reporting.

Goal: reproduce L3c/L4 as the first paper-compatible diffusion/boundary figure.

## Phase 2: Minimal Feedback-On 1D Gate

Add only:

- `PorePressureFeedback=1`;
- recommended operator `1`;
- feedback diagnostics already needed by L5.

Goal: reproduce L5 coupling stability without importing BND1 mode `2` or
MechanicalTopLoad.

## Phase 3: Boundary Policy

Before landslide:

- decide whether operator `1` is sufficient for reduced landslide baseline;
- if not, redesign boundary operator from BND1 lessons;
- do not make operator `2` default without feedback-on stability.

## Phase 4: Landslide Reduced Baseline

Proceed only after Phases 1-3:

- CPU-first;
- no GPU claim until CPU baseline is understood;
- no strict validation claim if feedback/boundary route is reduced.

## Deferred Work

Defer:

- strict mechanical top-load 1D route;
- full feedback triaxial/MCC;
- GPU port of experimental boundary/time modes;
- strict Cryer boundary;
- clean MCC validation.
