# M4 Future Work After Caveated MCC Package

## Context

M3i-revised freezes the current MCC triaxial route as a caveated CPU
feedback-off reduced prototype.  Clean validation is not abandoned forever, but
it is no longer the immediate path.  The current blockers are boundary-induced
local return failures, unresolved full feedback, no confirmed custom particle
import workflow, and no GPU MCC implementation.

## Route A: Continue Clean MCC Validation Later

This route should be chosen only if strict MCC triaxial validation becomes a
priority again.

Required work:

- implement or discover a safe custom smooth/fan-like particle import route;
- run a smooth-layout MCC dense diagnostic through the CPU solver;
- improve platen/specimen interface and edge/corner support;
- confirm no transient `ReturnStatus=-3/-5` episodes;
- revisit full feedback only after feedback-off return status is clean;
- keep GPU deferred until CPU state/update/restart behavior is stable.

Advantages:

- best route toward strict paper-level MCC triaxial validation;
- directly addresses the boundary-induced failure mechanism.

Costs:

- custom workflow work outside common GenCase XML usage;
- likely additional geometry and measurement validation;
- not a quick continuation.

## Route B: Use Caveated Reduced MCC Route for Development

This route keeps the current feedback-off explicit-platen MCC workflow as an
internal diagnostic tool.

Allowed uses:

- parser/state/output regression checks;
- CPU MCC return-map diagnostics;
- reduced DP/MCC qualitative comparison;
- pairwise reaction and p'-q postprocessing development;
- preliminary constitutive behavior exploration.

Required caveats:

- do not claim strict validation;
- do not claim full undrained u-pw behavior;
- report local return-status caveats;
- report pairwise reaction as pairwise interaction reaction, not full actuator
  reaction.

This is the recommended route if MCC remains useful for code development but
clean validation is not the immediate project goal.

## Route C: Shift to the Next Project Module

This route stops spending near-term effort on triaxial clean validation and
moves to another u-p module, landslide/erosion/slope benchmark, or other
project priority.

Recommended when:

- the project needs progress outside the triaxial MCC branch;
- caveated MCC diagnostics are enough for now;
- custom particle import is not worth the workflow cost today.

This route preserves all MCC implementation work as a CPU prototype and leaves
a clear re-entry point for later clean validation.

## Recommendation

Use Route B if the next work still needs MCC diagnostics.  Use Route C if the
project priority is broader u-p progress.  Do not pursue immediate M3p custom
particle import unless clean MCC validation becomes an explicit priority again.

Full pore-pressure feedback and GPU remain deferred in all routes.
