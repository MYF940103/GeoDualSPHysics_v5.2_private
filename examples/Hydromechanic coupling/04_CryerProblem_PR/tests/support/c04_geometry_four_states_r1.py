"""Compare P1 geometry at four saved C04 states without advancing the solution."""
import hashlib
import json
import argparse
import ctypes
from pathlib import Path
from time import perf_counter
import platform

from c04_weak_checkpoint_budget import Audit, surface_vol
from c04_weak_deformed_force import GEOM, recover, rms, scatter
from cryer_coupled_shell_modes import DAMP, DT, HYD, RHOW, T, np


TAG = "c04_geometry_four_states_r1"
STEPS = (4096, 4097, 4160, 36864)
TERMS = ("effective_stress", "pore_pressure", "external_traction", "sum")
SLOTS = ((0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (0, 2))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def measure(x, tet, orientation, cross):
    coords = x[tet]
    edge = coords[:, 1:] - coords[:, :1]
    if cross:
        a, b, c = edge.transpose(1, 0, 2)
        bc = np.cross(b, c)
        det = np.einsum("ij,ij->i", a, bc)
        weighted = np.stack((bc, np.cross(c, a), np.cross(a, b)), axis=1)
        weighted *= (orientation / 6)[:, None, None]
    else:
        det = np.linalg.det(edge)
        weighted = np.linalg.inv(edge).transpose(0, 2, 1) * (abs(det) / 6)[:, None, None]
    if not np.all(det * orientation > 0):
        raise ValueError("An element lost its reference orientation")
    return abs(det) / 6, np.concatenate((-weighted.sum(axis=1, keepdims=True), weighted), axis=1)


def surface_area(x, faces, sign):
    pts = x[faces]
    return (.5 * sign[:, None]) * np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0])


def force_terms(t, f, weighted, area, stress, p, n):
    internal = scatter(t, -np.einsum("tij,tkj->tki", stress[t].mean(axis=1), weighted), n)
    pore = scatter(t, p[t].mean(axis=1)[:, None, None] * weighted, n)
    load = scatter(f, np.broadcast_to((-10000 * area / 3)[:, None, :], (len(f), 3, 3)), n)
    return [internal, pore, load, internal + pore + load]


def delta_force(fixed, updated, m, v):
    da = (updated - fixed) / m.mass[:, None]
    return dict(fixed_component_rms_m_s2=rms(fixed / m.mass[:, None]),
                current_component_rms_m_s2=rms(updated / m.mass[:, None]),
                delta_component_rms_m_s2=rms(da), delta_component_max_m_s2=float(abs(da).max()),
                center18_delta_component_rms_m_s2=rms(da[m.shells == 1]),
                surface_delta_component_rms_m_s2=rms(da[m.surface]),
                delta_actual_v_power_W=float(np.sum((updated - fixed) * v)))


def hydraulics(audit, V, G, area, velocity, pressure, acceleration, is_open):
    t, f = audit.t, audit.f
    pt = pressure[t]
    # Subtraction makes a spatially constant pressure vanish exactly.
    gradp = np.einsum("tk,tkj->tj", pt - pt[:, :1], G) / V[:, None]
    face_gradient = -HYD * np.einsum("ij,ij->", gradp[audit.owner], area)
    face_inertia = -HYD * RHOW * np.einsum("ij,ij->", acceleration[f].mean(axis=1), area)
    pressure_row = HYD * np.einsum("tkj,tj->tk", G, gradp)
    inertia_row = HYD * RHOW * np.einsum("tkj,tj->tk", G, acceleration[t].mean(axis=1))
    vt = velocity[t]
    integrated_div = np.einsum("tkj,tkj->t", vt - vt[:, :1], G)
    div_row = np.broadcast_to(integrated_div[:, None] / 4, t.shape)
    st = audit.surf[t]
    # Negative eliminated-row residual gives the outward weak Dirichlet reaction.
    boundary = [-float(row[st].sum()) for row in (pressure_row, inertia_row, div_row)]
    outward = float(-np.einsum("ij,ij->", velocity[f].mean(axis=1), area))
    assert abs(outward + integrated_div.sum()) < 1e-14
    return dict(pressure_face_out_m3_s=float(face_gradient), inertia_face_out_m3_s=float(face_inertia),
                total_face_out_m3_s=float(face_gradient + face_inertia), contraction_rate_m3_s=outward,
                weak_out_by_pressure_inertia_volume_m3_s=boundary if is_open else None,
                weak_reaction_out_m3_s=sum(boundary) if is_open else None)


