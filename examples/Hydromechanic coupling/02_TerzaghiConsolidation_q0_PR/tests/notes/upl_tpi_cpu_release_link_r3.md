# P1 Release r3: link-only recovery preparation

Status: author preparation only, not executed. Original Release r2 is retained
as failed: both separately owned CL calls have genuine Popen/Win32 exit 0,
but the actual link call has exit 1104 and LNK1104 for `libcpmt.lib`.
The r2 builder replaced the complete `vcvars` LIB search path with directories
from A's explicit library receipt, omitting the implicit C++ runtime path.
This is a build-environment failure; it is not a solver or numerical result.

`support/upl_tpi_cpu_release_link_r3.py` does not modify the old builder,
failed receipt/logs, compiled objects, native adapter or source preparation.
It permits one new environment setup and one direct linker invocation only.
The two existing private r2 objects are accepted only with their original
successful CL calls, source-dependency files and prepared source/header
bindings. The failed link's original 86 object paths and ordering must remain
exact: the same two r2 private objects and the same 84 original A objects.
No source file or object is compiled again, no ABI or numerical flag changes.

The fresh environment retains all actual v143 14.36.32532 `vcvars` LIB
directories in order, then appends directories for A's explicitly recorded
libraries. It verifies a root-pinned `libcpmt.lib` is found in that original
search path. That first existing candidate is explicitly search evidence,
not an invented linker-read trace. The environment is obtained with a literal
CRLF batch file invoked as an unquoted no-space relative filename in its
new working directory. No raw environment containing possible credentials
is written to a log.

The old failed link arguments are preserved except output destinations:
EXE/PDB/import-library/ILK/PGD/LTCG state point under the fresh
`outputs/upl_tpi_cpu_release_link_r3/{out,int}` tree. Compiler object paths
are never redirected or replaced. Real environment/link calls retain their
original owner/child creation identity, arguments, console logs and actual
Popen and independent Win32 exits. A failed new link remains failed and
protected, with no retry or automatic next action.

Run only after independent root review:

```text
python -B tests/support/upl_tpi_cpu_release_link_r3.py
  --execution-authorized --admission ROOT_LINK_ADMISSION.json
```

The admission has `stage="upl_tpi_cpu_release_link_r3.admission"`,
`passed=true`, `link_only=true`, and `inputs=[{path,bytes,mtime_ns}, ...]`.
It pins the author script/note, actual r2 common helper, source preparation
and all its 266 source/header files plus source_diff, original A recipe,
failed r2 build/link call/log, two successful CL calls/logs/dependency files,
their two objects, original 84 objects, explicit libraries, runtime copies,
vcvars and linker plus the actual `libcpmt.lib` search candidate. Every
consumed frozen input is checked again by stat; old objects/BI4/source
archives are not swept with SHA. The already qualified linker keeps its frozen
stat identity; only the newly linked EXE receives one identity digest. No CL invocation occurs.

Only the new successful link receipt can supply a new Release program to a
later, separately admitted CPU short-window run. This script invokes no
help, solver, native read, VTK, Git, watcher or physical acceptance. The
paused C08 source and all its dependencies remain untouched. Runtime and
program copies are solely in the new tree; canonical EXEs are not installed.
