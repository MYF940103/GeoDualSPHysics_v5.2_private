# Wendland psi0 receiver offline review (author only)

Only new `support/c08_h18_wend_receiver_review_r1.py` and this note are authored.
Frozen source/Cubic helpers, programs, inputs and outputs remain unchanged.
No solver, build, decoder, VTK, analysis, Git, notifier or SHA scan is run by
authoring. Root must fully read the adapter before a unique offline invocation:

```text
python -X utf8 -B tests/support/c08_h18_wend_receiver_review_r1.py --manifest PATH --execution-authorized
```

Manifest: `tag`, `source`, `cases`; optional `reference_tag` and
`snapshots_tau_s` (default .3/.6/.9 seconds after the actual PRE). `source` is
the existing source-review manifest object, with tag/native_dir/native_call/
material_csv/plan/run/input_xml. Each case requires tag/native_dir/native_call/
material_csv/plan/run/input_xml and `actualAS:{coefficient,exponent}`. Paths are
absolute or relative to C08 root. A single .3 case is supported; .5/.7 can be
reviewed later under a new tag and an explicit common source. This adapter
currently admits only psi0, not the future other-material PREs.

The source adapter's `load()` is reused, then the frozen `reference_from()`
reads the genuine initial source and full PRE records. There is no repeated
BI4 decoding or full source analysis. Source proof remains explicitly typed
schema2/Wendland/15-key material input, exact full scalar plan and complete
1001-frame native qualification; source certificate is not equilibrium.

Receiver proof is the explicit `c08_h18_wend_native_r1.receiver` and metadata
stage. Material CSV must have exactly17 keys: source15 plus actual AS coefficient
and exponent. Every material value must match generated XML and its source;
Kernel2 and Run.out Wendland are bound independently. Actual native call must
use that DATA, full91/301 scalar plan, profile and the exact source Part1000.
Actual solver call/program/build/source closure and native reader exits are
bound; all original22/6805 IDs/1805fixed/5000soil, fixed marker/P0/current-J
ledger/cache/kappa-from-PRE, nonempty signed diagnostic, FS and plane budgets
remain. No Keep5, private AV override or experimental free-surface stage
policy is introduced. AS is typed ReleaseOnly .3/.5/.7 with the reader's
declared exponent set, and positive free-surface pressure handling is the
retained CompletedOnly path. The reader and adapter do not independently
reconstruct the entire target material contract: the actual receiving engine
must enforce its full GetContract2 match.

The first receiver save is the actual PRE+1 update (completed2000001), not a
fabricated t0/PRE record. A separate CSV records genuine first-state pressure,
stress and material-displacement changes against PRE. They are descriptive
changes after a physical update, not required bit equality or a physical
equivalence threshold. Scalar saved clocks are retained; tau is actual saved
time minus actual PRE time. No interpolation or metadata rewriting occurs.

Frozen `analyze_case/plot_results` are reused unchanged. Existing settlement
fields measure displacement from PRE, using original fixed initial-material
top/bottom layers. Added `*_including_preload` history fields measure total
settlement from source initialization; preload offsets are recorded separately.
The front advance from PRE is also separate from the old initial-front field.
Native p-fixed original P0 is distinct from pressure change since release and
is not established as the paper's unique excess-pressure definition.

Every actual91/301 receiver state already gets the frozen analysis' geometry
nearest-neighbour/pairs observations. New shallow figure/CSV outputs retain
all histories, extrema, fifty100-ID material layers, focus tracks, real first
step, selection metrics and genuine field snapshots. Multiple options are
compared only at exact shared step/time; differences are not half-step or
theory errors and no5Pa bound is applied to changed physics. A readable2x3
selection plot places front advance, nearest spacing, close pairs, KE and
pressure together. Parameter choice must consider clumping, pressure pulses,
material deformation and continued motion jointly; the slowest case is not
automatically best. No scalar score or winner/next-stage decision is encoded.

Actual fixed-plane NoPen remains release-only with same-stage Darcy reaction
unclosed. Source/receiver native qualification, short agreement and solver0
do not prove full physical/paper acceptance or general restart capability.
The check leaves physical acceptance and winner selection false and launches
no next solver, other psi, source rebuild, half chain or notifier. Analysis
failure preserves new partial artifacts and never reruns physics.
