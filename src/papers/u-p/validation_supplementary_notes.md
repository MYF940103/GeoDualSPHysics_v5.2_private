# Supplementary Notes for Self-Weight Consolidation Validation

Date: 2026-05-12

## 1. Why Scenario 2 Uses a Calibrated Effective Reference

The nominal Supporting Materials reference for self-weight Scenario 2 is a
quasi-static one-dimensional consolidation solution. It uses the Eq.(4)
undrained self-weight excess-pressure profile as the initial condition and a
top-drained, bottom-no-flux eigenbasis for the dissipation stage.

The production SPH model solves the dynamic u-pw PR system:

```text
PorePressRate = Kw/n * (-DivVel + k/(rho_w*g) LapPorePress + k LapZ)
```

The analytical curve is therefore not a raw particle-level PR equation
reference. It is a reduced one-dimensional storage/diffusion reference. The
GPU result follows the same dissipation trend, but the apparent SPH response is
about 12% faster in the bottom excess time series. Scaling the reference time
factor as:

```text
cv_eff = 1.1175 cv
```

reduces the bottom excess-pressure relative RMSE from about `7.59%` to about
`1.98%`.

## 2. Why `cv_eff` Is Not Material Retuning

The calibrated effective reference is not used to change the simulation
permeability, stiffness, water bulk modulus, porosity, or any material
parameter. It is used only to explain the difference between:

- the quasi-static analytical reduction;
- the dynamic coupled SPH response;
- explicit volumetric storage through `DivVel`;
- damping and Shepard regularization;
- particle-discrete operator effects.

The manuscript should describe this as an effective time-factor or apparent
consolidation-coefficient sensitivity, not as a calibrated permeability.

## 3. Why Scenario 1 Reference Is Context Rather Than a Strict Analytical Target

The Supporting Materials Scenario 1 reference assumes that the undrained
self-weight excess-pressure profile is instantaneously equal to Eq.(4) at the
drainage activation time. The validated GPU route uses a single-run
`BodyGravityStopTime` workflow instead:

1. body gravity generates the dynamic early self-weight response;
2. mechanical body gravity is stopped at `t=0.002 s`;
3. hydraulic gravity remains active;
4. top drainage activates at the same time.

Earlier A2 diagnostics showed that the actual generated profile near
`t=0.002 s` does not exactly equal the ideal Eq.(4) profile. Therefore Scenario
1 is presented as a stability and drainage-to-equilibrium validation, with the
cosine-series analytical expression kept as context only.

## 4. Why Mode 0 Remains the Production Default

`PorePressureBoundaryOperator=0` is the original production layer-correction
path. It remains the default because:

- Scenario 2 long-run validation is stable;
- Scenario 1 gravity-switch validation is stable;
- top-drained and bottom no-flux diagnostics remain small in the accepted
  validation runs;
- alternative boundary operators did not materially improve the self-weight
  validation metrics.

## 5. Why Modes 1 and 2 Remain Experimental

Mode `1` adds a simple operator-level virtual ghost treatment and is available
on CPU and GPU. It is retained as an experimental strict-boundary path, but it
does not reduce the Scenario 2 bottom excess discrepancy.

Mode `2` adds a CPU-only hydraulic mDBC-style boundary-particle prototype. It
does place reconstructed boundary hydraulic states into `LapPorePress` and
`LapZ`, but H1 showed that it does not improve the pressure-only or
self-weight short metrics, and hydrostatic residuals were slightly worse than
mode `0/1`. GPU mode `2` remains unsupported by design.

## 6. Why Corrected-Gradient Remains Deferred

Corrected-gradient diagnostics were implemented on CPU as diagnostic fields
only. The tests did not show improvement over the current production
material-only PR operators for the hydrostatic and self-weight smoke metrics.
The remaining Scenario 2 discrepancy is better explained by apparent
time-factor/storage behavior than by the material-only corrected-gradient
diagnostic.

Corrected-gradient production operators should therefore remain deferred until
a targeted benchmark shows clear benefit.

## 7. Why the Restart Route Remains Deferred

The staged restart route is still useful for future verification, but it is not
needed for the current paper-compatible self-weight validation because:

- the single-run `BodyGravityStopTime` route has passed short CPU/GPU parity;
- GPU medium and long runs are stable;
- the route avoids GPU restart-state mapping risk for stress, density,
  velocity, pore pressure, and plastic state;
- the intended physical split is still represented: mechanical body gravity is
  stopped while hydraulic gravity remains active.

The restart route should be revisited only if a future benchmark requires
explicit restart-state fidelity.

## 8. Recommended Supplementary Wording

The calibrated effective Scenario 2 reference is used only as a compact
diagnostic of apparent time-factor sensitivity. The production simulation
parameters are unchanged. Scenario 1 is reported as a gravity-switch
drainage-to-equilibrium validation rather than a strict analytical-profile
comparison, because the dynamic single-run workflow does not impose an
instantaneous Eq.(4) pressure state at the switching time. Boundary-operator
experiments and corrected-gradient diagnostics are retained for traceability
but are not part of the production validation line.