def time_geometry(x, t, f, orientation, face_sign):
    clocks = dict(inverse=[], cross=[], boundary=[])
    for order in (("inverse", "cross"), ("cross", "inverse"), ("inverse", "cross"), ("cross", "inverse")):
        for method in order:
            start = perf_counter()
            V, G = measure(x, t, orientation, method == "cross")
            clocks[method].append(perf_counter() - start)
            del V, G
        start = perf_counter()
        surface_area(x, f, face_sign)
        clocks["boundary"].append(perf_counter() - start)
    return clocks


def inspect(audit, step, old_budget, old_final):
    m, t, f = audit.m, audit.t, audit.f
    run = "cryer_weak_peak_r1" if step == 36864 else "cryer_weak_open_r1"
    path = T / "outputs" / run / f"state_{step}.npz"
    with np.load(path) as z:
        assert np.array_equal(z["ids"], m.ids) and int(z["step"]) == step
        assert Path(z["program"].item()).name == "cryer_weak_window.dll"
        p, s, u, v = (z[key] for key in ("p", "stress", "u", "v"))
        assert all(np.isfinite(array).all() for array in (p, s, u, v))
        assert step == 4096 or np.all(p[m.surface] == 0)
    sigma = np.empty((m.n, 3, 3))
    for k, (i, j) in enumerate(SLOTS):
        sigma[:, i, j] = sigma[:, j, i] = s[:, k]
    ref_t = m.x[t]
    orientation = np.sign(np.linalg.det(ref_t[:, 1:] - ref_t[:, :1]))
    x = m.x + u
    current_direct, direct = recover(x, orientation, t, f, s, p, sigma, audit.sign)
    Gdirect = direct.pop("registered_reference_gradients")
    V, G = measure(x, t, orientation, True)
    # Independent signed determinant using the reference shape gradients and stored u.
    grad_u = np.einsum("tki,tkj->tij", u[t], audit.G) / audit.V[:, None, None]
    jac = np.linalg.det(np.eye(3) + grad_u)
    Vcheck = audit.V * jac
    area = surface_area(x, f, audit.sign)
    current = force_terms(t, f, G, area, sigma, p, m.n)
    fixed = force_terms(t, f, audit.G, audit.area, sigma, p, m.n)
    trial_ref = (m.internal_stress(s), m.pressure_force(p), m.surface_force(10000.))
    ref_error = max(float(abs(a - b).max()) for a, b in zip(fixed, trial_ref))
    force_error = max(float(abs(a - b).max()) for a, b in zip(current, current_direct))
    G_error = float(abs(G - Gdirect).max())
    V_error = float(abs(V - Vcheck).max())
    assert G_error < 1e-16 and V_error < 1e-20 and max(ref_error, force_error) < 1e-12
    assert abs(V.sum() - surface_vol(x, f, area)) < 1e-15
    assert max(abs(row["error_J"]) for row in direct["six_work"]) < 1e-11
    assert np.max(abs(current[2][~audit.surf])) == 0
    delta = {name: delta_force(a, b, m, v) for name, a, b in zip(TERMS, fixed, current)}
    # Geometry substitutions compared to all terms evaluated on the current configuration.
    omitted = {key: rms((trial - current[3]) / m.mass[:, None]) for key, trial in (
        ("all_fixed", fixed[3]), ("current_faces_only", fixed[0] + fixed[1] + current[2]),
        ("current_bulk_only", current[0] + current[1] + fixed[2]),
        ("current_stress_and_faces", current[0] + fixed[1] + current[2]))}
    other_accel = audit.avacc(v) - DAMP * v
    a0 = fixed[3] / m.mass[:, None] + other_accel
    a1 = current[3] / m.mass[:, None] + other_accel
    H0 = hydraulics(audit, audit.V, audit.G, audit.area, v, p, a0, step > 4096)
    Hg = hydraulics(audit, V, G, area, v, p, a0, step > 4096)
    H1 = hydraulics(audit, V, G, area, v, p, a1, step > 4096)
    saved = old_budget[step]
    assert abs(H0["total_face_out_m3_s"] - saved["raw_one_sided_normal_Darcy_out_m3_s"]) < 1e-14
    if step > 4096:
        assert abs(H0["weak_reaction_out_m3_s"] - saved["weak_dirichlet_reaction_out_m3_s"]) < 1e-14
    if step == 36864:
        for key in TERMS:
            assert abs(delta[key]["delta_component_rms_m_s2"] -
                       old_final["difference"][key]["diff_component_RMS_m_s2"]) < 1e-10
    return dict(step=step, time_s=step * DT, tau_s=(step - 4096) * DT,
                input=str(path.relative_to(T)), sha256=digest(path), volume_m3=float(V.sum()),
                face_area_m2=float(np.linalg.norm(area, axis=1).sum()), element_J_range=[float(jac.min()), float(jac.max())],
                max_errors=dict(cross_vs_inverse_weighted_gradient_m2=G_error, volume_vs_reference_J_m3=V_error,
                                current_direct_vs_cross_N=force_error, fixed_vs_sparse_N=ref_error,
                                affine_virtual_work_J=max(abs(test["error_J"]) for test in direct["six_work"])),
                force=delta, mechanical_component_RMS_error_against_all_current_m_s2=omitted,
                hydraulic=dict(fixed=H0, current_geometry_same_acceleration=Hg, current_geometry_updated_mechanical_acceleration=H1),
                geometry_only_timing_seconds=time_geometry(x, t, f, orientation, audit.sign))


