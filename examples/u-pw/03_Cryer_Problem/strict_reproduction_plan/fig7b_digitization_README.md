# Figure 7B Digitization Inputs

No digitized Figure 7B data is currently available in this directory.

If digitized data is added later, use one CSV per Poisson ratio:

- `digitized_Fig7B_nu01.csv`
- `digitized_Fig7B_nu02.csv`
- `digitized_Fig7B_nu03.csv`
- `digitized_Fig7B_nu045.csv`

Required columns:

```csv
Tv,normalized_center_pressure
```

When these files are present, `cryer_reference_solution.py` will read them and
write `cryer_reference_fig7b_validation.csv` with pointwise errors. Until then,
the generated curves are analytical reference candidates, not a completed
Figure 7B validation.
