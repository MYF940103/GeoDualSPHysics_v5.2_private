# T4g Feedback Physical Consistency Notes

## Momentum Coupling Target

For a saturated porous skeleton, a common effective-stress split is:

```text
sigma_total = sigma_effective - alpha p_w I
```

If the mechanical momentum equation is written in terms of the skeleton
effective stress stored in `Sigmac`, the pore-pressure contribution enters as:

```text
a_pw = -alpha grad(p_w) / rho
```

The current branch uses `alpha=1` implicitly in the feedback acceleration path.
It does not write pore pressure into `Sigmac`.

## Double Counting Check

The source audit did not find an obvious direct double count for the current
linear-elastic triaxial route:

- `Sigmac` is the skeleton stress tensor advanced by the elastic/DP update.
- `FlexibleConfiningStress` is an external stress-like pair contribution and is
  not written into `Sigmac`.
- `PorePressureFeedback` is the separate momentum acceleration that represents
  `-grad(p_w)/rho`.

The problem is not that pore pressure is definitely counted twice in `Sigmac`
and feedback. The problem is that the explicit feedback acceleration can be much
larger than the confinement acceleration during dynamic equilibration, creating
a positive feedback loop with `DivVel` and `PorePressRate`.

## Operator Consistency

### Uniform Pressure

A pure internal pore-pressure gradient operator should produce zero acceleration
for uniform pressure. T4g manufactured tests show:

- operator 1: exactly zero on the static particle cloud;
- operator 0: nonzero near the free surface, with max acceleration about
  `38.53 m/s2` for a uniform `1000 Pa` field.

This makes operator 1 the more physically appropriate internal feedback
operator for the triaxial selected-confinement route.

### Linear Pressure

For `p = 1000 x` Pa/m and `rho=2100 kg/m3`, the expected acceleration is
approximately:

```text
a_x = -1000 / 2100 = -0.476 m/s2
```

The operator-1 manufactured result has the correct sign and a max magnitude of
about `0.475 m/s2`, with remaining error dominated by boundary support
truncation. Operator 0 is not a clean linear-gradient estimator.

### Total vs Excess Pressure

Under `HydraulicElevationSource=0`, hydrostatic pressure is zero:

```text
ExcessPorePress == PorePress
```

T4g confirms this. The `operator 1, interior-only` total-pressure case and the
excess-pressure case produce identical retained metrics.

## Why Selected Confinement Amplifies Feedback

The reduced cylinder has very few interior particles (`63`) and a large
near-boundary/confinement-target population. Selected flexible confinement
compresses lateral particles while cap leakage is suppressed. This quickly
creates steep spatial pore-pressure gradients. If feedback is applied to every
particle, large accelerations appear first in lateral/cap/edge classes, then
the velocity/divergence response drives the next pressure-rate spike.

Class filtering confirms the concentration mechanism: applying feedback only to
interior particles reduces exclusions and DtMin bursts, but the retained
interior feedback acceleration still grows to order `1e4 m/s2` by the final
short-run frames. The formulation therefore still needs a physically consistent
stabilization or coupling redesign; class filtering is diagnostic, not final.

## Current Interpretation

Current feedback is an intended effective-stress coupling term, not merely an
arbitrary numerical add-on. Its sign and units are consistent for operator 1.
However, the explicit unfiltered application is not dynamically stable for the
selected-confinement reduced triaxial sample. Operator 0 is less physically
consistent for internal feedback because it has a constant-pressure boundary
force. Operator 1 with class filtering is the best diagnostic candidate, but it
still fails the validation gate without additional formulation work.
