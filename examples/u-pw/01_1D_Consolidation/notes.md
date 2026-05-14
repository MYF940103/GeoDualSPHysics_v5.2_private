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

## L3e Validation Package

Date: 2026-05-14

`L3e_ValidationPackage` consolidates the 1D consolidation chain from L1 through
L3c. It is reporting-only.

Classification:

- L3a/L3c: validation-ready PR diffusion and boundary gates, with L3c preferred
  for the current paper-compatible figure because it states the zero
  effective-stress increment explicitly.
- L1/L2/L3b: stable reduced smoke or loading-route diagnostics.
- L3d: deferred strict mechanical loading route.

Key evidence:

- L2 and L3b remain stable but produce dynamic peaks of about `6.25e5 Pa` and
  `5.90e5 Pa`, respectively.
- L3c keeps the peak at `10 kPa`, with CPU/GPU `code=0`, `excluded=0`, and
  `DtMin=0`.
- L3c bottom RMSE is about `7.287e3 Pa`, and final profile RMSE is about
  `9.129e3 Pa`.
- L3c top drained residual is `0 Pa`; bottom no-flux proxy is about
  `2.3e-3 Pa`.

Recommendation:

Use L3c as the current 1D validation figure. Do not use L2/L3b as strict
validation and do not start a damping/viscosity sweep before a true mechanical
loading route is redesigned. Move to the next u-p module if this
diffusion/boundary coverage is sufficient.

## L4-L5 Strict Reproduction Decision Audit

Date: 2026-05-14

The L4-L5 audit separates strict 1D consolidation reproduction into three
levels:

- Level 1: PR diffusion and hydraulic-boundary validation from a Terzaghi
  initial excess-pressure state. L3c is the current short/medium gate; L4 is
  the recommended GPU long-run extension.
- Level 2: mechanical generation of the initial undrained pressure from the
  top surcharge `q0`. L2 `AccInput` and L3b direct material-surface force are
  stable but fail this level because they create dynamic peaks near `6e5 Pa`.
- Level 3: full coupled effective-stress and pore-pressure feedback response.
  This remains deferred.

Recommendation:

Run L4 next if the goal is the most stable and useful immediate validation.
It should reuse L3c, extend the GPU/CPU pressure-diffusion comparison, and
remain clearly labeled as a Level-1 diffusion/boundary validation.

L5 is still required for the most complete strict reproduction, but it should
be a separate CPU-first mechanical-loading design/prototype. Full feedback and
damping/viscosity sweeps should wait until the mechanical load route is fixed.

## L4 GPU Long-Run

Date: 2026-05-14

`ExternalLoad_L4_GPU_LongRun` extends the L3c consistent initial-state route to
`TimeMax=0.08 s` with `TimeOut=0.004 s`.

Key result:

- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- Final mapped time factor is `Tv≈2.231e-2`.
- Peak excess pressure remains `10000 Pa`.
- Final bottom excess pressure is about `1.95e-2 Pa`.
- Final top drained residual is `0 Pa`.
- Final bottom no-flux proxy is about `-2.4e-7 Pa`.
- Velocity and `DivVel` remain zero.
- Matching L4 CPU long-run was skipped because L3c CPU runtime indicates it
  would be expensive; L3c CPU/GPU parity remains the route parity reference.

Interpretation:

L4 strengthens the GPU PR diffusion and hydraulic-boundary evidence and can be
used as a Level-1 validation figure. It is not strict full 1D consolidation
reproduction. The long-run confirms bounded monotonic dissipation but also
shows that the feedback-off pressure gate dissipates faster than the Terzaghi
constrained-storage analytical reference. Mechanical load generation,
full-feedback coupling, and damping/viscosity sweeps remain deferred.

## L5 Feedback-On 1D Gate

Date: 2026-05-14

`ExternalLoad_L5_FeedbackOnGate` is the pre-landslide feedback-on coupling
gate. It keeps the L3c initial-state route but enables feedback with
`PorePressureFeedbackMode=1` and `PorePressureFeedbackOperator=1`.

Cases run:

