# BND1 u-pw Hydraulic Boundary-Condition Audit

Date: 2026-05-14

## 1D Consolidation Boundary Conditions

The u-pw 1D consolidation notes use the standard Terzaghi setup:

- top boundary: drained/free-drainage, `p_w = 0` for excess pore pressure after loading;
- bottom boundary: undrained/no-flux;
- lateral boundaries: undrained/no-flux;
- initial excess pore pressure: `p_w^0 = |q0|` for the analytical initial-value gate.

The top condition is a Dirichlet pore-pressure/excess-pressure boundary. The bottom and lateral conditions are Neumann hydraulic boundaries.

## Neumann Convention

For the PR update, no-flux should be interpreted as zero normal hydraulic-head gradient. In the current code:

- `HydraulicElevationSource=1`: no-flux is based on consistency of `p_w/(rho_w g) + z_h`, where `z_h` is the hydraulic elevation along the configured hydraulic gravity direction.
- `HydraulicElevationSource=0`: the elevation term is disabled, so the no-flux mirror reduces to a pore-pressure/excess-pressure reconstruction.

This distinction matters because a hydrostatic field has a nonzero total pressure gradient; enforcing zero total-pressure gradient would be wrong when elevation is active.

## Boundary/Dummy Particles

SPH PR diffusion operators need support near walls. Boundary or dummy hydraulic samples can be used to complete the near-wall quadrature:

- drained boundary samples prescribe `p_w` or excess pressure, usually `0`;
- no-flux boundary samples mirror/reconstruct interior hydraulic head/excess state;
- the boundary samples should enter the Laplacian/elevation quadrature rather than clamping lateral material pressure directly.

## Landslide/Slope Implication

For future landslide/slope cases, fixed solid walls are usually impermeable unless explicitly declared as drains, inflows, outflows, or user-defined hydraulic boundaries. Therefore the physically safer default for an opt-in boundary-particle hydraulic operator is:

- free surfaces or explicit drained boundaries: Dirichlet;
- ordinary solid walls: no-flux;
- special hydraulic boundaries: user-defined, not assumed.

This is why BND1 generalizes mode `2` away from a bottom-only no-flux prototype.

## Exceptions

The generalized rule should not apply to:

- free surfaces represented by material particles and controlled by the top drained layer correction;
- explicitly drained boundary particle sets;
- inflow/outflow hydraulic boundaries;
- future user-prescribed pore-pressure boundaries.

These require explicit classification rather than blanket no-flux behavior.
