# M3c MCC Stress Update Source Audit

## Insertion Point

The CPU constitutive dispatcher is `ApplySoilConstitutiveModelCpu` in
`source/JSphCpu.cpp`. It receives the elastic trial stress generated from
`Sigmac + Rsigmac * dt` and dispatches:

- `SoilConstitutiveModel=0`: linear elastic pass-through.
- `SoilConstitutiveModel=1`: Drucker-Prager through `ConsRelationEP_fast`.
- `SoilConstitutiveModel=2`: DP softening through `ConsRelationEPsft_fast`.
- `SoilConstitutiveModel=3`: M3c Modified Cam Clay CPU return mapping.

The call sites are the Verlet update and the symplectic predictor/corrector.
M3c passes both the previous stress and the elastic trial stress so that the
MCC helper can estimate the volumetric strain increment used for void-ratio
diagnostics.

## Existing Stress Path

The elastic trial stress is generated before the constitutive branch by the
existing stress-rate path:

1. strain-rate and spin terms are assembled in the interaction loop;
2. `GetStressRateTensor_Elastic` computes the elastic stress rate and Jaumann
   correction;
3. the integration step forms `sigma_e`;
4. the constitutive branch writes back `Sigmac` and `Kplastic`.

M3c does not modify the stress-rate assembly, PR pore-pressure update,
FlexibleConfiningStress, or DP branches.

## Sign Mapping

The production `Sigmac` convention stores compressive effective stress as
negative diagonal values. The M2/M3a MCC helper uses compression-positive
stress internally. M3c therefore maps all components as:

```text
stress_cp = -Sigmac
p' = trace(stress_cp)/3 = -trace(Sigmac)/3
Sigmac_new = -stress_cp_new
```

The mapping applies to normal and shear components consistently because the
M3a standalone parity helper used the same full-tensor sign flip.

## MCC State Access

The branch updates the CPU MCC state arrays initialized in M3b:

- `MccPcc`
- `MccVoidRatioc`
- `MccPlasticVolStrainc`
- `MccEqPlasticStrainc`
- `MccYieldFlagc`
- `MccPlasticMultiplierc`
- `MccReturnStatusc`
- `MccReturnIterationsc`
- `MccYieldResidualc`

`Kplastic` is mapped to `MccEqPlasticStrain` as a compatibility plastic
activity diagnostic. The dedicated MCC arrays remain the authoritative MCC
state outputs.

## Return Mapping

The M3c production helper copies the M3a parity-tested formulation into
`JSphCpu.cpp` as a local CPU helper rather than linking the research tool under
`papers/u-p` into the solver build.

It uses:

```text
f = q^2 + M^2 p'(p' - pc)
unknowns = p, q, pc, Delta_gamma
local Newton solve with finite-difference Jacobian and line search
```

The plastic correction scales the trial deviatoric stress by `q/q_trial`, uses
the MCC exponential hardening law for `pc`, and records iteration/residual
diagnostics.

## Failure Handling

Return statuses are explicit numeric codes:

- `0`: elastic
- `1`: plastic converged
- `-1`: tension cutoff
- `-2`: singular Jacobian
- `-3`: line-search failure
- `-4`: max-iteration failure

Failures do not silently become elastic. The stress remains at the trial value
for the failed local step and the status is written to `MccReturnStatus`.

## CPU / GPU Protection

`SoilConstitutiveModel=3` remains CPU-only. The parser still hard-errors on GPU
for model `3`; the GPU Release build is checked only to confirm compilation.

## Scope Boundaries

M3c does not implement:

- GPU MCC;
- full pore-pressure feedback;
- MCC restart extension beyond the existing M3b state output skeleton;
- strict MCC paper reproduction;
- kappa-based nonlinear elastic predictor.

The current predictor is the existing linear elastic `E,nu` stress-rate path,
matching the M2/M3a first prototype scope.
