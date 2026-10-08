# Lian Elastic Hydro-Mechanical Path Audit, 2026-07-31

Scope: continue the late-time excess pore-pressure residual investigation after the
plasticity-off full run proved byte-for-byte identical to the baseline.

## Existing-result checks

- Full output inspected:
  `tests/outputs/CaseLianFlexibleStrip2D_PR_plasticoff_full_20260729_out`.
- Plasticity is ruled out for this case: disabling the Drucker-Prager return
  mapping did not change any particle data in the full 50 s result.
- `PoreMdbcInterpolationMode=1` and `DtFixed=5e-6` had negligible influence in
  the earlier 3 s checks, while damping mainly changed amplitude and spatial
  extent.

## Drainage mask

- After `HydroMechDrainageStartTime=1.0`, the open free surface outside the
  strip is reset to zero pore pressure in the VTK output.
- At `t=3.00001 s`, free-surface particles outside the strip have zero excess
  pore pressure, while the strip-exempt free-surface particles retain nonzero
  pressure.
- Therefore the basic drainage mask is active and is not globally failing.

## Lian strip footprint sensitivity

- Correction after re-checking Lian et al. (2023), Section 4.3: the change from
  strip-contact/impervious treatment to drained open-top treatment is not itself
  an error. The paper states that all boundaries, including the strip-footing
  bottom, are impervious during ramp loading, and after ramp completion a fully
  permeable condition is applied to the upper open surface while the other
  boundaries remain impermeable.
- The hard-coded Lian strip footprint currently uses strict current-coordinate
  limits `x >= 0.0 && x <= 1.25`.
- The left-edge strip free-surface particle `Idp=1744` repeatedly moves by only
  `1e-6` to `1e-5 m` to the left of `x=0`.
- When that happens, the strict footprint drops the strip free-surface count
  from `13` to `12` and treats `Idp=1744` as drained/open rather than under the
  strip footprint. This is consistent with the intended physical boundary only
  if the particle has genuinely moved out of the footing contact/open-surface
  definition.
- These strict-footprint switches correlate with late negative-pressure and
  velocity spikes, for example:

| Part | Time [s] | Strict strip FS | eps=1e-3 strip FS | vmax [m/s] | min EPWP [kPa] | Lost id |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0282 | 14.10001 | 12 | 13 | 4.20e-2 | -3.076 | 1744 |
| 0492 | 24.60001 | 12 | 13 | 8.29e-2 | -3.993 | 1744 |
| 0602 | 30.10001 | 12 | 13 | 4.17e-2 | -3.842 | 1744 |
| 0773 | 38.65001 | 12 | 13 | 5.34e-2 | -3.360 | 1744 |

- A tiny tolerance such as `1e-3 m` would retain the left-edge particle while not
  including the next right-side top particle at `x=1.3 m`, but this would be a
  diagnostic smoothing test only. It should not be treated as the physical fix
  unless a contact/footprint tolerance is explicitly justified.

## Compression source and diffusion scale

- The active pore-pressure-rate path is the main interaction loop, not the older
  standalone helper.
- The implemented form is effectively
  `pdot = (Kw/n) * (-div(vs)) + (Kw/n) * seepage`.
- For the Lian parameters, `Kw/n = 2.5e9 Pa`. This makes late-time pore pressure
  very sensitive to tiny residual or spurious velocity divergence.
- With zero gravity, the position-head term is inactive, so Lian EPWP is the
  direct pore-pressure variable.
- With gravity, the code uses `p/(rho*g)+z`; the static hydrostatic component
  should cancel discretely only if the pressure and position Laplacian operators
  are mutually consistent.

## mDBC hydraulic boundary

- mDBC pore pressure is constructed as
  `p_boundary = p0_boundary + extrapolated(p - p0)`.
- This excess-pressure extrapolation plus baseline add-back is physically
  consistent with an undrained/no-flow hydraulic wall in principle.
- The remaining risk is numerical consistency: ghost position, boundary normal,
  interpolation support, and the ghost velocity used by the compression term
  must be consistent with the mechanical mDBC path.

## Damping and time integration

- Bui-Fukagawa damping is applied to acceleration after the interaction kernel
  has accumulated forces and pore-pressure rate.
- It does not directly alter the current-step pore-pressure rate; it only affects
  the next-step velocity field and therefore the next compression source term.
- Existing q0 and Lian notes show damping controls oscillation amplitude, but it
  is not the primary source of the strict-footprint late spikes.
- Fixed time step bypasses the automatic pore-diffusion `dtw` limiter in
  `DtVariable()`. Current Lian `DtFixed=1e-5` appears stable from the available
  sensitivity checks, but this remains a general safety risk for future cases.

## Current source ranking

1. Strongest Lian-specific numerical sensitivity: strict current-coordinate
   strip footprint at the left edge, which intermittently switches one surface
   particle between strip-contact and drained-open-top treatment. The switch is
   conceptually allowed by the case definition; the concern is only whether the
   one-particle on/off contact treatment is too sharp for the SPH discretisation.
2. General late-time sensitivity: amplified compression source
   `(Kw/n)*(-div(vs))`, especially near boundary/contact particles.
3. Boundary consistency: mDBC hydraulic ghost pressure is conceptually correct,
   but its support and normal consistency should still be stress-tested.
4. Damping/time integration: important for amplitude control, not the leading
   explanation for the Lian dropout events.

## Recommended next temporary validation

Run one reversible diagnostic patch only:

- As a diagnostic only, change the Lian hard-coded strip test to use a very
  small coordinate tolerance or a smoother contact membership for the footprint
  check.
- Run the Lian case to at least `t=15 s` first, because the first clear dropout
  appears near `t=14.1 s`.
- If that removes the `Idp=1744` switching and suppresses the negative EPWP
  spikes, then the formal discussion should be about a physically justified
  contact/load smoothing treatment, not about preventing open-top drainage after
  particles leave the footing contact region.
