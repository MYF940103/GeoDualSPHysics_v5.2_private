# C08: standalone local material tangent diagnostic

Author-only fixture `support/c08_h18_material_tangent_r1.cpp`, isolated build entry
`support/c08_h18_material_tangent_r1_build.py`, and this note. Authoring performs
no import, build, component, solver, native read, VTK, SHA, Git or queue action.
No public source, material law, PRE, input, old component or result is changed.

## Baseline and scope

The header-only original `FunSoilMaterial.h` is consumed from the already sealed
schema2 header directory used by `c08_h18_as03_step_r1`. The standalone fixture
links one entry object and the normal compiler CRT, with no86 physical objects,
JSph, BI4 library or GPU. Build and component require independent root review;
neither automatically runs the next phase. Actual dependency output must retain
the frozen material/types headers and exclude public source headers.

The two original actual5us CPU steps are Parts38 and76 of AS.3/n2.55. Their
`material_shadow.csv` does **not** contain six trial stresses. The new fixture
reads each sealed `stages.csv` and reconstructs the actual full trial using
`sigma_n[k]+float(Rsigma_h[k])*original_5us`, exactly as the old MaterialShadow.
The Jaumann contribution already present in this trial remains fixed. It uses
the saved original float kappa_n and original trigger=false, not kappa_h or a
reset history. All10000 full returns must first match the old raw_full six
double stresses and float kappa bitwise, with the original shadow status/reason,
continuous kappa and trial invariants also matching. The named ReturnMaterial
adapter is checked too. No missing GPU substage is reconstructed.

The material uses the frozen parser's original float expressions: E20MPa,
nu.33, K19607844Pa, G7518796.5Pa, phi=float(TORAD*25.f), phi_r=phi,
cohesion5000/1000Pa, cohesion decay5, friction decay0, psi0=0 and sf0, DP_PS.
The existing original material XML is checked by the builder. SoilTriggerFos
retains the original default1.65 but trigger stays false, as in both shadows;
it must not silently reduce strength. No new material parameters are introduced.

Four focus IDs4953/4954/6767/6865 are included in each part. Additionally select
the smallest native ID of each nonempty original full-return(status,reason)
class, determined **before** inspecting tangents:

|Part|Elastic/WithinYield|Smooth/SmoothFlow|TensionRepair/JointExistingApexCap|
|---|---:|---:|---:|
|38|2060|2455|4656|
|76|2060|2089|2103|

These are14 points, not an exhaustive material tangent field. There is no Apex
representative because neither actual full-step classification contains one;
perturbations may enter other existing branches and those are retained.

## Conditional tangents and units

At each fixed trial and kappa_n, use six engineering-strain columns
`(exx,eyy,ezz,gamma_xy,gamma_yz,gamma_xz)` and stress rows
`(xx,yy,zz,xy,yz,xz)`. Engineering shear is twice tensor shear. The elastic
trial perturbation is `delta_sigma_ii=lambda*tr(eps)+2G*eps_ii` and
`delta_sigma_ij=G*gamma_ij`, with lambda=K-2G/3. Add/subtract only this
increment to the genuine original trial; do not rotate again or evolve J/p.

Central differences use seven predeclared strain scales10^-5 through10^-11.
Every scale and both perturbation statuses/reasons/continuous and saved kappa
are exported. Branch changes and noncommitting counterfactuals are descriptive,
not new physical pass/fail gates. An unavailable counterfactual is explicitly
marked and its unavailable values are NaN, never replaced by an elastic answer.
The one original baseline remains a strict reproduction gate. No single scale
is automatically selected as the correct tangent; branch-consistent scale
behaviour and roundoff must be inspected together.

Two local laws are compared: original softening, and BasicValues with the full
double DP coefficients frozen at the same original kappa_n. The latter retains
the same trial/history and the original return/apex/tension policy. It does not
set n_coh=0 and re-round a replacement cohesion, reset kappa, or describe a new
physical collapse case. Its baseline output may differ from the evolving law.

For propagation n=(cos(theta),0,sin(theta)) and in-plane polarization u, impose
plane-strain increments eps_xx=u_x*n_x, eps_zz=u_z*n_z, eps_yy=0 and
gamma_xz=u_x*n_z+u_z*n_x. Then
`Q*u=(delta_sigma_xx*n_x+delta_sigma_xz*n_z,
delta_sigma_xz*n_x+delta_sigma_zz*n_z)`.
The source sigma_yy and all six derivative rows/columns remain present; plane
strain is not a plane-stress reduction. Deterministic integer angles0..180deg
include both endpoints. Report the two eigenvalues of sym(Q), the absolute
Qxz-Qzx asymmetry, and the original elastic reference in Pa. The elastic
reference has eigenvalues G and K+4G/3. The engineering6x6 asymmetry is exported
separately, without conflating it with the acoustic asymmetry.

Negative symmetric acoustic values, especially branch-changing finite-increment
ones, do not alone prove a continuum ellipticity loss, a numerical bug or the
cause of clumping. Nonassociated flow can produce nonsymmetric tangents. This
material-only diagnostic excludes mechanical neighbour geometry, AS, AV,
Darcy, free-surface projection, contact reaction and all time integration.

## Independent operations after root review

Build only:

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_material_tangent_r1_build.py --execution-authorized
```

After a genuinely successful build and separate component admission:

```text
tests/outputs/c08_h18_material_tangent_r1_build/C08H18MaterialTangentR1.exe --review tests/outputs/c08_h18_as03_step_r1_p38 tests/outputs/c08_h18_as03_step_r1_p76 tests/outputs/c08_h18_material_tangent_r1 --execution-authorized
```

Fresh outputs: points.csv14, branches.csv1176, tangents.csv7056,
acoustic.csv35476, summary.csv196 and completion.json. All are local-law
diagnostics; no additional plots, solver/native/VTK/PRE, half, other psi,
physical acceptance or future job is authorized automatically. Existing or
partial new output is protected rather than overwritten.
