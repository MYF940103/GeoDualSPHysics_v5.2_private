# 01 1D Consolidation Notes

## L2 Paper-Aligned External Load

Date: 2026-05-14

`ExternalLoad_L2_PaperAligned` aligns the 1D external-load setup with the
paper-style Terzaghi constants and adds analytical postprocessing.

Key result:

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- Top drained residual and bottom no-flux proxy are small.
- CPU/GPU responses are nearly identical.
- The `q0=-10 kPa` AccInput top material layer generates a much larger dynamic
  excess-pressure response than the Terzaghi analytical reference.

Interpretation:

L2 is a useful paper-aligned workflow diagnostic, but it is not a strict
paper-compatible validation. The main blocker is the reduced loading route:
native `AccInput` on `mkfluid=1` is not equivalent to a quasi-static surface
traction or loading plate at this load magnitude.

Next step if this module remains active:

- avoid broad damping/viscosity sweeps first;
- audit loading/staging or a proper plate/traction route;
- otherwise move to the next u-p benchmark/module with L2 documented as a
  bounded but non-strict external-load result.
