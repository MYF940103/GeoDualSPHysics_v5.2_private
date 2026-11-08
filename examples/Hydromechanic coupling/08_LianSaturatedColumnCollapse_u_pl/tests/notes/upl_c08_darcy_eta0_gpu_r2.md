# Private Darcy-only bare-r2 GPU builder revision r2 (author only)

Revision r1 stopped during source-capture verification, before NVCC or link (both configuration receipts retain calls=[]). ZipFile.writestr mutates the supplied ZipInfo, including header_offset; reusing the source ZipInfo made the still-open source archive index invalid for subsequent reads. The original disk archive was not changed. Independent fresh reopening verified CRC and all278 member bytes in both original and r1 partial candidate archives: only the intended CU denominator differs, and its inverse reconstructs the original bytes. Revision r2 changes only packaging to copy.copy(info), plus new tags/paths; the original r1 scripts, both failure receipts and three partial capture files remain untouched. No r1 build is retried.

Only the new support builder and this note are authored. No capture, input, job, program or directory is generated until the root explicitly runs the reviewed command. There is no solver, native, VTK, help command or physical-window action in the builder.

The prerequisite is the actual passed `logs/upl_c08_darcy_eta0_component_r1.check.json`: two ct calls, six Darcy calls, zero updates, unchanged upstream native fields/wall roles and all5000 original-rate bits restored. Its actual owned call must have Popen/Win32 exit0. Merely authored CPU code or a build does not satisfy this gate.

Both baselines are the closed original `upl_c08_bedkeep_{Debug,Release}_r1.build.json` (113 objects, same source capture/archive). No effective-AS source or object is adopted. The old effective-GPU builder supplies only its pure Windows command-line parser, and zero_cpu_r2 supplies the sealed typed process-invocation utility.

In frozen `src/source/JSphGpu_ker.cu`, the full Darcy weight anchor at line1515 occurs exactly once:

```cpp
const double w=vol2*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr2+double(CTE.eta2));
```

Only that denominator becomes `/rr2;`. The source capture proves one substitution, exact reverse reconstruction of the original CU bytes, and identical uncompressed bytes for all other archive members. The existing rr2<ALMOSTZERO guard remains. LP/Lx use this same changed weight; symC, gp, divAce, gradJ/variable-k chain, finite/domain guards, FS policy, force/AV Eta2, material, J/theta, planes and PRE handling are unchanged. This is not complete Lian Eq23/Eq25 or TPI.

On the first authorized build only, a fresh capture is generated under `outputs/upl_c08_darcy_eta0_gpu_r2_source` (CU, patch, source.json, source.zip). A second explicitly selected configuration reuses that frozen capture after checking it. The original total-stress AS path is retained; epsilon.2/n3 is checked against the retained rootr6 reference XML and remains input-driven. No new XML is authored. Original release code still disables Shepard and damping. The trace macros are off.

Each explicit `--configuration Debug|Release` command compiles only this original CUDA TU and links the matching original112 objects, including main, plus the new object: actual113 inputs. It reads the actual configuration's authoritative MSBuild NVCC command from its raw log (only that ASCII line is decoded) and the original UTF16 link tlog. CUDA11.7/MSVC14.36, sm86, static cudart, use_fast_math, the configuration's host/device flags and non-RDC layout are retained. Only source/include/output/scratch/PDB paths are rehomed. Debug and Release objects are never mixed. There is no custom project, full rebuild or device-link stage.

Fresh outputs and receipts are `outputs/upl_c08_darcy_eta0_gpu_{Debug,Release}_r2_build` and `logs/upl_c08_darcy_eta0_gpu_{Debug,Release}_r2.build.json`. Each success records program/source_capture/source_archive, original_total AS, Darcy_denominator=bare_r2, actualNVCC1/link1, all113 inputs, actual typed calls and recipe stats. Seven matched runtime files are copied into the new program directory. Original objects, canonical programs, runtime_r6 and all old candidates stay read-only. No recursive SHA scan is performed.

The prior same-TU Release build took actual123.499s NVCC plus8.086s link; this is an estimate of build scale, not a timing guarantee for Debug or a new benchmark. Bare-r2 changes close-pair weights by the factor1+eta2/rr2 and may increase stiffness. Original necessary timestep guards are preserved, not promoted to a full stability proof. Earlier small-deformation Eta0 error was worse; this candidate is not predeclared more accurate. A build alone admits no physical run.

After root review and the actual CPU pass, each command is independently selected; authoring did not execute them:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_darcy_eta0_gpu_r2_build.py --configuration Debug --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_darcy_eta0_gpu_r2_build.py --configuration Release --execution-authorized
```
