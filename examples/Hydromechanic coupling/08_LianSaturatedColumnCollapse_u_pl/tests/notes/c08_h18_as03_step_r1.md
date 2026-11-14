# AS03 onset: two independently admitted original CPU steps

Author-only new files are `support/c08_h18_as03_step_r1.cpp`, its `_build.py`
and this note. No import/build/component/solver/native/VTK/Git/hash/queue was
run. Root must read all files, separately admit one build, then independently
admit each selected component. There is no runner, owner, notifier, automatic
two-part loop, half chain or physical time window in this preparation.

The entry is mechanically derived from the sealed `c08_h18_late_step_r1.cpp`.
Only diagnostic/path tags, the AS0.5-to0.3 guard and exact source-part whitelist
change. StepState/Capture, MaterialShadow, the original1027-byte symplectic-call
block, pressure/J balance and trace attribution are retained byte-identically.
Its generated shared include instead derives from the already passed
`c08_h18_as03_rhs_r1.cpp`: only protected access and diagnostic AppInfo are
inserted. That source already reads the exact original AS03 full301 native
Parts38/76, completed2076001/2152001, with all6805 IDs/5000 soil and original
schema2 PRE/material/role/ledger/safety checks. Native headers and saved data
are never rewritten or decoded again by a separate reader.

Original86 physical DebugCPU objects, archived160 headers and source archive
are retained unchanged. There are no hooks in Single, constitutive or physical
TUs. The builder reuses actual successful AS03 RHS CL/link recipes, compiles
only one new entry and links87 objects. Its actual dependency output must
include the frozen shared source, FunSoilMaterial and CPU headers; current
public headers are rejected. No canonical executable or public source changes.

After root build admission, from the C08 case root:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_as03_step_r1_build.py --execution-authorized
```

Only the two following actual component profiles exist, each requiring a new
separate root admission with max_new_physical_steps=1. They are commands to
review and select individually, not an automatic script sequence. Use absolute
paths in the actual owned `m.invoke` call, as in the prior late-step tests:

```text
tests/outputs/c08_h18_as03_step_r1_build/C08H18As03StepR1.exe --check --native tests/outputs/c08_h18_as03n255_full3_r1/native_r1 --part 38 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1 tests/outputs/c08_h18_as03_step_r1_p38
tests/outputs/c08_h18_as03_step_r1_build/C08H18As03StepR1.exe --check --native tests/outputs/c08_h18_as03n255_full3_r1/native_r1 --part 76 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1 tests/outputs/c08_h18_as03_step_r1_p76
```

Each restores one existing completed GPU state by native ID, performs exactly
one original5us CPU step (two actual force/Darcy calls), then stops. All
original predictor bases, sort/ownership, pressure/J update bits, completed
positive-only FS cap, material six-stress and saved-kappa policies remain.
Predictor retains kappa_n; corrector commits its own returned history.
Neither apex, tension-face return, friction softening nor flow law is removed,
disabled or changed. The10000 pure same-input material shadows run only after
the actual step and cannot feed back. Their status/reason/lambda records are
bit-matched inferred shadows, not original-call status hooks.

Outputs per state remain stages35000, balance5000, material_shadow10000,
trace_balance5000 and summary3 rows, plus one actual completion. New flat
output directories and call/check receipts preserve every old result.
Original pressure/J and trace arithmetic budgets remain untouched; failure
retains the real exit/error/partial and does not justify retry, smaller steps,
relaxed gates or another physical run.

The measured identity is unchanged:

```text
delta(log J) - delta(trace sigma_effective)/(3K)
  = log-quadrature - rate-trace-mismatch - trial-addition-roundoff
    + material-return-trace
```

The goal is to measure whether this **current AS03 onset** state has a
TensionRepair trace change and how it compares with J/pressure/contact
integration. Psi0 smooth flow need not exclude a separate tension-face trace
return; unchanged deviatoric kappa does not prove its absence. Its presence
alone does not establish an implementation error or physical correctness.
Do not add the return-equivalent volume to J or subtract it from the pore
pressure source: J already integrates total velocity divergence.

Parts38/76 are first saved close-pair observations, not exact unsaved onset
times. A fresh CPU step from each state is not a replay of omitted GPU
substeps, restart interoperability, a new reference trajectory or full-history
causal proof. Do not extrapolate its5us increment over the0.9s history. The
original fixed-plane contact still has reaction_closed=false; observed
contact primary changes are not a closed reaction/work budget. All results
remain physical_acceptance=false and do not unlock other psi or a new window.
