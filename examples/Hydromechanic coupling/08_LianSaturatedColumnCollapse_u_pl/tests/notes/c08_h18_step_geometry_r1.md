# One original step and material-map review

`c08_h18_step_balance_r1` completed one original CPU symplectic step from the existing AS0.5/n2.55 Part60, actual10.600004999683293 ->10.600009999683293s, dt5us, completed2120001 ->2120002. This is a newly evaluated CPU step on a saved GPU state, not a missing GPU-stage replay, restart qualification, physical trajectory or whole-collapse acceptance. Its separate DebugCPU entry links86 unchanged original physical objects. Actual compile/link/component exits0 and protected source/PRE/input stat bindings remain unchanged.

All5000 soil IDs passed exact predictor/corrector J and pressure commits, saved pn/Jn base ownership through sorting, and completed positive-only FS cap checks.35000 stage rows,5000 balances and3 group summaries were emitted. The half-stage pressure uses pn plus half dt Rn; the full pressure uses the same pn plus dt Rh. Original J updates use the corresponding Jn/Jh and theta. There was no extra correction or physical parameter change.

For s=1-n0 and c=(Jh-s)/Kw, the observed identity is

`deltaJ + c*deltaP = dt*Jh*Dh + c*deltaCap + measured floating-point contributions`.

The total V0-weighted terms, in m2, are:

| Term | Value |
|---|---:|
| sum V0 deltaJ | +1.91392219325e-9 |
| sum V0 c deltaP | -2.27021677470e-9 |
| sum V0 dt Jh Dh | -3.56280776392e-10 |
| cap contribution | 0 |
| explicit floating contribution | -1.38050589338e-14 |
| aggregate arithmetic closure | 1.76091250980e-23 |

The largest computed compression quadrature defect `Kw*(log1p(deltaJ/(Jn-s))-deltaJ/(Jh-s))` is4.35459e-7Pa, RMS1.83207e-8Pa. Final pressure-cast error RMS is.00058860Pa, maximum.00366969Pa. Mean actual pressure increment is-.811784Pa. No soil pressure was capped, and all reported predictor/corrector contact displacement/velocity changes are0 for this step. This sample gives no evidence that a wrong midpoint base, positive cap, contact projection or single-step quadrature error produces its large pressure bias. These values must not be extrapolated as rigorous whole-run bounds; other times can differ. Same-stage Darcy/contact reaction remains unclosed in the general method.

## Original-material map

`c08_h18_material_map_r1.py` explicitly maps the source5000 soil IDs by initial coordinates to100x50 positions, then constructs4851 original counterclockwise quadrilaterals. It does not change any particle ID, state or connection in the solver. Cell area uses translated coordinates in the shoelace sum, avoiding cancellation from the global coordinate origin. An initial analysis-only assertion exposed1.6e-15m2 origin-cancellation error; it was repaired by this algebraically equivalent evaluation, without changing the initial-grid tolerance or any physical calculation. No old derived output existed or was overwritten.

| Case / actual tau | Minimum signed A/A0 | A<=0 cells | Chosen-diagonal reversed triangles | Area versus mean corner-J RMS |
|---|---:|---:|---:|---:|
| n2.55 / .300005s | .507429 | 0 | 0 | .027655 |
| n2.55 / .600005s | -1.291034 | 11 | 73 | .130549 |
| n2.55 / .900000s | -1.340957 | 18 | 129 | .172324 |
| n3.825 / .600005s | -.541589 | 2 | 51 | .099349 |
| n3.825 / .900000s | -.971845 | 5 | 110 | .123097 |

PRE has no reversed cells, minimum area ratio.998972 and area-versus-corner-J RMS7.3849e-5. The n2.55 map first becomes nonconvex around.310005s and has negative signed cell area around.470005s. At.6s native particle J still spans about.99422 to1.02372. At.9s the total signed map area remains close to its initial total while large local shape changes cancel. Both close-pair counts and positive native J can miss this structure.

These straight-sided quads are not an SPH mesh or an exact curved material-volume estimate. A reversal of their chords alone cannot prove a continuum material inversion, zero-energy instability, wrong J integration or a specific bug. Strong unresolved shear localization also changes this map. The finding does support checking local gradient completeness, support conditioning and constitutive localization around the earliest distorted cells rather than conducting another unmotivated AS sweep.

The raw material-map PNG was inspected, with all selected cell ratios retained and a shared color scale. Corresponding all-frame history/minimum-cell CSVs are in tests/figures/c08_h18_material_map_r1_*. Production source, formal inputs, PRE and all retained results remain unchanged.

## Primary-paper implications for the next bounded review

For constant isotropic permeability in2D, Lian2023 Eq23 has D=4rrT/r2-I, trace(D)=2. Consequently its full Hessian trace equals the receiver-C/bare-r2 Taylor-corrected scalar form when neighbours, volumes and the Eq22 gradient agree. Storing a full Hessian alone adds no correction. Production currently differs in pair-C, Eta2 and deliberate raw-FS treatment; variable-k product-rule differences are separate. Eq23 is not guaranteed exactly quadratic-complete on every distorted support.

The next low-cost test therefore freezes the actual deformed Part60 support/C/V and measures constant, affine, independent quadratic and harmonic-polynomial responses under current pair/Eta, receiver/Eta and literal receiver/bare shadows. Boundary cohorts are separate, and no shadow replaces a physical operator just because a polynomial norm is smaller.

Lian Eq47 is a row-dependent modification of its incompressible TPI pressure update: `pnext=p_extrap + S*dt/(S*dt+beta)*(p_candidate-p_extrap)`. Its beta.04 cannot be copied into the present finite-Kw explicit midpoint as an arbitrary multiplier or pressure clip. No TPI/negative-pressure policy is introduced in this stage. Other dilation groups remain held while this necessary consistency review proceeds.
