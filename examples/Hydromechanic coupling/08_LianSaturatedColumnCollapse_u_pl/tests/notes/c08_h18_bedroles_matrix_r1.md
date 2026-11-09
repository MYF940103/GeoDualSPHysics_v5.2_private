# Bed-last shared H1.8 matrix adapter (author only)

Only this note and `tests/support/c08_h18_bedroles_matrix_r1.py` are authored. They derive the reviewed/prepared but never physically launched `c08_h18_matrix_r1.py`; all its files, configs and manifest remain unchanged. The new corrected bed-role PRE is an active independent job and is not read, modified, stopped or reused before qualification by this authoring. No descriptor, config, admission, program or output is generated here.

The new future descriptor is `tests/configs/c08_h18_bedroles_profiles_r1.json`, written by root separately. Common H/dt/material/AS/count fields retain the old H1.8 values. Its explicit differences are source_job=`c08_h18_bedroles_pre_r1`, geometry_profile=`bedroles`, keep_bed_overlap=false and source_registry `{fixed:2060,soil:5000,release_begin:1805,release_count:255,retained_fixed:1805}`. `schedule_profiles` is the original `c08_h18_profiles_r2.json` stat Entry. Its original source/window/formal plans are reused by their original paths, not copied, rewritten or truncated. The descriptor's preload_plan and receiver table must equal that schedule profile.

The new native build intentionally binds the old numeric schedule descriptor, not its obsolete source_job identity. The context therefore requires `native_build.profiles == descriptor.schedule_profiles`, stat-binds that Entry, and requires the actual new build geometry_profile=bedroles and profile_source_job_used_as_runtime_identity=false. This preserves exact schedule proof without misidentifying the new source. Native and physical program identity are separate; no solver build or physical source change is involved.

New job tags are `c08_h18_bed_a03_w09_r1`, `c08_h18_bed_a05_w09_r1`, `c08_h18_bed_a07_w09_r1`. Each retains psi0, epsilon .3/.5/.7, exponent3.825, Cubic h/dp1.8, dp.04,5us, preload damping.03, TimeMax10.90, output.01, total-AS, AV.1, fixed-plane NoPen and original CompletedOnly. Release Shepard/damping remain OFF. The shared .90 plan is still180000 updates/end2180000/91 frames, first post completed2000001. No new timing rule, threshold, model, half run or automatic formal/other-psi job is added.

Preparation is a later separate action. It will create three new Def XMLs, one self-locating matrix BAT, and `c08_h18_bedroles_matrix_r1.jobs.json`, all exclusively. Expected geometry reorders the r6 template's paired setmkbound/drawbox commands from left/bed/right to left/right/bed and sets keep_bed_overlap=false. The right-face comment is corrected to normal255 retirement; it does not describe an old keep5 override. The resulting source and target share the new roles. The old original7060/2060 registry and soil IDs2060..7059 remain, but active fixed IDs after release are now contiguous0..1804 and retired IDs1805..2059, rather than old0..1799 plus five retained scattered IDs.

Exact adaptation categories against the old matrix are:

- label/path replacements: matrix TAG twice, descriptor path once, source label four times, native stage/path stem five times, native executable once, three job tags once each;
- profiles/context: explicit bedroles registry, new actual source, new full-source stage/registry, old shared schedule Entry instead of equality with the new descriptor; no qualification is inferred from the schedule source_job;
- expected XML: bed-last command order, keepfalse and explanatory comment; physical parameter values stay the same;
- prepared manifest: records the new geometry/registry alongside unchanged per-job plan/end/count;
- Run.out: requires the actual validated `[1805,2060),count255` source face and one normal255 release; it rejects a KeepBedOverlap release marker instead of requiring that marker;
- native: new source/receiver/metadata stages, explicit contiguous retained/retired ranges and keepfalse replace old kept-ID checks; all22/ledger/P0/kappa/FS/signed/clock/plane numerical budgets and coverage formulas are unchanged;
- one terminal message names the new roles and rejects old keep5/260 profiles. Queue mechanics remain unchanged.

The new shared reader is `tests/outputs/c08_h18_bedroles_native_r1_build/C08H18BedrolesNative_win64.exe`, with build receipt `logs/c08_h18_bedroles_native_r1.build.json`. Its unchanged CLI is

```text
C08H18BedrolesNative_win64.exe --receiver window psi0 DATA NEW_BEDROLE_PRE ORIGINAL_WINDOW_PLAN ACTUAL_XML_PROFILE_CSV FRESHOUT
```

Its real completion stage is `c08_h18_bedroles_native_r1.receiver`; metadata remains in `bedkeep_metadata.json` with stage `c08_h18_bedroles_native_r1.metadata`, geometry_profile=bedroles, keepfalse, original_target_begin1805/count255 and retained_fixed_ID_begin0/count1805. This historical leaf name does not assert keep5. The source certificate stage is `c08_h18_bedroles_native_r1.source`. No old kept-ID field or old KeepBedOverlap metadata is required. The reader itself rejects those old policy headers.

Run remains behind one root admission, actual successful new source run, full new source native call/completion, explicit source_equilibrium_reviewed and native_auto_authorized. The root-written admission path is `logs/c08_h18_bedroles_matrix_r1.admission.json`; other key meanings match the old matrix note. Its allowed_plan and profiles Entry must name this new matrix/descriptor, never the failed old source. One job's real engine safety and unique native checks must pass before the next starts. With native_auto_authorized=false, only the first raw job completes and the driver halts for review. Any failure retains evidence and stops the remaining jobs; nothing is retried or overwritten.

The actual ownership/run functions, strict AS CSV parser, 14-key actual-XML material profile, all original numeric budgets, process checks, wait/capture behavior and once-only45s same-thread notification are reused. After all three pass, root receives one terminal notification for physical comparison and selection. No winner is chosen by this adapter; early arrest, pressure changes and particle proximity require joint review.

Future commands, only after root full-read and separately authorized prepare/run, are:

```text
python -X utf8 -B tests/support/c08_h18_bedroles_matrix_r1.py prepare --execution-authorized
python -X utf8 -B tests/support/c08_h18_bedroles_matrix_r1.py run --execution-authorized --notify
```

Only AST/text/static XML structure checks are performed by authoring. There is no source build, config generation, GenCase, solver, decoder, payload analysis, VTK, notification, admission or Git action.
