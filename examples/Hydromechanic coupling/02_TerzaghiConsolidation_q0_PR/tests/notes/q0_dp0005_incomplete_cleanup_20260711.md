# q0 k=1e-4 dp=0.005 cleanup note

The root dp=0.005 comparison run (`CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt3em6`) was stopped before a reliable full-Tv result was obtained. The run was also strongly constrained by the small fixed time step and was not used as a formal convergence point.

Cleanup action: root XML/BAT and incomplete output were removed. Resolution figures/data that had included this incomplete point were moved to `tests/figures/resolution_archived_dp0005_incomplete/` for reference only and should not be used as formal root figures.
