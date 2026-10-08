# Hydromechanical late pore-pressure platform: root-cause status

Date: 2026-07-31

## Current diagnosis

The recurring late-time excess pore-pressure platform is generated in the pore-pressure update path by near cancellation between:

- the volumetric compression source term, and
- the Darcy/seepage dissipation term.

The active PR implementation is:

- CPU: `source/JSphCpu.cpp`, pore-rate pair loop around the `kwn*(-divv)` and `lapwrate+lapzrate` additions.
- GPU: `source/JSphGpu_ker.cu`, pore-rate pair loop around `CTE.porekwn*(-divv)` and `CTE.porekwn*seep`.

This is not explained by plasticity, corrected-gradient use, density-rate compression, direct head Darcy, Eta2, damping alone, or the missing solid-acceleration divergence term. Those tests either had negligible influence or produced only local/partial improvement.

## Why it appears late

For self-weight scenario 2, the raw explicit PR diffusion stiffness is:

```text
(Kw/n) k / (rho_w g) = 67.9579 m^2/s
```

whereas the elastic Terzaghi coefficient used by the benchmark is:

```text
k M / (rho_w g) = 0.274445 m^2/s
```

with `M=K+4G/3`. The ratio is about `247.6`. Therefore the explicit PR update depends on cancellation of two terms far larger than the physical drained consolidation coefficient. Once the real excess pore pressure falls to the late-stage residual scale, small residual errors in the mechanical divergence operator and mDBC support terms become comparable to the true diffusive decay.

For the Lian flexible strip, the same ratio is about `84.4`, so the mechanism is weaker but still present.

## Boundary role

Earlier diagnostics showed that impermeable mDBC boundary neighbors, especially near the bottom support in the self-weight column, can almost cancel the fluid-neighbor drainage contribution. Removing boundary seepage or boundary pore-rate terms improves a short late-time window, but a full-history run still reforms the platform. This indicates that boundary treatment is an amplifier/trigger, while the explicit storage/compression cancellation is the deeper numerical mechanism.

## Fix direction

A local tweak to the compression operator is unlikely to be sufficient. The next defensible fix should change the pressure update so that late-stage drainage is not obtained from explicit subtraction of large `Kw/n`-scaled terms:

1. Repair and validate the TPI path first, because Lian 2023 introduces TPI specifically to remove the direct water-bulk-modulus dependence from the pore-pressure update.
2. If TPI remains too sensitive to raw volumetric-rate noise, add a default-off semi-implicit or condensed elastic-storage pressure update for elastic benchmark cases, with clear XML selection.
3. Keep mDBC boundary particles as kernel support, but make the impermeable hydraulic ghost treatment consistent with zero normal hydraulic-head flux; do not rely on deleting all boundary contributions as a formal fix.

The temporary solid-acceleration diagnostic was removed from source after testing because it did not change the late-window slope.
