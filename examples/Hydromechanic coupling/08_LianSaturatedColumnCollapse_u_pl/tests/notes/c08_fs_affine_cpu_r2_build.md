# Affine FS CPU link correction

The r1 compiler exited zero and produced its normal default object c08_fs_affine_cpu_r1.obj. The helper incorrectly lowercased /Fo and /Fd; MSVC ignored those output options with D9002, and the subsequent link failed LNK1104 because fixture.obj did not exist. Preserve both original calls and logs. This is a build-wrapper error, not a numerical result.

The new r2 helper adopts that actual compiled object without recompiling. It retains the same 86 public DebugCPU objects, original link arguments/libraries and source stats; redirects only private link outputs and substitutes the actual object. It copies the same runtime companions. Public source, canonical executables and all physical datasets remain unchanged.

Building does not run the fixture. Root separately invokes the resulting program once in a fresh c08_fs_affine_cpu_r1 output after checking the successful link. The predeclared fixture geometry, fields and arithmetic budgets remain unchanged. No physical acceptance follows from a successful build or witness.
