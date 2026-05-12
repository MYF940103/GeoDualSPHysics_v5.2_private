# E1 Constitutive Switch Audit

Date: 2026-05-12

## Objective

Strict Terzaghi and Cryer comparisons assume a linear poroelastic skeleton. The
existing u-pw soil path used a Drucker-Prager return mapping by default, with an
optional CPU exponential softening branch. This audit identifies the insertion
point for a switch that can bypass plasticity for strict poroelastic benchmarks.

## Current Stress Update Path

| Item | Location | Notes |
|---|---|---|
| Elastic strain/spin rate | `JSphCpu.cpp::InteractionForcesFluid*`, `JSphGpu_ker.cu` interaction kernels | Pair interactions assemble `Rsigmac/Rsigmag`, the elastic stress-rate tensor. |
| Elastic trial stress | `JSphCpu.cpp::ComputeVerletVarsFluid`, `ComputeSymplecticPre`, `ComputeSymplecticCorr`; `JSphGpuSimple_ker.cu` step kernels | `sigma_e = sigma_old + rsigma * dt`. |
| DP yield check | `ConsRelationEP_fast()` in CPU and GPU step code | Uses invariants `I1`, `J2` and `f=sqrt(J2)+alpha I1-kc`. |
| Return mapping | `ConsRelationEP_fast()` | Corrects the trial stress and increments `Kplastic`. |
| Softening | `ConsRelationEPsft_fast()` | Uses peak/residual `coh/phi` and `Kplastic` with exponential degradation. |
| Plastic state | `Kplasticc/Kplasticg` | Restart/output state; predictor keeps old `Kplastic`, corrector/Verlet can update. |
| Diagnostics | `Kplastic` output already exists | E1 smoke summaries use `Kplastic` to prove elastic mode does not accumulate plastic strain. |

## Examples Relying On DP

The reduced triaxial, retrogressive slope, and softening smoke examples rely on
the existing Drucker-Prager path. The new switch must therefore preserve
Drucker-Prager as the default and preserve legacy `Softening=1` behavior.

## Compatibility Requirement

- Old XML without a new switch must keep Drucker-Prager behavior.
- Old XML with `Softening=1` and no new switch must still run the softening
  return mapping.
- Strict poroelastic XML must be able to force linear elasticity without relying
  on artificially high DP strength.
