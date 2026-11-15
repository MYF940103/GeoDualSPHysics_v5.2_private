# Private HG GPU implementation jobs: two independent profiles

AUTHOR ONLY: only this note and `tests/support/c08_h18_hg_gpu_jobs_r1.py` are new. No import, preparation, build, program/help, sanitizer, solver, reader/native decode, VTK, analysis, Git, hash scan or queue was executed by the author. Root separately admits each preparation and each run. No old source, program, PRE, config, result, worker or completion mechanism is changed.

| Profile | Program build | HG environment | Absolute completed-step cap | New updates / saved frames |
| --- | --- | --- | --- | --- |
| `off1` | `c08_h18_hg_gpu_Release_r1.build.json` | `C08_HG_H18` absent | 2000001 | 1 / 1 |
| `debug2` | `c08_h18_hg_gpu_Debug_r1.build.json` | `C08_HG_H18=1` | 2000002 | 2 / 2 |

There is no window profile, matrix loop, future job, reader, native adaptation, particle export, terminal queue or watcher in this script. A successful job remains pending independent native and HG-sidecar review; it does not establish physical accuracy, clumping repair, long-time stability, GPU/CPU bit equivalence or a formal release.

## Inputs and preparation

The original completed AS03 `c08_h18_as03_n255_r1` run, its native/review receipts and genuine generated seed triple are retained controls. Both profiles reuse the certified schema2 same-material Wendland psi0 10-second PRE, including actual stress, kappa, J, pore pressure and P0. The PRE is not recomputed. The original generated XML/BI4/Normals basename is preserved byte-for-byte; no GenCase or relabeling is performed. The original seventeen-key receiver profile is copied unchanged.

The generated physical XML stays Wendland H/dp1.8, fixed5us, AS.3/n2.55, AV.1, NoPen/bedroles/keepfalse and original material/dynamic-Darcy contract. Public `SoilHourglassXi` stays0: this private HG path is selected only by the explicitly owned environment. XML TimeMax10.9 and TimeOut.01 remain unchanged. The absolute `-nsteps` cap bounds the actual solver to one/two updates and forces the terminal PART. A copy of the retained Def XML is placed under the new test tag in `configs` as provenance/convenience; the actual solver consumes the unchanged generated triple in its fresh `outputs` directory.

For each profile, new paths use `c08_h18_hg_gpu_off1_r1` or `c08_h18_hg_gpu_debug2_r1`. The unique copied inputs, new `configs/*_Def.xml`, `configs/*.steps.csv`, prepare/start/call/run/status and independent solver-completion records are protected against reuse. Existing failed, partial or complete paths cause rejection. There is no automatic overwrite or retry.

The small plan starts from the certified PRE's actual scalar time and executes `clock += .000005` once per update. It records part index, global completed step, original zero-based saved step, actual time and dt. The first post-release clock is compared to the unchanged retained91-frame plan; the second short save is new and is not pretended to be an old nominal-time match. No `n*dt`, interpolation, shifted output frame or metadata rewrite is used. Exact saved clock/Step and all original native arrays remain for the separately selected native reader. Run.csv's six-decimal endpoint is only a rounded scheduling screen, explicitly not exact native-clock proof.

## Independent root admissions

Each profile has a separate `.root_prepare_admission.json` and `.root_run_admission.json` in `tests/logs`. Required fields are:

- `authorized=true`, exact `allowed_job`, `profile`, `phase` (`prepare` or `run`);
- frozen `execution_script`, `note`, and configuration-specific `source_build` stat entries;
- `root_thread_id` equal to both the actual root environment and `01a07683-bc64-7463-8db7-9ee6243967d8`;
- `automatic_native=false`, `automatic_next_job=false`; optional `terminal_queue` and `watcher` must be false;
- run admission additionally binds the exact passed `.prepare.json` via `preparation`.

Preparation validates the new passed private build and its three actual successful tool receipts:112 original objects plus private host and new CUDA=114, original physical CUDA objects retained, same frozen schema2 archive, three captured private sources, nine runtime files, operator `EnergyNormalizedAdjointLoadingOnly`, xi.1, policy schema1 and neighbor capacity128. The Debug snapshot macro must be present only for the Debug build. Required stats are checked at consumption and again before/after the bounded action; there is no new SHA or old-object scan.

## Actual process and terminal evidence

The existing `c08_h18_wend_matrix_r1.m.invoke` process helper is reused. It captures the actual Windows creation identity, executable, argv, parent, Popen wait exit and Win32 exit. Debug uses one `compute-sanitizer --tool memcheck --leak-check full --target-processes all --error-exitcode 99` tool with the actual solver supplied as the independently held target. Release launches its actual solver directly. The runner records its own PID/creation/exe/argv/parent and requires observed solver identity/argv and owner lineage, not merely a disappeared PID or console output. An already active exact private program prevents a duplicate launch.

Only the new HG environment variable is removed case-insensitively from the inherited environment. Debug sets it to1; OFF leaves it absent. This script does not infer HG execution from startup Configuration, generic labels, old RV telemetry, build success or a filename. HG policy, full adjoint, stage ordering, real Gamma/material-output matches, history, work and numerical bounds require the independently reviewed new HG sidecars after the solver job; all are explicitly pending here.

A genuine owned native solver exit0 plus original normal-completion and certified contract2 text writes `.solver_completed.json` **before** parsing Run.csv, checking frame coverage or reviewing sanitizer output. This immutable seal binds the actual call/start/program/source/PRE/input/plan and states coverage/HG/native review pending. Later summary, memcheck or other derived failure retains the completed solve; it is not permission to rerun it. The job itself passes only if actual tool and native target exits are both0, ownership is valid, no prior invocation failure exists, summary Steps and exact PART names/count match the profile, all exclusion counts are0, original AS/Wendland configuration matches, and Debug reports actual zero memcheck errors and zero leaked allocations. Normal exit alone is not this check, and the implementation check is not physical acceptance.

The last original console PART line, first genuine engine exception and surviving-process observations are retained on failure. An absent target handle is an unproved launch outcome, never invented exit0. No unsaved failure time/state is reconstructed. No process is stopped/restarted. The script never invokes postprocessing, another profile or any terminal queue, including on timeout/failure.

Root may later run each explicitly admitted action once:

    python support/c08_h18_hg_gpu_jobs_r1.py prepare --profile off1 --execution-authorized
    python support/c08_h18_hg_gpu_jobs_r1.py run --profile off1 --execution-authorized

Use `debug2` only under its own independent admissions. These commands are future instructions, not author execution or permission for an automatic sequence.
