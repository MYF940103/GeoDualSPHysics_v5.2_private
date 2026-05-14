# Draft Task Prompt: L5 CPU Mechanical Loading Route For 1D Consolidation

## Goal

Enter L5: CPU mechanical loading route for strict 1D consolidation
reproduction.

Background:

- L3c/L4 validate the initial-state PR diffusion and hydraulic boundaries.
- L2 `AccInput` and L3b direct force-on-material are stable but generate
  unrealistic dynamic pressure peaks.
- Strict full reproduction eventually requires paper-faithful top surcharge
  generation.

Strict scope:

- CPU-first.
- Default-off source features only.
- Do not modify the PR governing equation.
- Do not enter Cryer, triaxial, or MCC.
- Do not run broad damping/viscosity sweeps.
- Do not enable full feedback until the mechanical loading route is physically
  acceptable.
- GPU hard error for any new unsupported loading route.

Tasks:

1. Audit current force, boundary, platen, traction, and initial-stress support.
2. Compare candidate routes:
   - force-controlled loading plate;
   - true surface traction;
   - consistent vertical total/effective stress initializer;
   - quasi-static preloading stage.
3. Select one minimal CPU prototype route.
4. Design parser parameters:
   - default off;
   - clear target surface or plate;
   - load scale `q0=-10 kPa`;
   - ramp/equilibration controls;
   - diagnostics for applied force, reaction, velocity, displacement, and
     generated excess pressure.
5. Implement only if the route is safely scoped.
6. Run short CPU validation:
   - no `AccInput`;
   - no L3b material-force shortcut unless explicitly used as a negative
     control;
   - top drained and bottom/lateral no-flux;
   - compare generated pressure scale against `10 kPa`;
   - compare decay against Terzaghi after loading.
7. Write a report distinguishing:
   - mechanical load generation;
   - PR diffusion gate;
   - full feedback.
8. Update docs and commit.

Required final answers:

1. Which mechanical loading route was selected.
2. Whether source was patched and whether default behavior is unchanged.
3. Whether `AccInput` is avoided.
4. Whether generated excess pressure stays near `q0` scale.
5. Whether analytical comparison improves over L2/L3b.
6. Whether full feedback remains deferred.
7. Whether damping/viscosity sweep is still not recommended.
