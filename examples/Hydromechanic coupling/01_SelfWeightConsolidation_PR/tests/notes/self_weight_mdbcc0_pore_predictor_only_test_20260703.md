# Self-weight Scenario 2 mDBC-corrector=0 pore extrapolation cadence test

Date: 2026-07-03

Purpose: test whether the larger error seen with `SlipMode=2` and `MDBCCorrector=0` was caused by pore-pressure mDBC extrapolation being applied in the Symplectic corrector while stress/velocity mDBC extrapolation was skipped.

Code change:
- Removed the `else if(HydroMech) InteractionPorePressureMdbcCorrection()` fallback in both `JSphCpuSingle::Interaction_Forces()` and `JSphGpuSingle::Interaction_Forces()`.
- This makes mDBC pore-pressure extrapolation occur only through `MdbcBoundCorrection()`, so for `MDBCCorrector=0` it is applied in the predictor but not in the corrector.
- For `MDBCCorrector=1`, the behavior is unchanged because `MdbcBoundCorrection()` still runs in both predictor and corrector and updates velocity, stress, and pore pressure together.

Stage 1 result:
- Case: `CaseSWStage1_Slip2_MDBCCorr0_t040_PwPredOnly_GPU_out`.
- Best restart point remained `Part_0046` at `t=0.23 s`.
- Metrics at `Part_0046`: `rms_pore=0.053317 kPa`, `rms_sigma_zz=0.054313 kPa`, `max_speed=1.603e-5 m/s`.
- This is effectively the same as the previous SlipMode=2 run.

Scenario 2 early-window result:
- Case: `S2PwPred034_p0046_GPU_out`, stopped after `Part_0010` for early comparison.
- `Tv=0.005`: bottom excess SPH `9.891463 kPa`, theory `9.888994 kPa`, RMS `72.966 Pa`.
- `Tv=0.05`: bottom excess SPH `8.059855 kPa`, theory `8.035499 kPa`, RMS `34.277 Pa`.
- These match the previous `CaseSWScenario2_Slip2_GhostVel_from_p0046_partial` results within roundoff-level differences.

Conclusion:
- The corrector-only standalone mDBC pore-pressure extrapolation fallback is not the source of the observed larger SlipMode=2 error or later dissipation/platform behavior.
- Even though the test was accuracy-neutral, the scheduling change is retained because it keeps pore-pressure mDBC extrapolation consistent with the mDBC mechanical extrapolation when `MDBCCorrector=0`.
