# Self-weight Boundary Full-Ghost Velocity Diagnostic

Date: 2026-07-31

Purpose: check whether the late-time pore-pressure platform is caused by using
the mDBC tangential ghost velocity (`TangenVelc`) in the pore-pressure
compression source near no-slip boundary particles.

Temporary code: CPU-only environment-variable branch in `JSphCpu.cpp` that used
the full mDBC ghost velocity (`velrhop[p2]`) instead of `TangenVelc[p2]` only for
the boundary-neighbor contribution to `Kw/n * (-div(vs))`. The temporary branch
was removed after the test and CPU Debug/Release were rebuilt.

Case: 1D self-weight Scenario 2, restart from
`CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data`, `PartBegin=240`, `Kw=2e8`,
`k=1e-3`, `DtFixed=1e-6`, short window `Delta Tv=0.01`.

Command note: the first manual replay mistakenly included command-line `-mdbc`,
which overrides the XML slip setting and changed the run to `SlipMode="DBC
vel=0"`. That replay was discarded. The retained diagnostic below uses the
project test-bat convention: no command-line `-mdbc`, so the XML
`SlipMode=2` is preserved and `Run.out` reports `SlipMode="No-slip"`.

Result:

| variant | bottom EPWP at start [kPa] | bottom EPWP at end [kPa] | slope [kPa/Tv] |
| --- | ---: | ---: | ---: |
| current default path | 0.534759570 | 0.533379980 | -0.137959 |
| full mDBC ghost velocity for compression | 0.534759570 | 0.535499219 | +0.073965 |

Conclusion: the current `TangenVelc` compression path is not the source of the
late-time platform. Replacing it with the full mDBC ghost velocity worsens the
late window by adding positive compression/rebound. The remaining source should
be treated as a coupled storage/pressure-integration consistency issue rather
than a simple boundary velocity-choice bug.
