# Full Paper Case Audit for CPU Reproduction Before GPU

Date: 2026-05-11

This audit resets the pre-GPU completion standard for the u-pw PR branch. A
reduced execution smoke is useful, but it is not the same as a strict
reproduction of the paper cases.

## Source Basis and Limits

Files reviewed:

- `u_pw_sph_implementation_notes.md`
- `supporting_information_implementation_notes.md`
- `review_1d_consolidation_stability.md`
- `u_pw_parameters.md`
- `pore_pressure_boundary_ghost_plan.md`
- `corrected_gradient_pr_operator_plan.md`
- `gpu_port_plan.md`
- `cpu_pre_gpu_freeze_plan.md`
- `cpu_case_smoke_completion_plan.md`
- `porepress_restart_plan.md`
- `examples/u-pw/README_reproduction_plan.md`

The main paper PDF is present in `src/papers/u-p` and has now been converted to
`converted/u_pw_paper_text.md` using PyMuPDF. No separate Supporting
Information PDF was found in the folder, so Supporting Information details still
come from `supporting_information_implementation_notes.md`.

## Case Inventory

The current notes identify the following paper or Supporting Information cases:

| Case | Source | Purpose |
|---|---|---|
| 1D Terzaghi consolidation | Main paper notes | Pressure diffusion and coupled consolidation validation under top load. |
| Self-weight consolidation Scenario 1 | Supporting Information notes | Generate undrained self-weight pore pressure, then switch body gravity off and drain. |
| Self-weight consolidation Scenario 2 | Supporting Information notes | Generate undrained self-weight pore pressure, keep gravity on, and drain toward hydrostatic pressure. |
| Cryer problem | Reproduction roadmap / notes | Multidimensional consolidation benchmark with center pore-pressure response. |
| Undrained triaxial tests | Reproduction roadmap / notes | Coupled undrained loading and stress-path behavior. |
| Retrogressive slope / landslide benchmark | Main paper target | Reduced/benchmark landslide mechanism for retrogression. |
| Sainte-Monique landslide | Main paper target | Field-scale application requiring geometry, zoning, calibration, and production performance. |

No additional benchmark cases are identified in the currently available
markdown notes. This should be rechecked once the PDF text can be extracted.

## 1. 1D Terzaghi Consolidation

### Paper Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | 1D consolidation / Terzaghi pressure dissipation. |
| Section / figure | Main paper Section 4.1, Figures 1-6. |
| Geometry | Column, height `H=1.0 m`, width `0.1 m`. |
| Dimension | Treated as 1D behavior using a thin 2D/3D particle column. |
| Particle spacing | `Delta=0.01 m`. |
| Elastic material | `E=2e6 Pa`, `nu=0.3`. |
| Hydraulic material | `Kw=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`, `rho_w=1000 kg/m3`. |
| Loading | Top load `q0=-10 kPa` applied to free-surface particles as an equivalent acceleration. |
| Hydraulic BC | Top drained, bottom and lateral no-flux. |
| Initial pressure | Either load-generated excess or uniform initial excess depending on verification route. |
| Time step | Notes list `dt=1e-6 s`. Current code uses `dt_pore` restriction instead of fixed paper `dt`. |
| Stabilization | PR results use artificial viscosity parameter `alpha=0.1`; damping coefficient examples include `xi=4e-5`; paper compares several damping/viscosity combinations. |
| Reference | Classic Terzaghi series with `Tv=cv*t/H^2`. |

### Current Code Status

Status: partially implemented.

Completed:

- pressure-only 1D baseline runs;
- `PorePress` double state;
- PR rate with corrected volumetric sign;
- `dt_pore`;
- top drained layer correction;
- bottom no-flux layer correction;
- excess pressure initialization profile;
- output for pore-pressure diagnostics.

Not strict yet:

- top load is no longer source-side; formal external-load route should use native `AccInput`, moving wall, plate, or traction;
- layer hydraulic corrections are not a particle-consistent drained/no-flux boundary;
- no production pore-pressure boundary ghost / MLS;
- no strict lateral no-flux boundary in the current baseline;
- no strict Terzaghi coupled response validation after stable loading.

### Strict CPU Smoke Standard

Minimum strict smoke requires:

- GenCase code=0 and solver code=0;
- excluded=0;
- no NaN/Inf in `PorePress`, `ExcessPorePress`, `PorePressRate`;
- top drained layer holds excess pressure near zero;
- bottom and lateral no-flux do not generate obvious pressure spikes;
- pressure dissipation trend has correct sign;
- if coupled top loading is used, motion and excess pore pressure have physically plausible sign.

### Missing Features

