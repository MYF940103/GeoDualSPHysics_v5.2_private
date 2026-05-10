# Sensitive Clay Softening Model Audit

Date: 2026-05-11

## Sources Checked

- `src/papers/u-p/converted/u_pw_paper_text.md`
- `src/papers/u-p/full_paper_case_audit.md`
- `src/papers/u-p/sensitive_clay_model_plan.md`
- `examples/u-pw/05_Retrogressive_Slope/README.md`
- `examples/u-pw/05_Retrogressive_Slope/notes.md`
- `src/source/DualSphDef.h`
- `src/source/JSph.cpp`
- `src/source/JSphCpu.cpp`

No GPU source is considered part of this implementation pass.

## Paper Model

The main u-pw paper uses Drucker-Prager plasticity with isotropic strain
softening for sensitive clay in the retrogressive slope and Sainte-Monique
cases.

The converted text around Eq. (48) states that cohesion and friction are
degraded as functions of accumulated plastic strain:

```text
c = c_r + (c_p - c_r) exp(-eta * eps_p_acc)
phi = phi_r + (phi_p - phi_r) exp(-eta * eps_p_acc)
```

where:

- `c_p`, `phi_p` are peak cohesion and friction;
- `c_r`, `phi_r` are residual cohesion and friction;
- `eta` is the softening coefficient / shape factor;
- `eps_p_acc` is accumulated plastic strain.

For the retrogressive benchmark slopes the paper notes:

- `E = 25 MPa`;
- `nu = 0.3`;
- mixture density `2150 kg/m3`;
- porosity `0.4`;
- `Kw = 0.2 GPa`;
- `k = 1e-8 m/s`;
- friction and residual friction are both `0 deg`;
- dilatancy is `0 deg`;
- peak cohesion `15.1 kPa`;
- residual cohesion `1.5 kPa`;
- softening coefficient `eta = 5`;
- initial stresses use `K0 = 0.5`;
- the failure stage is triggered after gravity initialization by enabling
  softening and applying a strength reduction factor in the paper workflow.

For Sainte-Monique the same softening law is used with field-specific Table 1
values:

- peak/residual friction `10/0 deg`;
- peak/residual cohesion `45/1 kPa`;
- softening coefficients `eta = 2, 5, 10`.

## Current Code State

### Existing Parameters

`StSoilCte` already contains:

```cpp
float coh;
float phi;
float dlt;
float phi_r;
float coh_r;
float n_phi;
float n_coh;
```

`JSph::InitSoilParameters()` already reads:

```xml
<coh value="..." />
<phi value="..." />
<dlt value="..." />
<coh_r value="..." />
<phi_r value="..." />
<n_coh value="..." />
<n_phi value="..." />
```

The existing `n_coh` and `n_phi` map naturally to the paper's `eta`. The paper
uses one `eta` for both strength components in the slope cases; the current code
can also support separate cohesion and friction softening rates.

### Existing Return Mapping Helpers

`JSphCpu.cpp` already contains:

- `UpdateDPvars()`, which computes softened Drucker-Prager parameters using
  exponential degradation of `coh` and `phi`;
- `Updatedfdk()`, which adds the derivative of the yield function with respect
  to the softening variable;
- `ConsRelationEPsft_fast()`, a softened return-mapping routine using the
  current particle `Kplastic` as accumulated plastic strain;
- `ConsRelationEP_fast()`, the current production non-softening routine.

The active CPU integration paths call `ConsRelationEP_fast()`. The softened
routine is present but not used.

### Kplastic Meaning

`Kplasticc` is saved as output field `Kplastic`, restored during restart, sorted
with particles, and updated in the elastoplastic return mapping.

Inside both `ConsRelationEP_fast()` and `ConsRelationEPsft_fast()`, the
increment added to `Kplastic` is:

```cpp
sqrt((2/3) * deviatoric_plastic_strain_increment : deviatoric_plastic_strain_increment)
```

Therefore `Kplastic` is an accumulated equivalent deviatoric plastic strain
measure and is a suitable first CPU proxy for the paper's accumulated plastic
strain in Eq. (48).

## Current Code vs Paper

| Item | Paper | Current CPU code |
|---|---|---|
| Yield surface | Drucker-Prager | Drucker-Prager |
| Softening law | Exponential in accumulated plastic strain | Helper exists with the same exponential form |
| Softening state | Accumulated plastic strain | `Kplastic` equivalent deviatoric plastic strain |
| Activation workflow | Peak gravity initialization, then softening enabled | No explicit `Softening` switch yet |
| Strength reduction factor | Paper slope trigger includes a strength reduction step | Not implemented in this pass |
| GPU | Paper production-scale run | Out of scope |

## Recommended Implementation

Use the existing CPU softened return-mapping helper, but add an explicit soil
material switch:

```xml
<Softening value="0|1" />
```

Default `Softening=0` preserves existing Drucker-Prager behavior.

When enabled:

- use `ConsRelationEPsft_fast()` instead of `ConsRelationEP_fast()`;
- use `coh`, `phi` as peak values;
- use `coh_r`, `phi_r` as residual values;
- use `n_coh`, `n_phi` as exponential softening coefficients;
- use `Kplastic` as accumulated plastic strain;
- keep the residual strength floors built into the exponential law.

If residual values are absent or softening coefficients are zero, validate or
fall back safely:

- `coh_r` defaults to `coh`;
- `phi_r` defaults to `phi`;
- zero `n_coh` / `n_phi` means no degradation for that component;
- negative coefficients are invalid.

## Smoke Tests Needed

1. `Softening=0` backward-compatibility smoke.
2. `Softening=1` micro slope or weak column with visible `Kplastic` growth.
3. Extreme residual-parameter smoke to ensure no negative strength or NaN.
4. `05_Retrogressive_Slope` reduced softening smoke:
   - code=0;
   - excluded=0;
   - finite pore-pressure fields;
   - `Kplastic` grows;
   - behavior differs from `Softening=0`.

## Out Of Scope

- Modified Cam Clay.
- Full sensitive-clay remolding/destructuration beyond Eq. (48).
- Strength reduction factor workflow matching the paper's full initialization
  procedure.
- Production boundary MLS.
- GPU port.
