# P3 full2Tv input and real-clock preparation

Author-only stage. New assets are `support/upl_tpi_p3_full_plan_r1.py` and this note.
No preparation, XML/seed/clock output, solver, program, build, decoder or Git action
was executed while writing them. A separately reviewed prepare-only root admission
and explicit execution flag are required before the script creates its new products.
This input is a fresh full diagnostic, not physical acceptance or automatic solve.
Old formal inputs/results, stopped B workers, P1/P2/P3 products and C08 stay unchanged.

## Sole input change and future product paths

The exact source is the completed B10us window run
`logs/upl_tpi_m0_dt_B10us_window2s_GPU_r1.run.json`, with its genuine generated seed
`outputs/upl_tpi_m0_dt_B10us_window2s_GPU_r1_seed/upl_bigstep_2tv_CPU1_r1`.
Only the unique XML byte token `key="TimeMax" value="2.0"` becomes
`key="TimeMax" value="72.88428690075874"`. All other XML bytes remain identical,
including line endings, geometry, physics, original five-segment output table and
historical comments. In particular the XML's old SPR/AV OFF comments are stale;
actual values remain SPR=1 and AV=.1. This note explains them without rewriting
an old input or silently changing any other byte in the new runtime XML.

The future exclusive products are:

- `configs/upl_tpi_p3_full_r1.xml`, containing only that TimeMax value change.
- `outputs/upl_tpi_p3_full_r1_seed/upl_bigstep_2tv_CPU1_r1.xml`, identical runtime XML.
- The original small `.bi4` and `_Normals.nbi4` copied into that new seed directory.
- `logs/upl_tpi_p3_full_plan_r1.clock.csv`, exact original eight-column clock schema.
- `logs/upl_tpi_p3_full_plan_r1.prepare.json`, the separate preparation receipt.

The original generated case basename is retained in the new directory so it matches
the copied binary seed label; no GenCase output or new generated label is fabricated.
Small binary copies are checked bytewise, not parsed as solver results or hashed.
The new directory/files are created exclusively; existing or partial products prohibit
another preparation. Failure preserves partials and the first real error, never deletes
or replaces old files. A receipt does not start a solver or admit the old capped program.

## Time and output contracts

Fixed step stays `1.0000228881835938e-5 s` = original tD /1000.
Ramp and drainage tD stay `.0100002288818359375 s`; completed step1000 is pre-open,
and1001 is first post-open. TimeMax is exactly `72.88428690075874 s` and the future
runner's exact step cap is7288262. The verified scalar endpoint is
`72.88428815806371 s`, with1653 frames,1549 post-open frames and15490 true native
drained receiver checks. The input stage only plans those checks, it does not certify
any future native values or drainage implementation.

Actual time is rebuilt by binary64 `time += DT` for every update. It is never replaced
with completedSteps*DT. Output targets alone follow the original multiplication and
branch order of frozen `JDsOutputTime::GetNextTime`, whose actual source is stat-bound.
The original special table is retained exactly:

- From0: interval2^-13 s.
- From.009765625: interval2^-19 s.
- From.01025390625: interval2^-13 s.
- From.0250244140625: interval2^-9 s.
- From2.0000457763671875: interval.18218571428571428 s (legacy DeltaTv=.005).

With that real target-crossing rule, the new full part1262 is completed200000 at
`2.0000457763714676 s`, an ordinary save crossing the original timeout anchor.
The old2s part1262 is completed199996 at`2.00000577545594 s`, forced by its TimeMax.
Only old/new plan indices0..1261 (1262 records) truly share all eight fields, including
actual time bits, saved/completed Step, dt, target, drain flag and forced-final flag.
The old forced final is explicitly not shared. The script checks this by reading the
actual immutable old1263-row clock table; it does not assume a full1263 prefix.
This is plan evidence only, not a native-state or output-sidecar byte proof.

The continuum scheduling companion is the original unfitted M0 Cv based on E2e6,
nu.3,k1e-4,rhow1000,g9.81: Cv=.027444522857366895 m2/s.
tD+2/Cv is approximately72.88428594316754 s; the retained full cap is about.958 us
above that target. The planned actual end corresponds to legacy Tv2.0000000607867685.
A finite-Kw reference uses its own capacity and actual time. No reference, radius,
load, time origin, k or physical parameter is fitted by this preparation.

## Implementation counts and later accuracy review

For7288262 accepted updates, expected counts are21864786 endpoint calls/writes,
14576524 provisional validations/transitions,153053502000 core field comparisons,
43729572000 read-only HG history/rate checks,14576524 physical HG force/rate calls,
and36441310 total force phases. Each P3 pressure file has1653000 saved rows; all
three total4959000. Step7288261 fits the original unsigned32 native field; counters
fit unsigned64 and exact binary64 integer representation. The script checks these
integer ranges without executing any physical step.

The current P3 runtime still hard-rejects M0 TimeMax>2; its full qualifier/build must
be separately reviewed before this input can be used. A future actual full native
profile must independently retain22 typed arrays/1040IDs/P0/J/ledger/FS/geometry,
all signed intervals, true drain count, three pressure rounds/five force phases and
original HG guards. No old reader is relabelled as supporting this new full profile.
The1262 real shared states can be checked only after that future run/read completes.

Original full budgets remain separate: ten declared legacy Tv targets
.005,.05,.1,.25,.4,.5,.7,1,1.5,2; pressure RMS<=A+10Pa and late Tv>=1 increment<=5Pa;
top absolute error<=A+.001*S_infinity; bottom<=.005mm and<=A+.002mm;
all t>=.1s original100Pa mean-layer total-stress/top-gap gates. A's original failure
never exempts P3. A finite-Kw / B M0 are different companions at their own actual
saved times; old u-pw Vel0 is context only. Startup ramp/band/inertial/current-J
reference limitations remain. P3 is not literal LF/implicit/second-order, and a
successful2s window is not full-cycle or public-source acceptance.

## Independent prepare-only admission

Entry: `D:/anaconda3/python.exe -B tests/support/upl_tpi_p3_full_plan_r1.py
--admission PATH --execution-authorized` (one command, shown wrapped).
Admission stage is `upl_tpi_p3_full_plan_r1.prepare_admission`, passed/prepare_only
true, with unique stat-bound inputs: this script/note; reused `upl_tpi_cpu_run_r1.py`
and its note; exact source B10us run; its three seed files and old clock CSV;
actual frozen P3 `JDsOutputTime.cpp`. All inputs are rechecked at the preparation seal.
No SHA scan, old-object sweep, solver, default A, half, reference run, reader, VTK,
notification/watch worker or follow-on action is performed.
