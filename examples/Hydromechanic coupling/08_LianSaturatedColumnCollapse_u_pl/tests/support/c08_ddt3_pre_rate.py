"""Evaluate the two gravity references on the retained psi2p5 PRE frame. No integration."""
from pathlib import Path
import csv
import json
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm
import numpy as np
from scipy.spatial import cKDTree

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from postprocess_lian_release import native, verify_source_material

BASE = CASE / "CaseLianCollapse_psi2p5_pre_GPU_out"
TAG = "c08_ddt3_pre_rate"
COMPONENTS = ("xx", "yy", "zz", "xy", "yz", "xz")


def run():
    meta, data = native(BASE / "data/Part_1000.bi4")
    verify_source_material(meta, "psi2p5")
    assert int(meta["Step"]) + 1 == 2_000_000 and abs(float(meta["TimeStep"]) - 10) < 1e-8
    assert np.array_equal(data["Idp"], np.arange(7060))
    take = data["Idp"] >= 2060
    ids = data["Idp"][take]
    xz = data["Posd"][take][:, [0, 2]]
    sig = np.column_stack((data["SigmaState_kk"][take], data["SigmaState_ij"][take])).astype("f4")
    rho = data["Rhop"][take]
    assert len(ids) == 5000 and np.isfinite(sig).all() and np.all(rho > 0)
    runlog = (BASE / "Run.out").read_text(encoding="utf-8", errors="replace")
    def logged(key):
        return float(re.search(r"^" + key + r"=([\-\d.eE+]+)", runlog, re.MULTILINE)[1])
    assert 'Kernel="Wendland"' in runlog and 'Damping' in runlog
    h = np.float32(logged("KernelH"))
    mass = np.float32(logged("MassFluid"))
    cs0 = np.float32(logged("Cs0"))
    rho0, rhow, gz, phi_deg = 2072.5, 1000., -9.81, 25.
    assert 'Gravity=(0,0,-9.81)' in runlog and 'PoreWaterRho: 1000.000000' in runlog
    phi = np.deg2rad(phi_deg)
    assert abs(float(re.search(r"Frictional Angle:\s+([\d.]+)", runlog)[1]) - phi) < 1e-6
    support = 2 * float(h)
    squared_support = np.float32(support**2)
    eta2 = np.float32((.1 * float(h))**2)
    bwen = np.float32(-2.7852 / float(h)**3)
    assert abs(float(bwen) - float(re.search(r"Wendland\.bwen=([\-\d.]+)", runlog)[1])) < .01
    k0 = np.float32(1 - np.sin(np.float32(phi)))
    tree = cKDTree(xz)
    pair = tree.query_pairs(support + 1e-7, output_type="ndarray")
    ii, jj = np.concatenate((pair[:, 0], pair[:, 1])), np.concatenate((pair[:, 1], pair[:, 0]))
    dr = (xz[ii] - xz[jj]).astype("f4")
    r2 = np.sum(dr * dr, axis=1)
    good = (r2 >= 1e-18) & (r2 <= squared_support)
    ii, jj, dr, r2 = ii[good], jj[good], dr[good], r2[good]
    r = np.sqrt(r2)
    q = r / h
    one = np.float32(1) - .5 * q
    gradfac = bwen * q * (one * one) * one / r
    dotgrad = np.sum(dr * (gradfac[:, None] * dr), axis=1)
    coef = np.float32(.1 * support) * cs0 * (mass / rho[jj]) / (r2 + eta2) * dotgrad
    real_diff = sig[ii] - sig[jj]
    directions = np.array([k0, k0, 1, 0, 0, 0], dtype="f4")
    rates = {}
    for name, reference in (("legacy", rho0), ("submerged", rho0 - rhow)):
        bg = np.float32(reference) * np.float32(gz) * dr[:, 1]
        terms = coef[:, None] * (real_diff + bg[:, None] * directions)
        rates[name] = np.column_stack([np.bincount(ii, weights=component, minlength=len(ids))
                                       for component in terms.T])
    rates["legacy_minus_submerged"] = rates["legacy"] - rates["submerged"]
    assert np.all(rates["legacy_minus_submerged"][:, 3:] == 0)
    # Geometric support on the last PRE. Both side walls still exist in this frame.
    surface = np.isin(data["FSType"][take], [2, 3]) & (data["FSNormal"][take, 2] > 0) & (xz[:, 1] > 1.)
    assert surface.any() and xz[surface, 0].ptp() > 3.5
    d_surface = cKDTree(xz[surface]).query(xz)[0]
    d_wall = np.minimum.reduce((np.abs(xz[:, 0]), np.abs(4-xz[:, 0]), np.abs(xz[:, 1])))
    # Exclude angular holes from the geometrically interior set.
    angles = np.arctan2(dr[:, 1], dr[:, 0])
    order = np.lexsort((angles, ii))
    counts = np.bincount(ii, minlength=len(ids))
    assert np.all(counts > 0)
    gap = np.array([np.diff(np.r_[a, a[0] + 2*np.pi]).max()
                    for a in np.split(angles[order], np.cumsum(counts)[:-1])])
    zones = {"all": np.ones(len(ids), bool),
             "interior_above_2h_full_angular_support": (d_wall > support) & (d_surface > support) & (gap < np.pi/2),
             "top_free_surface_within_2h": d_surface <= support,
             "pre_wall_within_2h": d_wall <= support,
             "bed_within_2h": np.abs(xz[:, 1]) <= support,
             "left_wall_within_2h": np.abs(xz[:, 0]) <= support,
             "right_wall_within_2h": np.abs(4 - xz[:, 0]) <= support}
    folder = CASE / "tests/figures"
    with (folder / (TAG + "_summary.csv")).open("w", newline="", encoding="utf8") as handle:
        w = csv.writer(handle)
        w.writerow(("region", "count", "reference", "component", "mean_Pa_s", "rms_Pa_s", "p95_abs_Pa_s",
                    "min_Pa_s", "max_Pa_s"))
        for zone, mask in zones.items():
            for ref, values in rates.items():
                for comp, column in zip(COMPONENTS, values.T):
                    v = column[mask]
                    w.writerow((zone, len(v), ref, comp, v.mean(), np.sqrt(np.mean(v*v)),
                                np.percentile(abs(v), 95), v.min(), v.max()))
    fields = [("id", ids), ("x_m", xz[:, 0]), ("z_m", xz[:, 1]), ("n_soil_neighbors", counts),
              ("largest_angle_gap_deg", np.rad2deg(gap)), ("dist_surface_m", d_surface),
              ("dist_wall_m", d_wall)]
    fields += [(ref + "_" + comp + "_Pa_s", col) for ref, vals in rates.items()
               for comp, col in zip(COMPONENTS, vals.T)]
    np.savetxt(folder / (TAG + "_fields.csv"), np.column_stack([v for _, v in fields]),
               delimiter=",", fmt="%.12g", comments="", header=",".join(k for k, _ in fields))
    fig, axes = plt.subplots(3, 1, sharex=True, sharey=True, figsize=(8, 10), layout="constrained")
    vmax = max(np.abs(v[:, 2]).max() for v in rates.values()) / 1000.
    for ax, (label, vals) in zip(axes, rates.items()):
        sc = ax.scatter(*xz.T, c=vals[:, 2]/1000., cmap="RdBu_r",
                        norm=SymLogNorm(linthresh=1., vmin=-vmax, vmax=vmax), s=3)
        ax.set_aspect("equal")
        ax.set(ylabel="z [m]", title=label.replace("_", " "))
    axes[-1].set_xlabel("x [m]")
    fig.colorbar(sc, ax=axes, label="Effective vertical stress diffusion rate [kPa/s]")
    fig.suptitle("C08 psi = +2.5 deg | retained 10 s preload")
    fig.savefig(folder / (TAG + ".png"), dpi=175)
    plt.close(fig)
    record = {"source": str((BASE / "data/Part_1000.bi4").relative_to(CASE)), "time_s": float(meta["TimeStep"]),
              "completed_steps": int(meta["Step"])+1, "soil_particles": len(ids), "directed_pairs": len(ii),
              "upward_native_surface_particles": int(surface.sum()), "source_run": str((BASE / "Run.out").relative_to(CASE)),
              "component_order": COMPONENTS, "support_m": support, "Cs0_m_s": float(cs0), "nominal_mass": float(mass),
              "eta2_m2": float(eta2), "bwen": float(bwen), "DensityDTvalue": .1, "K0": float(k0),
              "rho0": rho0, "rhow": rhow, "gravity_z": gz, "phi_deg": phi_deg,
              "scope": "Frozen PRE, ordered soil pairs only. Same velocities, geometry, nominal mass/rho and six effective stress values in both variants. Float pair terms summed in float64, without GPU cell/atomic/reduction ordering, material return, velocity, projection, or solver write gate. Submerged reference subtracts constant reference water density only; neither variant is a time integration.",
              "regions": "PRE has three walls. Euclidean distance to native upward surface nodes and analytic x=0/4,z=0 wall planes. Interior >2H to all four limits, additionally maximum soil-neighbour angular gap <90 deg. Near-wall and near-FS zones overlap at corners."}
    (CASE / "tests/logs" / (TAG + ".json")).write_text(json.dumps(record, indent=2)+"\n", encoding="utf8")


if __name__ == "__main__":
    run()
