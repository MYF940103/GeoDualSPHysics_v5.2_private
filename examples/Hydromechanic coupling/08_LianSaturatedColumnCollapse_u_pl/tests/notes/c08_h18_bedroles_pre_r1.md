# Bed-last H1.8 fresh PRE owner (author only)

This is a mechanical derivative of the frozen `c08_h18_pre_r2.py`; it does not modify or restart r2 or its failed partials. The new owner is `tests/support/c08_h18_bedroles_pre_r1.py`, the root-prepared input is `tests/configs/c08_h18_bedroles_pre_r1_Def.xml`, and fresh physical output is `tests/outputs/c08_h18_bedroles_pre_r1`. The separate existing `c08_h18_bedroles_geometry_r1` qualification directory is not written or used as the solver output.

Only five source anchors differ from r2: (1) TAG, which derives the new NOTE/config/output/log/admission paths; (2) expected geometry command order left/bed/right becomes left/right/bed; (3) the input-mismatch diagnostic describes that order and the actual unchanged TimeMax13; (4) normal completion additionally requires the real validated right-wall range `[1805,2060), count=255`; (5) the one terminal message states the new source registry and rejects old keep5/260-derived readers. Reversing these five replacements reconstructs the original r2 owner bytes exactly. The root's existing Def was compared in memory with the declared template/geometry derivative and matched; no GenCase or owner function was executed for that comparison.

Root's single geometry qualification found fixed MK0 begin0/count255, MK1 begin255/count1550, MK2 begin1805/count255, and fluid2060/count5000: total7060, fixed2060, soil5000. Particle coordinates are retained by the geometry change, while shallow right/bottom overlap roles are assigned to bed NoSlip/+Z from initialization. This removes the prior asymmetric side-versus-bed ownership; it does not prove the old role was the failure cause or promise an elastic10s result. The new source and future receiver must share this geometry. Future normal retirement is255 and keep_bed_overlap=false; old retained-bed IDs, source contracts and reader expectations cannot be relabeled or mixed into this case.

All runtime/physics/safety settings remain r2: original unchanged runtime_r6/bedkeep Release program, Cubic h/dp1.8 and floatH=.072, dp.04, DtIni/DtFixed5us, DtMin1e-8, damping.03, Shepard40, strict elastic_source, source AS/NoPen/keepbed OFF, constant event10, TimeMax13 and `-nsteps:2000000`. TimeMax remains greater than the event so the original configuration contract is legal; the explicit step cap stops at complete PRE before release. Expected output is1001 states including initial Part0000. Actual scalar clock and nonuniform individual save steps are retained, never replaced by n*dt or fake10s.

The same actual handle/creation/exe/argv/parent ownership, original engine guards, Popen/Win32/solver exit capture, source build/runtime/stat closure, no-overwrite/failure preservation and separate solver_completed/postprocess_completed records are reused. Only after genuine normal source completion are Part0/100/500/1000 exported as separate Fluid5000 and Bound2060 series. Native certification and equilibrium remain pending; no reader, receiver, other psi, source build, retry or next solver is automatic. A postprocessing failure preserves completed BI4 and never triggers a new source run.

Root writes `tests/logs/c08_h18_bedroles_pre_r1.admission.json` after full-read. Required keys remain the r2 schema with only allowed_job changed: passed=true, allowed_job=`c08_h18_bedroles_pre_r1`, hdp1.8, fixed_dt_s0.000005, damping_coefficient0.03, planned_global_end2000000, expected_saved_frames1001. For --notify, the actual inherited thread and admission root_thread_id must match `01a07683-bc64-7463-8db7-9ee6243967d8`.

The future single root-authorized invocation is:

```text
python -X utf8 -B tests/support/c08_h18_bedroles_pre_r1.py --execution-authorized --notify
```

One terminal45s same-thread queue is attempted only after an actual solver call exists. It is sealed after the original run receipt, never resent after timeout, and has no child watcher. This authoring performed only AST, exact inverse text and pure in-memory XML checks; no configuration, geometry result, prior source, program, build, native payload or admission was changed, and no program/queue was launched.
