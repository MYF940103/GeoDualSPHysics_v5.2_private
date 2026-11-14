# C08 volume and stress-rate consistency audit

Read-only audit of the original schema2 `full_source.zip`; no public source, active program, input, PRE or numerical threshold changed. The private normal-Taylor trial was not selected. This audit identifies implementation differences, not a new physical root cause.

With the actual derivative boundary velocity, reference volume and current J, define

`H = sum_j Vj (vj-vi) tensor gradW_ij`.

The corrected mechanical gradient is `H Ci^T`; dynamic volume rate is `theta = sum_j Vj (vj-vi) dot (Ci gradW_ij)`. Thus `theta = trace(H Ci^T)` in exact arithmetic, with C applied once on both paths. The elastic stress-rate spin terms have cancelling trace, so `trace(sigma_dot_effective) = 3 K theta`. No duplicated C, factor3 or sign error was found.

Actual arithmetic differs: dynamic theta uses double volume/products/accumulation, whereas mechanical H uses float volume/gradient/accumulation and float corrected rows. The source alone does not establish a sufficiently large accumulated discrepancy to explain current C08 pressure. GPU references in the frozen archive: `JSphGpu_ker.cu:1931-1966,2078-2081,2260-2269,612-622`; CPU: `JSphCpu.cpp:2393-2441,2553-2556,2611-2620`.

Each force call clears Ace, stress rate and theta (`JSphGpu.cpp:1600-1608`). Dynamic mode disables the legacy pressure-rate path before overwriting it with the dynamic rate (`JSphGpuSingle.cpp:663,687`). J uses the same-stage theta. No duplicated old/new pressure rate or unreset history-rate accumulation was found.

At psi0 the Smooth plastic branch preserves effective-stress trace, but the separate TensionRepair branch may change it (`FunSoilMaterial.h:105-108,145-149`). This is not a reason to add the return correction to J. Psi0 also does not prohibit elastic volume change. With Kw=1GPa and n about.35, only1e-5 accumulated dilation corresponds dimensionally to about-28.6kPa without hydraulic cancellation. This dimensional example is not the measured global C08 dilation or an acceptance reference.

A known structural difference remains: momentum uses the raw symmetric pressure-force gradient, while Darcy uses corrected pressure differences, acceleration divergence and its separate second-order terms. Completed Ace includes AS/AV and enters Darcy in the same stage (`JSphGpu_ker.cu:1845-1854,1551-1600`; `JSphGpuSingle.cpp:670-687`). This can matter even when theta is small, but the audit found no new minimal patch justified by code alone. Previously rejected isolated-gradient and residual-viscosity changes must not be repeated as presumed fixes.

No solver, reader, build, hash scan, acceptance claim or automatic next run follows this note.
