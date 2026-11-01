# GPU observer: bounded implementation plan only

No code/build/run changes. Keep the active sort build's four utility files and every bound helper frozen. The public GPU master remains rejected.

**State/scope:** one private default-false observer bool; double J/theta-last-stage/JPre only. No feedback, dynamic Darcy, k law, new XML key, pressure/force/C/density/material/time-step changes. Start with fresh 2-D/g=0 elastic Symplectic, corrected PairDivergence, no-wall periodic fixtures and the CPU observer's other compatibility restrictions.

## Five-file hooks

| Existing location | Minimal addition |
|---|---|
| JSphGpu.h; Gpu.cpp InitVars ~133, AllocGpuMemoryParticles ~353, ReserveBasicArraysGpu ~627 | Null/reset private pointers; initialize J=1/theta=0 before initial force/save. Two persistent doubles + predictor + one sequential out-of-place sort scratch = four additional double-pool slots at peak. Existing position-z slots remain separately counted. |
| Gpu.cpp ResizeGpuMemoryParticles ~446, FreeGpuMemoryParticles ~340, host Alloc/FreeCpuMemoryParticles | Preserve current J/theta and live JPre over resize; free/null correctly. Add host output arrays only, not new persistent particle state. |
| GpuSingle.cpp RunCellDivide ~507 | Sort J/theta and active JPre with the same SortPart using the verified double overload. Reserve one scratch, swap/free, reuse. Test full and preserved-prefix sorts. No utility re-edit. |
| GpuSingle.cpp RunPeriodic ~425; Gpu_ker.h/.cu PeriodicDuplicateSymplectic | Copy J/theta/optional JPre via the same clone list, including XZ clones-of-clones, matching CpuSingle ~499. No owner-map cache across divide/resize. |
| Gpu.cpp PreInteractionVars_Forces ~1357; GpuSingle Interaction_Forces ~674; Gpu_ker.h StInterParmsg | Zero theta every force stage; pass a nullable theta pointer/default NULL without changing old call behavior. |
| Gpu_ker.cu KerInteractionForcesFluid/Box ~1981/~1658 | Add a local double theta sum beside the existing corrected pore-source divergence; store it outside the old nonzero force/Arc/viscosity condition. Keep every original force, stress and pore-rate expression/order unchanged. |
| Gpu.cpp ComputeSymplecticPre ~1480 / Corr ~1530 | At CPU-equivalent pressure/update hooks, reserve/swap JPre; Jhalf=Jn+dt/2*Jn*theta_n; Jnew=Jn+dt*Jhalf*theta_half. Corrector uses saved Jn, then frees/nulls JPre before predictor teardown. Require finite J>1-n0; elastic Kplastic check only for native normal fluid, not uninitialized clone slots. Separate small CUDA observer kernels suffice; do not redesign GpuSimple_ker integration. |
| Gpu.cpp ParticlesDataDown ~820; GpuSingle SaveData ~1183 | Download and compact actual J/theta with the same code/native-ID path. Private diagnostics: PoroVolumeRatio/PoroPorosity/PoroThetaLastStage only, matching CPU observer; no public dynamic metadata or feedback schema. Shared loader keeps rejecting J-state PART even master OFF. |

Thus likely edits are only JSphGpu.h/.cpp, JSphGpuSingle.cpp and JSphGpu_ker.h/.cu. No new class/framework or physical equation.

## Theta must match the CPU operand contract

CPU references: InteractionForcesFluid ~2379/~2528/~2737; ComputeSymplecticPre/CorrPorosity ~4431/~4446. Use
theta_i += double(float(mass_j/rhop_j)) * (v_j-v_i)_deriv dot (C_i gradW_ij).
Preserve the float quotient before promotion, existing float kernel factor, double accumulation, support/valid-fluid/active-wall tests and 2-D zero-y. Velocity is dv_grad_deriv: SPR derivative velocity if present, otherwise the legacy viscous/tangential selection. It is **not Arc/rhop**, nor necessarily the trace of the separately float-accumulated stress gradient.

Change the observer condition to porerate_i OR observe_i, including receiver-C loading: drained pressure may suppress dp/dt but must not suppress theta. Original pressure accumulation remains gated by porerate only. Reuse the pair pass; no extra neighbor traversal.

Do not introduce P3 periodic C/Ace owner-extension: CPU observer-only does not enable that dynamic path. Clone copies are exact at creation; later periodic theta recomputation is not an endpoint owner-equality claim. J never feeds physical quadrature/inertia. GPU PosCell/neighbor-order differences prevent assuming CPU/GPU 0 ULP.

## Minimum gates

1. Same-GPU retained OFF→new OFF, then fresh new OFF→observer ON: all original15 arrays, double stress, telemetry, actual shared times and native IDs exact. New diagnostics excluded only because absent OFF, not by masking a physical field.
2. Manufactured full-support translation/dilation/shear/rigid rotation: independently known instantaneous theta (trace for dilation, zero otherwise), nonempty shear controls; prescribed constant-theta explicit-midpoint J recurrence. Affine velocity is not a compatible periodic physical solution.
3. State-only native-ID values: full/prefix sort, live-JPre resize, XZ clones-of-clones, exact copied bytes and tail poison, JPre-present/absent and Debug memcheck teardown.
4. Bounded actual periodic force/integrator original15 OFF/ON exactness and saved J/theta recurrence; drained-receiver component proves theta independence from the pressure gate, not physical drainage acceptance.

This admits no feedback/pressure model, public GPU option, wall closure, new time policy, speedup, physical/full-cycle or restart acceptance. If physical bits change, repair wiring rather than relaxing gates.

