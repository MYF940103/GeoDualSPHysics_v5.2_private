# C5m Conservative Multi-Shell Radial Exchange Design

## Purpose

C5m adds `CurvedDrainedBoundaryMode=7`, a CPU-only experimental subroute of
`PorePressureBoundaryOperator=3` for strict Cryer spherical pressure diffusion.
It is a diagnostic finite-volume consistency prototype, not a production
general curved-boundary operator.

## Why Mode 6 Failed

Mode `6` made the integrated boundary sink look reasonable in the coarse
`dp=0.010` case, but it applied that sink only to the outer material shell.
The surface shell stayed far above the FV radial reference because the sink was
not coupled to a conservative outer-to-middle and middle-to-inner radial
exchange structure. A good global flux ratio can therefore coexist with a bad
radial pressure profile.

## Conservation Target

Mode `7` approximates the radial finite-volume equation

```text
dS_k/dt = F_{k-1/2} - F_{k+1/2}
F_{k+1/2} = -D A_{k+1/2} (u_{k+1}-u_k) / dr
```

where `S_k` is pressure storage in shell `k`, `D = Kw/n * k/(rho_w g_h)`, and
`A = 4*pi*r^2`. The inner boundary uses spherical symmetry,
`F_{-1/2}=0`. The outer drained boundary uses `u(R)=0`:

```text
F_R = D 4*pi*R^2 (u_outer - 0) / (R-r_outer)
```

Flux is positive outward.

## Shells

Shell edges are uniform in radius from `0` to `R`. `CurvedDrainedShellCount`
sets the shell count when `CurvedDrainedShellMode=1`; otherwise the count is
auto-derived from `R` and the curved-boundary thickness or `dp`. Particle
volumes are used for the discrete storage map, while analytic shell volumes are
reported for diagnostics.

Empty inner shells are treated as part of the `r=0` symmetry region. Empty
shells between populated shells, or empty outer shells, trigger fallback because
the radial exchange stencil is then not well-defined.

## Mapping Back to Particles

The implemented route is shell-average correction, not a material clamp:

```text
current_rate_k = volume_average(D * LapPorePress_SPH)
target_rate_k  = (F_in - F_out) / V_effective,k
correction_k   = target_rate_k - current_rate_k
LapPorePress_i += correction_k / D  for i in shell k
```

This keeps local material-material variation but forces the shell-average
storage derivative to match the finite-volume target. `CurvedDrainedShellCorrectionMode=0`
is also available as a diagnostic replacement mode, but the C5m gate uses mode
`1` shell-average correction.

## What Mode 7 Does Not Do

- It does not set material `PorePress` to zero.
- It does not count dummy boundary particle volumes.
- It does not alter the PR pressure update formula.
- It does not modify `FlexibleConfiningStress`, `SoilConstitutiveModel`, or
  `HydraulicElevationSource`.
- It is guarded to `HydraulicElevationSource=0` because the intended gate is
  gravity-free spherical diffusion.

## Diagnostics

The source log reports shell count, shell populations, shell means, interface
fluxes, FV rates, current SPH rates, correction rates, total storage,
boundary flux, conservation residual, negative pressure count, and maximum
rate/Laplacian correction. The C5m analysis script converts these into CSV and
figures for comparison with the C5i FV radial diffusion reference.
