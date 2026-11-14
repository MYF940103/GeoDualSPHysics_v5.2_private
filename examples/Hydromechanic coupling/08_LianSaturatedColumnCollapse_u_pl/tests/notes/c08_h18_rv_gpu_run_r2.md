# H1.8 RV future-window runner r2

## Scope and preserved evidence

This is an AUTHOR-ONLY preparation for a separately root-admitted future Release .90 s window. No prepare, build, solver, reader, VTK or Git was run while authoring it. The original bound support/c08_h18_rv_gpu_run_r1.py, its note, Debug2 run/start/call/status, native files and failed derived check are unchanged. The old run remains passed=false, solver_completed=true with first_failure exactly "Actual schema2 RV policy differs".

The actual Debug2 solver and tool exits were zero and the raw memcheck log reports zero errors and leaks. The postcheck compared a numeric JSON kernel_h_sph_float to m.f32(.072), but that helper returns four packed bytes. This is an audit type error, not evidence of a physical solver failure. Recovery is a separate offline artifact; no old result is relabelled passed.

## Exact mechanical changes

support/c08_h18_rv_gpu_run_r2.py copies r1 with five unique text replacements only:

1. The module description states future Release window only.
2. import struct is added.
3. NOTE points to this r2 note; SCRIPT is naturally the new file.
4. Only telemetry's expected kernel_h_sph_float becomes struct.unpack("<f",struct.pack("<f",.072))[0]. The packed-byte comparisons of two float32 inputs elsewhere remain unchanged.
5. CLI --profile permits window only. The existing OFF/Debug function definitions remain for pure offline telemetry reuse; the new executable CLI cannot prepare or rerun those completed jobs.

No physical value, stage formula, source archive, RV kernel, 66-column schema, numerical certificate, clock, plan, owner/handle capture, root admission or exclusive-write rule changes. solver_completed is still sealed immediately after genuine solver exit0 and normal schema2 Run.out, before derived Run.csv/sidecar/memcheck checks. No reader/VTK or next solver is automatic.

## Future executable contract, not executed

Root must first read and independently bind this new script and note in fresh prepare/run admissions. The unused physical job tag remains c08_h18_rv_window_GPU_r1, with the original 91-state plan, original schema2 Wendland PRE, dt5us, AS.3/n2.55 and private RV alpha.1 ReleaseOnly. Program/build receipts are c08_h18_rv_gpu_Release_r2; private numerical source/capture remain c08_h18_rv_gpu_r1_source. The old r1 build failed at NVCC PATH/compiler selection before CUDA compilation/link; its failure and partials remain preserved. The r2 builder uses the original ccbin-compatible PATH and new outputs only.

The ON policy remains schema2, C08H18RV66-r1, 66 main columns, 182 saved Pre/Cor rows, three same-graph double manufactured rows, and 180000 true calls/commits per phase at the endpoint. No original PRE recomputation, old OFF/Debug repetition, half chain or other psi is implied. One future direct-owner terminal queue attempt is allowed only after separate physical-window admission; uncertain delivery never resends or rearms.

The dedicated pure offline recovery is support/c08_h18_rv_debug2_runtime_recovery_r1.py. Its passed flag means runtime postcheck recovery only; native/RV certificate and physical review remain separate. Debug is not a Release bit-truth control and a successful implementation check is not a clumping repair.
