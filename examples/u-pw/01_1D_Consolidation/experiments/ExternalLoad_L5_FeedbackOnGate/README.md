# ExternalLoad L5 Feedback-On Gate

L5 is a CPU-first feedback-on coupling gate for the 1D consolidation route.
It deliberately keeps the L3c/L4 initial-state setup and only turns on
pore-pressure momentum feedback.

## Scope

- `PorePressureInit=3`
- initial excess pressure amplitudes: `1 kPa` and `10 kPa`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- no `AccInput`
- no `MechanicalTopLoad`
- `InitialStressMode=0`
- `PorePressureFeedback` is diagnostic here, not strict Terzaghi load generation

## Commands

Run CPU low/target:

```powershell
py -3 run_l5_feedback_on.py
```

Run target GPU only after the CPU target case is stable:

```powershell
py -3 run_l5_feedback_on.py --case target --gpu-target
```

Run analysis:

```powershell
py -3 analyze_l5_feedback_on_1d_consolidation.py
```
