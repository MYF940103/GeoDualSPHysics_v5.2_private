# Wendland H1.8 source offline review (author only)

Only new files `support/c08_h18_wend_review_r1.py` and this note are authored.
Frozen Cubic/plastic helpers and old results are unchanged. No solver, reader,
build, analysis, VTK, Git, notifier or SHA scan was invoked by authoring. Root
must fully read this adapter before one explicit offline invocation after the
separately admitted native read finishes.

```text
python -X utf8 -B tests/support/c08_h18_wend_review_r1.py --manifest PATH --execution-authorized
```

Manifest requires `tag`, `native_dir`, `native_call`, `material_csv`, `plan`,
`run`, `input_xml`. Paths are absolute or relative to C08 root. Actual source
is only `c08_h18_wend_psi0_pre_r2`; intended native directory is its `native_r1`.
Optional `compare_failed_Cubic` defaults true and consumes the already sealed
failed-source summary/CSV, without decoding or rereading its large payload.
No manifest, native completion or source admission is fabricated here.

The explicit new source stage is `c08_h18_wend_native_r1.source`, never a
relabelled Cubic stage. Full qualification requires the original1001 genuine
states/2M updates, all7060 IDs=2060fixed+5000soil,22 arrays/212bytes, unchanged
ledger/cache/P0/fixed/kappa/clock/signed budgets and the original complete
five-column scalar plan. The15-key material CSV must match actual generated
XML: prior14 keys plus `Kernel=2`. XML, actual Run.out `Kernel="Wendland"`,
no-exclusion Run.csv, actual source program/build/handle exits and new reader
call/program are bound separately. Native full-event kernel contract-token
proof and typed schema2 certificate are required. Non-event arrays alone are
not claimed to prove kernel identity, and full material contract reconstruction
still belongs to the real receiving engine. The adapter does not test a new
receiver or claim general restart support.

The frozen compare_r2 `read22/analyze_case` and plastic `source_plots` are
reused unchanged. All actual startup and late states remain, with source t
labels and readable kPa stress/pressure axes. Native absolute p and float
`p-fixed initial P0` are distinct; the latter is not established as Lian's
unique excess-pressure definition. Kappa remains the scalar constitutive
history, not a full plastic-strain tensor. Mixture KE and pressure-storage
quadratics are not a complete coupled energy or conservation proof.

New shallow `tests/figures/TAG_*` CSVs contain all history/extrema/fifty original
100-ID material layers/focus tracks; geometry nearest-neighbour and pairs
at r<.7dp; separate actual last0.5s/1s metrics and same-material changes. Tail
starts are the first saved time at or after actual end minus requested span;
the actual duration and sample count are reported, not replaced by nominal
time or interpolated samples. Pressure, effective/total stress, velocity,
KE, top/bottom/mean settlement, kappa/J/n/k endpoint/range/secant and per-ID
changes remain descriptive. The position finite difference is not a native
acceleration or force-equilibrium measurement. No new numerical acceptance
threshold is introduced.

Spatial diagnostics use all5000 soil points at every actual save. They report
nearest distances, near pairs and saved x/z<0 counts; a first saved penetration
is not an inferred first unsaved crossing. No clipping, smoothing, shifting,
fitting or input adjustment occurs. Additional geometry PNG and original
source history/tail/layer PNGs retain matching CSV data.

Three additional readable2x3 focus PNGs show the complete source, its actual
last1s and actual last0.5s separately. They distinguish absolute/native-excess
pressure RMS, maximum/RMS speed, effective/total stress, current mixture KE,
fixed initial-material mean/top/bottom settlement and maximum kappa/minimum
and maximum J-minus1. These use the same full history CSV, retain actual saved
times and native extrema, and neither fit trends nor infer a tensile cause
from observed close pairs. The large overview is not the sole result display.

Optional Cubic comparison uses only the533 complete original5000-soil states
already recorded by `c08_h18_loss_review_r1`. Match keys are exact actual step
and actual time; differences are descriptive different-kernel changes, not
theory errors, backend bounds or half-step errors. Cubic's separate7059-ID
forced final at5.32272s stays failed and is neither interpolated nor mixed
into complete-material means. The new comparison CSV and PNG only use genuine
shared times, so the old missing state cannot be silently filled or extended.

Successful offline analysis reports `analysis_complete` and pending visual QA.
Full native source qualification and normal execution do not automatically
establish equilibrium, physical accuracy or collapse readiness. Those remain
root's separate physical review; this adapter leaves physical/equilibrium
acceptance false and starts no solver, half chain, receiver or other material
group. Analysis failure preserves new partial outputs; it never reruns physics.
