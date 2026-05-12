# LIT-B Boundary Method Comparison

Date: 2026-05-12

| Source / method | Formulation type | Drained boundary treatment | Undrained/no-flux treatment | Boundary particles used? | Ghost/MLS used? | Operator-level or clamp? | Curved boundary support? | Compatible with current PR diffusion? | Directly implementable? | Risk / missing pieces |
|---|---|---|---|---|---|---|---|---|---|---|
| Original u-pw paper | transient u-pw PR/PPE | free-surface zero `p_w` or prescribed boundary/dummy `p_w` | pore-pressure Neumann needs MLS extrapolation to enforce `grad(p_w).n=0` | Yes | MLS for boundary pressure extrapolation | Intended operator/boundary-state treatment | Conceptually yes via free-surface/dummy particles | Yes, but needs boundary hydraulic state in PR operator | Not yet; needs source design | Need free-surface detection, boundary selection, MLS kernel, boundary state storage |
| u-pw Supporting Materials | quasi-static 1D consolidation reference | top drained in 1D analytical/reference sense | bottom no-flux in 1D eigenbasis | Not specified for Cryer | Not specified | Analytical/reference, not raw particle operator | No Cryer detail | Only for 1D layer problems | Already approximated by mode 0 for self-weight | Does not solve curved Cryer boundary |
| Drained/undrained SPH paper | drained/undrained penalty framework | drained means `p_w=0` | undrained via penalty `p_w=-K_w tr(eps)` | Yes, 3-4 dummy layers | Adami normalized pressure extrapolation | Boundary-state treatment, not PR diffusion | Wall/dummy boundaries; no PR curved diffusion formula | Partly: pressure extrapolation idea is useful | As inspiration only | Penalty formulation is not transient PR; extrapolation is not drained Dirichlet by itself |
| Current mode 0 | GeoDualSPHysics production PR | top layer post-update drained correction | bottom layer mean/no-flux-style correction | No production hydraulic boundary state | No | Mostly layer correction | No | Yes for 1D/self-weight | Already implemented | Not strict curved boundary |
| Current mode 1 | simple virtual ghost | top drained and bottom no-flux ghost terms in PR operator | head/excess mirror for bottom | No | Simple ghost | Operator-level plus safety projection | No general curved support | Yes | Implemented CPU/GPU experimental | Did not improve self-weight discrepancy |
| Current mode 2 | hydraulic mDBC prototype | selected boundary particles get hydraulic state | head/excess Neumann for bottom/top prototypes | Yes | Local reconstruction, not full original MLS | Operator-level | Not general Cryer sphere | Partly | CPU-only experimental | Short tests did not improve 1D; not adapted to curved Cryer |
| Current mode 3 modes 0/1 | curved drained ghost | spherical material-side Dirichlet ghost | Not a Neumann mode | No | Simple/image ghost | Operator-level | Yes for prescribed sphere | Yes | Implemented CPU-only | Surface material residual remains systematic |
| Current mode 3 mode 3 | multi-sample quadrature | five spherical virtual Dirichlet samples | Not a Neumann mode | No | Virtual quadrature, no MLS | Operator-level | Yes for prescribed sphere | Yes | Implemented CPU-only | Improvement only marginal; lacks boundary-particle hydraulic consistency |
| Diagnostic clamp | material surface drained clamp | directly sets material surface excess to zero | Not applicable | No | No | Post-update clamp | Yes by radius | Numerically intrusive | Diagnostic only | Strong artifacts; not production or strict method |

## Main Comparison Result

The methods closest to the original u-pw description are not current mode 3
ghost/quadrature methods. They are boundary-particle methods with pressure
state reconstruction and MLS/normalized-kernel extrapolation.

Mode 3 is useful as a controlled CPU experiment, but C5d shows it is not enough
to couple the material surface to an ideal drained sphere. The next source
change should therefore pivot toward boundary-particle hydraulic state and
paper-style extrapolation, not another local quadrature weight tweak.