def plot(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    labels = [str(r["step"]) for r in rows[1:]]
    for key, label in zip(TERMS, ("Effective stress", "Pore pressure", "Face pressure", "Sum")):
        axes[0].plot(labels, [r["force"][key]["delta_component_rms_m_s2"] for r in rows[1:]], "o-", label=label)
    axes[0].set(yscale="log", ylabel="RMS acceleration change (m/s²)", xlabel="Completed step", title="Updating geometry at fixed state")
    for key, label in (("total_face_out_m3_s", "One-sided face flux"), ("weak_reaction_out_m3_s", "Weak reaction")):
        change = []
        for r in rows[1:]:
            h = r["hydraulic"]
            change.append(100 * (h["current_geometry_updated_mechanical_acceleration"][key] / h["fixed"][key] - 1))
        axes[1].plot(labels, change, "o-", label=label)
    axes[1].axhline(0, color="0.4", linewidth=.8)
    axes[1].set(ylabel="Outward discharge change (%)", xlabel="Completed step", title="Open surface, posterior acceleration")
    for ax in axes:
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    result = T / "logs" / (TAG + ".json")
    figure = T / "figures" / (TAG + ".png")
    if result.exists() or figure.exists():
        raise FileExistsError("Existing four-state evidence")
    prior = {}
    for name in ("opening", "peak"):
        p = T / "logs" / f"c04_weak_checkpoint_budget_{name}_r1.json"
        prior.update({r["step"]: r for r in json.loads(p.read_text())["checkpoints"]})
    old_final = json.loads((T / "logs/c04_weak_updated_force_r1.json").read_text())
    audit = Audit()
    rows = [inspect(audit, step, prior, old_final) for step in STEPS]
    report = dict(source_sha256=digest(Path(__file__)), reference_cache_sha256=digest(GEOM),
                  geometry=dict(nodes=audit.m.n, faces=len(audit.f), tetrahedra=len(audit.t),
                                initial_native_mass_kg=float(audit.m.mass.sum()), initial_native_volume_m3=float(audit.m.native_volume.sum()),
                                initial_facet_volume_m3=float(audit.V.sum())),
                  machine=platform.processor(), python=platform.python_version(), numpy=np.__version__,
                  scope="Saved spatial stress, pressure, velocity, displacement and original masses. Forcing is 10 kPa. Geometry and reconstructed mechanical acceleration vary independently. AV uses fixed geometry and saved v in both reconstructions. No pressure rounds, constitutive updates or time integration.",
                  timing_scope="Four alternating NumPy geometry-only wall times per state; memory allocation included. No force, Darcy, sparse assembly, solver or GPU time. Use the --timing-only run for a verified single-thread comparison.", states=rows)
    plot(rows, figure)
    with result.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, allow_nan=False)
    print(result)


