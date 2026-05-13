# M1 Current Stress Update Audit

## Scope

This audit maps the current elastic and Drucker-Prager stress update path before any Modified Cam Clay implementation. It is documentation-only: no source was modified and no simulation was run.

## Stress Storage

CPU stress state is stored in `Sigmac`, with companion arrays `SigmaPrec`, `SigmaM1c`, `Rsigmac`, and `Kplasticc` in `source/JSphCpu.cpp`. The arrays are reserved in the CPU allocation path and sorted/restarted alongside the particle data.

The persisted stress output/restart representation uses:

- `Sigma_kk` for diagonal stress components;
- `Sigma_ij` for off-diagonal stress components;
- `Kplastic` for the accumulated DP plastic measure.

Restart loading in `source/JPartsLoad4.cpp` restores `Sigma_kk`, `Sigma_ij`, and `Kplastic` when those arrays exist. `source/JSphCpuSingle.cpp` maps restored values by `Idp`. `PorePress` is restored separately. `PorePressRate` and `DivVel` are diagnostics and are recomputed.

## Stress Convention

The current skeleton/effective stress convention stores compression as negative in `Sigmac`. The T4k initial-stress path documents and logs this explicitly: `InitialEffectiveStressIso=50` writes

```text
Sigmac.xx = Sigmac.yy = Sigmac.zz = -50 Pa
```

Therefore postprocessing and MCC planning should use a compression-positive internal mean stress

```text
p' = -(sigma_xx + sigma_yy + sigma_zz) / 3
```

where `sigma_ij` are the stored `Sigmac` components. The stored tensor should continue to be treated as skeleton/effective stress. Pore pressure is a separate field and is not written into `Sigmac`.

## Existing Constitutive Switch

The soil model is selected through `SoilConstitutiveModel` in `JSph::InitSoilParameters`:

- `0`: linear elastic skeleton;
- `1`: Drucker-Prager elastoplastic;
- `2`: Drucker-Prager with exponential softening.

The parser currently hard-errors for values greater than `2`. A future MCC path therefore needs a parser extension before `SoilConstitutiveModel=3` can be accepted.

Legacy `Softening=1` maps to model `2` when `SoilConstitutiveModel` is omitted. When model `0` is selected, the log states that DP yield, return mapping, plastic strain, `Kplastic` accumulation, and softening are bypassed.

## Elastic Trial Stress

`GetStressRateTensor_Elastic` computes the elastic stress rate from the strain-rate tensor, spin-rate tensor, bulk modulus, shear modulus, and current stress. It includes a Jaumann stress-rate correction.

The time integrators then form an elastic trial stress:

```text
sigma_e = SigmaPrec + Rsigmac * dt
```

or the corresponding half-step value. This trial tensor is passed to `ApplySoilConstitutiveModelCpu`.

## DP Return Path

`ApplySoilConstitutiveModelCpu` is the CPU constitutive dispatch point:

- model `0` returns `sigma_e` and sets `Kplastic` to zero;
- model `2` calls `ConsRelationEPsft_fast`;
- otherwise model `1` computes DP constants and calls `ConsRelationEP_fast`.

`ConsRelationEP_fast` computes

```text
I1 = sigma_xx + sigma_yy + sigma_zz
J2 = deviatoric_second_invariant
f = sqrt(J2) + DP_phi * I1 - DP_kc
```

If `f` is below tolerance, the trial stress is accepted. If plastic, a local corrector updates stress and increments `Kplastic` from the deviatoric plastic strain increment. The softening branch updates DP friction/cohesion from `Kplastic` before the same style of correction.

The current implementation is single precision in the local constitutive routines.

## Time Integration Placement

The stress update is embedded in both Verlet and Symplectic paths:

- the interaction loops compute `Rsigmac`;
- the integration step forms `sigma_e`;
- `ApplySoilConstitutiveModelCpu` applies model-specific correction;
- `Sigmac[p]` and `Kplasticc[p]` are written back.

This is a suitable insertion point for a future MCC branch because MCC can consume the same elastic trial stress and return an updated effective stress plus updated internal variables.

## Pore Pressure Separation

`PorePress` is stored and updated separately from `Sigmac`. Full pore-pressure feedback, when enabled, adds momentum acceleration through the feedback operator path. It does not convert `Sigmac` into total stress.

For MCC planning this means:

- `Sigmac` should be treated as effective stress;
- MCC return mapping should not include pore pressure inside the local stress tensor;
- drained/undrained behavior must be defined through the existing u-pw pressure update and boundary workflow, with full feedback still deferred.

## Output and Restart Gaps for MCC

The current restart/output path is enough for elastic and DP because it stores stress plus `Kplastic`. MCC will require additional restart-safe state arrays:

- preconsolidation pressure;
- void ratio or specific volume;
- plastic volumetric strain;
- MCC-specific plastic flags/diagnostics.

Without those fields, any staged MCC restart would be stress-consistent but not constitutive-state-consistent.

## CPU/GPU Differences

The GPU path mirrors the current model switch in `ApplySoilConstitutiveModelGpu` and supports the existing `0/1/2` branches. MCC should be CPU-first. Until the GPU kernel, memory arrays, parser checks, restart handling, and output paths are ported, `SoilConstitutiveModel=3` should hard-error on GPU.

## MCC Insertion Assessment

The current stress update path is suitable for an MCC CPU insertion because:

- it already computes an elastic trial stress;
- the constitutive correction is centralized in one CPU dispatch function;
- stress and `Kplastic` restart/output are already established;
- the T5 DP route provides a feedback-off platen baseline for first SPH smokes.

The path is not sufficient by itself because MCC needs new state variables, sign-convention guards, restart/output support, and single-point return-mapping tests before SPH integration.
