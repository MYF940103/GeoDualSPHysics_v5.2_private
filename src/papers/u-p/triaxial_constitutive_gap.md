# Triaxial Constitutive Model Gap

Date: 2026-05-11

Milestone: MAT-1 from `full_cpu_implementation_backlog.md`

This note records the material-model gap for strict undrained triaxial
reproduction. It does not implement a new constitutive model.

## Current State

The current u-pw PR CPU prototype uses the existing GeoDualSPHysics effective
stress path, which is Drucker-Prager style for the current reduced smoke cases.
The paper notes mention both Drucker-Prager and Modified Cam-Clay in the broader
u-pw formulation/benchmarks, but the local markdown notes do not provide the
exact triaxial material table.

Therefore:

- the reduced triaxial smoke can exercise u-pw field plumbing;
- it cannot be claimed as strict paper triaxial reproduction unless the paper
  triaxial material model is matched or the DP approximation is explicitly
  accepted and calibrated.

## Strict Reproduction Decision Needed

Before strict triaxial CPU smoke:

1. Extract from PDF/SI:
   - material model used for each triaxial test;
   - elastic parameters;
   - plasticity parameters;
   - consolidation or drainage condition;
   - initial confining stress;
   - axial loading path.
2. Decide:
   - **DP approximation path:** acceptable only for qualitative smoke and
     requires calibration notes;
   - **MCC path:** required if the paper triaxial tests are MCC-specific.

## If DP Approximation Is Accepted

Minimum requirements:

- map paper elastic constants to existing soil constants;
- document DP parameters used and why;
- mark output plots as approximate, not strict reproduction;
- stress-path script reports `p'` and `q` from existing stress tensors.

This path should not block PR core GPU, but it also should not be labeled as
strict triaxial reproduction.

## If MCC Is Required

Expected work:

- add MCC state variables and parameters;
- update stress integration;
- output MCC-specific state such as preconsolidation pressure / plastic strain;
- validate with an element-like or very small particle smoke before coupling
  with u-pw PR.

This is a large constitutive-model feature and should not be implemented
automatically in the current pre-GPU automation pass.

## GPU Implications

MCC or any new constitutive model is orthogonal to passive pore-pressure GPU
array work, but it would affect full GPU production mechanics. The correct
sequence is:

1. freeze PR scalar arrays and restart/output contracts;
2. decide DP vs MCC for strict triaxial;
3. implement/validate MCC on CPU only if required;
4. port constitutive logic to GPU only after CPU validation.

## Current Recommendation

Treat the current triaxial case as reduced DP/u-pw execution smoke. Strict
triaxial reproduction remains material-model blocked until the paper parameters
are extracted and the DP-vs-MCC decision is made.

