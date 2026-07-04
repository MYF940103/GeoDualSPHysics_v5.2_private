# Self-weight Mode3 mDBC stress path correction

Date: 2026-07-01

The tentative zero-order mDBC stress extrapolation isolation was cancelled before completion.

Corrected finding:

- The old CPU baseline commit `a407fbd` used `JSphCpuSingle::MdbcBoundCorrection() -> JSphCpu::Interaction_MdbcCorrection() -> InteractionMdbcCorrectionT2()`.
- In that actual old CPU path, boundary stress was extrapolated with the first-order form `sigma_g + grad(sigma) * dpos`.
- The zero-order stress assignment block is a separate retained routine and is not the path used by the old CPU self-weight baseline.
- GPU mDBC also has FastSingle and double kernels, but both old GPU kernels used the same first-order `dpos` stress extrapolation form in the main mDBC correction path.

Action taken:

- The interrupted `CaseSWScenario2_Mode3_OldStressMdbc_CPU` partial output was removed.
- The temporary source edit was reverted.
- CPU Debug and CPU Release were rebuilt after the revert.

Conclusion:

- Do not use zero-order mDBC stress extrapolation as an explanation for the current Mode3 mismatch.
- The remaining mismatch is not explained by the tested mDBC pore-pressure scheduling, merged pore-pressure-rate loop, XML compatibility, free-surface drainage predicate, CteB/Cs0 value, or zero-order mDBC stress extrapolation.
