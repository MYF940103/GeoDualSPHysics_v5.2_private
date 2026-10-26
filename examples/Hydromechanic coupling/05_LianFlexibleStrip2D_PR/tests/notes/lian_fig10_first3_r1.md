# Lian Fig10 first-three-time native comparison (2026-10-27)

## Inputs and figure convention

Paper: `src/papers/PDF/Lian 2023 u-pl.pdf`, page17 Fig10. The figure is an
embedded 1751x1949 raster (xref63), not recoverable raw SPH/FEM pressure data.
The source hash, original raster hash and exact panel pixel crops are recorded
in `../logs/lian_fig10_first3_r1.check.json`. The raster cache is reproducible
under `../outputs/lian_fig10_ref_r1`; the PDF is preserved unchanged.

The requested first three times and pressure limits are:

| Paper time (s) | Lower (kPa) | Upper (kPa) | Mirror coarse peak (kPa) | Native nodes above upper (%) |
|---:|---:|---:|---:|---:|
| 0.5 | 0 | 5 | 2.509984 | 0 |
| 1 | 0 | 5 | 4.140201 | 0 |
| 3 | 0 | 1.75 | 2.119560 | 9.024186 |

The paper SPH panel is on the left, FEM on the right. New plots use the
12-band SPH colorbar palette (RGB rounded to its 85-level steps); FEM crops
retain their original ABAQUS colors and Pa legends. All new pressure axes
are labeled kPa. The upper limit changes at3s; one auto-scale must not be
used across times. Exceeding values remain in the CSVs, with maxima and node
fractions labeled in the plots. These are node fractions, not integrated area.

Runs are `outputs/lian_mirror15_r1_c` (10us) and `_h` (5us), plus the
newly computed `outputs/lian_late15_r1` strict10us control for clarity.
The July root float-stress output is NOT used in this comparison. These three
runs all have double stress/float pore pressure, original mixedmDBC/q/ramp/
quadrature/damping and SPR/HG/gradient-correction off. Only the strict/mirror
footprint differs; the half run also changes dt. Original 13-node +4% load-width
quadrature is retained. No new physical solver was launched.

Parts10/20/60 are read directly from native BI4. Input PART/header and manifest
hashes, actual times, native20301IDs, initial pressure0, finite/elastic/geometry/
natural-step/drainage and mirror resultant checks were verified. `PorePress`
equals excess pressure here because the initial pressure and gravity are zero.
No VTK precision conversion, smoothing, pressure zero-clipping or magnitude
rescaling was used. Cloud contours use actual saved positions. Actual times
and all pressure values are in `_summary.csv` and each corresponding field CSV;
time mismatches do not exceed the retained1.01e-5s pairing tolerance.

## Findings and limitations

- At0.5s the left-top high-pressure zone and overall distribution resemble the
  paper. At1s the qualitative loading pattern remains similar, but the current
  low/moderate-pressure region extends farther; this is not exact agreement.
- At3s the shape retains the expected drained upper surface and pressure in
  the lower/left soil, but the high-pressure region is visibly too strong and
  broad compared with the paper raster. The2.11956kPa peak is21.12% above the
  paper's1.75kPa DISPLAY limit. This is NOT a21.12% relative error against an
  independently known FEM peak; a display bound is not a measured maximum.
- Mirror coarse/half native pressure-RMS differences at0.5/1/3s are
  0.007162/0.007660/0.002124Pa. Max pointwise differences are at most0.03003Pa
  in these selected states. Halving dt does not visibly resolve the paper
  discrepancy at these times; it is not proof of zero temporal error in general.
- Mirror/strict same-dt pressure-RMS differences at those times are
  0.077098/0.049013/0.021149Pa. The correction that prevents late12.4s load/
  drainage toggles barely changes these early fields. It must not be presented
  as solving this early discrepancy or as a new precision A/B result.
- There are no original paper scalar fields here; do not report a whole-field
  reference RMSE or exact numerical accuracy from the color image. Nor does
  shape resemblance establish 100-s/FEM acceptance or late-plateau removal.

The active formal100-s run is left unchanged. This requested offline check
does not authorize tuning coefficients to fit the picture or silently changing
boundary/loading physics. The common early-field discrepancy remains recorded
for the subsequent reference/consistency diagnosis.

## Deliverables and changed locations

- `../scripts/lian_fig10_first3_r1.py`: reproducible PDF/native extraction,
  original-scale comparison and coarse/half difference plots.
- `../figures/lian_fig10_first3_r1_comparison.png`: paperSPH/FEM versus strict/
  mirror10us at all three requested times.
- `../figures/lian_fig10_first3_r1_half.png`: mirror10/5us fields and separately
  labeled Pa differences, not kPa/theory errors.
- `../figures/lian_fig10_first3_r1_summary.csv`, `_pairs.csv` and nine
  `{strict_c,mirror_c,mirror_h}_part{0010,0020,0060}.csv`: scalar summaries,
  actual times and all original native point fields underlying the new plots.
- `../logs/lian_fig10_first3_r1.check.json`: hashes, cropping/palette/range
  metadata and inspected visual receipt; paper accuracy remains false.
- `../README.md` and `../.gitattributes`: index and byte-preserving new evidence.

No C++/CUDA, formal XML/BAT, running worker or its frozen inputs were modified.
