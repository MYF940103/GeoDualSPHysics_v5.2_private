# KeepBedOverlap short checks: display-only adapter

Author-only; not executed/imported. Exact new script/note names were absent on disk and from `git ls-files` before creation. The original three phase reviews, CSVs, PNGs and receipts are frozen.

After root full-read, one invocation from C08:

`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_bedkeep_short_display_r1.py --execution-authorized`

Reads only the passed `figures/upl_c08_bedkeep_short_review_r1_{smoke,off,short}.check.json` and their bound history/matched CSVs (plus the OFF exactness table). It does not read typed22/BI4, call/import the prior review implementation, recalculate native metrics, invoke a reader/solver/build, repeat timing or change any gate. The source checks and CSV stats must match before and after display. Any existing complete/partial new display prefix is refused.

- Smoke becomes a small actual-number table: CPU/GPU native-history values plus GPU-minus-CPU scalar difference, using explicit units and11 significant digits. A separate table labels the **per-ID pressure difference RMS** and material-XYZ maximum with their original5Pa/.005mm budgets, so subtraction of pressure RMS statistics cannot be mistaken for that paired metric. No offset axes are used.
- OFF/SHORT use exactly the existing three actual scalar-clock tau locations. Their tick text is `0.01,0.02,0.03`; this is display rounding only, not replacement time values or a new check against `n*dt`. The y-axis scientific/offset formatter is disabled. All original negative values remain; no clipping/interpolation/smoothing/fitted data is introduced.
- OFF labels the existing full typed22/layout/clock-byte exactness result, including signed diagnostics. SHORT remains descriptive across the two boundary operators and carries no5Pa/.005mm acceptance gate.

New files: `figures/upl_c08_bedkeep_short_display_r1_{smoke,off,short}_display.png` and one `figures/upl_c08_bedkeep_short_display_r1.check.json`. No old PNG/CSV/check is overwritten. This display revision does not delay the independently authorized bounded physical window or provide a new physical acceptance.
