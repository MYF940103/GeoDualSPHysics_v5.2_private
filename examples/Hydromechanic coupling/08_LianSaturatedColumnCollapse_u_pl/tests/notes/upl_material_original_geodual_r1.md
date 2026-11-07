# Published GeoDualSPHysics v1 material source audit

Read-only source comparison; no original code was compiled/executed or linked into production. No driver, candidate, build, solver, server package or retained result was changed.

## Provenance and small extraction

The user-specified [Mendeley version1](https://data.mendeley.com/datasets/z4sh62y97g/1) is published **17 December2025**, DOI **10.17632/z4sh62y97g.1**. The actual public API directory contains one file, `GeoDualSPHysics.rar`, fileID `994f9a73-3596-4bf2-b3a0-bd190014a12b`, **41,847,559 bytes**, not a multi-GB distribution.

The initial HTTP Range returned `206 bytes0-4095/41847559` and the RAR5 signature. Because the whole archive is only about40MiB, it was then obtained **in RAM**, with one archive SHA256 verification against the API's published value:

`47e72392512eb23bbd6ea99d8fcfabd7ca3f5ffc89431a656fb0cfd2b73fb7e1`

The complete RAR was not saved to disk. An installed libarchive reader enumerated386 entries and extracted only four unmodified byte streams. The new folder totals297,593 bytes including the small API/directory/retrieval records:

| Original archive path | Retained local file under `tests/support/upl_material_original_geodual_r1/` | Bytes |
|---|---|---:|
| `GeoDualSPHysics/src/source/JSphCpu.cpp` | `jsphcpu.cpp` | 141088 |
| `GeoDualSPHysics/src/source/JSphGpuSimple_ker.cu` | `jsphgpusimple_ker.cu` | 54078 |
| `GeoDualSPHysics/src/source/DualSphDef.h` | `dualsphdef.h` | 29363 |
| `GeoDualSPHysics/LICENSE GNU-LGPL` | `license gnu-lgpl` | 26455 |

`snapshot_v1.json`, `files_root_v1.json`, `folders_v1.json`, `archive_directory_v1.json`, `archive_header_range.bin` and `source_retrieval_v1.json` retain the version, original paths, HTTP range and archive-integrity evidence. This is a selected original-source reference, not a complete project/archive backup. No existing objects/source archives were rehashed.

**License versions must remain distinct:** the dataset metadata labels LGPL and links `lgpl-3.0.txt`; the extracted distribution license is explicitly **GNU LGPL2.1**, and the extracted source headers say **LGPL2.1 or any later version**. Retain those original notices and license verbatim. Do not describe the file notice as an LGPL3-only notice or substitute a different license text. This audit reports the actual artifacts, without making a new licensing determination.

## Material behavior actually found

The locations below refer to the retained original files, not the present engine.

1. **Active integration calls the basic function.** Original CPU calls `ConsRelationEP_fast` at lines2240/2407/2529 (Verlet/Pre/Cor); original GPU does so at509/697/891. GPU SFT alternatives at698/892 are commented out. After stripping comments, each inspected source has four basic occurrences (definition+three calls) and **one SFT occurrence (definition only)**. Thus these ordinary integrator paths do not dispatch to `ConsRelationEPsft_fast`. This is a precise finding about the two inspected integration files, not a claim that every external program in the archive was searched.

2. **The original SFT's stored history is deviatoric.** CPU SFT computes the plastic tensor from elastic compliance, removes its mean, and accumulates its deviatoric norm at2140-2141; GPU does the same at381-382. The original basic function also uses that history (CPU2006-2007/GPU247-248). For an ordinary unscaled radial increment, its mathematical limit is `delta_kappa=lambda/sqrt3`; float inverse/compliance arithmetic is still used.

3. **The SFT denominator separately contains a full-flow factor.** CPU2098/GPU339 use `dfdk*sqrt((2/3)*(3*DP_psi^2+.5))`, added with a plus to `G+9K*DP_phi*DP_psi` in the lambda denominator. The original therefore already has a mismatch between that full-flow denominator factor and its actual dev-history update. This is not evidence that the published source stored full-norm kappa.

4. **The original SFT helper has a coefficient/derivative fit mismatch.** `UpdateDPvars` is hardwired to the plus/“Medium”3-D fit at CPU1894-1910/GPU133-149; plane-strain and minus-fit alternatives are comments. `Updatedfdk` at CPU1911-1920/GPU150-159 contains the **plane-strain** derivative formula, without a DPCtes argument. The actual active basic callers independently select all three coefficient choices before calling the basic return, so do not misattribute this dormant SFT-helper issue to every basic3-D run.

5. **Stress/state arithmetic is float.** CPU uses `tsymatrix3f`, float stress locals/invariants/multiplier; GPU packs the material stress as `float2`. The original soil typedef at298-310 contains float phi/cohesion/softening/moduli fields, without hydromechanics, `MaterialReturn` or `psiDecay`. Neither material function implements a decaying-psi argument. This distribution is not a same-physics u-pl or stress-precision-only control for the current benchmarks.

6. **Tensile repair is post-return and does not update history again.** Both original functions form `G/sqrt(J2)` before the later tensile check, then apply the `I>DP_kc/DP_phi` mean correction and a deviatoric stress scale using the coefficients frozen at old kappa (basic CPU2011-2030; SFT2144-2163, corresponding GPU252-271/385-404). Kappa was accumulated before those repairs. This does not establish an exact apex flow/volume/history solution, and the early division does not protect a hydrostatic yielding trial.

## Differences from the current workspace

| Item | Published v1 | Current inspected CPU/GPU fast/SFT descendants |
|---|---|---|
| Basic/SFT dispatch | Basic active at the three step paths; SFT not selected there | Current `StrainSoftening` dispatch can select SFT, and an independent MR1 branch exists |
| Material stress | Float CPU tensor / GPU float2 | Double CPU tensor / GPU double2; material constants and saved kappa remain float |
| SFT coefficient helper | Plus3-D hardwired | Explicit DPCtes3 choices (`JSphCpu.cpp:3812`, GPU:135) |
| SFT derivative helper | Plane-strain derivative only | DPCtes-matched derivatives (`JSphCpu.cpp:3832`, GPU:155) |
| SFT stored kappa | Explicit compliance, mean removed, dev norm | `lambda*dkflowcoef` full-flow shortcut (`JSphCpu.cpp:4031/4058`, GPU:356/383) |
| SFT denominator | Plus full-flow term, coefficients at old kappa | Same plus/full-flow form retained in the current fast/SFT descendant |
| New-strength return | No endpoint new-kappa solve | Fast/SFT still freezes old coefficients for its final repair; MR1 is a separate endpoint/dev return |

**Required labeling correction for the completed22,680-row matrix:** `legacy_actual` is the actual **current workspace** `ConsRelationEPsft_fast`, not an unmodified Mendeley-v1 SFT and not the original active basic dispatch. Its full-history/sign/float-coefficient/no-psi-decay differences must not all be called integration error. The original basic, original defined-but-unselected SFT, current SFT descendant, and current MR1/general candidate are separate references. The raw source comparison changes that attribution; it does not invalidate the measured current-function results or justify rerunning them automatically.

The prior audit's observation that the *current* soft routine stores a full-flow history is correct for that inspected workspace. It must not be extended backwards into a claim that the published v1 code stored the same history. History of the intervening local edits is being reviewed separately; this note does not invent their origin or author.

## Protected artifacts and next use

Protected and unmodified: `src/source/JSphCpu.cpp`, `JSphGpuSimple_ker.cu`, `DualSphDef.h`, `FunSoilMaterial.h`; all material candidates/drivers/build receipts; the22,680-row inputs/native/reference results; formal C08 XML/BAT, runtime and r2 ZIP; all BI4/NBI4 and prior benchmark results. The only writes are the new selected-original folder and this note.

The original files are an external test reference with their notices. Any later original-function material test needs a separate deliberate test build and a clear published-v1 label; nothing here inserts them into the production target or replaces current source. Continue the already authorized unified basic/softening and apex/continuation work using the correctly identified references.
