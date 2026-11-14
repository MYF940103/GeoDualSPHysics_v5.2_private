# Private GPU storage-trace builds

Only `support/c08_h18_storage_trace_build_r1.py` and this note were authored.
No preparation/import, compilation, program/help, physical/native/VTK execution,
Git, SHA scan, owner or notifier was run or created by this author. Root must
read the complete builder and separately admit each backend build. A build is
not an implementation regression or a physical result.

The separate source author's preparation is
`support/c08_h18_storage_trace_r1_prepare.py`; the agreed receipt is
`logs/c08_h18_storage_trace_r1.prepare.json`. It binds
`outputs/c08_h18_storage_trace_source_r1/source.json` and `source.zip`.
The private source capture must prove byte-reversible insertions in only
`src/source/JSphGpu.cpp`, plus the added `src/source/C08StorageTrace.cu` and
`src/source/C08StorageTrace.h`; all other original archived bytes and primary
expressions remain unchanged, with no class-layout/public-interface/equation
change. The builder does not prepare or modify those files.

After the preparation is separately reviewed, from the C08 case root, each
command requires its own root admission:

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_storage_trace_build_r1.py Debug --execution-authorized
D:/anaconda3/python.exe -B tests/support/c08_h18_storage_trace_build_r1.py Release --execution-authorized
```

These are full private GPU programs using the standard original basename in
`outputs/c08_h18_storage_trace_Debug_r1` and `_Release_r1`. Neither command runs
the program, starts a solver, supplies a physical trajectory, creates an owner,
queues a notification or automatically starts the other backend.

For each backend the actual original schema2 successful build, CL/link tlogs,
resolved library tlog and original NVCC command in the saved build log are
authoritative. Original113 object identities are checked against the existing
successful same-backend FS-normal build's consumed stat records. This is a
stat binding to a previous seal, not a retrospective hash proof. Only
`JSphGpu.obj` is replaced and one independent observer CUDA object is added.
The other112 original objects, including original main and every original
physical CUDA object, remain unchanged. The final link has114 objects.
Original `JSphGpu_ker.cu` is neither modified nor recompiled. No full MSBuild
or physical CUDA/library rebuild occurs.

The complete private archived `src/source` tree is extracted beneath that
backend's private output. It contains the original160 headers plus the one
observer header; the private host and new observer TU compile from this tree.
Actual host source
dependencies must include the private observer/JSph/JSphGpu headers and reject
current public source headers. The CUDA recipe retains its original sole CUDA
include plus the explicit private tree; quoted project includes resolve in the
complete private source directory. Original source archives and public files
are never edited.

Only the private host and added observer TU enable `C08_STORAGE_TRACE=1`; old
`C08_STAGE_TRACE`/`C08_CAUSAL_TRACE` are explicitly undefined. Original Debug or
Release optimization, FP, runtime ABI, OpenMP, CUDA11.7 static runtime,
compute86/sm86 and MSVC14.36 HostX86/x64 choices are retained. No new language
standard, fast-math policy, RDC or device-link step is introduced. The observer
must therefore remain compatible with the original language settings. The
original physical GPU kernel object remains macro-off and instruction-identical
to the retained program; no extra neighbor pass is inserted into it. The
observer reads the actual float pressure rate, so its Darcy remainder includes
that rate's rounding. A rate-quantization bound is diagnostic rather than a
claim to observe an unrounded double rate.

The owned CUDA intermediate tree is
`%TEMP%/c08_h18_storage_trace_r1/Debug` or `/Release`, with no spaces. Host and
CUDA-host PDBs are separate. CL output switches are explicitly case-correct
`/Fo` and `/Fd`; linker output/PDB/import-library/LTCG paths are redirected to
the private program. Original compiler environment injection flags are removed,
and the actual PATH compiler must match original NVCC -ccbin. The nine original
runtime companions are copied and compared bytewise; this is no SHA scan.

Exactly one CL, one NVCC and one link call are expected per backend. Their real
owned call records and exits are retained. An existing output/intermediate,
partial build, call or receipt blocks re-execution. On failure, preserve all
new partial artifacts and the first real error; diagnose rather than replacing
the old failure. Source preparation, Debug smoke/memcheck, output no-feedback
comparison and any physical observation window require later independent root
review. The original PRE, source programs, formal cases and every prior result
remain protected.
