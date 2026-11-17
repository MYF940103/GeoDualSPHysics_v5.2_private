# Exact poromechanics maintenance r2 (author only)

Only this script/note are newly authored. No plan/apply, compact, fixture, deletion,
process action, reader, solver, build or SHA scan has been performed. Root must
read both files and admit `plan` and `apply` independently. This is not a watcher.
It never stops/resumes/restarts full owner51340/solver35020 or C08 owner36608/
solver43828. Only the new apply owner and its compact children use below-normal
priority. No existing evidence, failed result or cleanup record is overwritten.

```text
D:/anaconda3/python.exe -X utf8 -B validation/poromech_maintenance_r2.py plan --admission ROOT_PLAN_JSON --execution-authorized
D:/anaconda3/python.exe -X utf8 -B validation/poromech_maintenance_r2.py apply --admission ROOT_APPLY_JSON --execution-authorized
```

Each admission stage is poromech_maintenance_r2.<plan|apply>_admission,
passed=true, maintenance_only=true, inputs is a duplicate-free stat list. Bind
script/note/compact.exe, actual full start/root admission/four full builds,
psutil, seven old helper/link receipts and their retained EXE/helper.obj/
compile.pdb/link.pdb, and the three original Python sources. Apply also binds the
one successful plan. Historical receipt SHA strings are read unchanged but no
SHA is calculated; old link receipts prove exit_code0/owned_call_exited only,
not nonexistent historical Win32 evidence or component physical acceptance.

Plan exclusively writes validation/poromech_maintenance_r2.plan.json. It records
exact file path/size/mtime, NTFS GetFileAttributesW, GetCompressedFileSizeW reported
allocation, retained artifact bindings, protected processes and original evidence.
All targets resolve inside the named workspace; every existing lexical ancestor
and file must be free of reparse points. Unknown paths are not deletion targets.
The old helper/link JSON and full start/root admission/four build JSON are walked
recursively for named paths; each ILK must be absent. This is this bounded evidence
set, not a claim that every historical file was scanned or had no reference.

Deletion scope is exactly the seven C02 ILKs listed literally in the script, with
the original agreed byte sizes. Each helper must report linked_not_run and have
its genuine successful original link; EXE/helper.obj and both PDBs are retained.
The only other deletions are C04 tests/support/__pycache__/
cryer_{darcy_closed_r1,load_pair_r1,start_r1}.cpython-311.pyc, with each source.py
present and pinned. No directory, source, EXE/object/PDB, archive, original BI4/
NBI4/IBI4, PRE/restart chain, figure/CSV or formal output is a deletion candidate.

Compression scope is exactly nine closed directories, nonrecursive `*.vtk`:

| Case and tests/outputs directory | VTK count | Logical bytes |
|---|---:|---:|
| C02 stress_full_r1_float/particles | 401 | 41,500,292 |
| C02 stress_full_r1_dt1/particles | 401 | 41,500,292 |
| C02 stress_full_r1_dt05/particles | 401 | 41,500,292 |
| C04 vtk_reexport_20261008 | 11 | 56,655,042 |
| C04 vtk_reexport_20261008_initial | 11 | 55,720,088 |
| C08 c08_h18_wall_c_retry_full3_GPU_r2/particles | 602 | 430,599,463 |
| C08 c08_h18_hg_psi2p5_full3_r1/particles | 602 | 430,599,463 |
| C08 upl_c08_nopen_public_reg_r1/particles | 30 | 21,442,695 |
| C08 upl_c08_resume_r1_psi0_GPU_short/particles | 20 | 14,295,130 |

All2479 VTK files remain at their original paths; the additional root geometry
VTKs in C08 are excluded. Each compact invocation is exactly compact.exe /C /I /Q
*.vtk in that group's closed cwd, without /S or /EXE. It creates fresh call/log
evidence, uses the original Popen native handle for actual creation and final
Win32 exit, and records the literal CreateProcess argv rather than inventing a
separate live command-line observation. Each source file's logical size/mtime is
checked before and after; success also requires the compressed attribute on every
file. NTFS reported allocations are separately recorded before/after. Compression
is transparent filesystem storage, not VTK regeneration or numerical validation.

Before any deletion or real group compression, apply creates one fresh128KiB
repeating-byte fixture, invokes compact exactly once and directly compares its
whole bytes plus original size/mtime. It requires compressed attribute and
non-increased reported allocation. The fixture and call/log remain as evidence;
failure stops all real maintenance. This small fixture is a tool transparency
check, not a full-file byte/hash proof for all VTK data.

Apply accepts only the unique passed plan and exclusively opens
poromech_maintenance_r2.apply.journal.jsonl and .apply.check.json. Each of10 single
file deletions is bracketed by checks of the four protected process identities;
each of9 compact groups has one before/after process check, not2479 repeated
process scans. Exact creation/exe/argv/parent is checked, with C08 still stopped.
The original C08-owner admission only stored PID/creation/status; plan honestly
captures its current full identity tied to that creation, then apply compares it.
Each file gets its own journal entry; retained artifact stats and all consumed
evidence remain unchanged. A failed batch may have partially compressed files:
record them, preserve the first error and journal, and never automatically retry.

The final report distinguishes deleted logical bytes, deleted API-reported
allocation, and VTK API-reported allocation reduction. Volume free-space before/
after is descriptive only: it can change because the active solver or filesystem
does other work. These quantities are not exact volume reclamation, hash-based
bit proofs, physical acceptance or permission for more cleanup. No automatic
following action, solver, reader, build, queue, retry or periodic notifier exists.
