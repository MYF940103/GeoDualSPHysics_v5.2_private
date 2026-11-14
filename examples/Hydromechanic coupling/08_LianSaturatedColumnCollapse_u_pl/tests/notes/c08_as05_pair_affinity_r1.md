# Bounded affine-patch interpretation of original AS05 close pairs

Read-only continuation of c08_as05_closepair_stress_r1.md, not a physical acceptance gate. Use actual PRE positions as the material reference, actual PRE particle volumes, frozen Wendland H=float0.072 and fixed reference-neighbor radius2H. Positive weights are W(reference distance,H)*V_PRE. At each of316 first saved pair appearances fit the xz-plane map F=(sum w*dx*xi^T)*(sum w*xi*xi^T)^-1 independently at both endpoints. Only626 endpoint/time fits plus the tightest example were needed; no full91-state deformation-field analysis, BI4 decode or new solver.

315 pairs were initially inside2H; one began3.9973dp apart, outside3.6dp support, and is excluded from reference-neighbor statistics. All fitted reference moment matrices were nonsingular with condition1–2.145 and all fitted detF positive. D2norm=sum(w*|dx-F*xi|^2)/sum(w*|xi|^2). Pair predicted length is |0.5*(Fi+Fj)*DeltaXij|.

| Diagnostic for315 reference-neighbor onsets |5%|Median|95%|
|---|---:|---:|---:|
|Measured / predicted pair length|0.5814|0.6945|0.9812|
|Pair vector residual / initial length|0.06793|0.34488|0.69004|
|Endpoint D2norm|0.00813|0.04181|0.23379|
|Endpoint detF|0.97522|1.00068|1.02432|
|Native J/J_PRE|0.99590|0.99786|1.00097|

The first two compressive pairs7010/7011 and6960/6961 have measured0.66652/0.69410dp versus predicted0.64941/0.64603dp (ratios1.026/1.074). Their length contraction is compatible with strong anisotropic patch deformation, although directional residuals are substantial. It is therefore unsafe to classify their spacing alone as tensile instability.

The tightest pair5585/5586 at tau0.540005 measures0.36309dp versus predicted0.63020dp, ratio0.5761, with nonpositive mean pair-axis stress. A new bulk pair2503/2553 at tau0.600005 measures0.69404dp versus predicted1.00298dp, ratio0.6920, while endpoint F singular values are near1 and total pair-axis stresses are-5.34/-20.17kPa. Later close approaches often exceed the shortening represented by this smoothed affine patch, even in compression.

The sole outside-support pair7010/7014 closes at tau0.470005 after starting3.9973dp apart. Its extrapolated affine length is not a bonded-neighbor prediction and is not included in the table. Large patch residuals near shear/slip discontinuities are expected to invalidate a single smooth local map.

Neither detF nor D2 is an independent truth for particle volume, a fitted instability threshold, proof of correct continuum plasticity, or proof of hourglass/tensile causation. The native J follows its own integrated velocity divergence. This diagnostic only separates simple affine length change from more nonaffine concentration at the fixed predeclared support. It motivates inspecting both stress and deformation instead of stronger AS alone. A reproduction helper is being preserved separately; the active private FS trial and all dependencies remain unchanged.