- hydraulic boundary ghost / MLS for drained and no-flux boundaries;
- lateral no-flux boundary support;
- a faithful load/traction route;
- strict postprocessing against Terzaghi analytical profiles.

## 2. Self-Weight Consolidation Scenario 1

### Paper / SI Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | Generate self-weight undrained pore pressure, then turn off mechanical body gravity and drain. |
| Section / figure | Supporting Information; exact figure ID TODO. |
| Geometry | Same 1D column family as consolidation. |
| Material | Same 1D consolidation values: `E=2e6 Pa`, `nu=0.3`, `Kw=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`. |
| Initial condition | Hydrostatic initialization, then undrained self-weight response. |
| Undrained analytical response | `p_w0(z) = [(Kw/n) rho g (H-z)] / [K + 4G/3 + Kw/n]`. |
| Stage A | Body gravity on, top undrained, bottom no-flux. |
| Stage B | Restart or switch with body gravity off, hydraulic gravity still active, top drained active. |
| Stabilization | Monaghan artificial viscosity `alpha=0.4` in SI notes, kinematic damping `xi` range `0..0.05`, Shepard every `20..40` steps. |

### Current Code Status

Status: strict staged CPU smoke largely possible for 1D column, not full
long-time reproduction complete.

Completed:

- `BodyGravityStopTime`;
- CPU `PorePress` restart from BI4 by `Idp`;
- `HydraulicGravity` separated from body `Gravity`;
- `HydromechDampingXi`;
- `PorePressureShepard` mode 1;
- self-weight Scenario 1 Stage A/B XML and smoke scaffold.

Remaining strict gaps:

- layer hydraulic boundary corrections are still simplified;
- long-time analytical comparison is deferred;
- exact SI artificial viscosity combination is not frozen;
- strict paper figure reproduction still needs plotting and final parameter lock.

### Strict CPU Smoke Standard

- Stage A: code=0, excluded=0, positive self-weight excess pore pressure, no NaN.
- Stage B: restart log confirms `PorePress` restored and XML init skipped.
- Body gravity is zero in Stage B while hydraulic gravity remains nonzero.
- top drained layer excess pressure is zero after activation.
- bottom no-flux proxy remains small.
- no obvious restart impulse in velocity or `DivVel`.

### Missing Features

- boundary ghost / MLS remains needed for strict boundary reproduction;
- final analytical postprocessing and paper-figure comparison.

## 3. Self-Weight Consolidation Scenario 2

### Paper / SI Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | Same initial self-weight pore pressure, but body gravity remains active during drainage. |
| Final trend | Total pore pressure tends toward hydrostatic profile. |
| Hydraulic BC | top drained after undrained stage, bottom no-flux. |
| Stabilization | Same SI damping / viscosity / Shepard family. |

### Current Code Status

Status: good reduced/1D smoke and long diagnostic line exists; strict paper
reproduction still requires boundary and plotting decisions.

Completed:

- stable CPU line through previous long diagnostic;
- self-weight Scenario 2 XML/BAT scaffold;
- diagnostics confirm top drained and bottom no-flux behavior in the 1D column.

Remaining strict gaps:

- simple layer boundary treatment is still not paper-equivalent MLS;
- long CPU runs should not be treated as final production strategy before GPU;
- exact SI figure/postprocessing remains incomplete.

### Strict CPU Smoke Standard

- code=0, excluded=0, no NaN;
- excess pore pressure decays after top drainage;
- total pore pressure trends toward hydrostatic, not away from it;
- top drained excess remains zero;
- bottom no-flux proxy remains small.

## 4. Cryer Problem

### Paper Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | Multidimensional consolidation benchmark, likely center pore-pressure response. |
| Section / figure | Main paper Section 4.2, Figure 7. |
| Geometry | Poroelastic sphere of radius `R=a`. |
| Dimension | 3D sphere in the paper; a coarse axisymmetric/reduced smoke would be an approximation only. |
| Material / hydraulic parameters | Same elastic/material parameters as 1D Terzaghi except Poisson ratio sweep. |
| Poisson ratios | `nu=0.1`, `0.2`, `0.3`, `0.45`. |
| Loading | Uniform all-around normal traction `p0` at the surface. |
| Boundary | Exterior surface drained. |
| Reference | Center pore pressure `p_w(r=0)/p0` compared to Mandel-Cryer analytical solution. |

### Current Code Status

Status: reduced execution smoke only / not strict Cryer reproduction.

Existing reduced smoke cannot be called strict because it lacks:

- strict Cryer geometry;
- drained spherical or curved boundary treatment;
- pore-pressure boundary ghost / MLS;
- center pore pressure extraction and analytical comparison;
- confirmed paper material parameters.

