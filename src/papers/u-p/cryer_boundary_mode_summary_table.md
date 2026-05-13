# Cryer Boundary Mode Summary Table

Date: 2026-05-13

This table summarizes the strict Cryer curved-drained boundary attempts through
C5o. The table is a no-go record, not a production recommendation.

| Mode | Concept | Source change? | CPU/GPU | Pressure-only result | Main improvement | Main failure | Final status |
|---|---|---|---|---|---|---|---|
| Mode 0 legacy | Original first-order spherical Dirichlet ghost behavior | Existing/prototype path | CPU only for strict route; GPU deferred | Not sufficient for strict FV gate | First reduced curved boundary route | Surface residual and excessive center pressure | Retained only as legacy reference |
| Mode 1 simple/strengthened ghost | Stronger image ghost for curved drained surface | Yes, C5c | CPU only; GPU hard error for curved route | Small improvement only | Showed direction of stronger drained coupling | Did not remove systematic surface residual | Retained as diagnostic |
| PPO 2 hydraulic mDBC-style path | Separate `PorePressureBoundaryOperator=2` hydraulic boundary-particle style route | Earlier operator work | CPU diagnostic; GPU not strict Cryer-ready | Not a strict Cryer spherical diffusion solution | Useful for general hydraulic-boundary thinking | Does not solve continuous curved drained sphere | Not used for strict route |
| Curved mode 2 clamp | Diagnostic material surface clamp | Yes, C5c | CPU diagnostic only | Reduces center pressure strongly | Proved the surface residual matters | Directly clamps material pressure, not production | Rejected except as diagnostic bound |
| Mode 3 old spherical ghost | Material-side spherical Dirichlet ghost | Yes, C4-C/C4-D | CPU only; GPU hard error | Center peak about `7.66 p0` | Enabled first strict-sphere smoke | Surface residual systematic | Not C6-ready |
| Mode 3 strengthened | Strengthened material-side spherical ghost | Yes, C5c | CPU only; GPU hard error | Slight residual reduction | Tested stronger material-side drain | Improvement too small | Frozen |
| Mode 3 quadrature | Material-side multi-sample spherical quadrature | Yes, C5d | CPU only; GPU hard error | Slight improvement only | Reduced sample-location dependence | Still not a robust drained boundary | Frozen |
| Mode 4 raw | Boundary-particle prescribed drained state, raw volume weighting | Yes, C5e | CPU only; GPU hard error | Over-drained; final pressure-only center `-97.17 Pa` | Moved toward literature-like boundary particles | Raw boundary volume over-counting | Rejected as production |
| Mode 4 normalized | Boundary-particle prescribed drained state with local partition normalization | Yes, C5f | CPU only; GPU hard error | Better than raw, but over-strong nonuniform Robin-like; median flux ratios about `1.63-2.26` | Reduced pressure-rate artifact and some residuals | Still too high center peak and nonuniform flux | Retained as comparison baseline |
| Mode 5 MLS normal-gradient | Local constrained MLS normal-gradient flux correction | Yes, C5j | CPU only; GPU hard error | No flux reversal, but final flux ratio about `4` and surface shell too high | Improved center/volume RMSE versus mode 4 | Did not match FV radial diffusion | Frozen diagnostic |
| Mode 6 radial-shell flux | FV-style outer boundary flux distributed to surface shell | Yes, C5k | CPU only; GPU hard error | `dp=0.010` median flux ratio near `1`, but surface shell still far too high; `dp=0.008` flux reversal | Showed global boundary flux alone is not enough | Near-boundary redistribution/inward exchange inconsistent | Frozen diagnostic |
| Mode 7 conservative shell exchange | Conservative multi-shell radial FV exchange | Yes, C5m | CPU only; GPU hard error | Shell balance residual near machine zero, but pressure-only gate failed | Proved shell bookkeeping can be enforced | Center/volume/surface not jointly improved; flux reversal remained | Frozen diagnostic |
| Mode 8 corrected Laplacian | Boundary-aware quadratic MLS Laplacian | Yes, C5n | CPU only; GPU hard error | Manufactured gate passed, dynamic pressure-only gate over-drained badly | Fixed static near-boundary polynomial consistency | Negative pressure, flux reversal, huge rate artifact | Frozen as diagnostic |
| Mode 8 limiter | Positivity and MLS/material blend limiters | Yes, C5o | CPU only; GPU hard error | Best blend improved center and reduced rate artifact but surface shell and flux still failed | Confirmed simple limiting is not enough | Negative pressure not eliminated; flux reversal in all limiter cases | No-go for current local patch route |

## Decision

No current mode passes the pressure-only spherical FV diffusion gate. The
strict Cryer route is deferred before C6. Future Cryer work should begin from a
redesigned dynamic drained-boundary value problem, not another local extension
of modes `3` through `8`.
