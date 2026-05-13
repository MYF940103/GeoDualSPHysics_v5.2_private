# T4n1 Next Step Recommendation

## Options Considered

### Option 1 - Continue T4n2 Ramped Selector Transition

Pros:

- directly targets the T4n abrupt active-set jump;
- likely reduces `q`, velocity, and pore-pressure spikes at the switch;
- small source change if implemented as a selector weight.

Cons:

- no direct Zhao/u-pw reference for ramping the selector;
- can become a numerical smoothing device rather than a physical boundary
  condition;
- does not address feedback-on instability by itself;
- could hide reduced-cylinder geometry sensitivity.

### Option 2 - Restart-Based Equilibrium

Pros:

- aligns with the literature principle of starting loading from an equilibrated
  stress state;
- avoids adding an artificial transition force law;
- separates Stage A isotropic confinement from Stage B triaxial loading;
- can verify whether state transfer preserves stress, pore pressure, velocity,
  and material history.

Cons:

- requires a careful restart fidelity audit;
- may expose missing fields in restart/output;
- may still need damping and a hold period after restart.

### Option 3 - Zhao-Style Initial Stress + Damping / `l0/ln` Rescaling

Pros:

- directly supported by Zhao;
- addresses stress waves and confinement magnitude consistency;
- more defensible than feedback caps or selector smoothing.

Cons:

- `l0/ln` rescaling is a new source task;
- corrected/renormalized magnitude may amplify force if applied carelessly;
- does not solve the lateral-only triaxial transition by itself.

### Option 4 - Pause Strict Full-Feedback Triaxial Route

Pros:

- avoids accumulating diagnostic patches;
- protects DP/MCC work from unstable foundations.

Cons:

- leaves the triaxial confinement route incomplete;
- postpones a benchmark that is still strategically valuable.

## Recommendation

Choose Option 2 as the next main task: restart-based equilibrium audit and
prototype.

The recommended T4n2 should not be a ramped selector source patch. It should be:

```text
T4n2: restart-based all-surface confinement equilibrium audit
```

The narrow goal is to determine whether GeoDualSPHysics can:

1. run Stage A with Zhao all-surface `f_i` confinement, initial stress, damping,
   feedback off;
2. reach a quiet hydrostatic-enough state;
3. save/restart that state without losing stress, pore pressure, velocity, or
   relevant history fields;
4. continue Stage B with lateral-only confinement and no axial loading;
5. check whether `p'`, `q`, pore pressure, velocity, and `DivVel` stay bounded.

If restart fidelity is not adequate, then a constrained ramped selector
transition can be considered as an engineering fallback. If restart fidelity is
adequate but the Stage B state still loses hydrostatic balance, the blocker is
not the switch discontinuity alone; it is the reduced cylinder geometry and/or
missing Zhao large-deformation confinement correction.

## T4n2 Acceptance Criteria

T4n2 should pass only if:

- restart preserves stress and pore-pressure fields;
- Stage B lateral-only feedback-off state does not show a large `q` jump;
- velocity, `DivVel`, and `PorePressRate` remain bounded;
- no pressure reversal or strong negative pressure is reintroduced;
- full feedback remains off until the mechanical switch gate is passed.

## What Not To Do Next

Do not enter DP or MCC. Do not run axial loading. Do not add feedback caps as a
validation route. Do not promote a ramped selector transition unless restart is
blocked or shown insufficient and the ramp is explicitly labeled diagnostic.
