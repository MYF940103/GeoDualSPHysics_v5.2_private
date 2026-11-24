"""Measure stress gradients and compare volume weights in the saved positive-angle preload."""
import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


CASE = Path(__file__).resolve().parents[2]
FIELD_CSV = CASE / "figures/validation_explicit/psi2p5/preload/fields.csv"
DEFINITION = CASE / "CaseLianCollapse_psi2p5_pre_Def.xml"
RESULT = CASE / "tests/figures/c08_ddt3_prestress_review.csv"


def gradient(values, z):
    dz = z - z.mean()
    centered = values - values.mean()
    slope = np.dot(dz, centered) / np.dot(dz, dz)
    residual = centered - slope * dz
    return slope, np.sqrt(np.mean(residual**2))


def main():
    xml = ET.parse(DEFINITION)
    rho0 = float(xml.find(".//constantsdef/rhop0").get("value"))
    gravity = float(xml.find(".//constantsdef/gravity").get("z"))
    water = float(xml.find(".//hydromechanics/PoreWaterRho").get("value"))
    phi = float(xml.find(".//soils/phi").get("value"))
    bulk = -rho0 * gravity * .001
    submerged = -(rho0 - water) * gravity * .001
    k0 = 1 - math.sin(math.radians(phi))
    with FIELD_CSV.open(encoding="utf-8-sig", newline="") as source:
        rows = [r for r in csv.DictReader(source) if int(r["part"]) == 1000]
    ids = sorted(int(r["id"]) for r in rows)
    times = {float(r["time_s"]) for r in rows}
    if ids != list(range(2060, 7060)) or len(times) != 1:
        raise ValueError("Expected the complete last PRE frame with 5000 known soil IDs")
    fields = {key: np.array([float(r[key]) for r in rows]) for key in (
        "x_m", "z_m", "sigma_eff_zz_kPa", "sigma_total_zz_kPa", "sigma_eff_xx_kPa",
        "p_kPa", "J", "rho_mix_kg_m3")}
    if not all(np.isfinite(v).all() for v in fields.values()):
        raise ValueError("Nonfinite native fields")
    if not np.allclose(fields["sigma_eff_zz_kPa"] - fields["p_kPa"], fields["sigma_total_zz_kPa"],
                       rtol=0, atol=2e-12):
        raise ValueError("Stored compression sign convention does not match total stress")
    # V0=m0/rho0; this signed relative difference needs neither a guessed mass nor a 2D thickness.
    relative = rho0 / (fields["rho_mix_kg_m3"] * fields["J"]) - 1.0
    x, z = fields["x_m"], fields["z_m"]
    masks = {"all_soil": np.ones(len(rows), dtype=bool),
             "interior_0.5<x<3.5_0.3<z<1.7_m": (x > .5) & (x < 3.5) & (z > .3) & (z < 1.7)}
    results = []
    for label, mask in masks.items():
        dz = z[mask]
        row = dict(mask=label, part=1000, actual_time_s=float(rows[0]["time_s"]),
                   count=int(mask.sum()), rho0_kg_m3=rho0, water_kg_m3=water, gravity_z_m_s2=gravity,
                   bulk_background_kPa_m=bulk, submerged_background_kPa_m=submerged,
                   hydrostatic_pressure_slope_kPa_m=water*gravity*.001,
                   lateral_bulk_background_kPa_m=k0*bulk, lateral_submerged_background_kPa_m=k0*submerged)
        for key in ("sigma_eff_zz_kPa", "p_kPa", "sigma_total_zz_kPa", "sigma_eff_xx_kPa"):
            slope, rms = gradient(fields[key][mask], dz)
            row[key+"_slope_per_m"] = slope
            row[key+"_residual_rms"] = rms
        row["effective_zz_slope_minus_bulk_kPa_m"] = row["sigma_eff_zz_kPa_slope_per_m"] - bulk
        row["effective_zz_slope_minus_submerged_kPa_m"] = row["sigma_eff_zz_kPa_slope_per_m"] - submerged
        signed_percent = 100 * relative[mask]
        row.update(m0_over_rho_vs_V0J_min_pct=signed_percent.min(),
                   m0_over_rho_vs_V0J_mean_pct=signed_percent.mean(),
                   m0_over_rho_vs_V0J_max_pct=signed_percent.max(),
                   m0_over_rho_vs_V0J_max_absolute_pct=np.abs(signed_percent).max(),
                   J_min=fields["J"][mask].min(), J_max=fields["J"][mask].max())
        results.append(row)
    with RESULT.open("w", encoding="utf-8", newline="") as dest:
        writer = csv.DictWriter(dest, list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(RESULT)


if __name__ == "__main__":
    main()
