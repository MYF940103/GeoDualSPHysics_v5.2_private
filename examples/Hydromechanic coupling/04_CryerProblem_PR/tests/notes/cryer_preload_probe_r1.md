# Cryer undrained ramp/hold initial-state probe

This new test is prepared for review, not executed by its author. It does not change production source, canonical programs, formal XML/BAT, geometry, mass or retained data. Default script invocation only prints help. The original weak-damping peak run is complete and must not be restarted.

## Inputs and limited physical change

The XML/BAT derive exactly from `cryer_damp_peak_r1`. The only numerical changes are ramp `0 -> 2^-8 = 0.00390625 s`, drainage start `0 -> 2^-7 = 0.0078125 s`, existing `HydroMechDrainageFixedGrid=1`, TimeMax `17*2^-11 = 0.00830078125 s`, and TimeOut `2^-13 = 0.0001220703125 s`; corresponding descriptions change. BAT changes only the test tag/output name. Fixed dt remains `2^-21 s`: 17408 steps, 69 native saves including t=0, 256 steps per interval. No restart or state reset occurs between ramp, holding and opening drainage.

Canonical GPU Release, FrDraw sphere R=.05 m/dp=.0025 m, k=1e-5, original raw confinement, grad1, original viscosity and damping coefficient .00004 remain unchanged. This coefficient is **SoilDampingCoef**, not hourglass strength. HG/SPR/shifting remain off. Pore state/rate and density are float; persistent stress and saved position are double, not an entirely double coupled system. Old single-float versus new results are not an isolated stress-precision A/B.

Delay of the p=0 prescription is not proof of exact discrete no-flux Neumann behavior: the independently reviewed receiver-C Darcy operator has a volume-weighted pair balance defect. The probe diagnoses whether a useful initial state actually develops; it does not assume that switching drainage alone constructs one.

## Prerequisites and original safety

Explicit `--prepare` requires the independently reviewed weak peak, 24-step source-clock event and offline Darcy records. Event review SHA256 is `12f6308083f84beec4387192587054028055fa18f32024a320412851f5bbb001`. Review links, retained weak-peak outputs, frozen build/source/program/runtime/readers and new inputs are hash-bound. Preparation obtains the current equal CODEX thread/session identity. No prepare/run/queue is performed during static authoring. The parent added explicit runtime parameter-echo checks and initial geometry/material/state byte equality against the retained weak-peak Part0 before sealing this new probe.

`--run` admits just one fresh GPU run, refuses existing artifacts/active GPU solver and only stops its own wrapper tree if needed. Every one of 69 saves must retain all 37173 unique material IDs, finite values, positive density, no exclusions/plasticity, initial mass/h/dp, double position/stress flags, actual load telemetry and radius<=.0525 m. Fixed dt must separately meet the original pore limit; nonzero native saves retain the original mechanical dterror<=1e-14 guard. Native times/zero-based steps must exactly match the binary grid. Actual load must be inward after t=0. No 1D uniform-stress gate is applied to the spherical startup.

FSType2/3 must be genuinely nonempty at each save, and changes from the initial mask are recorded. The verified source-clock ordering makes saved Part64 at t=tD the **last pre-open state**. Strict p=0 is required on every true FSType2/3 node only for saves t>tD (Parts65–68), not before the event. No instantaneous q scalar is saved; the reported source-clock q is a derived reference, while native load vectors are observed.

Solver output hashes and an independent completion manifest are sealed before offline native analysis. A completed solver with failed new analysis is repaired offline, never rerun. Normal solver exit does not imply equilibrium, physical, peak, half-step or full-cycle acceptance.

## Finite-Kw equilibrium reference and new diagnostic criteria

Use exact input K=E/[3(1-2nu)], M=Kw/n and q=10000 Pa. The conditional homogeneous undrained reference is p*=qM/(K+M)=9975.062344 Pa, effective diagonal stress=-qK/(K+M)=-24.9376559 Pa, total diagonal=-q with zero shear, and outward displacement u(x0)=a*x0 with a=-q/[3(K+M)]=-4.987531172e-6. Surface R outward displacement is -.000249376559 mm. These are reference values only, never assigned to numerical state; the backend uses float constants/density.

On **each** of the last four closed saved states, Parts61–64, independently require: native-reference-volume-weighted pressure target RMS<=100 Pa; total-stress six-component target RMS<=100 Pa; maximum speed<=1e-5 m/s; fixed-origin **single scalar** isotropic-fit full-vector RMS residual<=1e-5 mm; and outer-shell per-particle inward displacement target-error RMS<=1e-5 mm. These are newly declared equilibrium diagnostics, not relaxed original safety gates or automatic physical admission. A safe completed run that misses a diagnostic is still retained/reported pending review, not mislabeled solver failure.

Fit a by minimizing sum V0*|u-a*x0|^2 with no translation or free tensor in the criterion; full 3x3 fit is reported only as a diagnostic. Shell uses fixed initial r0>=R-2h and inward r0-r. Each shell particle's target is **-a*r0**, not the surface-R displacement. Both shell mean and per-point RMS error are reported, preventing shell averaging from concealing errors. All material statistics use fixed initial V0=m/rho0 weights; current native volume is separately sum m/rho. The fixed center set is the 18 original IDs with r0<=dp+1e-12, not a presumed r=0 node.

The CSV records pressure/effective and total stress, density/current volume/r^2, velocities, fits, load virial normalized by native and geometric volumes, net force/torque, and conditional small-strain fluid-content observations: <tr(sigma')/(3K)+p/M>, 3a+<p>/M and tr(full-fit)+<p>/M. None is exact fluid mass, and none establishes a cause from float-density rounding alone. No drained-theory function or old peak trajectory is reused; tau=t-tD is just a clock label. The 69-frame window is for initial-state diagnosis, not a Mandel peak measurement.

## Review and one-shot continuation

Only after full static review may the parent run `python tests/support/cryer_preload_probe_r1.py --prepare`, then `--run` from this case (or absolute paths). New output is `tests/outputs/cryer_preload_probe_r1`; manifest/log/check records are in tests/logs, matching summary CSV in tests/figures. Failed equilibrium checks never automatically authorize half/long/formal runs. One terminal same-thread queue attempt is exclusively created, with no retry, old-worker rearm or connectivity test. Subsequent offline review decides any separately justified damping/consistency/initial-state work.
