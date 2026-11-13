# AS.3 completed CSV: readable field display only

Author-only `support/c08_h18_field_display_r1.py` and this note. No rendering,
native/binary read, VTK, solver, build, Git or notifier was invoked. Active
AS.5 and all its dependencies remain untouched.

Root completely reviews the short script, then may invoke exactly once:

```text
python -X utf8 -B tests/support/c08_h18_field_display_r1.py --execution-authorized
```

The only data input is the existing sealed
`figures/c08_h18_wend_a03_partial_review_r1_fields.csv` (15000 rows), bound to
its entry in `logs/c08_h18_wend_a03_partial_review_r1.check.json`. Actual
Parts30/60/89 each retain all5000 original soil IDs and their saved time/tau.
No selected point, pressure extremum, startup record or field value is removed.
CSV supplies soil only: this display does not synthesize boundary particles.

Three fresh PNGs use prefix `figures/c08_h18_wend_a03_display_r1_partNNNN.png`.
Each is2x2: absolute p, native p-fixed originalP0, plastic history kappa, J.
Both pressure displays use kPa while original CSV remains Pa. Each field uses
its complete min/max over all three selected states, identical across the
three pictures. Pressure crosses zero with TwoSlopeNorm and an explicit zero
tick; this has different positive/negative color-half scales. Other fields use
the same original Normalize convention. No clipping, smoothing, interpolation,
new limit fitting or new physics is introduced. Spatial limits also span all
actual selected points; aspect stays equal. Concise two-line titles and four
individual colorbars replace the tall frozen1x4 display.

The old pictures remain untouched. No duplicated source-data CSV is needed;
fresh `logs/c08_h18_wend_a03_display_r1.check.json` binds script/note/sealed
analysis/CSV and new PNGs, actual snapshot clocks, units and shared ranges.
Visual QA remains pending until root views the new pictures. A successful
display does not change the failed90 receiver, complete the missing .90s
frame, establish paper-defined excess or make a new parameter choice.
