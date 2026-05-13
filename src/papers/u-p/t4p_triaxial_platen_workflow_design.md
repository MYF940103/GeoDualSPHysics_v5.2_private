# T4p Triaxial Platen Workflow Design

## Route 1: Current AccInput Top Layer

Current route:

- top layer is `mkfluid=1`;
- AccInput applies axial body acceleration to that material layer;
- bottom support is implicit/geometric rather than a platen layer;
- lateral confinement uses `FlexibleConfiningStress`.

Advantages:

- already implemented;
- useful for reduced smoke tests;
- simple to run and debug.

Limitations:

- not a prescribed-velocity platen;
- top layer remains deformable soil material;
- no clean axial reaction force;
- cap particles can contaminate stress-path measurement;
- not a strict triaxial boundary.

Status: keep as smoke only, not validation.

## Route 2: Prescribed-Velocity Top/Bottom Cap Layers

Proposed strict route:

- create explicit top and bottom platen layers;
- bottom platen fixed;
- top platen prescribed downward velocity or displacement;
- specimen soil remains `mkfluid`;
- platen layers are excluded from measurement and p-q statistics;
- lateral confinement is provided by `FlexibleConfiningStress`;
- axial reaction is measured at the platen.

This is closest to Zhao and to laboratory/FEM triaxial practice. It separates
stress boundary and kinematic boundary roles:

- lateral membrane: stress/confinement boundary;
- platens: kinematic/support boundary.

Open question: whether existing `mkbound` moving/fixed machinery interacts
adequately with the u-pw soil skeleton, or whether a material-platen proxy with
velocity override is needed.

Status: recommended next implementation route.

## Route 3: Restart After Isotropic Equilibrium + Prescribed Cap Loading

This combines the best pieces established so far:

Stage A:

- all-surface `f_i` confinement;
- initial hydrostatic effective stress;
- feedback off or carefully controlled;
- damping/equilibration;
- restart saved when low `q` and low velocity are achieved.

Stage B:

- restart from Stage A;
- lateral `FlexibleConfiningStress` retained;
- top/bottom platen boundary activated;
- no `CapConfiningStress` patch;
- feedback off first;
- verify platen contact/reaction and q stability.

Stage C:

- feedback gate;
- only then axial loading.

This is the recommended workflow after the platen boundary exists.

## Route 4: Stress-Controlled Caps

Stress-controlled caps would apply top/bottom normal traction directly. This is
not recommended now because it resembles the failed `CapConfiningStress` path:
it can easily become another acceleration patch without contact/reaction
physics.

## Recommendation

Proceed with Route 2 as the next technical step, embedded in Route 3 staging:
build an explicit platen boundary workflow, then test restart-based isotropic
equilibrium followed by lateral confinement plus prescribed platen motion.

Do not continue tuning `CapConfiningStress` as a production route.
