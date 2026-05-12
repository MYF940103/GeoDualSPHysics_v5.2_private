# Cryer C4-B3 Flexible Confining Stress Implementation Plan

Date: 2026-05-12

## Scope

C4-B3 should be a minimal CPU-first implementation of the flexible confining
stress source. It should not attempt strict Cryer reproduction yet.

Allowed in C4-B3:

- XML/parser support for the confining stress switch;
- CPU pairwise mechanical momentum term;
- CPU diagnostics;
- no-load regression smoke;
- small sphere/cube loading sign smoke;
- coarse coupled Cryer loading-only smoke if earlier tests pass.

Out of scope in C4-B3:

- GPU implementation;
- drained curved pore-pressure boundary;
- corrected-gradient production;
- strict Figure 7B comparison;
- long run;
- Scenario 1/2 changes.

## Likely Source Files

Expected files, subject to confirmation during implementation:

- `source/DualSphDef.h`: new configuration structure or fields.
- `source/JSph.h` / `source/JSph.cpp`: XML parsing, defaults, validation, log.
- `source/JSphCpu.cpp`: CPU pairwise stress-like contribution and diagnostics.
- `source/JSphCpuSingle.cpp`: optional diagnostic summary integration.
- `source/JSphGpu.cpp`: hard error if the switch is enabled before GPU support.

GPU kernels should not be edited in C4-B3 unless the task is explicitly expanded.

## CPU Pairwise Term

Add an isotropic diagonal stress contribution in the same region as the
mechanical stress divergence:

```text
sigma_conf = -p0(t) I
coef_conf = m_j * ( -p0_i - p0_j ) / (rho_i rho_j)
a_conf_i += coef_conf * gradW_ij
```

The first implementation should apply only to material-material pairs.

## XML Parser Changes

Default off:

```xml
<parameter key="FlexibleConfiningStress" value="0" />
```

Required when active:

- `ConfiningStressP0`;
- ramp start/end;
- target marker or all-material mode;
- mode `0`.

If GPU is requested while active and GPU support is missing, abort with a clear
message.

## Tests

### Test 1: No-load regression

Same reduced short case, switch off. Expected: identical behavior to before the
patch within normal floating-point noise.

### Test 2: Static loading sign smoke

Small free material sphere or cube, `SoilConstitutiveModel=0`, no hydraulic
claim. Expected:

- code=0;
- excluded=0;
- surface acceleration inward for a sphere;
- net force near zero for a symmetric sphere;
- center-of-mass acceleration near zero.

### Test 3: Symmetry / net-force test

Use diagnostic bins to verify interior cancellation and surface localization.

### Test 4: Coarse Cryer loading-only smoke

Use the strict sphere draft as a coarse CPU-only loading smoke after Test 2/3.
This is not strict reproduction until drained boundary is solved.

### Test 5: GPU hard-error test

If a GPU run is attempted with `FlexibleConfiningStress=1`, it should hard error
until GPU support is implemented.

## Stop Criteria

Do not proceed to drained boundary or strict Cryer simulation if:

- sign check fails;
- symmetry residual is large;
- no-load regression changes;
- interior cancellation does not occur;
- diagnostic output is insufficient to explain the applied load.

## Commit Plan

One commit should cover CPU implementation, smoke scripts, diagnostics, and the
C4-B3 report:

```text
Add CPU flexible confining stress source
```

Strict Cryer simulation should remain paused after C4-B3 unless the loading
diagnostics pass and the drained boundary route is selected.

