# Boundary velocity path audit, 2026-07-27

Purpose: identify which mDBC boundary velocity path controls the late pore-pressure-rate residual after the correction-matrix test showed that first-order correction is not the main cause.

Code path audited:

1. `JSphCpuSingle::MdbcBoundCorrection()` calls `Interaction_MdbcCorrection()`.
2. `InteractionMdbcCorrectionT2()` extrapolates a ghost velocity from neighboring soil particles and writes `TangenVelc`.
3. `JSphCpu::InteractionForcesFluid()` uses `TangenVelc` in fluid-bound pairs as `dv*_visc`.
4. The same `dv*_visc` is used by the u-pw pore-pressure-rate compression term `comp = K_w/n * (-div(v_s))`.

Important implementation detail:

- For static boundaries in these tests, `Velrhop` boundary velocity and `MotionVelc` are both zero.
- Therefore the difference between the current path and raw/motion path is exactly the mDBC tangential ghost velocity stored in `TangenVelc`.
- `TangenVelc` is a mechanical mDBC ghost/tangential velocity. It is not the physical wall velocity.

First-step restart results, Pa/s:

| Case/window | Boundary group | affected particles | mean total, current | mean total, raw/motion | current minus raw, affected-particle mean | current minus raw, whole-window mean |
|---|---|---:|---:|---:|---:|---:|
| Lian t=3s, x=[0,4], z=[0,2] | all wall pairs | 133 | -1012.5 | -2350.3 | +1337.8 | +222.7 |
| Lian t=3s, x=[0,4], z=[0,2] | bottom no-slip | 80 | +1821.7 | +1788.9 | +32.8 | +3.3 |
| Lian t=3s, x=[0,4], z=[0,2] | lateral free-slip | 58 | -4834.4 | -7856.9 | +3022.5 | +219.4 |
| Lian t=1s, strip x=[0,1.25], z=[8,10.1] | free-slip wall contacts | 53 | -294454.0 | -130233.6 | -164220.4 | -34401.9 |
| SelfWeight Part_0300 | no-slip wall contacts | 54 | +93204.3 | +93204.3 | 0.0 | 0.0 |

Conclusion:

1. In the Lian late left-bottom window, the velocity-path sensitivity is dominated by the lateral free-slip wall, not the bottom no-slip wall.
2. The lateral free-slip `TangenVelc` contribution explains the previous raw-velocity test: it adds about +223 Pa/s to the whole-window pore-rate residual, moving the residual from roughly -234 Pa/s to about -11 Pa/s.
3. The bottom no-slip wall contribution is small in this diagnostic window, about +3 Pa/s when normalized by all selected particles.
4. SelfWeight does not show a velocity-path difference because its static no-slip wall has no effective `TangenVelc` offset in this restart state.

Most likely numerical issue to test next:

The mDBC free-slip tangential ghost velocity is mechanically reasonable for shear-free wall interaction, but using that same tangential ghost velocity inside the pore-pressure compression term may be too permissive for an impermeable hydraulic wall. For pore-rate compression, the wall-side solid velocity should probably be controlled by the hydraulic/mechanical wall constraint more directly: no normal flux hydraulically, and no wall-normal solid velocity mechanically; tangential free-slip motion may not need to enter the pore-pressure-rate boundary pair in the same way it enters viscous/gradient terms.

Recommended next temporary test:

- Keep mDBC mechanical interaction unchanged.
- In the pore-pressure-rate term only, use `MotionVelc`/raw wall velocity for fluid-bound pairs on free-slip impermeable walls, while retaining the existing `TangenVelc` for mechanical gradients and viscosity.
- Run the Lian t=3s and t=50s comparisons plus SelfWeight/q0 safeguards. If Lian late dissipation improves without degrading early contours or 1D consolidation, then promote it to an XML-controlled pore-rate boundary-velocity mode.

Kept record:

- `bvel_audit_firststep.csv`
