# One same-material plastic H1.8 source per explicit invocation

Author-only shared owner: `support/c08_h18_plastic_pre_r1.py`. No preparation,
GenCase, solver, native decode, export, build or notification was executed during
authoring. Existing source attempts, root XML, production source, runtime_r6,
real PREs and outputs are unchanged. This owner does not select AS or launch
receivers/other groups. Root first reviews psi0; availability of the other
choices is not their physical admission.

Group material triples are fixed and match the intended same-material receiver:

| group | peak cohesion Pa | initial psi degrees | DilationDecay |
|---|---:|---:|---:|
| psi0 | 5000 | 0 | 0 |
| psi2p5 | 5000 | 2.5 | .2 |
| psim5 | 7500 | -5 | .2 |

`prepare --group psi0 --execution-authorized` writes only a new group Def XML,
thin self-directory BAT and prepare receipt. The tag is
`c08_h18_plastic_<group>_pre_r1`; XML/BAT are in tests/configs, result files in
tests/logs and later solver output in tests/outputs/TAG. The original root
shared_preload_r3_Def template changes only Cubic hdp1.8, DtIni/DtFixed5us,
damping.03, bed-last mainlist priority (left/right/bed), elastic_source=false,
explicit keep_bed_overlap=false and the group's coh/dlt/DilationDecay. TimeMax
stays13, TimeOut.01, release event10, AS/NoPenOFF and Shepard40 unchanged. All
other material, pore, boundary, time-step and exclusion parameters are checked
against the original template; comments may differ. There is no initial stress
assignment, kappa reset, statefile import, plastic-flow override or relaxed
return status. GenCase later verifies fixed roles0:0/255,1:255/1550,
2:1805/255 and fluid2060/5000, total7060. The five shallow right corner samples
are bed NoSlip/+Z from initialization, not a later keep5 override.

The actual program is the already passed new
`tests/outputs/c08_preload_schema2_Release_r1/DualSPHysics5.2_GEO_win64.exe`.
Its build receipt, actual MSBuild Popen/Win32 exits, full_source capture/archive,
program and copied9 runtime destination Entries are verified. GenCase/PartVTK
and DLL/config dependencies come from that same directory. This uses no old
runtime_r6 executable identity or assumed113-object closure. Pure signature,
selected frame numbers and PartVTK variable-list constants are reused from the
frozen bedroles owner, whose file is also stat-bound; its old run function is
never called.

`run --group psi0 --execution-authorized --notify` requires root's independent
`logs/TAG.admission.json`. Required keys are:

- `passed:true`, `allowed_job:TAG`, `group`, `hdp:1.8`, `fixed_dt_s:.000005`,
  `damping_coefficient:.03`, `planned_global_end:2000000`,
  `expected_saved_frames:1001`;
- `material:{coh:5000,dlt:0,DilationDecay:0}` for psi0 (table gives other groups);
- actual stat Entries `program`, `source_build`, `source_capture`,
  `source_archive`, `input_xml` (prepared Def), `preparation` (prepare receipt);
- `root_thread_id:"01a07683-bc64-7463-8db7-9ee6243967d8"` when notify is requested.

The author writes no admission and pre-fills no passed physical qualification.
Run refuses existing outputs, claims, calls, or partial evidence. Only its
prepare receipt and root admission may exist beforehand. It checks no GPU
solver is active, runs one GenCase, then uses existing base.owned real handles
for program/argv/creation/parent and actual Popen/Win32/solver exits. Original
engine finite/cell/material/necessary-step guards remain authoritative. Source
false permits the existing CommitAllowed Smooth/Apex/TensionRepair returns;
failure statuses still fail. Complete stress/kappa/J/p history evolves normally.

The mandatory `-nsteps:2000000` stops before release even though TimeMax is13.
It does not use n*dt as a replacement for the scalar engine clock. A successful
summary must report2M,1001 contiguous saves,7060/2060/5000 and no exclusions,
with no state import or release. At5us actual accumulated source time can be
slightly below10; frame labels retain their actual data, not corrected metadata.
After genuine solver completion only parts0/100/500/1000 are exported with
separate PartFluid5000 and PartBound2060 VTK (8 explicit calls). These correspond
to nominal0/1/5/10s; positions are the utility's float VTK output. The owner
neither decodes arrays nor claims schema2 certification, kappa0, source yield
admissibility or equilibrium. An independent same-material schema2 reader and
physical source review must decide those from actual outputs.

Solver completion and export completion are separate fields. If export fails,
completed BI4 remain; repair derived outputs without rerunning physics. If the
engine fails, first exception lines, actual exits, original last console and
partials remain, with no invented unsaved failure time. When explicitly enabled
from the admitted actual root thread, the terminal queue is attempted once
with45s timeout, including failures; uncertain delivery is never resent and no
watcher/restart is created. The BAT's notify option obeys the same real-thread
restriction. No native, receiver, new PRE, other-group or parameter sequence is
automatically started. Success remains a source run pending native/equilibrium
review, not physical acceptance or general restart support.
