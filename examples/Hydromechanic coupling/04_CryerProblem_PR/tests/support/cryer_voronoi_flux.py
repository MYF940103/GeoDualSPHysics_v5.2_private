"""Orthogonal Darcy two-point fluxes on the physical Cryer point cloud.

Build only finite faces incident on an interior site. Surface-only faces and the
outer hull are assembled independently in cryer_voronoi_surface.py. SI units.
"""
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.spatial import Voronoi

from cryer_tet_darcy_spectrum import assemble


T = Path(__file__).resolve().parents[1]
TAG = "cryer_voronoi_flux_interior_r1"
CACHE = T / "outputs/cryer_tet_reference_r1.npz"


def face_geometry(x, is_surface, inradius):
    scale = 0.0025
    diagram = Voronoi(x / scale)
    verts = scale * diagram.vertices
    groups = defaultdict(list)
    for face, ((i, j), poly) in enumerate(zip(diagram.ridge_points, diagram.ridge_vertices)):
        if is_surface[i] and is_surface[j]:
            continue
        if -1 in poly or len(poly) < 3:
            raise ValueError(f"Unbounded or degenerate interior face {i},{j}")
        groups[len(poly)].append((face, poly))
    endpoints, areas, planes = [], [], []
    max_corner = 0.
    for group in groups.values():
        index, polygons = zip(*group)
        edges = np.sort(diagram.ridge_points[list(index)], axis=1)
        i, j = edges.T
        xyz = verts[np.asarray(polygons)]
        max_corner = max(max_corner, np.linalg.norm(xyz, axis=2).max())
        edge = x[j] - x[i]
        normal = edge / np.linalg.norm(edge, axis=1)[:, None]
        mid = (x[i] + x[j]) / 2
        plane = np.einsum("fkc,fc->fk", xyz - mid[:, None, :], normal)
        local = xyz - xyz.mean(axis=1)[:, None, :]
        # Explicit cyclic order; ridge-vertex order is not an input contract.
        axes = np.eye(3)[np.argmin(abs(normal), axis=1)]
        axis1 = np.cross(axes, normal)
        axis1 /= np.linalg.norm(axis1, axis=1)[:, None]
        axis2 = np.cross(normal, axis1)
        angle = np.arctan2(np.einsum("fkc,fc->fk", local, axis2),
                           np.einsum("fkc,fc->fk", local, axis1))
        cyclic = np.take_along_axis(local, np.argsort(angle, axis=1)[:, :, None], axis=1)
        vec = np.cross(cyclic, np.roll(cyclic, -1, axis=1)).sum(axis=1) / 2
        area = np.einsum("fc,fc->f", vec, normal)
        if not np.all(area > 0):
            raise ArithmeticError("A reconstructed face has nonpositive area")
        endpoints.append(edges)
        areas.append(area)
        planes.append(np.abs(plane).max())
    # All vertices of these convex cells are strictly inside the inscribed sphere.
    # Hence clipping by any true outer facet leaves every interior cell intact.
    if not (max_corner < inradius and max(planes) < 1e-10):
        raise ArithmeticError(f"Interior containment or bisector failure: {max_corner}, {max(planes)}")
    edges = np.concatenate(endpoints)
    order = np.lexsort((edges[:, 1], edges[:, 0]))
    return edges[order], np.concatenate(areas)[order], float(max_corner), float(max(planes))


def graph(x, edges, area):
    i, j = edges.T
    dx = x[j] - x[i]
    dist = np.linalg.norm(dx, axis=1)
    weight = area / dist
    # Positive stiffness K represents integrated negative Laplacian.
    half = sparse.coo_matrix((weight, (i, j)), shape=(len(x), len(x))).tocsr()
    adj = half + half.T
    stiffness = sparse.diags(np.asarray(adj.sum(axis=1)).ravel()) - adj
    pyramid = area * dist / 6
    volume = (np.bincount(i, weights=pyramid, minlength=len(x)) +
              np.bincount(j, weights=pyramid, minlength=len(x)))
    return stiffness.tocsr(), volume


