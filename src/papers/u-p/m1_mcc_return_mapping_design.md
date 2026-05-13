# M1 MCC Return Mapping Design

## Candidate Algorithms

### Option 1: Explicit Trial With Simple Projection

This is the smallest implementation but is not recommended as the main MCC route. MCC has a nonlinear cap and pressure-dependent hardening, so a radial-like return can drift from the yield surface and mishandle volumetric plasticity.

Use only as a debug comparison in a standalone driver.

### Option 2: Semi-Implicit Local Newton Return

This is the recommended first implementation route.

Basic structure:

1. Convert stored `Sigmac` trial stress to compression-positive MCC invariants.
2. Compute trial `p'_tr`, `q_tr`, and `f_tr`.
3. If `f_tr <= tolerance`, accept elastic trial stress.
4. If plastic, solve a local nonlinear return problem for plastic multiplier and updated hardening state.
5. Convert updated stress back to stored negative-compression `Sigmac`.

The local solve should use double precision even if storage remains float.

### Option 3: Fully Implicit Closest Point Projection

This is more robust and more paper-faithful for large increments, but it is a larger source change. It should be considered after the semi-implicit prototype passes single-point tests.

### Option 4: Substepping

Substepping can improve robustness when SPH time steps still produce large constitutive increments. It should be an optional guard after the base Newton return is correct.

## Recommended M2 Route

Start with a CPU-only semi-implicit local Newton return mapping in a standalone material-point driver. Do not connect it to SPH until the single-point tests pass.

## Trial Stress

The current SPH path already provides:

```text
sigma_e = SigmaPrec + Rsigmac * dt
```

MCC should treat `sigma_e` as the effective stress trial state. Pore pressure remains outside the local return mapping.

## Yield Check

Convert trial stress:

```text
p_tr = -trace(sigma_e) / 3
q_tr = sqrt(3 * J2_tr)
f_tr = q_tr^2 + M^2 * p_tr * (p_tr - p_c_old)
```

If `p_tr <= MccTensionCutoff`, the step is outside the intended MCC compression domain and should fail or enter a clearly counted guarded path.

## Plastic Update Targets

The return mapping must update:

- stress tensor;
- `p_c`;
- void ratio or specific volume;
- plastic volumetric strain;
- equivalent plastic strain diagnostic;
- yield flag;
- plastic multiplier.

The hardening update should use a compression-positive plastic volumetric strain increment:

```text
p_c_new = p_c_old * exp(v * d_epsilon_p_v / (lambda - kappa))
```

or a consistent linearized form in the first prototype. The chosen form must be tested against isotropic compression.

## p' <= 0 Handling

No production MCC result should rely on hidden tensile clamping. Recommended behavior:

- single-point driver: fail with a diagnostic row;
- SPH prototype: count failures and optionally stop;
- only add a clamp as an explicit debug option, not a validation setting.

## Convergence Criteria

Suggested local criteria:

- normalized yield residual below `MccReturnTolerance`;
- plastic multiplier increment below tolerance;
- `p' > MccTensionCutoff`;
- `p_c >= p'` after return, allowing a small numerical tolerance.

If Newton fails:

1. retry with local substepping if enabled;
2. otherwise mark return failure and stop the run for development builds.

Silent fallback to elastic behavior is not acceptable.

## Precision

The existing DP routines are single precision. MCC is more sensitive because of the cap geometry and hardening. Recommended:

- compute local invariants and Newton iterations in `double`;
- store arrays as `float` only after single-point drift checks;
- consider double storage for `p_c` if long-run drift appears.

## Why CPU First

CPU is required first because:

- local Newton debugging needs detailed diagnostics;
- restart and output fields must be validated;
- GPU device code would duplicate unproven logic;
- current GPU triaxial validation is deferred.

Only after CPU single-point and CPU SPH smokes pass should GPU parity be planned.
