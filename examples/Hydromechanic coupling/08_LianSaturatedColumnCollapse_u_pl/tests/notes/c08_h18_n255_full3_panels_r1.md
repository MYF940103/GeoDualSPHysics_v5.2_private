# Readable full3 panels

The full301 offline review succeeded. Visual inspection found clipped long titles in its inherited single-column field PNGs and some tail-panel text. Preserve those outputs and their check unchanged. This fresh render-only helper reads only the bound snapshot/history CSVs, emits two three-time/four-field figures and one concise six-panel history figure, and checks their input stat bindings before/after. No solver, native decoding, VTK, parameter change, fitting, smoothing, pressure clipping, old-case analysis or hashes are performed.

The six snapshots retain all5000 native material IDs at the actual saved times. All six share the full pressure, native p-P0, kappa and J ranges. Native p-P0 is not the paper's plastic-volumetric excess. Negative pressure is retained. The first history point is the actual PRE+1 state, not a manufactured zero-time point. Existing CSVs are neither changed nor repeated. Physical acceptance remains false.

After full source review, run once:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_n255_full3_panels_r1.py --execution-authorized`

Fresh outputs: `tests/figures/c08_h18_n255_full3_panels_r1_{early_fields,late_fields,history}.png` and `tests/logs/c08_h18_n255_full3_panels_r1.check.json`. Existing output/partial names refuse overwrite. Inspect all three before delivery.
