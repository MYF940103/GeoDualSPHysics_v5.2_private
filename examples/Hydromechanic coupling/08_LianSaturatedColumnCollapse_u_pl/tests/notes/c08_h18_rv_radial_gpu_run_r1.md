# C08 H1.8 radial GPU profiles: owned runner r1

Author-only new runner: `tests/support/c08_h18_rv_radial_gpu_run_r1.py` and this note. No prepare/build/help/solver/native/VTK/Git or queue was executed by the author. The previous vector runner and all old success/failure evidence remain untouched. Root independently reads these assets and admits each prepare/run phase; only the later separate implementation review can justify a new physical window. A window profile existing in this script is not its admission.

## Closed profiles and source reuse

Profiles are exactly:

- `off1`: `c08_h18_rv_radial_off1_GPU_r1`, new Release program, new environment variable absent, one new update/completed2000001/one frame.
- `debug2`: `c08_h18_rv_radial_debug2_GPU_r1`, new Debug program under actual compute-sanitizer memcheck, variable explicitly1, two new updates/completed2000001 and2000002/two frames.
- `window`: `c08_h18_rv_radial_window_GPU_r1`, new Release program, variable1,180000 new updates/completed2180000/91 original saves; **not yet admitted**.

New private builds are `logs/c08_h18_rv_radial_gpu_{Debug,Release}_r1.build.json`:112 original physics objects plus genuinely recompiled host/new CU, final `--fmad=false` only on the new CU, schema3/radial operator. The build receipt and bound source capture must agree with the certified original schema2 source archive. Exact fixture_columns6 is checked from the actual bound capture, not invented in an already completed build receipt. Main87/manufactured57 and the new operator/environment remain explicit guards.

All profiles copy the existing passed `c08_h18_as03_n255_r1` generated XML/BI4/normal triple and its original17-key native profile byte-for-byte, preserving the generated basename. No GenCase, new PRE or source-material initialization is run. The original certified Wendland same-material schema2 PRE is reused with sigma/J/p/P0/kappa histories. Settings stay WendlandH1.8/dp.04/5us,AS total.3/n2.55,AV.1,keepfalse/bedroles,255 retired/6805 active, original fixed-plane NoPen/CompletedOnly/free-seepage, current variable-k law and original material. Same-stage Darcy reaction remains not closed.

For short profiles, only new `configs/<tag>.steps.csv` is written, with scalar `clock+=5e-6` from the PRE's actual saved clock. The91-frame window keeps the original `c08_h18_release_w09_r2.steps.csv` untouched. No n*dt clock substitution, nominal-time interpolation or rewritten native metadata occurs. The first receiver save is after one actual update, not a fabricated exact initial receiver state. The native reader remains the existing `C08H18RvNativeR1` with its own independent off1/debug2/window contracts; this runner never invokes it.

## Exact new sidecars and certificates

Only `C08_RV_RADIAL_H18=1` enables the new operator; the child environment removes an inherited value first. OFF leaves it absent. Four sidecars are expected only when ON:

- `C08H18RadialResidualPolicy.json`, schema3/operator compression_only_radial_residual_limiter/main_schema C08H18Radial87-r1.
- `C08H18RadialResidual.csv`, exact87 columns and2 rows per native save, ordered Pre thenCor.
- `C08H18RadialManufactured.csv`, exact57 columns andfive genuine first-force scratch rows, modes1..5.
- `C08H18RadialLimiterFixtures.csv`, exact6 columns andeight actual device limiter fixtures.

All87/57/6 header literals come from the frozen new header/host, not old66/vector-form semantics. The policy explicitly records alpha.1, original source-clock, bedroles/PRE scope,5 manufactures/eight fixtures, directed half-count policy, no old vector form/contraction certificate, no BI4/native22 schema change, and hypothetical manufactured commit fields. JSON types are checked as well as values. `kernel_h_sph_float` is the numeric `struct.unpack('<f',m.f32(.072))[0]`; `m.f32` returns packed bytes, so it must not be compared directly with a JSON number.

