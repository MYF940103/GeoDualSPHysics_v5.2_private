# T4n2 Restart Equilibrium Audit

Purpose: audit whether a Zhao all-surface isotropic confinement state can be
saved and restarted before switching to lateral-only confinement.

Run order:

1. `xRun_CaseT4n2_StageA_AllSurface_FeedbackOff_win64_CPU_release.bat`
2. `xRun_CaseT4n2_StageB_Restart_Lateral_FeedbackOff_win64_CPU_release.bat`
3. `xRun_CaseT4n2_Fresh_Lateral_FeedbackOff_win64_CPU_release.bat`
4. `xRun_CaseT4n2_StageC_Restart_Lateral_FeedbackDelayed_win64_CPU_release.bat`
5. `py analyze_t4n2_restart_equilibrium.py`

The Stage B/C BAT files restart from Stage A `Part_0023`, the actual final
saved frame of the Stage A short run. The restart outputs are intentionally
not committed; only XML/BAT/scripts/CSV/figures/reports are retained.

Main result: restart preserves the u-pw state fields that are currently stored
in Part files (`PorePress`, `Sigma_kk`, `Sigma_ij`, `Kplastic`, velocity and
density), but the lateral-only Stage B still loses hydrostatic balance and
delayed feedback remains unstable.
