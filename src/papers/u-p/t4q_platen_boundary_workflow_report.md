# T4q Platen Boundary Workflow Report

## Purpose

T4q tests whether strict triaxial platen mechanics can start from existing
DualSPHysics XML features instead of the failed `CapConfiningStress`
acceleration patch.

This stage does not implement DP, MCC, GPU support, or full paper
reproduction. It is an elastic, CPU-only feasibility smoke.

## Files

Experiment directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4q_PlatenBoundaryWorkflow/`

Main files:

- `CaseT4q_PlatenGeometry_NoLoad_Def.xml`
- `CaseT4q_TopVelocity_NoConfinement_Def.xml`
- `CaseT4q_TopVelocity_LateralConfinement_Def.xml`
- `analyze_t4q_platen_workflow.py`
- `t4q_case_summary.csv`
- `t4q_group_counts.csv`
- `t4q_platen_motion_metrics.csv`
- `t4q_specimen_deformation_metrics.csv`
- `t4q_measurement_region_metrics.csv`
- `t4q_confinement_metrics.csv`
- `t4q_reaction_proxy_metrics.csv`
- `figures/`

## XML-Only Platen Route

The XML-only route exists and is technically usable:

- specimen: `mkfluid=0`, `407` particles;
- bottom platen: `mkbound=2`, fixed, `74` particles;
- top platen: `mkbound=1`, moving, `74` particles;
- top platen motion: standard `<motion><objreal ref="1"><mvrect ...>`;
- lateral confinement: existing `FlexibleConfiningStress` with `f_i` and
  lateral selector;
- `CapConfiningStress=0`.

No source patch was required for the T4q smoke.

## CPU Smoke Results

All three CPU Release cases completed:

| Case | Code | Excluded | DtMin | Kplastic max | Purpose |
| --- | ---: | ---: | ---: | ---: | --- |
| Geometry/no load | `0` | `0` | `0` | `0` | verify groups and fixed platens |
| Top velocity/no confinement | `0` | `0` | `0` | `0` | verify prescribed top platen motion |
| Top velocity/lateral confinement | `0` | `0` | `0` | `0` | verify platen + lateral confinement coexistence |

The generated particle grouping is clean:

| Group | Count |
| --- | ---: |
| bottom fixed platen | `74` |
| top moving platen | `74` |
| soil specimen | `407` |
| measurement core | `15` |
| platen contamination in measurement | `0` |

## Platen Motion

The top platen follows the prescribed velocity:

- prescribed `v_z = -0.005 m/s`;
- final top platen displacement: about `-7.5e-6 m`;
- bottom platen displacement: `0`;
- final specimen axial strain proxy:
  - no confinement: about `-1.61e-5`;
  - lateral confinement: about `-1.58e-5`.

This confirms that the existing moving-boundary XML path can drive a reduced
top platen and that the fixed bottom platen remains fixed.

## Lateral Confinement Compatibility

The lateral flexible confinement case remains stable and compatible with the
moving platen:

- active lateral targets: `112`;
- legacy material candidates: `407`;
- `f_i <= 0.70`: `208`;
- lateral inward radial acceleration mean: about `1.87 m/s2`;
- lateral inward radial acceleration max: about `1.91 m/s2`;
- cap axial leakage diagnostic: `0`;
- net force / COM acceleration residual remains small.

Therefore platen motion and lateral `FlexibleConfiningStress` can coexist in
the current CPU XML workflow.

## Pore Pressure And Stress Notes

The T4q smokes are not validation runs:

- `PorePressureFeedback=0`;
- no initial hydrostatic equilibrium stage;
- no DP/MCC;
- no reaction-force validation;
- no strict p-q comparison.

Pore pressure is generated during the short top-platen motion even with
feedback disabled:

- final mean pore pressure is about `4.19e3 Pa` without lateral confinement;
- final mean pore pressure is about `1.25e4 Pa` with lateral confinement.

These values only show that the u-pw diagnostic fields are active. They should
not be interpreted as triaxial validation.

## Reaction / Axial Stress

T4q does not yet provide a validated axial reaction or axial stress output.
The CSV records `reaction_proxy_available=0`.

Possible next routes:

1. use existing force postprocessing if it can robustly isolate top/bottom
   `mkbound` reactions;
2. add a small CPU-only reaction accumulator for platen groups;
3. define specimen-only axial strain and p-q output after reaction is known.

## Source Patch Decision

No source patch is needed for the first explicit platen workflow:

- top prescribed velocity works through existing `<motion>`;
- bottom fixed platen works through fixed `mkbound`;
- specimen/platen grouping is clean;
- lateral confinement can run with platen motion.

A future source patch is still likely for strict validation, mainly for
reaction-force diagnostics and possibly more controlled platen constraints.
That patch should not touch PR, the soil constitutive model, or Cryer logic.

## Answer To Required Questions

1. XML-only platen route exists: yes, for a reduced smoke.
2. Top platen prescribed velocity works: yes, using moving `mkbound=1`.
3. Bottom platen fixed works: yes, using fixed `mkbound=2`.
4. Platen/specimen/measurement grouping is clean: yes, measurement
   contamination is `0`.
5. `AccInput` should remain smoke-only: yes. It should not be used as strict
   platen loading.
6. Platen + lateral `FlexibleConfiningStress` coexist: yes, in the CPU short
   smoke.
7. Reaction / axial stress proxy: not yet validated or available.
8. Source patch needed now: no. Later, likely for reaction output and strict
   platen diagnostics.
9. T4r recommendation: proceed to a platen-based selected-confinement baseline,
   still elastic and CPU-only, with reaction diagnostics as the next blocker.
10. DP/MCC/GPU: remain deferred.
