# Pair-k manufactured plot display correction (author only)

New `support/upl_c08_pairk_plot_r1.py` and this note; names checked absent/untracked. No execution, plot or input edit by the author. Preserve the original pair-k review, CSVs, PNGs and check.

The helper reads only the passed `logs/upl_c08_pairk_flux_review_r1.check.json` and its stat-bound derived `_manufactured.csv` / `_quantization.csv`. It does not reread the96/576-row helper CSVs, perform aggregation, decode data or rerun scientific analysis. The same nine panels, curve values, field/storage selections and cohorts are retained. The upper six panels keep their original zero-reference symlog1Pa/s display. Only the bottom three storage-effect panels change to linear autoscaling with MaxNLocator numeric major ticks, no offset or scientific-exponent abbreviation; the caption describes the two axis policies.

After root full-read, one explicit plot-only command:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pairk_plot_r1.py --execution-authorized
```

Fresh output: `figures/upl_c08_pairk_plot_r1_manufactured_readable.png`; receipt `logs/upl_c08_pairk_plot_r1.check.json`. Refuse existing outputs and verify consumed stats after plotting. No new CSV, error metric, physical threshold, operator acceptance, force, solver, native reader, build or SHA scan. This fixes readability only; all original conditional-ghost/model/stability limitations remain.
