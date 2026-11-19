"""First-order SPH divergence on measured Cryer geometry for known radial fields."""
import json
from cryer_shell_equilibrium import NATIVE, TESTS, TOTAL, SOIL, need, write
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

TAG = "cryer_shell_gradient_r1"
DP = .0025
H = .0045
AMPLITUDE = 1e-4


def main():
    dest = TESTS / "figures" / (TAG + ".csv")
    log = TESTS / "logs" / (TAG + ".check.json")
    need(not dest.exists() and not log.exists(), "Preserve prior analysis")
    ids = pd.read_csv(NATIVE / "native_ids.csv", float_precision="round_trip").iloc[SOIL]
    x = ids[["x0", "y0", "z0"]].to_numpy()
    volume = ids.initial_native_volume_m3.to_numpy()
    radii = np.linalg.norm(x, axis=1)
    shell = np.rint(radii / DP).astype(int)
    selected = np.flatnonzero(shell <= 10)
    native = np.memmap(NATIVE/"common26.bin", offset=12, dtype="<f8", mode="r",
                       shape=(577, 1+TOTAL*26))
    peak = native[417, 1:].reshape(TOTAL, 26)[SOIL]
    need(np.array_equal(native[0, 1:].reshape(TOTAL, 26)[SOIL, :3], x), "ID order")
    need(native[417, 0] == 417 * 2.**-13 and np.all(volume > 0), "Peak clock or volumes")
    # u=a*x*cos(k*r) gives div(u)=a*(3*cos(k*r) - k*r*sin(k*r)).
    # The alternating field is smooth at the origin, and contains no shell relabelling.
    fields = {}
    truth = {}
    for name, wave in (("affine", 0.), ("smooth", np.pi/(8*DP)), ("alternating", np.pi/DP)):
        phase = wave*radii
        fields[name] = AMPLITUDE * x * np.cos(phase)[:, None]
        truth[name] = AMPLITUDE * (3*np.cos(phase) - phase*np.sin(phase))
    fields["peak"] = peak[:, :3] - x
    tree = cKDTree(x)
    neighbors = tree.query_ball_point(x[selected], 2*H)
    theta = {name: np.empty(len(selected)) for name in fields}
    variation = np.empty(len(selected))
    neighbor_counts = []
    max_condition = 0.
    for s, (g, neighbor_list) in enumerate(zip(selected, neighbors)):
        other = np.array(sorted(neighbor_list))
        other = other[other != g]
        dx = x[other] - x[g]
        r = np.linalg.norm(dx, axis=1)
        # GetKernelWendland_Fac is proportional to (1-r/(2H))^3. The common
        # factor (including sign) cancels in the first-moment correction.
        weights = np.maximum(1-r/(2*H), 0)**3 * volume[other]
        neighbor_counts.append(np.count_nonzero(weights))
        moment = dx.T @ (weights[:, None]*dx)
        cond = np.linalg.cond(moment)
        need(np.isfinite(cond) and cond < 100, "Ill-conditioned moment at native ID "+str(g+8))
        max_condition = max(max_condition, cond)
        basis = np.linalg.solve(moment, (weights[:, None]*dx).T)
        for name, field in fields.items():
            grad = (field[other]-field[g]).T @ basis.T
            theta[name][s] = np.trace(grad)
            if name == "peak":
                variation[s] = np.linalg.det(np.eye(3)+grad)-1
    original_J = peak[selected, 8]-1
    rows = []
    for group in range(11):
        use = np.ones(len(selected), dtype=bool) if group == 0 else shell[selected] == group
        row = dict(group="all_inner_10_shells" if not group else str(group), count=int(sum(use)),
                   r_min_m=radii[selected[use]].min(), r_max_m=radii[selected[use]].max())
        for name in truth:
            target = truth[name][selected[use]]
            computed = theta[name][use]
            row[name+"_response_projection"] = np.dot(computed, target)/np.dot(target, target)
            row[name+"_normalized_rms_error"] = np.linalg.norm(computed-target)/np.linalg.norm(target)
            row[name+"_mean_div"] = computed.mean()
        row.update(peak_div_mean=theta["peak"][use].mean(), peak_det_minus_1_mean=variation[use].mean(),
                   saved_J_minus_1_mean=original_J[use].mean(),
                   peak_det_minus_J_rms=np.sqrt(np.mean((variation[use]-original_J[use])**2)))
        rows.append(row)
    affine_max = np.max(np.abs(theta["affine"]-truth["affine"][selected]))
    need(affine_max < 1e-15, "Affine reproduction")
    write(dest, rows)
    with log.open("x", encoding="utf8") as out:
        json.dump(dict(h_m=H, dp_m=DP, material_peak_part=417, sample_count=len(selected),
                       finite_moment_condition_max=max_condition, neighbors_min=int(min(neighbor_counts)),
                       neighbors_max=int(max(neighbor_counts)), affine_absolute_error_max=affine_max,
                       summaries=rows[:3], plot_data=dest.name,
                       scope="Frozen initial geometry, initial native volumes, analytic fields and actual total displacement; no time-integrator replay."),
                  out, indent=2, allow_nan=False)
    print(log)


if __name__ == "__main__":
    main()
