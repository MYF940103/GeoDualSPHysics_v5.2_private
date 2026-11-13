# Corrected-r2 frozen CPU matrix offline review r1

Status: author-only; this tool has not been imported or executed. New files are this note and `tests/support/c08_fs_matrix_review_r1.py`. It reads only the completed corrected-r2 Raw/Normal datasets, run/build/call receipts and their declared stat bindings. It launches no process, solver, native reader, compiler, GPU or hash scan and changes no input/retained artifact.

After root full read, prospective invocation is `python tests/support/c08_fs_matrix_review_r1.py` from the case root. Defaults read `tests/outputs/c08_fs_matrix_cpu_r2_raw`, `_normal`, and `tests/logs/c08_fs_matrix_cpu_r2.run.json`/`.build.json`. Fresh outputs: `tests/figures/c08_fs_matrix_review_r1.summary.csv`, `.eigenvalues.csv`, `.png`, plus `tests/logs/c08_fs_matrix_review_r1.check.json`. `--prefix` and `--check` permit explicitly fresh alternate destinations; existing outputs are rejected, never overwritten. Python needs NumPy and Matplotlib only beyond the standard library; BLAS thread defaults are1.

## Input qualifications

Require the sealed DebugCPU87-object pairing, shared entry, exactly one original/candidate CPU-object substitution, matching built/run programs, unchanged declared consumed source/header/object/file stats, successful recorded Popen and Win32 exits, actual child PID/creation time/parent/executable/argv, and exact `--expect raw|normal --out` arguments. These are checks of retained actual-process receipts, not new process observations. No old source gate or builder is rerun.

Each genuine completion must identify corrected r2, the expected reference only, Wendland, fixed prescribed Ace/J pressure-operator scope, real FS/C, zero physical steps and physical_acceptance=false. Require two profiles, each486 controls+81 baseline checks+6561 matrix entries. Each program supplies13122 unique matrix entries,1134 unique control/baseline rows and162 unique nodes over both complete0..80 ID sets. Nodes must agree byte-for-byte between programs; positive actual storage weights W=V*n/Kw are consumed without modification.

Every actual control/matrix entry must match its supplied independent-reference budget. Check hydro null against its original two-arithmetic-plus-pressure-quantization budget and exact constant-pressure baseline. All OFF actual_bits must agree across executables, all inner ON control bits must agree within/across programs, and all inner ON basis entries must be exactly identical across programs. Right-null residual |A*1| must fit each row's sum of supplied entry budgets; the reference residual is checked against that same already declared row budget. No fitted tolerance, row-sum repair or matrix normalization occurs.

## Metrics and uncertainty

Write four summary rows: Raw/Normal x J0/J1. For both the actual basis matrix and direct-double reference matrix report diagonal extrema, strict negative off-diagonal count/minimum, maximum absolute row gain, Gershgorin right edge, right-null error, storage-weighted left defect, full eigenvalue extrema/residual, explicit-midpoint gains and storage numerical abscissa. A second negative-off-diagonal count uses Aij+Bij<0 to distinguish signs resolved against the supplied entry budget. No M-matrix property is assumed or required.

The storage left defect uses w^T*A, with per-second maximum divided by sum(w), and descriptive relative1-norm divided by sum(w)*||A||inf. Storage-weighted similarity uses diag(sqrt(w))*A*diag(1/sqrt(w)) solely to measure the norm; it does not alter the exported operator.

For dt=5us form M=I+dt*A+dt^2*A*A/2 without calling an integrator. Report max|1+dt*lambda+(dt*lambda)^2/2|, ||M||inf, and the largest singular value of diag(sqrt(w))*M*diag(1/sqrt(w)). Eigenvalues near zero are retained unchanged, including the constant mode. There is no automatic stable/all-stable boolean or physical admission decision; a spectral radius near1 does not imply storage-energy contraction, conservation or absence of nonnormal transient growth.

The324 eigen CSV rows contain81 actual and81 reference eigenvalues per mode/profile in the same row columns, each list sorted independently by real then imaginary part. A row rank is **not** a matched eigenmode or a certified perturbation correspondence. Summary compares actual/reference spectra separately.

The supplied nonnegative entry-budget matrix B gives ||E||inf<=||B||inf and ||E||2<=sqrt(||B||1*||B||inf) for differences covered entrywise. Also report observed ||A-Aref||2. These are operator uncertainty measures, **not eigenvalue displacement bounds for a nonnormal matrix**; no Bauer-Fike assertion or automatic classification of tiny positive real parts is made. The direct reference is a double assembly of the intended numerical formulas, not an exact continuum operator. Eigen residuals describe the eigensolver calculation only.

The2x3 PNG shows both full complex spectra, the unthresholded near-zero spectral edge, midpoint gains minus1, right-null/budget ratios and storage left defect. The symlog linear region1e-10 is display scaling only, never an admission threshold. Short Raw/Normal labels map to the full sealed source/program receipts in the check JSON; nothing is smoothed, clipped, repaired or ranked as a winner.

`analysis_complete=true` means input and descriptive analysis completed. It never means stable, conservative, physically accepted or representative of collapsed C08 walls. The81-node manufactured operator excludes mDBC, moving geometry and pressure-feedback acceleration. Root must separately assess the actual scientific evidence and remaining coupled risks before any physical action.
