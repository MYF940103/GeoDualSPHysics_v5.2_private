"""Evaluate a face-integrated weak stress divergence on the original Cryer sphere."""
import argparse
import json

from cryer_shell_equilibrium import TESTS, Reference, Q, R, T_D, need
from cryer_peak_paired_manufactured import radial_state
from cryer_p3_peak_shells import ordered
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, vstack
from scipy.spatial import cKDTree, ConvexHull

TAG = "cryer_smoothed_traction_r1"
PARTS = (139, 416, 512)


def quadrature_surface(directions):
    hull = ConvexHull(directions)
    tri = hull.simplices.copy()
    a, b, c = directions[tri].transpose(1, 0, 2)
    inward = np.einsum("ij,ij->i", a, np.cross(b, c)) < 0
    tri[inward] = tri[inward][:, [0, 2, 1]]
    a, b, c = directions[tri].transpose(1, 0, 2)
    area = .5*np.cross(b-a, c-a)
    vol = np.einsum("ij,ij->i", a, np.cross(b, c))/6
    # For each oriented edge, the second incident cell sees the opposite area vector.
    edges = np.stack((tri, np.roll(tri, -1, axis=1)), axis=-1).reshape(-1, 2)
    key = np.sort(edges, axis=1)
    order = np.lexsort((key[:, 1], key[:, 0])).reshape(-1, 2)
    left, right = order.T
    need(np.array_equal(edges[left], edges[right, ::-1]) and np.min(vol) > 0,
         "Outward closed angular triangulation")
    u, v = directions[edges[left]].transpose(1, 0, 2)
    return a+b+c, area, vol, u+v, -.5*np.cross(u, v), left//3, right//3, tri


def shapes(points, tree, h, stats):
    blocks = []
    for start in range(0, len(points), 256):
        queries = points[start:start+256]
        donors = tree.query_ball_point(queries, 2*h)
        counts = np.array([len(ids) for ids in donors])
        rows = np.repeat(np.arange(len(queries)), counts)
        cols = np.concatenate(donors).astype(np.int32)
        offsets = (tree.data[cols]-queries[rows])/h
        lengths = np.linalg.norm(offsets, axis=1)
        weight = (1-lengths/2)**4*(1+2*lengths)
        design = np.column_stack((np.ones(len(cols)), offsets))
        boundaries = np.r_[0, np.cumsum(counts)]
        moments = np.empty((len(queries), 4, 4))
        for j in range(4):
            for k in range(j+1):
                moments[:, j, k] = moments[:, k, j] = np.bincount(
                    rows, weights=weight*design[:, j]*design[:, k], minlength=len(queries))
        rhs = np.zeros((len(queries), 4, 1))
        rhs[:, 0] = 1
        fit = np.linalg.solve(moments, rhs)[:, :, 0]
        phi = weight*np.einsum("ij,ij->i", design, fit[rows])
        check = np.add.reduceat(phi[:, None]*design, boundaries[:-1], axis=0)
        stats["max_shape_reproduction_error"] = max(stats["max_shape_reproduction_error"],
                                                    float(np.max(abs(check-rhs[:, :, 0]))))
        stats["min_donors"] = min(stats["min_donors"], int(counts.min()))
        blocks.append(csr_matrix((phi, cols, boundaries), shape=(len(queries), tree.n)))
    return vstack(blocks, format="csr")


