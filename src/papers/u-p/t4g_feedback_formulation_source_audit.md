# T4g Feedback Formulation Source Audit

## Scope

T4g audits the pore-pressure feedback acceleration used by the reduced
selected-confinement triaxial cases. It does not change the PR pore-pressure
rate equation, the constitutive model, or the Cryer boundary code.

## Source Path

| Item | Location | Finding |
| --- | --- | --- |
| Symmetric feedback operator | `source/JSphCpu.cpp:3873` | `ComputePorePressureAccelT` computes a stress-style pair term using `(p_i+p_j)`. It can create a surface-force-like response under uniform pressure when kernel support is truncated. |
| Difference-gradient operator | `source/JSphCpu.cpp:3941` | `ComputePorePressureAccelDiffT` computes `-m_j (p_j-p_i)/(rho_i rho_j) grad W_ij`, equivalent to `-grad(p_w)/rho` when the SPH gradient is consistent. |
| Feedback application | `source/JSphCpu.cpp:4009` | `ApplyPorePressureFeedback` selects operator 0 or 1, applies the T4e gate and T4f limiter/relaxation if enabled, and adds the resulting acceleration directly to `Acec`. |
| Force order | `source/JSphCpuSingle.cpp:847` | Stress/confinement acceleration is computed first, then pore-pressure feedback is added, then hydromechanical damping is applied, then PR `PorePressRate` is computed. |
| Parser/defaults | `source/JSph.cpp:247`, `source/JSph.cpp:999` | Feedback defaults remain disabled, total-pressure mode, operator 0 unless XML opts in. |
| GPU path | `source/JSphGpu.cpp:1006` | GPU supports only the default ungated/unstabilized operator-1 path. T4e/T4f/T4g non-default controls hard-error. |

## Pressure Variable

`PorePressureFeedbackMode=0` uses total `PorePress`. `PorePressureFeedbackMode=1`
uses `PorePress - p_hydro`. Under `HydraulicElevationSource=0`, the hydrostatic
reference is zero, so total and excess feedback are expected to be identical.
The T4g total/excess interior-only pair confirms this: both cases have identical
max `PorePressRate`, final pressure, velocity, and reversal metrics.

## Sign and Units

For operator 1, the implemented form is:

```text
a_fb,i = sum_j -m_j (p_j - p_i)/(rho_i rho_j) gradW_ij
```

Since `gradW_ij = fac(r_ij) r_ij` with `r_ij = x_i - x_j`, this is the usual
SPH estimate of `-grad(p_w)/rho_i` when the first moment is consistent. The
manufactured linear-pressure test gives acceleration in the expected direction.

Operator 0 is:

```text
a_fb,i = sum_j -m_j (p_i + p_j)/(rho_i rho_j) gradW_ij
```

This is stress-divergence-like, not a pure pressure-gradient-difference
operator. It is not constant-pressure consistent near a free surface.

## Effective Stress Coupling

In the current soil path `Sigmac` is advanced from the skeleton stress rate in
`GetStressRateTensor_Elastic` / the Drucker-Prager return path. Pore pressure is
not subtracted from `Sigmac` before the stress-divergence acceleration. The
separate feedback acceleration is therefore the intended effective-stress
coupling path, not an obvious direct double count in the current code. The audit
does find that this path is dynamically too strong for selected-confinement
equilibration.

## Particle Scope

Before T4g, feedback was applied to every material fluid particle:

- interior particles;
- lateral selected confinement particles;
- top and bottom cap particles;
- edge-ring particles.

This allowed large pressure-gradient feedback to act directly on the
near-boundary and confinement-target regions that already receive selected
flexible confinement. T4g adds an opt-in CPU class filter so the feedback
acceleration can be restricted without changing the PR pressure update.

## T4g Source Addition

The following default-off controls were added:

- `PorePressureFeedbackUseClassFilter`;
- `PorePressureFeedbackExcludeCaps`;
- `PorePressureFeedbackExcludeEdges`;
- `PorePressureFeedbackExcludeConfinementTargets`;
- `PorePressureFeedbackInteriorOnly`.

With `PorePressureFeedbackInteriorOnly=1`, only cylinder class `1` particles
receive feedback acceleration. The filter is CPU-only, requires
`ConfiningStressGeometry=1`, and is treated as a non-default feedback control
for GPU hard-error purposes. It only changes feedback acceleration application;
it does not modify `PorePress`, `PorePressRate`, `LapPorePress`, `DivVel`, or
the stress update.

## Positive Feedback Loop

The code order permits the following loop:

1. selected confinement generates compression and pore pressure;
2. pressure gradients generate feedback acceleration;
3. feedback acceleration changes velocity and `DivVel`;
4. `DivVel` enters the next PR `PorePressRate`;
5. amplified pressure gradients feed back into acceleration.

T4g results show this loop is concentrated by class and operator choice, but
class filtering alone does not remove it.
