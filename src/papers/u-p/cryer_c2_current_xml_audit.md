# Cryer C2 Current XML Audit

Date: 2026-05-12

Files audited:

- `examples/u-pw/03_Cryer_Problem/CaseCryer_PR_Baseline_Def.xml`
- `examples/u-pw/03_Cryer_Problem/CaseCryer_PR_Smoke_Def.xml`
- `examples/u-pw/03_Cryer_Problem/CaseCryer_PR_TODO_Def.xml`

No GenCase, DualSPHysics, GPU, CPU, or PartVTK execution was performed during
this audit.

## Summary Table

| XML | Geometry | PR fields | Boundary/loading | Strict Cryer status |
|---|---|---|---|---|
| `CaseCryer_PR_Baseline_Def.xml` | Reduced rectangular/column-style domain. | `HydromechCoupling=1`, `PorePressureModel=1`, `SavePorePressure=1`. | Uses `PorePressureBoundaryOperator=0`, top drained/bottom no-flux layer controls, uniform analytical-excess seed. No all-around traction. | Reduced launch workflow only. |
| `CaseCryer_PR_Smoke_Def.xml` | Reduced rectangular/column-style smoke. | PR fields enabled for a very short CPU smoke. | Same reduced layer-style hydraulic controls. No all-around traction. | Smoke scaffold only. |
| `CaseCryer_PR_TODO_Def.xml` | Placeholder. | Minimal PR intent only. | No strict geometry or loading. | Historical TODO scaffold. |

## Baseline XML Details

The baseline XML is useful because it provides:

- reproducible GenCase -> DualSPHysics -> PartVTK launch files;
- production default `PorePressureBoundaryOperator=0`;
- `PorePressureFeedback=1`;
- `PorePressureFeedbackMode=1`;
- `PorePressureFeedbackOperator=1`;
- `PorePressureShepard=1`;
- `PorePressureDtSafety=0.20`;
- `SavePorePressure=1`;
- material constants matching the 1D consolidation setup for `E`, `nu`,
  porosity, permeability, water bulk modulus, and water density.

It does not provide:

- a sphere;
- a radius `R=a`;
- a curved exterior surface;
- drained exterior boundary over the sphere;
- all-around normal traction `p0`;
- Poisson-ratio sweep;
- normalized center-pressure reference comparison.

## Geometry Classification

The current Cryer XMLs are best classified as:

- `CaseCryer_PR_Baseline_Def.xml`: reduced Cryer-like launch workflow;
- `CaseCryer_PR_Smoke_Def.xml`: reduced execution smoke;
- `CaseCryer_PR_TODO_Def.xml`: strict-reproduction placeholder.

None of the current XML files is a strict Cryer candidate.

## Center Pressure Readiness

The current geometry still permits a near-center pore-pressure proxy for smoke
monitoring. It does not yet support strict `p_w(r=0,t)/p0` because:

- there is no sphere center tied to `R=a`;
- there is no applied `p0`;
- there is no dimensionless `Tv` mapping;
- the current helper is not connected to a verified analytical reference.
