"""Apply the geometry-only fitted pair areas to the original, nonuniform saved stress."""
from upl_tpi_bed_pair_moments_r1 import solve
from upl_tpi_bottom_patch_r1 import DATA, FIG, TEST, PERIOD, Bed, ordered, read, require

import json
import numpy as np
import pandas as pd

TAG = "upl_tpi_bed_pair_replay_r1"


def evaluate(state, layer, bed, i, j, area):
    volume = bed.v0 * state["PoroVolumeRatio"]
    mass = volume * (1000. + (bed.rho0 - 1000.) / state["PoroVolumeRatio"])
    pressure = state["PorePress"].astype(float)
    sigma_xx = state["SigmaState_kk"][:, 0].astype(np.float32).astype(float)
    sigma_zz = state["SigmaState_kk"][:, 2].astype(np.float32).astype(float)
    sigma_xz = state["SigmaState_ij"][:, 2].astype(np.float32).astype(float)
    pore_edge = -(pressure[i] + pressure[j]) * area[:, 1]
    skeleton_edge = ((sigma_zz[i] + sigma_zz[j]) * area[:, 1]
                     + (sigma_xz[i] + sigma_xz[j]) * area[:, 0])

    def scatter(edges):
        return np.bincount(i, edges, minlength=1040) - np.bincount(j, edges, minlength=1040)

    def cut(edges, level):
        return float(np.sum(edges * ((layer[i] >= level).astype(int)
                                     - (layer[j] >= level).astype(int))) / PERIOD)

    result = {}
    for name, edges in (("effective", skeleton_edge), ("pore", pore_edge),
                        ("total", skeleton_edge + pore_edge)):
        for level, label in ((0, "bed"), (4, "outer"), (50, "middle")):
            result[f"{label}_{name}_Pa"] = cut(edges, level)
        result[f"first_row_{name}_az_m_s2"] = float(np.mean((scatter(edges) / mass)[layer == 0]))
    # Independent power assembly. Input a manufactured, smooth non-affine velocity and the
    # actual nonuniform total stress. Fixed nodes have zero velocity. Wall-side quadrature
    # participates in the adjoint deformation work, including its virtual stress state.
    pos = state["Posd"]
    x, z = pos[:, 0], pos[:, 2]
    velocity = np.column_stack((np.sin(2*np.pi*x/PERIOD) * z,
                                z * (np.cos(2*np.pi*x/PERIOD) - z)))
    velocity[layer < 0] = 0.
    stress = np.empty((1040, 2, 2))
    stress[:, 0, 0], stress[:, 1, 1] = sigma_xx-pressure, sigma_zz-pressure
    stress[:, 0, 1] = stress[:, 1, 0] = sigma_xz
    difference = velocity[j] - velocity[i]
    strain_volume = np.zeros_like(stress)
    for u in range(2):
        for v in range(2):
            work_edge = difference[:, u] * area[:, v]
            strain_volume[:, u, v] = np.bincount(i, work_edge, minlength=1040) + np.bincount(j, work_edge, minlength=1040)
    pair_force = np.einsum("eab,eb->ea", stress[i] + stress[j], area)
    external_power = sum(np.dot(velocity[:, u], scatter(pair_force[:, u])) for u in range(2))
    deformation_power = np.einsum("iab,iab->", stress, strain_volume)
    result["power_adjoint_absolute_W_per_m"] = abs(float(external_power + deformation_power))
    work_scale = float(np.abs(np.sum(difference * pair_force, axis=1)).sum())
    result["power_adjoint_relative_to_unsigned_pair_work"] = (
        result["power_adjoint_absolute_W_per_m"] / work_scale if work_scale else 0.)
    require(result["power_adjoint_relative_to_unsigned_pair_work"] < 1e-12, "Power identity failed")
    return result


def main():
    csv = FIG / (TAG + ".csv")
    receipt = TEST / "logs" / (TAG + ".check.json")
    require(not csv.exists() and not receipt.exists(), "This fresh review already exists")
    previous = pd.read_csv(FIG / "upl_tpi_bed_pair_moments_r1.csv", float_precision="round_trip")
    cuts = pd.read_csv(FIG / "upl_tpi_bottom_cut_r1.csv", float_precision="round_trip")
    bed = Bed(read(DATA / "Part_0000.bi4"))
    layer = np.rint(bed.z / .01 - .5).astype(int)
    results = []
    for part in previous.part.unique():
        frame = read(DATA / f"Part_{part:04d}.bi4")
        state = ordered(frame)
        time = float(frame["part"]["values"]["TimeStep"])
        for mode in ("raw", "bulk-normalized"):
            row = previous[(previous.part == part) & (previous.bulk == mode)].iloc[0]
            require(time == row.time_s, "Actual saved times differ")
            i, j, g, vol, coeff, normalization = solve(bed, state, layer, mode, replay=True)
            require(abs(normalization - row.normalization) < 1e-13, "Geometry normalization differs")
            require(abs(coeff.min() - row.min_coefficient) < 1e-11 and
                    abs(coeff.max() - row.max_coefficient) < 1e-11, "Shared coefficient fit changed")
            area = (vol[i] * vol[j])[:, None] * g
            original = evaluate(state, layer, bed, i, j, area)
            corrected = evaluate(state, layer, bed, i, j, coeff[:, None] * area)
            for label, level in (("bed", 0), ("outer", 4), ("middle", 50)):
                known = cuts[(cuts.part == part) & (cuts.operator == "native") & (cuts.cut == level)]
                require(abs(original[label+"_total_Pa"]/normalization-known.transmitted_Pa.item()) < 1e-8,
                        "Unmodified saved-field cut failed independent replay")
            for label in ("outer", "middle"):
                require(abs(corrected[label+"_total_Pa"]-original[label+"_total_Pa"]) < 1e-9,
                        "Local shared area changed an exterior cut")
            for name, metrics in (("before", original), ("after", corrected)):
                results.append(dict(part=int(part), time_s=time, bulk=mode, state=name, **metrics))
    pd.DataFrame(results).to_csv(csv, index=False)
    receipt.write_text(json.dumps(dict(frames=5, states_per_frame=4, frozen_geometry_only=True,
        max_relative_power_residual=max(v["power_adjoint_relative_to_unsigned_pair_work"] for v in results),
        final=[v for v in results if v["part"] == 1652], physical_gate_passed=False),
        indent=2, allow_nan=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
