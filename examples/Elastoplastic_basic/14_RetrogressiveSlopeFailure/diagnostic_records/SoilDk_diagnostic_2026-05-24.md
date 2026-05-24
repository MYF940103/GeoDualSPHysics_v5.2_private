# SoilDk diagnostic for reverse softening bands

Date: 2026-05-24

## Purpose

Check whether the reverse bands in the retrogressive slope failure case are produced by localized increments of equivalent plastic strain (`Kplastic`) before cohesion drops to residual strength.

## Diagnostic change

Added a temporary GPU diagnostic output:

- `SoilDk`: accumulated positive increment of `Kplastic` between two output files.
- The diagnostic is output only through the GPU path used in this test and does not alter stress update, return mapping, or softening.

## Case

- Case: `CaseRetroSlope_Bui2021_failure_soildk`
- Restart source: `CaseRetroSlope_Bui2021_init_GPU_out\data\Part_0050.bi4`
- Duration: 5 s
- Output interval: 0.1 s
- GPU executable: `DualSPHysics5.2_GEO_win64.exe`

Run completed with 0 excluded particles.

## Outputs

- Summary CSV: `diagnostic_records/soildk_diagnostic_summary.csv`
- Overview figure: `diagnostic_records/soildk_kplastic_coh_parts25_30_35.png`
- Interior-band figure: `diagnostic_records/soildk_interior_reverse_bands_parts24_35.png`
- VTK files: `CaseRetroSlope_Bui2021_failure_soildk_GPU_out/particles/PartFluid_*.vtk`

## Main observation

The global maximum of `SoilDk` is dominated by the basal sliding band. After restricting the window to the internal block region (`8 < x < 25`, `0.5 < z < 5.2`), the reverse bands coincide with localized `SoilDk` increments.

Representative internal-band peaks:

| Part | Time (s) | Location | SoilDk | Kplastic | SoilCoh | SoilJ2 |
|---:|---:|---|---:|---:|---:|---:|
| 24 | 2.4 | x=23.21, z=1.90 | 0.472 | 5.19 | 1500 | 2.25e6 |
| 29 | 2.9 | x=13.87, z=1.45 | 0.346 | 1.92 | 1501 | 2.25e6 |
| 30 | 3.0 | x=13.89, z=1.43 | 0.362 | 2.28 | 1500 | 2.25e6 |
| 31 | 3.1 | x=12.98, z=2.94 | 0.361 | 1.74 | 1502 | 2.26e6 |
| 33 | 3.3 | x=12.52, z=3.60 | 0.399 | 2.27 | 1500 | 2.25e6 |
| 35 | 3.5 | x=12.37, z=3.87 | 0.442 | 3.00 | 1500 | 2.25e6 |

## Interpretation

The reverse bands are not caused by high `J2` or tensile stress. They are zones where local plastic increments first concentrate, then cohesion rapidly collapses to residual strength. After cohesion reaches residual strength, the return mapping projects the stress state to the residual yield surface, so `J2` becomes locally low (`~2.25e6`). This explains the observed pattern:

1. `SoilYieldF` becomes active.
2. `Kplastic` increases locally.
3. `SoilCoh` drops sharply.
4. `SoilJ2` appears as a low-value band, not a high-shear band.

Because `n_coh=5`, an increment of `Kplastic` of only 0.3-0.4 over one 0.1 s output interval is enough to push cohesion very close to residual strength. This supports the diagnosis that the reverse bands are driven by localized plastic strain-rate concentration, not by artificial tensile stress alone.

