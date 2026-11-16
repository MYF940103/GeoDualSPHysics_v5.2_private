# GPU P1 r2: source-boundary guard and independent device fixtures

Author preparation only. Frozen r1 authors, its 269-file prepared source,
successful Debug build and every original result remain unchanged. This
preparation does not build, run help/solver/native, execute the fixtures,
hash old files, restart an owner or perform Git operations.

The sole necessary r1 defect is the source pressure check. If pn equalled
oldFinal, a constrained nonzero pn could pass; numeric pn==0 also permitted
negative zero. End-stage projection could erase the evidence. The actual
source-stage check now calls one shared device SourceStateValid predicate:
both fields finite, drained pn must have positive-zero float bits regardless
of oldFinal, while an unconstrained pn must retain exact oldFinal bits.
A newly opened row may legitimately have a finite nonzero oldFinal and pn=+0.
No pressure-update equation, row diagonal/residual, force, J, material,
history rotation, timestep, interface or public class layout is changed.

The same actual predicate is used by a new independently allocated device
fixture kernel called through the unchanged Initialize wrapper. Eight source
cases include drained nonzero==oldFinal rejection, drained negative-zero
rejection, new/retained drained positive-zero acceptance, unchanged ordinary
source acceptance, changed ordinary source rejection, and exact ordinary
signed-zero distinctions. Eight OwnerRole cases exercise both normal and
periodic fixed/fluid ownership and the two crossed-role rejections.

Fixture inputs are uploaded to dedicated device arrays, then read by the
real kernel; they are not only host boolean checks or compile-time literal
tests. Its private result packet counts all 16 device evaluations and is copied back only after the genuine
launch/status check and a synchronizing D2H read. No View, DeviceState,
physical material/pressure/history/force pointer or physical counter is
passed. Temporary allocations are cleaned on both success and exception.
Only actual successful device execution emits:

```text
UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0
```

A build or source review alone does not prove that marker, a passed fixture,
memcheck, native correctness or physical accuracy. Default A still does not
call the private Initialize wrapper, allocate history, publish the endpoint
descriptor, or execute a private fixture/physical force pass.

`support/upl_tpi_gpu_r2_prepare.py` copies the complete root-passed r1 prepare
closure into the new `outputs/upl_tpi_gpu_r2_source` directory. All 269
filenames remain; only `upl_tpi_gpu_r1.cuh` changes. Its old namespace,
`.h` API, policy/summary/CSV schema and all other 268 source/header/doc files
are byte-identical copies. The new source_diff separately references the
unchanged parent diff. The source receipt is `logs/upl_tpi_gpu_r2.prepare.json`.

Run preparation only after independent root review:

```text
python -B tests/support/upl_tpi_gpu_r2_prepare.py
  --execution-authorized --admission ROOT_PREPARE_ADMISSION.json
```

The root admission has `stage="upl_tpi_gpu_r2.prepare_admission"`,
`passed=true`, `prepare_only=true`, and `inputs=[{path,bytes,mtime_ns}, ...]`
pinning these two authors, original r1 prepare/diff and all 269 actual r1
prepared files. Existing trees/receipts, including failures, are protected.
The new prepare receipt records base_prepare, the 269 files, only the changed
`.cuh`, and JSphGpu_ker.cu as the single TU needing recompilation. It records
fixture_executed=false; preparation cannot promote a fixture to passed.

Next independent build may adopt the original r1 Debug's three successful
new host objects and recompile only this CUDA TU, keeping the complete exact
111-object link closure; full four-TU Debug recompilation is also permissible
under a new reviewed build. Release has no prior P1 build and should build
all four matched replacements plus 107 original objects. Either choice needs
new output/receipt tags and actual tool exits. Only a later independently
admitted two-update/two-frame Debug memcheck run can execute the fixtures.
Subsequent Release A/B/C still require native and source/history review;
there is no automatic solver, half, full run, C08 restart or 3D admission.
