# AS kernel normalization audit during the private FS trial

Read-only audit of the frozen schema2 implementation used by the retained control; the active private program changes only the separately documented FS hydraulic closure. No parameter, program, PRE or active dependency was changed by this audit.

The active soil AS path uses f=W(r,H)/W(dp,H) from the selected actual kernel and runtime H, followed by f^n (original GPU source2210–2211,1879/1888; CPU2196–2197,2348–2357). The reference dp is initial spacing, not a moving nearest-neighbor distance. The older cubic tensile helper with fixed q=2/3 is a separate path whose soil-force call sites are commented out. No hardcoded Cubic1.2 denominator was found in the active AS path.

The current XML explicitly sets epsilon0.5 and exponent3.825. The source default exponent is fixed2.55, not automatically scaled by hdp (JSph.cpp1761–1762). The reference dry cohesive collapse XMLs use Wendland/hdp1.8 and Visco0.1 with exponent2.55 (including the file where the exponent is commented and hence takes the default). Those settings are a useful separate reference, not a reason to change the active trial mid-run.

For dynamic feedback, R=-epsilon*[Sigma_effective-pI]_positive is stored in Pa; the momentum contribution applies Vj/rho_i. The old dry form stores R/rho^2 and multiplies particle mass. Uniform-density scaling is equivalent; no duplicate pore-pressure subtraction or double density division was found. The fluid-pair AS force is algebraically reciprocal under current rho_i*Vi weighting because it uses symmetric Ri+Rj and the raw radial gradient. This does not close fixed-wall reaction, variable-mass total momentum or energy.

Weights below are f^n only, not multiplied by epsilon and not complete forces:

| r/dp | Wendland H/dp1.8 n3.825 | Wendland H/dp1.8 n5 | Cubic H/dp1.2 n2.55 |
|---|---:|---:|---:|
|0.25|7.0799|12.9167|9.3229|
|0.5|4.5862|7.3222|6.0314|
|0.7|2.7550|3.7612|3.4609|
|1|1|1|1|
|1.25|0.34166|0.24565|0.22880|
|1.5|0.09310|0.04490|0.03508|
|2|0.002995|0.000503|0.0000709|

Exponent5 strengthens close-range weighting and decreases longer-range weighting, without changing support3.6dp for Wendland. Matching the Cubic reference's local logarithmic slope at dp would give n about5.0165; that is a local mathematical match, not a validated parameter choice. The actual exponent5 experiment worsened pressure spikes and failed, so the slope match does not justify it physically.

Bui2008 local MD879–897 and1464–1472 explicitly relates exponent to kernel/H/dp and tests; its epsilon0.5/n2.55 recommendation concerns Cubic H/dp1.2. Neither the source nor the displayed formula hard-cuts AS at r>=dp. Close pairs, negative pressure and early arrest still require causal evidence; these implementation checks do not attribute them to AS.

The active single FS trial retains epsilon0.5/n3.825. Any future exponent2.55 dry-reference comparison requires a separate decision after that result, not a simultaneous intervention or an automatic additional solver.
