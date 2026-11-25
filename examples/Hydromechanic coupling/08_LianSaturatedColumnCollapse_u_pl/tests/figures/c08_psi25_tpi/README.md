# Saturated dilative column compared with Lian et al. (2023)

Each result directory contains two fixed-axis outline overlays, signed front differences, horizontal slices of the upper envelope and native pressure, plastic strain and nearest-neighbor summaries. The formal no-HG explicit u-pl run at ψ = +2.5° is included in every comparison. The plots use all 5,000 material particles. Pore pressure is the native total pressure. Material excess is the native difference from the original PorePress0 for each ID.

The reference panels are the colored bodies in the original 180 dpi render of Fig. 15 and both columns of Fig. 16. For each panel the digitizer maps the printed axes to metres. The calibrated Fig. 15 front is checked against the retained independent front table. Text and black arrow cutouts can make small notches or holes in digitized outlines. Fig. 16 does not have those arrows. Raster uncertainty for a Fig. 15 front is approximately two pixels (0.032 m). Particle centers are about 0.02 m inside the initial physical front. Neither offset is subtracted.

For area comparisons one particle covers the points within dp/√2 of its center. This distance is the center-to-corner distance in the initial square particle grid. Paper and simulation are sampled on the original pixel centers in the same 0–8 m by 0–2 m domain. The intersection over union (IoU) is reported for the full frame and for x ≥ 2 m, which gives the slide and toe greater weight. For the right-side envelope the height of each column of pixels is its highest occupied pixel. Empty columns count as zero height, and the RMS uses columns occupied by either body. The raw maximum center x and the 99th percentile of center x are also recorded to expose isolated particles at the toe.

Review the series jointly. A reduction in negative pressure at 0.3 s alone cannot demonstrate a recovered slide. At 0.6 and 1.2 s look for the front, the right-half IoU and the right upper envelope to improve together relative to the explicit baseline. Compare separately against the stabilized and non-stabilized outlines at 0.5 and 1.2 s. Use nearest-neighbor tails, pressure tails and plastic strain to identify clumping, pressure spikes or runaway motion that may mimic a better front. The paper contains numerical references. It supplies no exact material-point fields or uncertainty-based pass threshold for these metrics.

From the case root, run the following after the independent native checks on any candidate. The script compares only requested times with actual saved release clocks within 5.01 µs, records the precise differences and leaves missing candidate frames blank.

```powershell
D:/anaconda3/python.exe -B tests/support/c08_psi25_tpi_shape.py --tag <new_name> --run "TPI beta 0" <run_dir_0> --run "TPI beta 0.04" <run_dir_004>
```
