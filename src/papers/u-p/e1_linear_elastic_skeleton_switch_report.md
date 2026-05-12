# E1 Linear Elastic Skeleton Switch Report

Date: 2026-05-12

## Why This Switch Is Needed

Terzaghi-style 1D consolidation and Cryer's problem are linear poroelastic
benchmarks. A Drucker-Prager skeleton can alter the pressure-generation term
through plastic strain, stress-path changes, and effective compressibility, even
when the u-pw PR equation itself is unchanged. High cohesion is not a strict
substitute, because it still evaluates the yield surface and can become
case/resolution dependent.

## XML Parameter

The implemented soil parameter is:

```xml
<execution>
  <special>
    <soils>
      <SoilConstitutiveModel value="0" />
    </soils>
  </special>
</execution>
```

Semantics:

| Value | Meaning |
|---:|---|
| `0` | Linear elastic skeleton. DP yield, return mapping, `Kplastic`, and softening are bypassed. |
| `1` | Drucker-Prager elastoplastic skeleton. This is the default. |
| `2` | Drucker-Prager with exponential softening. |

Legacy compatibility:

- XML without `SoilConstitutiveModel` defaults to model `1`.
- XML with legacy `Softening=1` and no `SoilConstitutiveModel` maps to model
  `2`.
- If a user explicitly sets `SoilConstitutiveModel=0` or `1`, any legacy
  `Softening=1` is ignored with a warning.

## Implementation Status

| Path | Status |
|---|---|
| CPU Verlet / Symplectic | Implemented. |
| GPU Verlet / Symplectic | Implemented. |
| DP default behavior | Preserved as model `1`. |
| DP+softening | Preserved as model `2`; GPU now has the same switch branch available through the existing device softening helper. |
| Pore-pressure PR equation | Unchanged. |
| Hydraulic boundary modes | Unchanged. |

In model `0`, the elastic trial stress is accepted directly and `Kplastic` is
forced to zero.

## Verification Results

`examples/u-pw/01_1D_Consolidation/experiments/ElasticSwitch_E1/` contains:

- `CaseElasticSwitch_E1_Elastic_Def.xml`
- `CaseElasticSwitch_E1_DP_Def.xml`
- `CaseElasticSwitch_E1_SofteningLegacy_Def.xml`
- CPU/GPU example-style launchers
- `analyze_e1_elastic_switch.py`

The smoke checks were deliberately short (`TimeMax=0.005 s`) and use the known
stable L1 AccInput geometry. CPU Release and GPU Release builds completed
successfully before running these checks.

Summary from `e1_elastic_switch_summary.csv`:

| Case | Inferred model | Code | Excluded | Runtime (s) | Frames | `Kplastic` max abs | Check |
|---|---:|---:|---:|---:|---:|---:|---|
| Elastic CPU | 0 | 0 | 0 | 151.595 | 6 | 0.0 | pass |
| DP CPU | 1 | 0 | 0 | 132.982 | 6 | 0.0 | backward compatibility smoke passed |
| Legacy `Softening=1` CPU | 2 | 0 | 0 | 132.203 | 6 | 0.0 | legacy mapping smoke passed |
| Elastic GPU | 0 | 0 | 0 | 12.470 | 6 | 0.0 | pass |

Observed checks:

- model `0`: `code=0`, `excluded=0`, `Kplastic=0` on CPU and GPU;
- model `1`: DP backward-compatibility run succeeds;
- legacy `Softening=1`: parser maps to model `2` and run succeeds;
- pore-pressure output fields remain available in all smoke cases.

## Cryer/Terzaghi Usage

Strict Cryer and strict Terzaghi analytical comparisons should explicitly set:

```xml
<SoilConstitutiveModel value="0" />
```

The reduced Cryer baseline can remain a launch workflow, but the strict Cryer
draft now declares linear elasticity.

## Remaining Limitations

- The switch does not solve strict Cryer spherical traction.
- The switch does not solve drained curved hydraulic boundary treatment.
- It does not introduce corrected-gradient, MLS, or boundary quadrature
  operators.

## Next Step

Return to C4-B: audit native spherical traction support before attempting a
strict Cryer sphere simulation.
