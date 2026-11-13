# Sealed full or partial CSV: generic readable 2x2 field display

Only this note and `tests/support/c08_h18_field_display_r2.py` are authored.
The r1 display helper, old plots, original CSVs, active inputs and all solver
dependencies remain unchanged. No script, rendering, native reader, build,
solver, VTK, Git, hash scan or notifier is executed during authoring.

After root fully reads the new helper, one unique display invocation is:

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_field_display_r2.py --manifest PATH --execution-authorized
```

Manifest has `{tag,review_check,fields_csv,title}`. Paths are absolute or relative
to the C08 root; `tag` is a fresh safe output prefix and `title` is explicit
display text. The prior check must have `analysis_complete=true`,
`consumed_stats_unchanged=true`, an explicit receiver summary or summaries, and
the exact requested fields CSV bound in `files`. Existing stat helpers check
that binding and the prior consumed identities; no native/source qualification
gates or payload scans are rerun. The helper does not manufacture a review or
silently accept a raw failed solver directory.

Both existing formats are supported: partial CSV without a tag column when the
review has exactly one receiver, and full CSV with explicit receiver tags.
Every supplied actual `(receiver tag,part)` snapshot is drawn, including all5000
original soil IDs2060..7059 exactly once. Its original saved time/tau and the
prior actual receiver interval are retained. No requested time is substituted,
and no missing snapshot is synthesized. Prior partial flags, actual sample
counts, endpoints and runtime observations are copied into the display receipt;
a completed analysis never upgrades a partial run or establishes physics.

Each new figure is2x2: absolute pore pressure, native p minus fixed originalP0,
plastic history kappa and J. Pressure displays convert Pa to kPa; kappa/J stay
raw. Receipt range keys are explicitly `p_kPa`,
`native_p_minus_fixedP0_kPa`, `kappa`, and `J`, so the stored pressure numbers
and key units agree. Every field's full min/max over all supplied states is
shared across all figures. A constant field alone gets a small disclosed
colorbar padding, with its exact data range retained separately. No field
values are clipped, removed, smoothed, interpolated, fitted or changed.

All figures share the complete supplied x/z extents plus .04m margins, with
equal spatial aspect on every panel. Pressure ranges crossing zero use the
existing diverging `TwoSlopeNorm` convention and an explicit zero tick; its
positive and negative color halves have different scales. Each field retains
its own colorbar. Wrapped titles, constrained layout and tight saved bounds
prevent the earlier cropped1x4 title problem without overwriting an old PNG.

Fresh outputs are `tests/figures/TAG_snapshotNN_partNNNN.png` for every supplied
snapshot and `tests/logs/TAG.check.json`; no duplicate data CSV is created.
Existing matching or partial outputs prevent another invocation. The receipt
records actual snapshot clocks, original case tags, shared spatial/full-data/
colorbar ranges, prior scopes and every new PNG identity. Failed display work
preserves its new partial artifacts. Visual QA remains pending until root views
the PNGs. Display success does not define paper excess pressure, prove tensile
causation or conservation, select AS parameters, or authorize another run.
