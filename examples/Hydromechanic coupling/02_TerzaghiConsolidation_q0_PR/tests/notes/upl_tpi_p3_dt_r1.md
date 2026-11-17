# P3 five-phase host timestep audit r1

Author-only new `tests/support/upl_tpi_p3_dt_r1.h`, cloned locally from the final P2 header. The actual P2 source copy `outputs/upl_tpi_p2_CPU_r1_source/upl_tpi_m0_dt_r2.h` was read and byte-matched to the final P2 author. No prepare, build, program, solver, native, Git or SHA action is performed.

It retains namespace `upl_tpi_m0_dt_r2` and future destination include `upl_tpi_m0_dt_r2.h`; it must replace, never co-include, the prior helper. It is host-only and rejects __CUDACC__. Public class/device ABI and CUDA source are not changed by this header.

## Selection and numerical bound

A/pressureBC=false returns before reading prototype environment. B requires explicit `UPL_TPI_P3_ROWS_R1=3` and `UPL_TPI_M0_DT_R1=EQ40_RH1`. Init accepts literal schemeB and the original fresh source0/time0, CPU/GPU backend and fixed dt exactly event/1000. The original event value `.0100002288818359375` and the actual10us clock are unchanged.

The actual necessary bound arithmetic is the same P2 expression:

`bound = min(min(forceCFL,skeletonWaveAVCFL),hydro)` and `signed_error = dt-bound`.

True physical Kw/k are unchanged; true-Kw hydro remains Rh=1 reference. The old Kw wave is diagnostic only; unavailable base-class HG reference remains DBL_MAX with HG_limit_reference_available=false, and the original independent derived HG safety gate remains required. No DtMin clipping, extra safety relaxation,20us expansion or sufficient-stability claim is added.

## Five genuine phases

The existing Init/Record/Saved/Finish/Enabled/AllowedDt/EndpointPhase signatures are retained. Phase0 is the original predictor force, phase1 the original mechanical corrector, phases2/3/4 the three actual endpoint pressure forces. The caller passes the pressure helper's independently verified EndpointPhase; this writer independently checks its expected phase.

Each Record requires owner, actual source TimeStep, completed source step and fixed dt. Only phase0 establishes sourceTime; every later phase must match that same original TimeStep bitwise. Only successful phase4 increments completed and sets lastEnd=time+dt. Global TimeStep is never temporarily changed. Duplicate, missing, reordered or wrong-source phases reject.

Extrema's min/max arithmetic is unchanged. Every true phase contributes to interval and full-run necessary-bound minima and signed-error maximum; only the extra third endpoint count and wrap modulo5 are added. Saved is legal only after complete five-stage updates and verifies all five interval counts equal. Finish verifies all five cumulative counts=N and genuine final saved clock.

## New schema and sentinels

New sidecars: `UplTpiP3DtR1.policy.json/.csv/.summary.json`, stage `upl_tpi_p3_dt_r1`, endpoint_defect_rounds=3, force_phases_per_update=5, source_clock_policy=`original_TimeStep_all_five_phases`.

CSV is23 columns: the original P2 schema adds `interval_endpoint3` and `total_endpoint3`. The exact order is:part,actual_save_time_s,saved_step,completed_updates,dt_s; five interval counts; five cumulative counts;interval_empty; min_force_CFL_s,min_skeleton_wave_AV_CFL_s,min_Rh_hydro_s,min_legacy_Kw_wave_CFL_reference_s,min_HG_limit_reference_s,min_selected_bound_s,max_dt_minus_bound_s.

Initial empty minima stay DBL_MAX and initial maximum stays -DBL_MAX. These are explicit sentinels, not measured bounds/errors. The original native initial signed diagnostic is not rewritten. All nonempty intervals retain the original <=1e-14 signed guard; the future reviewer must compare the true five-phase max to the actual native signed record, not the old three/four-phase formula. The unavailable HG reference is never interpreted as a physical number or used to remove the original HG gate.

No reader or physical action is admitted by writing this file. Independent source/glue/build/fixture/A-regression and genuine native qualification remain necessary. A passed necessary timestep gate is not SPH stability, precision or full-run acceptance.