### Strict CPU Smoke Standard

Strict smoke requires at least:

- a coarse but geometrically faithful Cryer domain;
- correct drained outer boundary or documented approximation;
- center pore-pressure output/postprocessing;
- code=0, excluded=0, no NaN;
- center pressure trend has expected qualitative Cryer response.

### Missing Features

- curved drained pore-pressure boundary;
- boundary ghost / MLS;
- center probe/postprocessing;
- strict spherical geometry and traction/confinement route.

## 5. Undrained Triaxial Tests

### Paper Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | Undrained loading and stress path response. |
| Section / figure | Main paper Section 4.3, Figures 8-9; Supporting Information Figures S3-S5. |
| Geometry | Cylinder, height `0.15 m`, diameter `0.05 m`. |
| Discretization | `53,175` particles, initial spacing `0.002 m`. |
| Material model | Modified Cam Clay. Exact MCC parameters are taken from reference [33] and are not fully present in the extracted main text. |
| Hydraulic condition | Undrained / no-flux. |
| Loading | Top boundary particles move at constant vertical velocity `0.01 m/s`; bottom fixed; top/bottom free-slip. |
| Confinement | Flexible confined boundary conditions on lateral free surface. |
| Permeability | `k=1e-8 m/s` to achieve undrained response. |
| Tests | TU-L, TU-M, TU-N. Initial preconsolidation pressure `(pc)_0=200 kPa`; confining pressures `150 kPa`, `30 kPa`, and `200 kPa` respectively. |
| Output | axial strain, pore pressure, stress path `p' - q`. |

### Current Code Status

Status: reduced execution smoke only / not strict triaxial reproduction.

Existing smoke uses current available mechanisms and cannot be considered strict
because it lacks:

- axial strain/stress control matching the paper;
- confinement/lateral stress boundary;
- stress path output validated as `p'` and `q`;
- MCC if required for strict material matching;
- calibrated DP alternative if MCC is intentionally deferred.

### Strict CPU Smoke Standard

- GenCase and solver code=0;
- excluded=0;
- no NaN;
- small controlled axial deformation;
- undrained pore pressure sign plausible;
- `p'`, `q`, axial strain, and pore pressure can be extracted or explicitly
  reported as missing.

### Missing Features

- loading/confinement design;
- stress-path postprocessing;
- material model decision: DP approximation vs MCC.

## 6. Retrogressive Slope / Landslide Benchmark

### Paper Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | Retrogressive landslide benchmark / qualitative failure progression. |
| Section / figure | Main paper Section 5, Figures 10-22. |
| Geometry | Two slope models: 5 m high at 45 degrees with base length 25 m/top length 20 m; 8 m high with base length 17 m/top length 16 m. |
| Discretization | `Delta=0.1 m`; 11,275 particles for 5 m slope and 8,470 particles for 8 m slope. |
| Material | Sensitive clay with Drucker-Prager yield and isotropic exponential strain softening. |
| Parameters | `E=25 MPa`, `nu=0.3`, mixture density `2150 kg/m3`, water density `1000 kg/m3`, porosity `0.4`, `Kw=0.2 GPa`, `k=1e-8 m/s`. |
| Strength | peak cohesion `15.1 kPa`, residual cohesion `1.5 kPa`, friction `0 deg`, dilatancy `0 deg`, softening coefficient `5`. |
| Initial state | `K0=0.5`, gravity loading using peak strength and `eta=0`; resulting effective stresses and pore pressures used for failure simulation. |
| Trigger | set softening coefficient and apply strength reduction factor `1.65` to cohesion. |
| Boundary | base no-slip, left side wall free-slip. |
| Reference | retrogression, displacement, failure pattern. |

### Current Code Status

Status: reduced geometry execution smoke only / not strict reproduction.

The current reduced slope smoke can check geometry, solver stability, and field
output. It cannot reproduce the paper benchmark without:

- sensitive clay / strain softening / remolding;
- material zoning if present;
- initial stress and pore-pressure state;
- large-deformation validation;
- likely GPU runtime for useful resolution.

### Strict CPU Smoke Standard

A strict CPU smoke would require at least a reduced but paper-consistent slope
setup with:

- no NaN/crash;
- plausible pore-pressure field;
- failure direction qualitatively correct;
- material model assumptions explicitly mapped to the paper.

Current CPU smoke is only a reduced execution smoke.

## 7. Sainte-Monique Landslide Case

### Paper Setup Known From Notes

