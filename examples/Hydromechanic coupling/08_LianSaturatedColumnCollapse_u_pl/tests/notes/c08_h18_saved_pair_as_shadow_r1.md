# Fixed saved pair: total stress and AS shadow r1

Author-only support/c08_h18_saved_pair_as_shadow_r1.py and this note. No script/import/analysis, source change, build, decoder, solver, API, VTK, Git or SHA is executed. Root separately reviews and admits one offline analysis. Scope is exactly original AS03 and the retained/unselected Lstar receiver-C/bare trajectory,91saves each, fixed material IDs6817/6866. Paired-C/bare's different worst pair is background only and is not loaded.

## Minimal evidence and input scope

Reuse passed c08_h18_lstar_window_review_r1.check.json seals. Bind its actual original/Lstar run/native receipts, typed22/layout/clocks and emitted cohort CSV before using them. The known22 dtype is memory-mapped; only these two IDs' fields and each record clock are read, without rerunning all-soil metrics or decoding anything. Both genuine91step/time histories must match. IDs/initial layers/coordinates/fixed P0 come from the actual sealed source cohort CSV, not arithmetic guesses based on ID order. Selected native fields must be finite and P0 must match that material reference. All complete, partial or failed analysis files are protected.

The run/build/program/source-capture/archive/input bindings are retained. Read only three source-archive members: JSphGpu_ker.cu for actual total-AS/momentum formulas, FunSphKernel.h for literal Wendland arithmetic and DualSphDef.h for ALMOSTZERO. This verifies the bounded formula anchors without scanning source/object hashes. Lstar's known intervention changes pressure LP/Lx only; it is not a different AS algorithm. No physical parameter is inferred from a filename.

## Pa tensor brackets and two distinct cast paths

Tension is positive and saved effective sigma is double, with diagonal xx/yy/zz and shear xy/yz/xz. Let d=xi−xj, r=|d|, n=d/r. The true saved tensors are total=sigma_eff−pI. Endpoint CSV records both tensors, their normal projections and maximum3Dprincipal values. Positive maximum eigenvalue alone does not imply AS along the in-plane pair: a positive y-only eigenvector can have zero projection onto n.

Archived GPU703–714 (CPU2135–2139) feeds float(sigma_eff−pI) into Bui's float eigensolver with rhop=1. Thus its dynamic R is in Pa, not Pa/rho². The NumPy model uses eigh64 of that float-input matrix, positive-part reconstruction P=Q max(lambda,0) Q^T and R_numpy=−epsilon P. This reconstructs a mathematical spectral shadow in double; it is not the actual16-iteration float Jacobi result or stored GPU AS tensor. CSV explicitly distinguishes raw-total and float-input eigenvalues, cast error and directional positive-part content.

Momentum has a different original cast sequence (GPU1845–1852/CPU2313–2322): sum float(sigma_eff_i), float(sigma_eff_j), then subtract double(pi)+double(pj) on the diagonal. Define this combined matrix as Tsum. It must not be replaced by sum float(total_i)+float(total_j), nor split into supposedly independently committed effective/pore forces.

AS weighting (GPU1881–1899/CPU2348–2366) is f=[W(r,h)/W(dp,h)]^power. Epsilon/power/h come from each actual native metadata header; dp comes from its bound original XML. The code checks the closed .3f/2.55f/Wendland H=.072f scope. Wdp uses float(Dp*Dp), not a moving nearest-neighbor distance. The actual2Dsource constants use float(.557/h²), not a substituted exact7/(4pi), and the source Wab multiplication order is reproduced with explicit float32 steps. NumPy's float32 power/sqrt remains a source-form approximation, not GPU fast-math/powf/FMA bit truth.

The primary diagnostic is

B = n^T [Tsum + f(R_numpy_i+R_numpy_j)] n  [Pa].

CSV retains Tsum and weighted-AS directional components separately. For the raw radial kernel gradW=fac*d with fac<0 inside support, B>0 is a conditional attraction bracket and B<0 a conditional repulsion bracket. This is a directional mathematical saved-state tendency, not the actually rounded pair force: native double d defines n while the production loop casts displacements/gradient components to float. No m/s² amplitude is claimed. Native V and rho_mix are recorded directly and the finite positive prefactor Vj/rho_i+Vi/rho_j is checked, without using Vel.w, water density, dp², inferred particle mass or another rho^-2 division. Source CPU3137–3141 confirms the current-J quadrature/mixture-inertia convention; exported V/rho retain their already qualified values.

## Undefined states and limits

Source-form support uses the saved-coordinate float-displacement r² and original ALMOSTZERO=1e−18f / float(2h)² bounds. This is not the GPU pos-cell neighbor graph or its exact subtraction/FMA history. A zero-distance state remains a CSV row with undefined direction/projections. An outside-support state retains its valid saved tensor projections but has undefined kernel-weighted B/tendency; no kernel polynomial is extrapolated beyond support. A zero kernel weight is marked explicitly rather than inventing a force. No tiny direction, pressure clip, fitted epsilon/exponent or discarded row is introduced.

Exactly182rows and one PNG are written under fresh figures/c08_h18_saved_pair_as_shadow_r1.* plus logs/<tag>.check.json. Rows retain actual clock/step/signed dterror, IDs/material reference, positions/velocities/rdot/spacing, p/P0, all six effective/total stresses, J/n/nativeV/rho/kappa/FS, spectral projections, kernel quantities and Pa brackets. The PNG plots both complete saved histories for spacing, rdot, effective/total normal stresses, directional positive spectrum and B with its momentum/AS components. Missing directional/support values stay gaps, not interpolated data. All data, including pressure and tensor components not separately plotted, remain in CSV.

The result can show that a nonzero directional spectral-AS condition exists at a saved state preceding a later observed close approach. It cannot establish that the actual intervening Pre/Cor force had already applied that AS, reconstruct an unsaved onset, prove all-neighbor/net acceleration or identify clumping causality. Walls, AV, other neighbors, constitutive/history effects and pressure feedback are not summed. Bui's bounded W ratio and vanishing raw gradient as r→0 are not a hard-core distance constraint. No parameter sweep or physical trajectory is admitted by this diagnostic.

Future root-only invocation: D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_saved_pair_as_shadow_r1.py --execution-authorized. A passed check remains physical_acceptance=false and visual_QA_pending=true; root inspects its sole figure. Failure preserves completed data and new partials and never triggers a decoder or solver retry.