def verify_timing():
    out = T / "logs" / (TAG + "_timing.json")
    if out.exists():
        raise FileExistsError(out)
    count = None
    for dll in sorted((Path(np.__file__).parent / ".libs").glob("*openblas*.dll")):
        lib = ctypes.CDLL(str(dll))
        for name in ("openblas_get_num_threads64_", "openblas_get_num_threads"):
            getter = getattr(lib, name, None)
            if getter:
                count = getter()
                break
        if count is not None:
            break
    if count != 1:
        raise RuntimeError(f"Start Python with OPENBLAS_NUM_THREADS=1; native Windows NumPy thread count was {count}")
    prior = T / "logs" / (TAG + ".json")
    old = json.loads(prior.read_text())
    with np.load(GEOM) as z:
        x0, ids, t, f, area = (z[key] for key in ("x0", "native_ids", "tets", "faces", "face_area_out"))
    ref = x0[t]
    orientation = np.sign(np.linalg.det(ref[:, 1:] - ref[:, :1]))
    face_sign = np.sign(np.einsum("ij,ij->i", surface_area(x0, f, np.ones(len(f))), area))
    clocks = []
    for state in old["states"]:
        path = T / state["input"]
        assert digest(path) == state["sha256"]
        with np.load(path) as z:
            assert np.array_equal(ids, z["ids"]) and int(z["step"]) == state["step"]
            x = x0 + z["u"]
        V0, G0 = measure(x, t, orientation, False)
        V1, G1 = measure(x, t, orientation, True)
        assert abs(V0 - V1).max() < 1e-20 and abs(G0 - G1).max() < 1e-16
        clocks.append(dict(step=state["step"], seconds=time_geometry(x, t, f, orientation, face_sign)))
    median = {key: float(np.median([v for s in clocks for v in s["seconds"][key]])) for key in ("inverse", "cross", "boundary")}
    report = dict(source_sha256=digest(Path(__file__)), frozen_state_receipt_sha256=digest(prior),
                  numpy_openblas_dll=dll.name, native_thread_getter=name, actual_threads=count,
                  machine=platform.processor(), python=platform.python_version(), numpy=np.__version__,
                  same_shape_warmup=True, samples=clocks, median_seconds=median,
                  inverse_over_cross_geometry_only=median["inverse"] / median["cross"],
                  scope="CPU NumPy geometry arrays and allocation only. Fixed connectivity and signed orientation. Excludes force, hydraulic assembly, solver and GPU kernels.")
    with out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing-only", action="store_true", help="Repeat geometry timing on the recorded inputs with a native thread-count check.")
    if parser.parse_args().timing_only:
        verify_timing()
    else:
        main()