def main(output, boundary_nodes=False):
    tag = TAG+"_surface_nodes" if boundary_nodes else TAG
    folder = TESTS/"figures"
    files = [folder/(tag+suffix) for suffix in ("_shells.csv", ".png")]
    receipt = TESTS/"logs"/(tag+".check.json")
    need(not any(f.exists() for f in [*files, receipt]), "Preserve existing results")
    native = ordered(output/"data", 0, ["Posd", "FSType", "PoroCurrentVolume", "PoroMixtureDensity"])
    x = native["Posd"]
    radii = np.linalg.norm(x, axis=1)
    shell = np.rint(radii/.0025).astype(int)
    soil_volume = native["PoroCurrentVolume"]
    mass = soil_volume*native["PoroMixtureDensity"]
    surface = np.isin(native["FSType"], (2, 3))
    need(np.array_equal(surface, shell == 20) and surface.sum() == 5153, "Initial drained shell")
    er = x/radii[:, None]
    tri_sum, cap, unit_vol, edge_sum, side, left, right, tri = quadrature_surface(er[surface])
    tree = cKDTree(x)
    affine = np.array([[.2, .4, .3], [-.7, .1, .6], [.35, -.15, .8]])
    # Exercise the adjoint with an additional non-affine velocity field.
    vtest = x@affine.T + np.column_stack((x[:, 1]*x[:, 2], x[:, 2]**2, x[:, 0]**2))/R
    ref = Reference(.3, finite=False)
    ref.cv = ref.H*ref.kappa
    ref.decay = ref.xi**2*ref.cv/R**2
    shell_radii = np.arange(1, 21)*.0025
    tensors = []
    for part in PARTS:
        p, rr, tt, _ = radial_state(ref, shell_radii, part*2**-13-T_D)
        tensors.append((Q-p+tt)[shell-1, None, None]*np.eye(3) +
                       (rr-tt)[shell-1, None, None]*er[:, :, None]*er[:, None, :])
    # Uniform stress is kept explicit here to test its nodal cancellation with surface traction.
    tensors.append(np.broadcast_to(np.eye(3)*Q, (len(x), 3, 3)))
    t = np.stack(tensors, axis=1)
    trials = t.shape[1]
    stats = dict(max_shape_reproduction_error=0., min_donors=len(x))
    force = np.zeros((len(x), trials, 3))
    internal_power = np.zeros(trials)
    test_grad_inner = np.zeros((len(x), 3, 3))
    quadrature_weight = np.zeros(len(x))
    surface_area_at_nodes = np.zeros_like(x)
    h = float(np.float32(.0045))
    prior_s = np.zeros((len(cap), trials, 3, 3))
    prior_face_v = np.zeros_like(cap)
    for band in range(1, 21):
        lo, hi = (band-1)*.0025, band*.0025
        volume = unit_vol*(hi**3-lo**3)
        cell_x = .25*(hi**4-lo**4)/(hi**3-lo**3)*tri_sum
        cap_x = hi*tri_sum/3
        side_x = ((hi**3-lo**3)/(hi**2-lo**2))*edge_sum/3
        wc = shapes(cell_x, tree, h, stats)
        stress = (wc@t.reshape(len(x), -1)).reshape(len(cap), trials, 3, 3)
        quadrature_weight += wc.T@volume
        # Combine fluxes across shared faces before transferring them to material points.
        if band > 1:
            traction = np.einsum("ntij,nj->nti", stress-prior_s, cap*lo**2)
            force += (prior_cap.T@traction.reshape(len(cap), -1)).reshape(force.shape)
        ws = shapes(side_x, tree, h, stats)
        side_area = side*(hi**2-lo**2)
        traction = np.einsum("ntij,nj->nti", stress[right]-stress[left], side_area)
        force += (ws.T@traction.reshape(len(side), -1)).reshape(force.shape)
        if boundary_nodes and band == 20:
            ids = np.flatnonzero(surface)[tri]
            wcap = csr_matrix((np.full(ids.size, 1/3), (np.repeat(np.arange(len(ids)), 3), ids.ravel())),
                              shape=(len(ids), len(x)))
        else:
            wcap = shapes(cap_x, tree, h, stats)
        cap_v = wcap@vtest
        side_v = ws@vtest
        grad_int = ((cap_v[:, :, None]*hi**2-prior_face_v[:, :, None]*lo**2)
                    *cap[:, None, :])
        side_outer = side_v[:, :, None]*side_area[:, None, :]
        np.add.at(grad_int, left, side_outer)
        np.add.at(grad_int, right, -side_outer)
        internal_power -= np.einsum("ntij,nij->t", stress, grad_int)
        test_grad_inner += (wc.T@grad_int.reshape(len(cap), 9)).reshape(len(x), 3, 3)
        if band == 20:
            cap_area = cap*hi**2
            outer_tr = -np.einsum("ntij,nj->nti", stress, cap_area)
            force += (wcap.T@outer_tr.reshape(len(cap), -1)).reshape(force.shape)
            surface_area_at_nodes = wcap.T@cap_area
        prior_s, prior_cap, prior_face_v = stress, wcap, cap_v
    integrated_volume = float(np.sum(unit_vol)*R**3)
    need(abs(quadrature_weight.sum()/integrated_volume-1)<1e-11 and
         stats["max_shape_reproduction_error"] < 1e-10, "Volume and affine basis")
    work_at_nodes = np.einsum("nti,ni->t", force, vtest)
    adjoint_from_nodes = -np.einsum("ntij,nij->t", t, test_grad_inner)
    power_error = max(np.max(abs(work_at_nodes-internal_power)),
                      np.max(abs(work_at_nodes-adjoint_from_nodes)))
    # T=+qI internal traction and explicitly assigned +q n surface load cancel per particle.
    patch_error = float(np.max(abs(force[:, -1]+Q*surface_area_at_nodes)))
    netforce = np.linalg.norm(force.sum(axis=0), axis=1)
    torque = np.linalg.norm(np.cross(x[:, None, :], force).sum(axis=0), axis=1)
    need(power_error<1e-9 and patch_error<1e-10 and
         np.max(netforce)<1e-8 and np.max(torque)<1e-9, "Virtual work, traction and rigid modes")
    rows = []
    for trial, part in enumerate(PARTS):
        acc = force[:, trial]/mass[:, None]
        for label, select in [("all", shell>0), ("inner10", shell<=10),
                              *[(str(j), shell==j) for j in range(1, 21)]]:
            magnitude = np.linalg.norm(acc[select], axis=1)
            rows.append(dict(part=part, tau_s=part*2**-13-T_D, shell=label,
                             ids=int(select.sum()), rms_m_s2=float(np.sqrt(np.mean(magnitude**2))),
                             max_m_s2=float(np.max(magnitude))))
    df = pd.DataFrame(rows)
    df.to_csv(files[0], index=False)
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for part, group in df[df.shell.str.isnumeric()].groupby("part"):
        r = group.shell.astype(int)/20
        axs[0].plot(r, group.rms_m_s2, marker=".", label=f"{group.tau_s.iloc[0]*1000:.2f} ms")
    baseline = pd.read_csv(folder/"cryer_peak_paired_manufactured_r1_shells.csv")
    for label, group in baseline[baseline.geometry=="initial_reference_sphere"].groupby("operator"):
        axs[1].plot(group.r0_over_a, group.vector_rms_m_s2, marker=".", label=label.replace("_", " "))
    peak = df[(df.part==416)&(df.shell.str.isnumeric())]
    axs[1].plot(peak.shell.astype(int)/20, peak.rms_m_s2, marker="s", ms=3, label="Integrated weak form")
    for axis, title in zip(axs, ("Weak form at three drainage-relative times", "Matched manufactured peak field")):
        axis.set(xlabel="Initial material radius / sphere radius", ylabel="RMS acceleration (m/s²)", title=title)
        axis.grid(alpha=.25); axis.legend()
    fig.savefig(files[1], dpi=160)
    plt.close(fig)
    doc = dict(parts=PARTS, material_ids=len(x), outer_ids=int(surface.sum()), cells=len(cap)*20,
               max_virtual_power_difference_W=float(power_error), net_force_N=netforce.tolist(),
               net_torque_Nm=torque.tolist(), max_uniform_patch_difference_N=patch_error,
               hull_volume_m3=integrated_volume, original_particle_volume_m3=float(soil_volume.sum()),
               min_geometric_weight_m3=float(quadrature_weight.min()),
               nonpositive_geometric_weights=int(np.sum(quadrature_weight<=0)),
               quantiles_geometric_to_native_volume=np.quantile(quadrature_weight/soil_volume,[0,.01,.5,.99,1]).tolist(),
               field="Analytical pressure and effective stress on the initial native positions. Original mass divides the forces.",
               scope="Reference-configuration offline weak operator. Geometric nodal work volume differs from the material volume used for storage and inertia.",
               **stats)
    with receipt.open("x", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, allow_nan=False)
    print(json.dumps(doc, indent=2))
    print(df[df.shell.isin(("all", "1", "20"))].to_string(index=False))


