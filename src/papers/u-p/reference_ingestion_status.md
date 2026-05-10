# Reference Ingestion Status

Date: 2026-05-11

## PDF Search

PDF files were found in several project locations:

- `src/papers/u-p/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf`
- `doc/guides/*.pdf`
- `examples/Examples_*.pdf`
- other example/reference PDFs.

For this u-pw reproduction pass, only the u-pw paper PDF was converted into the
u-p reference folder.

## Tool Status

Initial tool check:

- `pdftotext`: missing
- `PyMuPDF` (`fitz`): missing
- `pypdf`: missing

Installed with:

```powershell
py -m pip install pymupdf pypdf
```

The conversion used PyMuPDF text extraction.

## Converted Files

| Source | Output | Status |
|---|---|---|
| `src/papers/u-p/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf` | `src/papers/u-p/converted/u_pw_paper_text.md` | Converted successfully: 31 pages, approximately 136k extracted characters. |

No separate Supporting Information PDF was found in the repository. The
Supporting Information details continue to rely on
`supporting_information_implementation_notes.md`.

## Newly Confirmed From Extracted Paper Text

The extracted text confirms or improves the local notes for:

- 1D consolidation:
  - column height `1.0 m`;
  - width `0.1 m`;
  - `1000` particles;
  - `Delta=0.01 m`;
  - `E=2e6 Pa`;
  - `nu=0.3`;
  - `Kw=2e8 Pa`;
  - `n=0.3`;
  - `k=1e-3 m/s`;
  - `dt=1e-6 s`;
  - top free surface with zero pore pressure;
  - bottom and lateral boundaries undrained;
  - external load `q0=-10 kPa` applied to free-surface particles as an equivalent acceleration.
- Cryer:
  - poroelastic sphere;
  - drained exterior surface;
  - uniform normal traction `p0`;
  - center pore pressure compared to the Mandel-Cryer analytical solution;
  - Poisson ratios `0.1`, `0.2`, `0.3`, `0.45`;
  - other elastic/material parameters same as 1D Terzaghi.
- Undrained triaxial:
  - cylinder height `0.15 m`;
  - diameter `0.05 m`;
  - `53,175` particles;
  - `Delta=0.002 m`;
  - top/bottom boundary particles;
  - bottom fixed;
  - top vertical velocity `0.01 m/s`;
  - free-slip top/bottom;
  - `k=1e-8 m/s`;
  - lateral confinement via flexible confined boundary conditions;
  - MCC model;
  - TU-L/TU-M/TU-N tests with `(pc)_0=200 kPa` and confining pressures `150`, `30`, `200 kPa`.
- Retrogressive slopes:
  - 5 m high, 45 degree, base length 25 m, top length 20 m, `Delta=0.1 m`, `11275` particles;
  - 8 m high, base length 17 m, top length 16 m, `Delta=0.1 m`, `8470` particles;
  - `E=25 MPa`, `nu=0.3`, mixture density `2150 kg/m3`, water density `1000 kg/m3`, porosity `0.4`;
  - `Kw=0.2 GPa`, `k=1e-8 m/s`;
  - peak cohesion `15.1 kPa`, residual cohesion `1.5 kPa`, softening coefficient `5`, friction and dilatancy `0 deg`;
  - initial stresses with `K0=0.5`, gravity loading, then strength reduction factor `1.65`.
- Sainte-Monique:
  - interparticle distance `0.6 m`;
  - smoothing length factor `1.5`;
  - artificial viscosity `0.1`, `0.0`;
  - damping coefficient `1.0e-5`;
  - density `1700 kg/m3`;
  - porosity `0.2`;
  - `E=13 MPa`;
  - `nu=0.33`;
  - `Kw=200 MPa`;
  - peak/residual friction `10/0 deg`;
  - peak/residual cohesion `45/1 kPa`;
  - `k=1e-8 m/s`;
  - softening coefficients `2`, `5`, `10`;
  - runout around `52 m` versus field `50 m`, retrogression around `116 m` versus field `100 m`.

## Remaining Reference Gaps

- Supporting Information PDF is not present locally.
- Some formulas and section labels remain garbled due to PDF font extraction.
- Exact MCC parameters for triaxial tests are referenced as coming from another
  work and are not fully listed in the extracted main text.
- Full field topography data for Sainte-Monique is not present.

