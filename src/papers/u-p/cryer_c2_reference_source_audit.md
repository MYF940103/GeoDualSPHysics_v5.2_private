# Cryer C2 Reference Source Audit

Date: 2026-05-12

## Sources Checked

| Source | Status | Relevant Cryer content |
|---|---|---|
| `papers/u-p/converted/u_pw_paper_text.md` | Found | Main paper Section 4.2 text, equations (46)-(47) in OCR/text-extracted form, and Figure 7 description. |
| `papers/u-p/full_paper_case_audit.md` | Found | Current case audit summary: sphere radius `R=a`, drained surface, traction `p0`, Poisson sweep, center pressure reference. |
| `papers/u-p/reference_ingestion_status.md` | Found | Notes that Cryer compares center pore pressure with a Mandel-Cryer analytical solution. |
| `examples/u-pw/03_Cryer_Problem/notes.md` | Found | Local reduced-workflow notes and known strict blockers. |
| Supporting notes / implementation plans | Found partial | Mention that strict Cryer needs curved drained boundary and center-pressure postprocessing. |

## Extracted Paper Information

The converted main paper text states that Cryer's problem is a poroelastic
sphere with a drained exterior surface subjected to a uniform normal traction
`p0`. At the sphere center, pore pressure initially reaches the load scale and
then rises further before dissipating. This is the Mandel-Cryer effect.

The paper text also includes an analytical center-pressure expression and a
root equation for the coefficients. The text extraction is not clean enough to
be used directly as a coded formula without manual verification against the PDF
or an external authoritative reference. The usable qualitative and parameter
facts are:

- comparison quantity: `p_w(r=0,t)/p0`;
- normalized independent variable: dimensionless time `Tv`;
- Poisson-ratio sweep: `nu=0.1`, `0.2`, `0.3`, `0.45`;
- material constants: same as the one-dimensional Terzaghi simulation except
  for the changing Poisson ratio;
- paper simulation settings in the caption include `dt=1e-6 s`, artificial
  viscosity `alpha=0.1`, and damping `xi=4e-5`.

## Directly Usable Reference Status

The repository currently contains enough information to define the Cryer
benchmark target, but not enough machine-readable data to produce a trusted
strict analytical comparison automatically.

Usable now:

- benchmark type and qualitative center-pressure response;
- pressure normalization by `p0`;
- Poisson-ratio values;
- shared material constants relative to the 1D Terzaghi setup.

Still missing or needing manual verification:

- clean analytical series implementation;
- exact root equation notation after PDF extraction cleanup;
- dimensionless time definition and parameter mapping;
- sphere radius/geometry scaling used in the paper setup;
- machine-readable Figure 7B reference curves or verified digitization;
- selected `p0` if the strict run uses an explicit traction load.

## Recommendation

Do not call the current Cryer workflow strict until one of the following is
available:

1. a verified analytical series implementation from the clean PDF equation and
   the cited reference;
2. digitized Figure 7B curves with documented uncertainty;
3. a small independent reference script validated against a published Cryer
   solution.

Until then, Cryer postprocessing can prepare the center-pressure extraction
pipeline, but any numerical comparison should be labeled qualitative.