def main():
    outputs = [T / ("outputs/" + TAG + ".npz"), T / ("logs/" + TAG + ".json"),
               T / ("figures/" + TAG + ".csv")]
    if any(path.exists() for path in outputs):
        raise FileExistsError("Preserve the completed interior diagnostic")
    t, ve, _, x, fs, shell, ids, core, p1 = assemble(CACHE)
    with np.load(CACHE) as ref:
        area_vec = ref["face_area_out"]
        center = x[ref["faces"]].mean(axis=1)
    inradius = np.min((area_vec * center).sum(axis=1) / np.linalg.norm(area_vec, axis=1))
    is_surface = shell == 20
    edges, area, corner, plane = face_geometry(x, is_surface, inradius)
    K, vol = graph(x, edges, area)
    p1vol = np.bincount(t.ravel(), weights=np.repeat(ve / 4, 4), minlength=len(x))
    linear = np.max(abs((K @ x)[core]))
    r2 = np.sum(x*x, axis=1)
    lap = -(K @ r2)[core] / vol[core]
    if not (np.all(vol[core] > 0) and linear < 1e-12 and np.max(abs(lap-6)) < 1e-8):
        raise ArithmeticError(f"Interior affine/radial consistency failure: {linear}, {lap.min()}, {lap.max()}")
    drain_jump = np.where(is_surface, 0., 1.)
    rows = []
    summaries = {}
    for name, op, volumes in (("orthogonal_faces", K, vol), ("tet_P1", p1, p1vol)):
        A = op[core][:, core]
        p = drain_jump.copy()
        jacobi = []
        for _ in range(3):
            p[core] -= (op @ p)[core] / A.diagonal()
            jacobi.append(dict(min=float(p[core].min()), max=float(p[core].max()),
                               above_1=int((p[core] > 1+1e-12).sum()),
                               below_0=int((p[core] < -1e-12).sum())))
        p = drain_jump
        rate = -(op @ p)[core] / volumes[core]
        shell_core = shell[core]
        for s in np.unique(shell_core):
            v = rate[shell_core == s]
            rows.append((name, int(s), len(v), v.mean(), v.std(), v.min(), v.max()))
        quadratics = {}
        for a in range(3):
            for b in range(a, 3):
                qrate = -(op @ (x[:, a] * x[:, b]))[core] / volumes[core]
                error = qrate - (2 if a == b else 0)
                quadratics["xyz"[a]+"xyz"[b]] = dict(rms=float(np.sqrt(np.mean(error**2))),
                                                     maxabs=float(abs(error).max()))
        summaries[name] = dict(jacobi_open_three_rounds=jacobi,
                               full_diagonal_quadratics=quadratics,
                               negative_laplacian_radial_square_abs_error=float(
                                   abs((op @ r2)[core] / volumes[core] + 6).max()))
    if any(r["above_1"] or r["below_0"] for r in summaries["orthogonal_faces"]["jacobi_open_three_rounds"]):
        raise ArithmeticError("Dirichlet pure-diffusion maximum principle violated")
    i, j = edges.T
    rng = np.random.default_rng(7419)
    y = rng.standard_normal(len(ids))
    energy = float(y @ (K @ y))
    edge_energy = float(np.sum(area / np.linalg.norm(x[j]-x[i], axis=1) * (y[j]-y[i])**2))
    if abs(energy - edge_energy) > 1e-12 * energy:
        raise ArithmeticError("Pressure work and edge dissipation differ")
    np.savez_compressed(outputs[0], ids=ids, edges=edges, area_m2=area,
                        interior_slots=core, interior_volume_m3=vol[core])
    with outputs[2].open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["operator","shell","count","mean_initial_laplacian_per_m2",
                         "angular_sd_per_m2","minimum_per_m2","maximum_per_m2"])
        writer.writerows(rows)
    report = dict(nodes=len(ids), interior=len(core), drained=len(fs), faces=len(area),
                  shortest_supported_area_m2=float(area.min()), max_interior_corner_radius_m=corner,
                  true_hull_inscribed_radius_m=float(inradius), max_bisector_error_m=plane,
                  affine_integral_residual_max_m2=float(linear), open_energy=edge_energy,
                  open_energy_reassembly_error=float(abs(energy-edge_energy)), operators=summaries,
                  scope="Interior isotropic Darcy graph and frozen unit drainage jump; independent of inertial integration.")
    with outputs[1].open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
