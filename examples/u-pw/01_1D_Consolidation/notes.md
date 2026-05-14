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

## L3 Loading Route Audit

Date: 2026-05-14

`ExternalLoad_L3_InitialPressureGate` tests the recommended no-source route:
initialize the analytical load-generated excess pressure directly and remove
mechanical `AccInput`.

Key result:

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- Peak excess pressure stays at the prescribed `10 kPa`, rather than the L2
  dynamic peak of about `6.25e5 Pa`.
- Bottom RMSE versus the `q0=10 kPa` Terzaghi curve improves by about `30x`;
  final profile RMSE improves by about `5.25x`.
- Top drained and bottom no-flux diagnostics remain clean.

Interpretation:

L3a is a PR diffusion and hydraulic boundary gate. It is much closer to the
analytical initial-value problem than L2, but it is not a strict paper-level
mechanical load reproduction because `PorePressureFeedback=0` bypasses the
skeleton storage response. Do not start a broad damping/viscosity sweep from
L2. If strict 1D reproduction remains active, design L3b as a top loading
plate/surface traction or consistent stress/pore-pressure initialization route.

## L3b Mechanical Top-Load Prototype

Date: 2026-05-14

`ExternalLoad_L3b_MechanicalTopLoad` adds a CPU-only, default-off
`MechanicalTopLoad` route. It removes `AccInput` and applies the total load
`Fz=q0*A` to the detected top material surface.

Key result:

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- CPU Release/Debug and GPU Release builds pass.
- GPU simulation is deferred; `MechanicalTopLoad=1` is CPU-only.
- Applied load scale is correct: `q0=-10 kPa`, `A=0.1 m2`, `Fz=-1000 N`.
- The pore-pressure response is still dynamically over-amplified:
  peak excess is about `5.9e5 Pa`.
- Analytical comparison is not improved over L2 and is far from L3a.

Interpretation:

L3b confirms that a direct top material-surface force is still too close to an
acceleration-driven load-generation route. It is not native `AccInput`, but it
is also not a quasi-static force-controlled platen or a consistent Terzaghi
initial stress state. The next strict route should be L3c consistent
stress/pore-pressure initialization or a true force-controlled loading plate.
Damping/viscosity sweeps remain premature.

## L3c Consistent Initial State

Date: 2026-05-14

`ExternalLoad_L3c_ConsistentInitialState` uses the Terzaghi analytical initial
condition directly:

- `p_w^0=|q0|=10 kPa`;
- zero effective-stress increment (`InitialStressMode=0`);
- no `AccInput`;
- no `MechanicalTopLoad`;
- `PorePressureFeedback=0`;
- top drained from initialization and bottom no-flux correction enabled.

Key result:

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- Peak excess pressure remains `10 kPa`, so the L2/L3b dynamic peak is avoided.
- CPU bottom RMSE versus Terzaghi q0 is about `7.287e3 Pa`; final profile RMSE
  is about `9.129e3 Pa`.
- GPU metrics match CPU to roundoff for this reduced gate.
- Top drained residual is `0 Pa`; bottom no-flux proxy is about `2.3e-3 Pa`.

Interpretation:

L3c confirms that the consistent feedback-off Terzaghi gate is the uniform
initial excess-pressure route with no added effective-stress impulse. The
current `InitialStressMode=1` is CPU-only isotropic effective compression and
is not a vertical surcharge or total-stress initializer. L3c is therefore a
paper-compatible PR diffusion/boundary and initial-state validation, not a full
mechanical load-generation reproduction. Damping/viscosity sweeps remain
premature.
