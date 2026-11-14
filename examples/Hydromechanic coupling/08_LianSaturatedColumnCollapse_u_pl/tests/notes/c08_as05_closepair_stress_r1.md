# Original AS05 saved close-pair stress classification

Read-only audit of retained original c08_h18_wend_psi0_a05_w09_r1, all91 exported states/5000 soil IDs. No BI4 decoder, solver, source or active-file modification. Literal typed header is6805/22/91. The actual double export orders kk=(xx,yy,zz), ij=(xy,yz,xz); the full3x3 tensor including yy is used. Total stress is effective SigmaState minus absolute PorePress*I; positive principal stress denotes tension.

The retained descriptive radius r<0.7dp identifies316 unique edges/563 material IDs and3707 pair-frame observations. It is not a physical failure or tensile-instability criterion. At each edge's first saved appearance:

| Saved classification | Edges /316 |
|---|---:|
|Both ends have no positive total-stress principal|253|
|Both ends have nonpositive pair-axis total normal stress|293|
|Mean pair-axis stress positive|6|
|Both pair-axis stresses positive|3|
|Any positive effective-stress principal|5|
|Both J<1|279|
|Both accumulated kappa>0|311|
|Both endpoints approaching along the pair axis|312|
|Both absolute pressures negative|265|

Negative pressure occurs already at the first saved post-update state (2particles,min-31.42Pa); total tensile principals appear globally by tau0.010005, with no close pairs until tau0.180005. The first two edges are7010/7011(r0.666522dp) and6960/6961(0.694104dp), near x3.94–4.03m,z0.019–0.054m. Both ends of both edges have strictly compressive effective and total principals, J0.998459–0.999603 and kappa0.288–0.755. Their pair-axis total stresses range-41.16 to-9.63kPa although p is negative, about-1.77 to-2.32kPa.

At the110-edge saved peak,tau0.600005,75 edges have nonpositive total principals at both ends and97 have nonpositive pair-axis stresses at both ends; only4 have positive mean-axis stress and none have both axis stresses positive.103 have bothJ<1,106 bothkappa>0,all110 bothp<0; only2 touch saved FS2/3. Final23 edges at0.9s include18 both-total-nontensile and20 both-axis-nontensile, with1 mean-axis-positive and none both-axis-positive.

The tightest edge5585/5586 occurs at tau0.540005,r0.363086dp. Total pair-axis stresses are-25.47/+2.24kPa (mean-11.62kPa); both effective tensors are compressive, J0.995234/0.997615 and kappa0.927/0.854. Small spacing alone cannot decide whether AS is missing or whether the deformation is nonphysical.

Across all3707 pair observations,2562 have nonpositive total principals at both ends and3296 nonpositive axis stress at both ends;151 have positive mean-axis stress,58 both-axis-positive and54 any effective tension. Only103 touch saved FS2/3. No endpoint lies at the existing saved-plane criterion z<=4e-8m; pooled endpoint z/dp median34.03, so the entire population is not a near-bed group. Do not invent an h-wide near-bed mask after viewing the result.

These are saved-time classifications, not an observation of each pair's true substep onset or the exact stress that generated its preceding AS force. SaveData recomputes FSType. No claim of tensile causation, current plastic shear-rate localization, geometric-volume truth or repair follows. A smaller genuine tensile subset exists, but dominant saved close-pair onset is associated with compression/plastic deformation. Local affine deformation versus nonaffine concentration must be considered before calling every close pair tensile instability or increasing AS again.