def exterior_work(output):
    """Compare MLS exterior interpolation with strictly surface-supported traction."""
    target = TESTS/"logs"/(TAG+".surface.json")
    need(not target.exists(), "Preserve existing exterior review")
    native = ordered(output/"data", 0, ["Posd", "FSType"])
    x = native["Posd"]
    ids = np.flatnonzero(np.isin(native["FSType"], (2, 3)))
    hull = ConvexHull(x[ids])
    tri = ids[hull.simplices]
    a, b, c = x[tri].transpose(1, 0, 2)
    center = (a+b+c)/3
    area = np.cross(b-a, c-a)/2
    area *= np.sign(np.einsum("ij,ij->i", center, area))[:, None]
    full = shapes(center, cKDTree(x), float(np.float32(.0045)),
                  dict(max_shape_reproduction_error=0., min_donors=len(x)))
    face = csr_matrix((np.full(tri.size, 1/3), (np.repeat(np.arange(len(tri)), 3), tri.ravel())),
                      shape=(len(tri), len(x)))
    radial = -x/R
    bubble = radial*(1-(np.linalg.norm(x, axis=1)/R)**2)[:, None]
    bubble[ids] = 0.
    rows = {}
    for name, w in (("full_MLS", full), ("surface_barycentric", face)):
        force = w.T@(-Q*area)
        power = lambda vel: float(np.einsum("ij,ij->", force, vel))
        rows[name] = dict(radial_affine_power_W=power(radial), zero_boundary_power_W=power(bubble),
                          particles_receiving_force=int(np.count_nonzero(np.linalg.norm(force, axis=1))),
                          net_force_N=float(np.linalg.norm(force.sum(axis=0))),
                          torque_Nm=float(np.linalg.norm(np.cross(x, force).sum(axis=0))))
    need(abs(rows["full_MLS"]["radial_affine_power_W"]-rows["surface_barycentric"]["radial_affine_power_W"])<1e-9
         and rows["surface_barycentric"]["zero_boundary_power_W"]==0., "Affine and strictly surface work")
    with target.open("x", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, allow_nan=False)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Actual returned P3 solver directory containing data/")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--exterior-work", action="store_true", help="Run the separate surface virtual-work audit")
    mode.add_argument("--boundary-nodes", action="store_true", help="Use only surface vertices in the exterior face test and trial")
    args = parser.parse_args()
    if args.exterior_work:
        exterior_work(args.output)
    else:
        main(args.output, args.boundary_nodes)
