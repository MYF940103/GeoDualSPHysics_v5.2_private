# Single same-configuration Release GPU control (author-only)

One new `upl_material_release_native_r1_source_GPU_release` source job only, using the actual passed `upl_material_release_Release_r3` program and byte-for-byte copies of the old Release-r2 source XML/BI4/normals. Same800 updates,2.5us/event380/end.002s. Direct GPU, no repeated sanitizer, receiver, half or automatic next job. All old/new Debug evidence remains unchanged, including the failed strict Release-vs-Debug baseline.

Explicit independent commands, run only after root review:

- `python support/upl_material_gpu_release_control_r1_build.py` builds only the small reader TU against actual r3 DebugCPU85 objects.
- `python support/upl_material_gpu_release_control_r1_run.py --execution-authorized` starts only the new Release source.
- `python support/upl_material_gpu_release_control_r1_decode.py --execution-authorized` decodes only its closed actual run, all original22 arrays/IDs/real scalar clock/signed intervals/PRE/ledger/free-seepage gates.
- `python support/upl_material_gpu_release_control_r1_review.py` compares all22 actual saved states with retained old Release source, original strict bit and complete signed-clock CSV equality, no substituted5Pa tolerance.

The reader TU includes the original new-reader file unchanged. Its own internal main/undef would defeat an outside main-renaming macro, so a small `wmain` dispatches directly to `Read("source","GPU_release",...)`. Link uses the standard MSVC CRT startup `/ENTRY:wmainCRTStartup`, preserving CRT initialization and global constructors; the included old main is present but unused. This changes only the test entry, not any numeric function or guard. Microsoft documents the standard console CRT startup at https://learn.microsoft.com/cpp/build/reference/entry-entry-point-symbol .

The separate initial audit is `logs/upl_material_release_gpu_initial_audit_r1.json`. It establishes actual identical initial physical soil state/trueFS mask but Release/Debug compilation confounding; it does not declare strict equality or establish compiler flags as the sole cause. No old/source/production file is modified by these new author files.
