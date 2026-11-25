"""Summarize the retained +2.5 degree material-point and time-history CSVs."""
import csv
from pathlib import Path

import numpy as np


CASE = Path(__file__).resolve().parents[2]
FORMAL = CASE / "figures/validation_explicit"
TEST = CASE / "tests/figures/c08_ddt3_psi2p5"
OUTPUT = FORMAL / "psi2p5_ddt3_comparison"
PARTICLES = 5000


def read_csv(path):
    return np.genfromtxt(path, names=True, delimiter=",", encoding="utf8")


def write_csv(name, rows):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / name).open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    field = read_csv(TEST / "comparison_material.csv")
    histories = {0: read_csv(FORMAL / "psi2p5/history.csv"), 3: read_csv(TEST / "collapse/history.csv")}
    if len(histories[0]) != 301 or any(
        not np.array_equal(histories[0][name], histories[3][name])
        for name in ("part", "time_s", "tau_s", "completed_step")
    ):
        raise ValueError("Collapse histories must share all 301 saved clocks and steps")
    if len(field) != 8 * PARTICLES:
        raise ValueError("Expected four saved fields per setting")
    sampled = []
    extrema = []
    for setting, h in histories.items():
        # Keep each run's own 0.3 s positions as the reference for subsequent particle motion.
        base_positions = None
        for part, nominal in ((30, .3), (60, .6), (120, 1.2), (300, 3.)):
            rows = field[(field["DensityDT"] == setting) & (field["nominal_tau_s"] == nominal)]
            rows.sort(order="id")
            if not np.array_equal(rows["id"], np.arange(2060, 2060 + PARTICLES)):
                raise ValueError("Saved material IDs differ")
            r = h[part]
            # Material CSV uses 12 significant digits. History CSV retains the native clock.
            if not np.allclose(rows["actual_tau_s"], r["tau_s"], rtol=0, atol=5e-12):
                raise ValueError("Material CSV and history time differ")
            pos = np.column_stack((rows["x_m"], rows["z_m"]))
            if base_positions is None:
                base_positions = pos.copy()
            movement = np.linalg.norm(pos - base_positions, axis=1) * 1000
            nn = rows["nearest_over_dp"]
            if abs(np.quantile(nn, .05) - r["nearest_p05_dp"]) > 1e-10:
                raise ValueError("Published 5th percentile distance differs from the material CSV")
            item = dict(DensityDT=setting, nominal_tau_s=nominal, actual_tau_s=r["tau_s"],
                        completed_step=int(r["completed_step"]), soil_points=len(pos),
                        nn_p01_dp=np.quantile(nn,.01), nn_p05_dp=np.quantile(nn,.05),
                        nn_median_dp=np.median(nn), nn_min_dp=nn.min(),
                        count_nn_below_0p5dp=int((nn < .5).sum()),
                        displacement_from_0p3s_median_mm=np.median(movement),
                        displacement_from_0p3s_p95_mm=np.quantile(movement,.95),
                        displacement_from_0p3s_max_mm=movement.max(),
                        front_id=int(rows["id"][np.argmax(pos[:,0])]))
            for name in ("height_m", "front_x_m", "runout_m", "top_settlement_mm", "mean_settlement_mm",
                         "bottom_settlement_mm", "kappa_mean", "kappa_max", "kappa_nonzero", "J_min", "J_max"):
                item[name] = r[name]
            sampled.append(item)
        below = h["nearest_below_half_dp"] > 0
        closest = int(np.argmin(h["nearest_min_dp"]))
        extrema.append(dict(DensityDT=setting, frames=len(h),
                            closest_nn_dp=h["nearest_min_dp"][closest], closest_tau_s=h["tau_s"][closest],
                            max_particles_below_0p5dp=int(h["nearest_below_half_dp"].max()),
                            frames_with_nn_below_0p5dp=int(below.sum()),
                            first_tau_below_0p5dp_s=h["tau_s"][below][0] if below.any() else "",
                            last_tau_below_0p5dp_s=h["tau_s"][below][-1] if below.any() else "",
                            peak_kinetic_energy_J_per_m=h["kinetic_energy_J_per_m"].max(),
                            peak_kinetic_tau_s=h["tau_s"][np.argmax(h["kinetic_energy_J_per_m"])],
                            peak_speed_m_s=h["speed_max_m_s"].max(),
                            last_second_front_advance_m=h["front_x_m"][-1]-h["front_x_m"][200]))
    write_csv("material_samples.csv", sampled)
    write_csv("material_extrema.csv", extrema)


if __name__ == "__main__":
    main()
