# MaterialReturn=1 gravity-container cold startup

This stage extends the existing narrow material policy to the already admitted fixed gravity container. The four production files are `src/source/JSph.h`, `JSph.cpp`, `JSphCpu.cpp`, and `JSphGpu.cpp`. The shared predicate was renamed to `IsDynamicPorePlasticConfig`; MaterialReturn=1 may use the existing container or the original periodic scope. No equation, array, kernel, or integration-stage ordering changed. The preceding verified checkpoint was `8edd7366ed429d6d7d2a794e46b000592946de79`.

## Closed observations

- The gravity CPU build passed with 86 objects (85 non-main); the GPU host-delta build passed with the separately verified complete 111-object closure. Their original build receipts retain their actual source archives and size/mtime observations.
- CPU and GPU each executed one fresh 128-update startup and one native read. Each saved 5 frames, 7060 original IDs (5000 soil + 2060 fixed), and all 22 typed arrays through Step127 at 0.00048828125 s, with dt=2^-18 s and no excluded particles. GPU's single physical run used memcheck: tool and solver exited 0 with zero errors/leaks.
- Both native receipts passed the original ledger/cache, fixed-marker, free-seepage metadata/nonempty FS sign, necessary signed-clock, initial/fixed κ=0, and soil finite/nondecreasing κ guards. There are 25000 soil ledger/cache observations, 10300 fixed-marker observations, 20000 κ comparisons, and 100 FS2/3 soil IDs per frame. All observed soil κ remain 0.
- The unique offline pair analysis exited 0. It preserves every exported field and compares full typed22/clock files with the retained same-backend controls. New CPU versus the retained **default MR0** CPU, and new GPU versus the retained **explicit MR1** GPU, each have 0 changed bytes/bits in those two complete files. These are distinct control identities.
- The four-panel PNG was viewed and its metrics independently checked against the closed typed exports/native histories. The original analysis receipt's pending-visual-QA flag is preserved; the separate visual-QA receipt closes that review.

Across the five actual saved times, the soil CPU/GPU maximum descriptive differences are:

| Quantity | Maximum difference |
|---|---:|
| pressure RMS | 0.000422109473 Pa |
| pressure maximum | 0.00390625 Pa |
| material XYZ displacement maximum | 1.21797472e-12 m |
| total-stress Frobenius RMS | 0.000755396911 Pa |
| J maximum | 1.27180488e-11 |
| porosity maximum | 8.26683166e-12 |
| mixture density maximum | 1.36401468e-8 kg/m³ |
| conductivity / κ | 0 / 0 |

At the endpoint, CPU/GPU soil pressure means are 1668.58332961/1668.58327281 Pa, pressure RMS values 3495.00803748/3495.00798715 Pa, and material displacement RMS values 0.00109036247743/0.00109036248500 mm. Both have maximum displacement 0.00116944316253 mm. Effective-stress Frobenius RMS is 50.13878296/50.13878835 Pa; the largest |J−1| is about 7.2602543e-6.

## Scope and provenance

This is a cold, initially unstressed fixed-wall startup with constant conductivity and the existing free-seepage policy. It is not a gravity-equilibrium, nonzero-plastic-wall, preload, wall-release, localization, or collapse validation. Native CODE/Ace/reaction are absent; no wall-force or instantaneous acceleration claim is inferred. The total velocity divergence continues to drive the single J update, with no extra plastic-volume source. No 5 Pa cross-model gate or fitted reference is introduced. Initial cross-backend FSNormal/PosDiv differences remain preserved; all22 cross-backend bit identity is not claimed.

After the physical runs, native reads, and pair analysis were sealed, the root agent moved the same MaterialReturn/DilationDecay read/validation statements adjacent to strength-softening input handling in `InitSoilParameters`. XML paths, values, defaults, activation flags, and equations are unchanged. The subsequent **CPU-only** default Debug build (`upl_config_cleanup_DebugCPU_r1`) passed with 86/85 objects, typed exit0, and unchanged protected/source size/mtime observations. Its source archive is later than the gravity-run archives; historical bindings were not rewritten. No GPU build or numerical rerun was required or performed for that cosmetic move.

## Evidence

- `logs/upl_material_gravity_{DebugCPU,Debug}_r1.build.json`
- `logs/upl_material_gravity_{CPU,GPU}_r1.check.json` and matching original call/start/input records
- `logs/upl_material_gravity_{CPU,GPU}_r1_native_r1.check.json` and matching native calls
- `logs/upl_material_gravity_pair_r1.call.json`
- `figures/upl_material_gravity_pair_r1.png`, `_metrics.csv`, `.check.json`, and `.visual_qa.json`
- `logs/upl_config_cleanup_DebugCPU_r1.build.json` and its source/start/call records

All recorded inputs, programs, and exports were observed through size/mtime; no SHA sweep, solver replay, or decoder replay was performed during this review. Physical acceptance remains false. The next activity is preload/initial-state planning, not an authorized longer run.
