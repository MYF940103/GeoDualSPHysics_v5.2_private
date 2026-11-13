# Wendland AS options: sealed reviews and exact common saved states

Only this note and `tests/support/c08_h18_wend_options_review_r1.py` are added.
Authoring does not execute Python, a build, solver, native reader, VTK, Git or
hash scan. No old source, helper, configuration, PRE, output or active dependency
changes. Root must fully read the new adapter before one offline invocation:

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_wend_options_review_r1.py --manifest PATH --execution-authorized
```

Run from the C08 case root. Manifest paths are absolute or relative to that root;
the shared `old.path()` resolver retains this convention. New derived outputs
are exclusively `tests/figures/TAG_*.csv`, `tests/figures/TAG_*.png` and
`tests/logs/TAG.check.json`. An existing matching output prevents execution.
Failures preserve newly written partial artifacts; never delete them to retry.

## Explicit manifest and prior qualification

The manifest has `tag`, `reference_tag`, `options`, and optionally
`material_detail_completed_steps`. Supply two or three distinct coefficients
from .3/.5/.7, all at exponent3.825. Each option has exactly these required keys:

```text
tag: actual solver case tag
kind: completed | partial
review_check: existing sealed per-option offline review check JSON
history_csv: that review's existing all-actual-save history CSV
native_dir: the same review's existing qualified typed22 directory
```

No .5/.7 receipt or result is invented by this authoring. A `partial` option
requires a separately completed, explicitly qualified saved-prefix review and
its native diagnostic, even when it is a future failed .5/.7 case. In particular,
the existing .3 option can point to:

```text
tag: c08_h18_wend_psi0_a03_w09_r1
kind: partial
review_check: tests/logs/c08_h18_wend_a03_partial_review_r1.check.json
history_csv: tests/figures/c08_h18_wend_a03_partial_review_r1_history.csv
native_dir: tests/outputs/c08_h18_wend_psi0_a03_w09_r1/native_partial_r1
```

The new adapter does not import or rerun the hardcoded failed90 loader. It reads
the supplied prior check, requires `analysis_complete` and
`consumed_stats_unchanged`, and verifies every `consumed` and `files` stat with
the existing `bind()`. The first consumed entry must remain the prior analysis
manifest, as in the current receiver/partial adapters. That manifest must expose
`source` and either `case` or `cases`; exactly one case must match the option tag.
The requested history must be a bound output of that check. Native files,
profile, generated XML, run, original full91 plan and native call must all be
bound consumed inputs of the same check.

Completed options require the existing `c08_h18_wend_receiver_review_r1` review,
`c08_h18_wend_native_r1.receiver` full91 completion, global2180000 and real
successful solver exits. Partial options require an explicit `partial_review`
stage, `saved_prefix_native_qualified=true`, `receiver_complete=false`,
`whole_run_passed=false`, and a Wendland partial receiver native stage with
`diagnostic_complete`, `saved_prefix_native_passed` and `partial` true while
`passed`, `whole_run_native_passed`, `full_run_completed` and
`certified_receiver` remain false. Their real solver completion must remain false
with matching nonzero exits. Native and prior-review counts must agree, retain
the original91/2180000 target, and disclaim reconstructed unsaved states and a
proven terminal solver step. A future independently reviewed partial adapter
must expose this same explicit qualification contract; a raw failed run or an
unqualified count is insufficient.

Existing profile/XML qualification is consumed without rerunning its gates.
Actual source run, source15-key profile, PRE, physical program/build/source
capture/archive and original launch plan must be the same across all options;
the sealed receiver17-key profile values must match apart from their AS
coefficient. The supplied prior qualification remains the
authority for original numerical budgets, ownership, all-frame ledger/cache,
kernel/contract and safety gates. This tool does not weaken or reissue those
qualifications. Stat equality is an evidence identity check, not a cryptographic
content proof. No new process status or active directory is used as qualification.

## Exact comparisons and material differences

All history records must match their native `clocks.csv` by ordinal part,
`completed_step` and the exact parsed double `time_s`. Their actual
`tau_s=time_s-source_actual_time_s` is preserved. Comparison uses only the set
intersection of `(completed_step,time_s)` across every supplied option. There
is no interpolation, rounded-time matching, nearest-time substitution, forced
endpoint or rewritten metadata. No exact intersection is an error.

For .3 failed90 against genuinely completed full91 options, the expected common
prefix ends at2178001 and actual tau approximately .8900049999663064, subject to
the literal sealed clocks. The full91 final save near .9 is retained only in its
own-window results. The tool never constructs a missing .3 frame.

`common_history.csv` preserves same-time pressure RMS/extrema, native fixed-P0
excess RMS, nearest spacing/close pairs, kappa, J, KE, speed, front advance,
material settlement and stress RMS. `history_differences.csv` subtracts the
explicit reference option at those same exact saves. `common_window_metrics.csv`
uses the existing selection-summary helper on that common window only.
`own_window_metrics.csv` uses the same helper on each option's own saved window,
with explicit first/end step, actual start/end time, duration, sample count,
native status and solver exit. These different own-window extrema and endpoints
are not an unqualified cross-endpoint ranking or winner score.

The existing `SCHEMA`, `TYPES`, read-only memmap convention and `read22()` are
reused. The immutable typed22 header and literal layout are checked; only exact
common frames are read for the new material comparison. `read22()` checks all22
finite arrays, original IDs and real clock/signed diagnostic for those frames.
No BI4 is decoded and no source payload is reread. All5000 original soil IDs
2060..7059 are matched in material coordinates; their fixed original P0 bits
must agree. Differences always mean option minus explicit reference:

- Pressure: signed mean, RMS, maximum absolute difference and its original ID.
- XYZ: component mean/RMS/maxima and Euclidean RMS/maximum displacement difference
  in mm, with the original maximum ID.
- Effective stress: all six native double components; the Frobenius norm counts
  off-diagonal squares twice. Report RMS and maximum per-material norm and ID.
- Total stress: `Sigma_effective-p*I`; compare the same full tensor and norm.
- J and porosity n: signed mean, RMS and maximum absolute difference with IDs.

`material_differences.csv` covers every exact common save. `material_fields.csv`
also preserves every original ID's signed differences at the first and last
common saves by default. Optional `material_detail_completed_steps` selects
distinct literal completed steps from the actual common intersection; it cannot
request an interpolated time. An empty list suppresses that detailed table.

Two new PNGs show common-window pressure/spacing/deformation/motion and material
pressure/XYZ/effective-total stress/J/n difference histories. Both use actual
common tau and short epsilon=.3/.5/.7 labels. Full case tags, qualification status
and epsilon mappings remain in CSVs and the receipt. The resulting check leaves
`visual_QA_pending=true`; root must
inspect the PNGs and matching CSVs before describing them as visually reviewed.

## Scientific limits

These are changed-parameter trajectories, not half-step convergence or errors
against theory. No5Pa/.005mm bound, scalar winner score, automatic next AS/psi,
formal run, half chain, solver, native reader or notifier is introduced. Exit0
and a sealed native result do not prove physical or paper accuracy.

The .7dp nearest-pair threshold is descriptive and is not proof of tensile
instability. Negative pore pressure alone does not establish tensile total
stress. These differences do not replay actual force-stage spectra, GPU
cell/PosCell/FMA, pressure-rate subterms, NoPen impulses, the unsaved rejected
wall stage, local causal mechanisms, or complete energy conservation. The
existing release-only NoPen/Darcy-reaction limitation is unchanged. A partial
diagnostic remains partial even if its common-window curves look favourable;
low speed, a smaller pressure peak or closer parameter agreement alone does not
select a valid parameter or demonstrate a repaired model.
