"""How much of the baseline suction discrepancy is observable in Lian Fig. 16(a)?"""
import csv
import gzip
from collections import defaultdict
from pathlib import Path

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
FIELDS = TESTS/"figures/c08_psi25_tpi_fields/paper_surface_zero_r1/matched_particle_fields.csv.gz"
TAG = "TPI beta=0.04 (positive clamp)"
REFERENCE = "paper_range_equivalent_kPa_fig15_or_fig16a"


def main():
    groups=defaultdict(list)
    with gzip.open(FIELDS,"rt",newline="",encoding="utf8") as f:
        for row in csv.DictReader(f):
            if row["run"]==TAG and row["field"]=="p":
                groups[float(row["nominal_tau_s"])].append(row)
    output=[]
    for t,rows in sorted(groups.items()):
        ids=np.array([int(r["id"]) for r in rows])
        if len(ids)!=5000 or len(set(ids))!=5000:
            raise ValueError("Missing or duplicate soil samples")
        actual=np.array([float(r["native_value"]) for r in rows])
        printed=np.array([float(r[REFERENCE] or "nan") for r in rows])
        # Ignore the neighborhoods of both end colors when quoting paired pressure values.
        readable=np.isfinite(printed)&(printed> -9.5)&(printed<19.5)
        for limit in (-5,-10,-15,-20):
            low=actual<limit
            subset=readable&low
            y=printed[subset]
            delta=y-actual[subset]
            output.append(dict(nominal_tau_s=t,actual_tau_s=rows[0]["actual_tau_s"],threshold_kPa=limit,
                native_below=int(low.sum()),in_paper_mask=int(np.sum(low&np.isfinite(printed))),
                paper_near_lower_limit=int(np.sum(low&(printed<=-9.5))),common_readable=int(subset.sum()),
                native_median_common=float(np.median(actual[subset])) if y.size else "",
                print_median_common=float(np.median(y)) if y.size else "",
                median_print_minus_native_kPa=float(np.median(delta)) if y.size else "",
                print_minus_native_p10_kPa=float(np.percentile(delta,10)) if y.size else "",
                print_minus_native_p90_kPa=float(np.percentile(delta,90)) if y.size else ""))
    if not groups or not {0.5,1.2}.issubset(groups):
        raise ValueError("Incomplete Figure 16 times")
    with (TESTS/"figures/c08_positive_strain_balance/printed_band.csv").open("x",newline="",encoding="utf8") as f:
        out=csv.DictWriter(f,fieldnames=output[0]);out.writeheader();out.writerows(output)


if __name__=="__main__":
    main()
