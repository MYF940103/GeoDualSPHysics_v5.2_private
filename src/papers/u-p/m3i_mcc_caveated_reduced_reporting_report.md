# M3i-Revised Caveated MCC Reduced Reporting Package

## Objective

M3i-revised is a stage-level reporting closure.  It adds no new simulations,
does not modify source, and does not claim clean Modified Cam Clay validation.
Its purpose is to consolidate the feedback-off explicit-platen MCC route after
the smooth-layout decision: clean triaxial MCC validation is deferred, and the
current route is preserved as a caveated reduced prototype for internal
diagnostics and future development.

## Scope

The package is CPU-only, feedback-off, and based on the explicit top/bottom
platen workflow with lateral `FlexibleConfiningStress`.  It uses the pairwise
platen/specimen reaction diagnostic and `SoilConstitutiveModel=3` MCC CPU stress
update.  It does not include full pore-pressure feedback, GPU MCC, custom
particle import, true actuator reaction, strict drained/undrained MCC
validation, or paper-level triaxial reproduction.

The package is retained under:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/M3i_MCCCaveatedReducedPackage/
```

## Consolidated Stages

M3i-revised summarizes:

- T4s elastic feedback-off platen baseline;
- T4t pairwise platen reaction diagnostics;
- T5, T5b, and T5c DP feedback-off platen results;
- M3c MCC high-pc and mild smoke tests;
- M3d MCC high-pc and mild extended tests;
- M3d2 return robustness diagnostics;
- M3d3 substepping and fallback diagnostics;
- M3f return/staging diagnostics;
- M3h admissible line-search diagnostics;
- M3j-B boundary-induced failure audit;
- M3k dense platen/edge failure-onset diagnostic;
- M3l platen/specimen smoothing;
- M3m refined platen-edge geometry;
- M3n smooth Cartesian refinement;
- M3o fan-like generator feasibility.

The consolidated tables are:

- `m3i_case_inventory.csv`;
- `m3i_summary_metrics.csv`;
- `m3i_mcc_state_summary.csv`;
- `m3i_return_status_summary.csv`;
- `m3i_boundary_failure_evidence.csv`;
- `m3i_geometry_route_summary.csv`;
- `m3i_reaction_stress_path_summary.csv`;
- `m3i_pore_pressure_summary.csv`;
- `m3i_no_go_decision_table.csv`.

## What Works

The reduced MCC route works as a CPU prototype:

- MCC parser, parameter validation, state arrays, initialization, and
  `SaveMccState` output are in place;
- the CPU MCC stress-update branch is connected for `SoilConstitutiveModel=3`;
- high-pc MCC behaves as an elastic-like reference;
- mild MCC activates yield and evolves `pc`, void ratio, plastic volumetric
  strain, equivalent plastic strain, `Kplastic`, and return diagnostics;
- pairwise platen reaction and specimen p'-q diagnostics are available;
- feedback-off pore pressure remains bounded in the tested cases;
- DP and MCC reduced stress paths can be compared on the same explicit-platen
  workflow.

The main figure candidates generated here are:

1. DP vs MCC reaction-based axial stress-strain;
2. DP vs MCC p'-q paths;
3. MCC `pc` evolution;
4. MCC void ratio and plastic volumetric strain evolution;
5. ReturnStatus comparison;
6. boundary-induced failure evidence;
7. pairwise reaction vs `Fz_proxy`;
8. pore pressure vs axial strain.

Supplementary figure candidates include geometry-route return-status outcomes,
support/neighbor proxy comparison, velocity boundedness, and PorePressRate
boundedness.

## What Is Not Clean

The current route is not clean MCC validation:

- original-rate mild MCC still has local `ReturnStatus=-3` episodes;
- substepping and admissible line search do not cleanly remove all transient
  failures;
- fallback routes produce `ReturnStatus=-5` and are safety diagnostics, not
  validation settings;
- smooth Cartesian refinement improves some support metrics but worsens
  transient `-1/-3` populations;
- the M3o fan-like generator is not connected to the solver workflow;
- full pore-pressure feedback remains unresolved;
- GPU MCC still hard-errors by design;
- pairwise reaction is not full actuator reaction;
- strict drained/undrained MCC paper reproduction has not started.

## Boundary-Induced Failure Interpretation

The strongest evidence now points to boundary-induced local strain/support
paths, not global MCC constitutive collapse:

- failed returns are concentrated in edge, cap, and platen-adjacent regions;
- measurement-core particles are rarely the trigger;
- M3k captured first failure onset at `t=0.001005 s`, with
  `ReturnStatus=-1:92` and `ReturnStatus=-3:4`;
- the first `-3` particles are symmetric top edge/corner particles;
- first `-3` support/core is about `0.618`, with a specimen-neighbor proxy near
  `56` versus core around `178`;
- first `-3` local velocity-gradient proxy is about `0.112`, compared with
  same-region nonfailed around `0.075` and core around `0.027`;
- local stress path is abnormal, with first `-3` particles around
  `p'≈73.97 Pa`, `q≈93.76 Pa`, `q/p'≈1.27`, and residual around `3888`;
- geometry/interface changes materially alter the failure population without
  changing MCC return mapping.

This is why continuing return-map patches is not the priority.  The route would
need a better platen/specimen boundary and/or true smooth particle import before
clean validation can be claimed.

## Final Route Decision

Clean MCC validation is deferred.  The current MCC route is useful for internal
development diagnostics and preliminary reduced behavior comparisons, but it is
not suitable for strict paper-level validation.

The project decision after M3o is to pause custom fan-like solver import and
stop spending immediate effort on clean triaxial MCC validation.  The current
package is therefore caveated by design:

- it can support code diagnostics, output checks, and reduced DP/MCC comparison;
- it cannot support claims of strict undrained MCC validation;
- it should not be used as the final paper reproduction benchmark.

## Next Step

Recommended next direction is Route B or Route C from the future-work note:

- Route B: use the caveated reduced MCC route for development diagnostics only;
- Route C: shift effort to the next higher-priority u-p module or benchmark.

Route A, clean MCC validation through custom smooth/fan-like solver import,
should wait until the project explicitly chooses to pay that workflow cost.
Full pore-pressure feedback and GPU remain deferred.
