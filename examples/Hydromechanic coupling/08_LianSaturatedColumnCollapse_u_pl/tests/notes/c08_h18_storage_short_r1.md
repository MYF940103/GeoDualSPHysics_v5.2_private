# Original-physics storage-observer short preparations

Only `support/c08_h18_storage_short_r1.py` and this note were authored. Nothing
was imported or executed. No source preparation, compiler, GenCase, program,
solver, reader, VTK, Git, SHA scan, owner or notifier was run or created.
The helper exposes **prepare only**; it has no run/native/window phase.

After root reads this helper, one selected preparation may be invoked from the
C08 case root, only after its actual private backend build passes:

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_storage_short_r1.py --phase prepare --job debug2 --execution-authorized
D:/anaconda3/python.exe -B tests/support/c08_h18_storage_short_r1.py --phase prepare --job short3 --execution-authorized
```

These are two independent file preparations, not an automatic sequence. New
tags are `c08_h18_storage_debug2_GPU_r1` and `c08_h18_storage_short3_GPU_r1`.
Each gets a fresh output directory, byte-identical copied original AS03/n2.55
definition, original generated seed triple and17-key receiver material CSV,
plus its own five-column step plan and `.prepare.json`. The generated seed
basename stays `c08_h18_as03_n255_r1`, inside the new directory, so embedded
labels/references are retained without rewriting XML, dates, seed or normals.
The actual command's input prefix points to that **new copy**, and output is
the new short tag. No GenCase is needed or run. Original files are stat-bound
and copied bytes are compared; no SHA scan is used.

The original definition/seed remains physically unchanged: WendlandH1.8,
dp.04, fixed5us, AS.3/n2.55, AV.1, actual same-material schema2 Wendland PRE,
retire255/keepfalse, original NoPen/CompletedOnly, TimeOut.01 and TimeMax10.9.
The duration is bounded only by the native global step limit; it is not a new
3s or full physical acceptance. No wall/support/load/damping/filter/pressure
model changes are introduced by these preparations.

|Profile|Backend|New updates|Actual global `-nsteps:`|Actual saved completed steps|
|---|---|---:|---:|---|
|debug2|GPU Debug|2|2000002|2000001,2000002|
|short3|GPU Release|4001|2004001|2000001,2002001,2004001|

The true original schema2 archive assigns CLI nsteps directly to NstepsBreak
(`JSphCfgRun.cpp:432-434`, `JSph.cpp:1034`); `JSphGpuSingle.cpp:1239,1254,1257`
compares it to the **global** Nstep. PRE imports completed2000000. Passing
literal2 or4001 would therefore stop incorrectly; these values are new-update
counts, not native CLI limits. No local Nstep reset or source change is used.

Plans start from the independently certified PRE actual clock
9.9999999997060076s and use repeated scalar `clock += .000005` for each real
new update, never `n*dt`. They retain true completed/saved_step=completed−1.
The first output is PRE+one update, not an invented imported t0. Debug's
second output is the forced final step. Release's three outputs are the actual
first three original .01s saves. Shared original planned times are checked
within the unchanged1e-14s clock budget. The new planned rows do not claim any
native output has occurred or that signed intervals have already passed.

The preparation binds the private actual program/build/capture/archive/runtime
separately from the original AS03 program/source and original certified PRE.
The private build must have114 objects, original112 retained including all
physical CUDA and original main, one rebuilt host and one new observer CUDA.
No private AV intervention is admitted. The original AS03 .90s run, native
completion and descriptive analysis must already be valid; that does not make
the new observer no-feedback or physically accepted.

Root will separately review the fresh preparation and directly use the existing
`m.invoke` owned tool contract, outside this helper. That contract captures the
Popen child handle's real creation/exe/argv/parent, wait/Win32 exits and unique
log/call files; a wrapped Debug memcheck must additionally bind the target
solver handle. There is no second owner, notifier, watcher or terminal queue.
Preserve any failed call and original console evidence without blind rerun.

After genuine short completion, root still separately admits the exact new
`c08_h18_storage_native_r1` debug2/short3 reader once and checks22 arrays,
6805 IDs, true clocks/steps, P0/J/kappa/ledger/FS/plane/signed guards. Debug2
needs its real memcheck result and is not Release bit truth. Only Release
short3 can then be byte-compared with the genuine original AS03 .90s first3
records, including all22 arrays, actual time payloads/layout and signed clock
records, without rewriting2/3/91 native headers. The ordinary native reader
does not certify the storage sidecar, its cumulative accounting or rate
quantization bound; those require separate offline review. Nothing here
automatically admits a .90s observation, full3s, other psi, PRE, half chain,
physical acceptance or another solver.
