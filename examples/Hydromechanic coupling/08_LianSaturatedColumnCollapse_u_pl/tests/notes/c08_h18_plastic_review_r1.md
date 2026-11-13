# Offline schema2 plastic source/receiver review (author only)

Only `support/c08_h18_plastic_review_r1.py` and this note are new. No old script,
figure, CSV, native bundle, source, runtime, input or receipt is modified. No
analysis, build, decoder, GenCase, VTK, solver, queue or Git mutation was run.
The actual new native utility has built, but no plastic-source payload was
read during authoring. This script only consumes already sealed native arrays.

The frozen c08_h18_compare_r2.py was fully read. Its SCHEMA/types, read22,
reference_from and analyze_case functions are reused unchanged by direct calls,
not monkeypatching. They analyze every actual save once, preserving all22 fields,
actual IDs and native clocks, fixed P0/excess, monotone material kappa, and the
same fifty original100-ID material layers. Source displacement references the
actual initial source positions; receiver displacement uses its own material
PRE positions. Receiver plots reuse the old plot_results function unchanged.
Only a new source display adapter uses actual source time t (never release
tau), with pressure/stress layer axes in kPa, at most4 major ticks and scientific
formatting without offsets. Derived source CSV stress/pressure units remain Pa;
old pictures, tables and analysis code remain intact.

Interface:

```text
python -X utf8 -B support/c08_h18_plastic_review_r1.py --manifest PATH --execution-authorized
```

Manifest has `schema:2`, fresh safe `tag`, `mode:"source"|"receiver"`, and
`cases:[SPEC,...]`. Each SPEC has these required keys:

```text
tag             unique short derived case label
native_dir      existing new native output directory
source          actual source run stage/tag, not a generic material label
group           psi0 | psi2p5 | psim5
actualAS        null for source; {coefficient:...,exponent:...} for receiver
H               .072 (compared after original float conversion)
input_xml       actual generated execution XML consumed by the engine
material_csv    actual14-key source CSV /16-key receiver profile CSV
native_call     sealed actual typed Popen/Win32 native invocation receipt
run             sealed actual source/receiver owner run receipt
plan            original complete five-column source/receiver plan CSV
```

Paths are absolute or relative to the C08 case root. No files or admission are
created from this example. Additional `evidence` Entries may be stat-bound.
`snapshots_tau_s` optionally names requested receiver times; the reused code
chooses nearest actual saved records, labels their actual times and performs
no interpolation. `source_references:[SPEC,...]` is mandatory in receiver mode:
one full source for each distinct source tag. Each receiver must match that
source's group and actual PRE Entry. Plastic PREs cannot be shared across these
three materials. The new utility is fixed by the passed
logs/c08_h18_plastic_native_r1.build.json program; old schema1/keep5 stages are
rejected rather than relabelled. No new reader is launched.

The adapter binds the actual native argv to its DATA, profile CSV, complete
plan and fresh output, and requires real Popen/Win32 exits0. Actual physical
run/call input/program/build/capture/archive Entries are bound separately;
terminal solver/tool exits must agree and ownership errors must be empty.
Program copies may retain the matching build program's bytes/mtime, but the
actual solver path is bound to the real owner handle. No payload hashes are
computed. The actual generated XML is matched to every profile CSV material
value after original float conversion; group/DP/E/nu/cohesion/psi/decay and
residual laws are closed. FOS uses the actual soils XML value or its existing
1.65 default; fresh_trigger_active must be0. Runtime mode is not inferred from
a filename or a material color.

The new source stages accept all three groups and nonzero soil kappa, with
native coverage checks for nondecreasing5000 histories, fixed kappa0 and
initial7060 kappa0. Actual source yield summaries use saved kappa through the
material softening law; they are not reconstructed trial/status observations.
All original22/212-byte/ID/P0/J-ledger/cache/fixed/clock/signed budgets are kept.
A partial source remains partial/uncertified, with the real failure and actual
end time. It cannot become a receiver reference. Full requires actual solver0,
2M steps,1001 saves and the native full-event schema2 header/array qualification.
A genuine solver-completed source may have a separately failed VTK export;
that failure is retained rather than demanding a new physical run. The reader's
native `runtime_success_claimed:false` is not overwritten by owner success.

Receiver mode requires actual completed window91/end2180000 or formal301/
end2600000, first post completed2000001, original contiguous fixed0..1804 and
retired1805..2059,5000 soil, all original FS/plane/kappa/P0/clock/signed guards,
actual typed AS and CompletedOnly metadata. Source schema2/law2/material group
must match. The native reader uses the actual source contract2 string; neither
it nor this analysis independently reconstructs every target contract token.
The receiving engine is responsible for exact GetContract2 matching. This
analysis cannot reopen a failed source or qualify a receiver launch.

Output uses the new prefix tests/figures/MANIFEST_TAG and a fresh
tests/logs/MANIFEST_TAG.check.json. Tables are history, extrema, fixed layers,
focus tracks and tail_changes; receiver adds the exact plotted snapshot point
table. Source gets full-history, tail and readable material-layer PNGs;
receivers retain history/tail and raw point field PNGs. No values are clipped,
smoothed or fitted. Plots/check remain visual_QA_pending until root views them.

Reported quantities include absolute p and native float(p-fixed initial P0),
effective and total stress, velocity, current mixture KE, pressure-storage
quadratic, mean/top/bottom material settlement, J/n/k, nonzero kappa history and
actual extreme IDs. Native p-P0 is not established as the unique paper excess
definition; kappa is the model's scalar history, not full plastic strain. KE and
pressure quadratics are per unit depth and are not a complete coupled energy.
The tail interval is the actual last up-to1s for source/formal (window receiver
uses the retained up-to.3s convention), with observed changes/secants and actual
duration. A short partial does not become a1s convergence record. No5Pa or new
physical budget, fitted trend, automatic equilibrium/accuracy/winner acceptance,
half chain or continuation is added. Even a full10s source remains pending
physical equilibrium review.