| Item | Value / status |
|---|---|
| Target | Field-scale Sainte-Monique landslide application. |
| Section / figure | Main paper Section 6, Figures 23-26, Table 1. |
| Geometry | Sainte-Monique cross-section; left slope about 24 degrees and right slope about 26 degrees. Field topography data are not present in the repo. |
| Discretization | `Delta=0.6 m`, 7,723 domain particles, smoothing length factor `1.5`. |
| Material | sensitive clay with Drucker-Prager plus softening law. |
| Parameters | density `1700 kg/m3`, porosity `0.2`, `E=13 MPa`, `nu=0.33`, `Kw=200 MPa`, `k=1e-8 m/s`. |
| Strength | peak/residual friction `10/0 deg`; peak/residual cohesion `45/1 kPa`; softening coefficients `2`, `5`, `10`. |
| Initial state | `K0=0.5`, gravity loading with peak properties and `eta=0`, then softening activated. |
| Workflow | simulation ends after 55 s or after sliding ceases; production run requires GPU/checkpoint workflow. |
| Reference | runout about 52 m vs field 50 m; retrogression about 116 m vs field 100 m for one chosen softening line. |

### Current Code Status

Status: placeholder/reduced field scaffold only / data-blocked.

The current scaffold is not a validated field reproduction because it lacks:

- field topography;
- material zones;
- calibration;
- initial stress/pore-pressure state;
- production GPU workflow.

### Strict CPU Smoke Standard

For the current data-blocked state, strict CPU smoke is not possible. A reduced
placeholder smoke can only test XML/geometry mechanics and output fields.

## Feature Categories

| Feature | Category |
|---|---|
| PR pressure update, `dt_pore`, `PorePress` storage | A. PR core |
| excess feedback mode, difference-gradient feedback | A. PR core / B. numerical operator |
| top drained / bottom no-flux layer corrections | B. hydraulic boundary / numerical operator |
| boundary pore-pressure ghost / MLS | B. hydraulic boundary / numerical operator |
| corrected-gradient PR operators | B. hydraulic boundary / numerical operator |
| PorePress restart | D. case workflow / restart infrastructure |
| BodyGravityStopTime | D. case workflow |
| AccInput external loading | D. case XML/setup |
| loading plate / traction / confinement | D. case setup and mechanics boundary |
| DP / MCC / sensitive clay softening | C. constitutive model |
| initial stress and field pore pressure construction | D. setup / C. constitutive consistency |
| Terzaghi, Cryer, triaxial, slope postprocessing | E. postprocessing |
| GPU kernels and memory | F. GPU/performance layer |

## Case Status Matrix

| Case | Current status | Strict smoke possible now? | Required code features | Required XML/setup | Required postprocessing | Blocks GPU G1? |
|---|---|---:|---|---|---|---|
| 01 Terzaghi / pressure-only | pressure-only baseline complete; coupled external-load not strict | Partly | boundary ghost/MLS for strict coupled BC; faithful loading path | AccInput/plate/traction setup; lateral no-flux | Terzaghi profile comparison | Yes for strict full-paper gate; pressure-only alone is not enough. |
| 02 Self-weight Scenario 1 | staged CPU smoke route exists | Mostly for 1D smoke | boundary ghost/MLS for strict BC | Stage A/B XML with restart | Eq.(4) and Scenario 1 profile comparison | Partly; route exists, strict boundary still open. |
| 02 Self-weight Scenario 2 | reduced/1D smoke and diagnostic long line exist | Mostly for 1D smoke | boundary ghost/MLS for strict BC | gravity-on drainage XML | hydrostatic convergence plots | Partly; strict boundary/postprocessing still open. |
| 03 Cryer | reduced execution smoke only | No | curved drained pressure boundary, boundary ghost/MLS | strict geometry/parameters | center pressure analytical comparison | Yes under the new full CPU gate. |
| 04 Undrained triaxial | reduced execution smoke only | No | loading/confinement boundary; possibly MCC | strict specimen, strain/stress control | `p'-q`, axial strain, pore pressure | Yes under the new full CPU gate. |
| 05 Retrogressive slope | reduced geometry smoke only | No | sensitive clay/softening for strict benchmark | paper slope geometry/initial state | failure/retrogression metrics | Yes unless strict slope is explicitly deferred. |
| 06 Sainte-Monique | placeholder/reduced scaffold, data-blocked | No | sensitive clay/field workflow, restart/GPU later | field topography/material zones/calibration | field displacement/failure metrics | Yes unless data-blocked field reproduction is explicitly deferred. |

## Audit Conclusion

GPU G1 remains blocked by the user's new completion standard. The current CPU
branch has a useful PR core and several reduced smokes, but 03-06 are not strict
paper reproductions. The next step is a full CPU implementation backlog that
separates PR-core blockers from boundary, loading, constitutive, setup, and
postprocessing blockers.