- low-amplitude CPU: `p_w0=1 kPa`;
- target-amplitude CPU: `p_w0=10 kPa`;
- target-amplitude GPU after CPU stability was confirmed.

All three runs completed with `code=0`, `excluded=0`, and no DtMin
adjustments. The target cases keep the peak excess pressure at `10 kPa`, avoid
the L2/L3b `~6e5 Pa` dynamic peak, and preserve the hydraulic boundary checks
(`top residual=0` or near zero; bottom no-flux proxy about `-5.1e-2 Pa` at
target amplitude).

Feedback-on behavior is bounded but not clean Terzaghi decay:

- CPU target velocity max is about `1.12e-2 m/s`;
- CPU target `DivVel` maxAbs is about `1.04e-1 1/s`;
- CPU target `PorePressRate` maxAbs is about `1.54e8 Pa/s`;
- target cases show negative excess-pressure excursions near `-8.2 kPa`;
- the volume mean excess pressure has non-monotonic episodes.

GPU target pressure and velocity metrics match CPU closely, but GPU diagnostic
maxima for `PorePressRate` and feedback acceleration are larger. This should be
tracked before any GPU landslide feedback claim.

Interpretation:

L5 is enough to enter a CPU-first reduced landslide baseline with strong
diagnostics and caveats. It is not a strict coupled Terzaghi validation.
L5b consistent stress initialization remains the next 1D improvement if a
cleaner feedback-on consolidation gate is required. Damping/viscosity sweeps
remain premature.

## BND1 Generalized Operator 2 Boundary Audit

Date: 2026-05-14

`BND1_Operator2Generalized` checks whether `PorePressureBoundaryOperator=2`
can be generalized from a top/bottom prototype into an all-solid-wall no-flux
hydraulic boundary-particle route before landslide work.

Source audit:

- old mode `2` scanned boundary particles but only classified top drained and
  bottom no-flux bands;
- lateral/ordinary solid walls were skipped as inactive neighbours;
- GPU mode `2` was and remains unsupported.

Patch:

- mode `2` only;
- top/free drained boundary particles keep excess Dirichlet `p'=0`;
- every other ordinary solid boundary particle gets reconstructed
  excess/head no-flux state;
- mode `0`, mode `1`, PR pressure update, feedback, and soil models are
  unchanged.

Verification:

- feedback-off mode `2`: `code=0`, `excluded=0`, `DtMin=0`, ordinary solid
  no-flux contributions are present;
- feedback-on mode `2`: `code=0`, but `excluded=973` and `DtMin=10252`, so it
  fails the coupling gate;
- mode `2` feedback-off analytical error is also worse than mode `1` in this
  short 1D gate.

Decision:

Do not make mode `2` default. Do not port it to GPU yet. Do not use it for
landslide baseline until BND2/BND4 resolve the feedback-on instability and
broader wall diagnostics.

## TINT1 Pore-Pressure Time-Integration Audit

Date: 2026-05-14

TINT1 maps the PR pore-pressure update into the existing Verlet/Symplectic
time stages. No source changes and no new runs were made.

Key staging:

- CPU/GPU Verlet: `Interaction_Forces` computes `PorePressRate` and feedback
  acceleration, then `UpdatePorePressure`, then `ComputeVerlet`.
- CPU/GPU Symplectic: predictor interaction and `ComputeSymplecticPre` run
  first; corrector interaction computes `PorePressRate` and feedback
  acceleration, then `UpdatePorePressure`, then `ComputeSymplecticCorr`.

Interpretation:

`PorePress` is currently an explicit operator-split hydraulic scalar. It is not
integrated like density and not integrated like stress. Feedback acceleration
uses old/stage pressure, while the updated pressure is committed for the next
interaction. This may be fine for L3c/L4 feedback-off diffusion gates, but it
is a staging risk for feedback-on and generalized boundary-particle cases.

Recommended next action:

Design a CPU-only TINT2 opt-in mode, likely an end-of-step or operator-split
pressure update. Keep the default unchanged and keep GPU nonzero modes
deferred until CPU validation passes. Landslide baseline should remain
temporarily deferred unless it uses the existing mode `1` route with explicit
caveats.
