# BND2 Plan: Operator 2 Default Decision and GPU Port Criteria

Date: 2026-05-14

## Current BND1 Decision

`PorePressureBoundaryOperator=2` has been generalized on CPU so ordinary solid boundary particles participate as no-flux hydraulic boundary samples. BND1 confirms the new path is active, but it is not yet a recommended/default operator:

- feedback-off mode `2` is stable but not better than mode `1` in the short 1D analytical gate;
- feedback-on mode `2` is unstable at `p_w0=10 kPa`;
- GPU mode `2` remains unsupported.

## Criteria Before Making Mode 2 Default

Mode `2` can only be considered for default/recommended status after:

1. 1D feedback-off consolidation: `code=0`, `excluded=0`, `DtMin=0`, analytical error no worse than mode `1`.
2. 1D feedback-on gate: stable at `p_w0=10 kPa`, no particle exclusion, no `DtMin` burst.
3. Hydrostatic/no-flow closed-wall diagnostic: no spurious pressure flux.
4. Simple slope/sandbox boundary diagnostic: fixed solid boundaries act no-flux without pressure blow-up.
5. Boundary contribution diagnostics remain interpretable for top drained, bottom no-flux, and lateral/ordinary no-flux walls.

## Likely BND2 CPU Work

- Add a hydrostatic/no-flow wall diagnostic case.
- Add a short slope/sandbox wall-only case before landslide.
- Investigate whether mode `2` needs:
  - boundary contribution scaling;
  - exclusion of periodic duplicate walls;
  - better classification of free-surface vs solid wall boundaries;
  - improved use of `BoundNormal` for side walls;
  - feedback-aware stabilization.

Any such work should remain CPU-first and default-off.

## GPU Port Requirements

GPU porting should wait until CPU mode `2` passes BND2. A future port would need:

- GPU boundary-particle neighbour loops for boundary samples;
- boundary hydraulic reconstruction from nearby material particles;
- top drained and ordinary solid no-flux classification;
- diagnostics matching CPU boundary contribution counts;
- CPU/GPU parity for feedback-off and feedback-on gates.

Likely files:

- `source/JSphGpu.cpp`;
- `source/JSphGpu_ker.cu`;
- GPU memory/diagnostic plumbing if persistent boundary counters are added.

## Rollback Strategy

If BND2 does not stabilize mode `2`, keep:

- mode `0` as production default;
- mode `1` as the current GPU-supported experimental PR boundary operator;
- mode `2` as CPU-only experimental;
- landslide baseline on mode `1` or another verified route.

## Docs Plan

Documentation should state:

- mode `2` is generalized but experimental;
- it is not default;
- it is not GPU-supported;
- landslide baseline should wait for BND2/BND4 if mode `2` is required.
