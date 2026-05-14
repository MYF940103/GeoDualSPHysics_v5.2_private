# L3e 1D Consolidation Validation Package

This package consolidates the L1-L3c 1D consolidation route history. It does
not contain new solver runs.

## Contents

- `l3e_case_inventory.csv`
- `l3e_summary_metrics.csv`
- `l3e_analytical_error_comparison.csv`
- `l3e_boundary_metrics_comparison.csv`
- `l3e_loading_route_comparison.csv`
- `l3e_cpu_gpu_comparison.csv`
- `figures/`

Regenerate the package from retained upstream CSVs:

```powershell
py -3 build_l3e_validation_package.py
```

## Main Conclusion

Use L3c as the current paper-compatible PR diffusion and initial-state
validation figure. L2 and L3b are stable reduced loading-route diagnostics, but
they are not strict Terzaghi validation because their load-generation routes
create large dynamic pore-pressure peaks.
