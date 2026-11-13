# One explicitly admitted Wendland H1.8 psi0 preload

Authoring only: this note and `support/c08_h18_wend_pre_r1.py` are new. The
owner is a local, explicit copy of frozen `c08_h18_plastic_pre_r1.py`; old
source, code, input, PRE, native/VTK, plans and receipts remain unchanged.
No prepare, build, GenCase, program/help, solver, native, export, Git or queue
has been run during authoring. Root must review the causal/spectral evidence
and these files before deciding whether to admit this candidate.

The only physical change versus that psi0 H1.8 source is **Kernel1 Cubic to
Kernel2 Wendland**. Both use support radius2H, with H=.072 and dp=.04, but
weights and gradients change; this is not an h-only, same-operator or
no-feedback comparison. Pairing/penetration reduction is a hypothesis to
test, not a result. Artificial stress and NoPen remain off during preload.

The copy changes exclusive names, restricts the CLI to psi0, adds explicit
Kernel2 XML/admission/runtime checks and a kernel label to receipts. It binds
the old frozen author file for provenance without executing that file's
functions. New `Path(__file__)` and NOTE Entries are the actual new wrapper
and this actual note in prepare, root-admission consumption and run contexts;
the original owner is not relabelled as the new caller. Pure signature,
selected-frame numbers and PartVTK variable constants are still explicitly
reused from the frozen bedroles helper, whose file is also stat-bound.

Unchanged physical settings: fresh zero-effective-stress actual gravity
loading, same-material plastic schema2/law2, psi0/cp5000/cr1000/ncoh5, phi25,
nu.33/E20MPa, fixed5us, damping.03, Shepard40, Model1/Ck2, left/right/bed draw
priority, mixed wall-slip and all initial/material/history/necessary-step
policies. No sigma field assignment or kappa/J/p reset is introduced. The
right wall has original IDs1805..2059; keep_bed_overlap=false. Initial fixed
registry is MK0[0,255), MK1[255,1805), MK2[1805,2060), plus soil2060..7059.
No density, particle-loss, material or stability threshold is relaxed.

An output-bookkeeping correction in this new copy keeps `solver_completed`
false until actual2M/1001/no-loss output checks pass. A zero native exit is
recorded separately as `solver_returned_zero:true`. This prevents a returned
zero caused by the engine's ParticlesOUT interruption from being called a
completed source. `[Simulation INTERRUPTED` explicitly rejects. The old
failed run JSON is not rewritten. Solver0 with valid complete output but a
later VTK failure still retains `solver_completed:true` and requires only
derived-output repair, never another physical run.

Commands, each independently invoked by root:

```text
python -X utf8 -B support/c08_h18_wend_pre_r1.py prepare --group psi0 --execution-authorized
python -X utf8 -B support/c08_h18_wend_pre_r1.py run --group psi0 --execution-authorized --notify
```

`prepare` writes only new tests/configs XML/BAT and a prepare receipt. It has
0GenCase/0solver/0reader. Tag is `c08_h18_wend_psi0_pre_r1`; later raw data go
under `tests/outputs/TAG`. Config input is derived from the retained root
shared_preload_r3 template using the exact prior H1.8/bed-last/plastic changes
and Kernel2. Hdp/Kernel comments disclose the different kernel; DtFixed's
comment now correctly says5us. TimeMax13 and event10 stay; `-nsteps:2000000`
stops the source before release. OutputTime stays.01s with1001 planned saves;
actual scalar+=dt times are retained, not replaced by n*dt.

The program is the already built schema2 Release:
`tests/outputs/c08_preload_schema2_Release_r1/DualSPHysics5.2_GEO_win64.exe`.
Its actual build receipt, MSBuild exits, full source capture/archive, program
and copied9 runtime Entries are checked. GenCase/PartVTK/DLLs come from that
same directory. No new production source/build or old runtime_r6 identity is
claimed. Canonical/current server programs are untouched.

`run` needs root's fresh `logs/TAG.admission.json`, with:

```text
passed:true, allowed_job:TAG, group:"psi0", kernel:2, kernel_name:"Wendland",
hdp:1.8, fixed_dt_s:.000005, damping_coefficient:.03,
planned_global_end:2000000, expected_saved_frames:1001,
material:{coh:5000,dlt:0,DilationDecay:0},
program, source_build, source_capture, source_archive, input_xml, preparation,
root_thread_id:"01a07683-bc64-7463-8db7-9ee6243967d8" when notify is requested.
```

The six Entries are actual file stat dictionaries; input_xml is the prepared
Def, preparation the new prepare receipt. Root supplies any physical decision
and implementation prerequisites separately; this author fills no passed
physical admission. Run refuses existing output/call/claim/partial evidence,
checks no GPU solver is active, performs one GenCase and one solver, and uses
the existing true Popen/Win32/child identity handles. It checks generated
geometry, material, H/dp and parameters; all counters/counts are observed.
No active solver is stopped or replaced.

Only an actually complete no-loss2M/1001 source gets the eight selected
nominal0/1/5/10s separate Fluid5000/Bound2060 VTK exports. Raw BI4 stay intact;
VTK positions are float utility output, not the native precision reference.
The owner never invokes a native reader. Completed output is not schema2
qualification or equilibrium. Existing closed Cubic readers cannot silently
stand in for a reviewed Wendland source/target contract; independent actual
kernel/input binding and native/physical review remain necessary.

There is one direct owner's terminal same-thread queue attempt with45s
timeout, never a watcher/rearm/retry. Uncertain delivery is never resent.
No automatic decoder, half/smoke, receiver, another psi, parameter sequence,
new PRE or subsequent solver is launched. Failure preserves the first real
exception, actual exits and last original saved console line without invented
unsaved failure time. All previous failures remain failed and protected.
