# Shared H1.8 three-window driver (author only)

The only authored files are `tests/support/c08_h18_matrix_r1.py` and this note. Nothing is executed by authoring. Existing corrected source r2, the failed zero-PART r1 source, active source owner/program/input, runtime_r6, frozen native source, `c08_h18_profiles_r2.json`, and its complete scalar-time plans remain untouched. No physical source or project is changed or built. The profiles and plans are read-only dependencies, not a place to write a later winner.

`prepare --execution-authorized` may be reviewed and invoked while the source is running. It only writes three new psi0 Def XMLs, one self-locating matrix BAT, and `tests/configs/c08_h18_matrix_r1.jobs.json`, all with exclusive creation. The jobs are `c08_h18_a03_w09_r1`, `c08_h18_a05_w09_r1`, `c08_h18_a07_w09_r1`. They use epsilon .3/.5/.7 and exponent3.825, Cubic h/dp1.8, dp.04, DtIni/DtFixed5us, preload damping.03, TimeMax10.90/output.01, total-stress AS, AV.1, keep5, fixed-plane NoPen and original CompletedOnly. Release damping/Shepard are OFF. The one future source path is `tests/outputs/c08_h18_pre_r2/data/Part_1000.bi4`; preparing a path is not source qualification. Other template physics must match the retained r6 psi0 XML. No GenCase, solver, decoder, admission or queue is started by prepare.

The supplied plan `c08_h18_release_w09_r2.steps.csv` is used verbatim for every job: 180000 new updates, end2180000, 91 states, first post-save completed2000001. It includes the actual scalar source end9.999999999706008 and first save10.000004999706007. The driver does not calculate saves by n*dt, assign a fake10s source clock, remove that first sample, rewrite native headers, or inherit old90/300 counts. The shared native reader independently replays the five-column plan and actual saved clocks. The full301-state/three-material profile and possible n3/n5 followups are not launched by this driver.

`run --execution-authorized --notify` requires one root-written `tests/logs/c08_h18_matrix_r1.admission.json`. Its keys are:

- `passed=true`, `allowed_plan="c08_h18_matrix_r1"`, `profiles` = current profile stat Entry;
- `source_equilibrium_reviewed=true`, recording root's separate review of the actual new source as a bounded baseline (not claiming strict drained equilibrium);
- `source_run` = the actual passed corrected r2 run Entry;
- `source_native` = the actual full-source completion Entry, `source_native_call` = its real typed0 call Entry;
- `native_build` = the passed shared `c08_h18_native_r1.build.json` Entry;
- `native_auto_authorized` = an explicit bool; only true permits the already reviewed receiver reader;
- `root_thread_id="01a07683-bc64-7463-8db7-9ee6243967d8"` for notification, matching the actual inherited thread.

Source admission requires a genuinely completed2000000-step/1001-frame engine run, a full new law2 elastic PRE certificate, actual native full-source call and matching source/program/input/plan stats. A partial or native-only certificate cannot substitute for runtime success and root equilibrium review. The original unchanged runtime_r6 solver must match its bedkeep113-object Release build and installation receipt. The driver refuses an active GPU or C08 reader before physical/native work. It never waits for, interferes with, or launches alongside the current source.

Each new job owns its real GenCase and GPU process using the retained `invoke`/`base.owned` handle/creation/exe/argv/parent and Popen/Win32/solver exit logic. Its original global counts, no exclusions, source import clock, exactly one keep5/retire255 event, AS token/logs, and macro-off execution are checked before native work. All ordinary engine material/wall/domain/necessary-step guards remain active. A failed engine or unsafe output stops the matrix; no subsequent parameter is started, and the real first error, partials and last raw PART console line remain. Run receipts are sealed before decoder calls; a decoder error cannot relabel or rerun a completed physical calculation.

With explicit native authorization, one fresh native directory per job is decoded using the shared CLI:

```text
C08H18Native_win64.exe --receiver window psi0 DATA NEW_PRE ORIGINAL_PLAN ACTUAL_XML_PROFILE_CSV FRESHOUT
```

The 14-key profile CSV is exported from that job's actual generated XML: group, epsilon/exponent, DPCtes, phi/phi_r/n_phi, coh/coh_r/n_coh, dlt, DilationDecay, SoilTriggerFos and fresh_trigger_active=0. No public solver parameter or23rd array is added. One unique call uses the reviewed six-utility reader build, keeps its real stage `c08_h18_native_r1.receiver`, and checks the existing all22/6805=5000soil+1805fixed, P0, J/n/rho/k/cache ledger, kappa, free-seepage, clock/signed and plane budgets/counts plus actual AS/keep/CompletedOnly headers. These are implementation/admission checks, not a new physical tolerance. No 5Pa model-equivalence gate, extra force, half chain, VTK or resampling is introduced.

Each native success is sealed in `logs/JOB.native_r1.json`, bound to the already immutable `logs/JOB.run.json`, actual native call, shared reader build, original plan and profile. Only after a job's original safety and native checks pass does the next job start. If native_auto_authorized=false, the first completed raw job is retained and the driver halts pending native review; it cannot silently admit the second. Existing output, owner or partial native data refuse replay rather than being reused or overwritten.

After all three run/native checks pass, the matrix emits one terminal record and, if requested, one45s same-thread queue. A failure or native hold also terminates once and retains the evidence. Timeout has uncertain delivery and is never resent, rearmed or watched. Root then performs physical comparison/selection from the actual91-state results: pressure extrema/pulses/RMS, near-pair/NN distributions and gaps, kappa/J, displacement/settlement/front, velocity and early arrest. Less motion or a lower pressure peak alone is not an improvement criterion. This driver neither selects a winner nor runs later exponents, formal3s or other psi groups; the user's continuation is carried by the one terminal root notification.

Intended later commands, each only after root full-read, are:

```text
python -X utf8 -B tests/support/c08_h18_matrix_r1.py prepare --execution-authorized
python -X utf8 -B tests/support/c08_h18_matrix_r1.py run --execution-authorized --notify
```

Author checks are AST/text only; no program/help/imported owner, source build, solver, GenCase, decoder, native payload analysis, VTK, queue or Git operation has been run.
