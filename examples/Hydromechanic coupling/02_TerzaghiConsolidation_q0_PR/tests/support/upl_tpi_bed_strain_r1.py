"""Compare constrained elastic stress, integrated native volume and material spacing in C02."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

TEST = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_bed_strain_r1"


def main():
    csv = TEST / "figures" / (TAG + ".csv")
    check = TEST / "logs" / (TAG + ".check.json")
    if csv.exists() or check.exists():
        raise RuntimeError("Preserve the existing result")
    retained = TEST / "figures/upl_tpi_p3_full_physics_r1.layers.csv.gz"
    profiles = pd.read_csv(retained, float_precision="round_trip").sort_values(["part", "initial_layer"])
    if len(profiles) != 1653 * 100:
        raise ValueError("Incomplete profiles")
    report = (TEST / "outputs/upl_tpi_p3_B10us_full2tv_GPU_r1/Run.out").read_text(encoding="utf-8", errors="replace")
    def get_modulus(label):
        return float(re.search(r"^\s*" + label + r" Modulus:\s+([\d.]+)\s*$", report, re.MULTILINE).group(1))
    bulk, shear = get_modulus("Bulk"), get_modulus("Shear")
    constrained = bulk + 4 * shear / 3
    def field(col):
        return profiles[col].to_numpy().reshape(1653, 100)
    z0 = field("z0_m")
    z = z0 - field("settlement_mm") * .001
    if not np.all(np.diff(z, axis=1) > 0) or not np.all(z[:, 0] > 0):
        raise ValueError("Material layer order lost")
    J = field("J")
    ln_J = np.log(J)
    stress = field("effective_zz_Pa")
    trace = sum(field("effective_"+k+"_Pa") for k in ("xx", "yy", "zz"))
    pore = field("pressure_Pa")
    stress_gap = stress - constrained * ln_J
    # In 1D plane strain the physical J averaged over a material interval equals
    # current length/reference length. A layer J is a nodal value, so the interval
    # comparisons are quadrature diagnostics and are never input to the integrator.
    stretch = np.diff(z, axis=1) / np.diff(z0, axis=1)
    interval_J = .5 * (J[:, 1:] + J[:, :-1])
    # Independent one-dimensional reconstruction: assign each cell its ID-layer mean J.
    # Integrate across complete cells plus half of the target cell to reach its center.
    dp = float(np.median(np.diff(z0[0])))
    displacement_J = dp * (np.cumsum(J-1., axis=1) - .5*(J-1.))
    displacement_gap_mm = 1000 * ((z-z0) - displacement_J)
    hist = pd.DataFrame(dict(part=field("part")[:, 0],time_s=field("time_s")[:, 0],
        bed_recorded_sigma_eff_Pa=stress[:, 0],bed_pore_Pa=pore[:, 0],
        bed_sigma_eff_minus_MlnJ_Pa=stress_gap[:, 0],
        max_layer_abs_sigma_eff_minus_MlnJ_Pa=np.max(abs(stress_gap),axis=1),
        max_layer_abs_mean_stress_minus_KlnJ_Pa=np.max(abs(trace/3-bulk*ln_J),axis=1),
        bed_native_J=J[:, 0],bed_half_cell_geometric_stretch=z[:, 0]/z0[:, 0],
        first_center_interval_stretch=stretch[:, 0],first_interval_endpoint_J_mean=interval_J[:, 0],
        middle_center_interval_stretch=stretch[:, 49],middle_interval_endpoint_J_mean=interval_J[:, 49],
        bed_dz_minus_J_integral_mm=displacement_gap_mm[:, 0],
        top_dz_minus_J_integral_mm=displacement_gap_mm[:, -1],
        max_layer_abs_dz_minus_J_integral_mm=np.max(abs(displacement_gap_mm),axis=1),
        bed_J_for_uniform_total_stress=np.exp((-10000.+pore[:, 0])/constrained)))
    if hist.part.iloc[-1] != 1652 or hist.time_s.iloc[-1] != 72.88428815806371 or not np.isfinite(hist).all().all():
        raise ValueError("Invalid C02 chronology or metrics")
    hist.to_csv(csv, index=False)
    check.write_text(json.dumps(dict(frames=len(hist),material_layers=100,bulk_Pa=bulk,shear_Pa=shear,
        constrained_Pa=constrained,final=hist.iloc[-1].to_dict(),
        max_all_saved_abs_sigma_eff_minus_MlnJ_Pa=float(np.abs(stress_gap).max()),
        max_all_saved_abs_mean_stress_minus_KlnJ_Pa=float(abs(trace/3-bulk*ln_J).max()),
        physical_acceptance=False),indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