Actual saved rows require all original force/save clocks, phases and counts,5000 validated soil, committed1/error0/CUDA0. Every phase's actual calls/commits and both global Pre/Cor counts must equal the real completed step minus2000000. For Debug2 this is4 main rows,5 MFG and8 fixtures; for the future window182/5/8 with final calls/commits180000 per phase. The fresh gamma/LS/normalization, power/net/central+reduction torque, exchange, frozen Euler and hypothetical/actual float-commit budgets retain their source definitions. The runner rechecks original exported inequalities and14 per-phase running ratios<=1, monotone maxima and current-stage<=running maximum. It never applies old work+2form or claims to reconstruct unobserved stage histories from sparse saves.

Manufactured fields `committed_*` are **hypothetical float-Ace candidates**, so they are not zeroed or discarded. The actual manufactured `committed` flag must be0, with certificates/manufactured flags1/error0/CUDA0, first-force original clock and original affine-null q/force budgets. These five calls never add physical phase calls/commits. Fixtures check the actual device limiter's eight closed sign/cap cases and expected double bits; their power and inactive force-zero convention do not normalize any native signed clock or dterror.

This is a runtime/ownership and sidecar export check. Full independent numerical/native implementation review remains pending. The raw22/P0/J/kappa/FS/ledger/plane/clock/signed guards belong to the later unchanged native reader and separate reviewer; sidecar success or default-OFF file absence cannot replace them. OFF file absence is not allocation telemetry: source scope plus later actual one-frame native byte comparison is required. Debug success/memcheck is not Release bit truth. Source budgets formed from actual neighbors are not reconstructed by this runner from saved summary rows.

## Ownership, sealing and independent admissions

Prepare/run each require a fresh exact root admission file bound to this script/note stat, profile/tag/phase and the current root thread. Paths follow the original `.root_prepare_admission.json`/`.root_run_admission.json` convention. A future window additionally requires separately passed implementation gates, `single_window_only`, one terminal queue and no automatic next action. Nothing runs because an earlier profile passed.

The direct owner records its actual creation/executable/argv/parent and freezes program/build/source/PRE/input/plan/runtime stats. All tool argv are strings. The real process wrapper records child/target creation, executable/argv/parent plus Popen and native Win32 handle exits. Debug target is the actual private program under the sanitizer; both tool and target must exit0 and actual memcheck logs must show0 errors and0 leaked bytes/allocations. No duplicate exact private executable may already be running.

Normal solver completion is sealed as soon as genuine exit0/Run.out normal schema2 completion is observed, **before** summary/coverage/sidecar/memcheck checks. A subsequent postcheck failure preserves `solver_completed=true`; it never authorizes another solve. Original first failure, actual exits, last raw saved console line, partial outputs and surviving-owned-process observations remain. No unsaved failure time/state is reconstructed, old output overwritten, threshold relaxed, retry/rearm or owner restart performed.

The future window's direct owner is its sole completion mechanism: one current-root Codex queue attempt with45s timeout, only after the original final run/status is sealed. Timeout may already have delivered; no resend, watcher or connectivity self-test exists. OFF1/Debug2 do not queue. Terminal messages require independent native/physical review and cannot admit another profile, other psi, PRE, half, full run or acceptance.

Canonical run fields retain `source_build/source_capture/source_archive/program/source_pre_file/source_native/planned_steps/input_xml/actual_call/Run_out/Run_csv`; ON adds `rv_policy/rv_sidecar/rv_manufactured/rv_fixtures`. Debug's `memcheck_actual_call` aliases the genuine same actual sanitizer call; no fabricated secondary invocation. Every native execution remains separately root-admitted and unique.

Root-only commands after independent admissions, not executed by author:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_radial_gpu_run_r1.py prepare --profile off1 --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_radial_gpu_run_r1.py run --profile off1 --execution-authorized
```

Debug2 uses the same two commands with `--profile debug2` and its independent admissions. No window command is a current authorization.
