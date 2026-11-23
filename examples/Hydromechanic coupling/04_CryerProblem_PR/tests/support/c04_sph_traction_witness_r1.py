"""Test positive work quadratures for the retained corrected Cryer SPH divergence."""
import argparse
import hashlib
import json
import os
import time
from itertools import combinations
from pathlib import Path

for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[name] = "4"

import numpy as np
from scipy.linalg import solve
from scipy.sparse import csr_matrix
from scipy.spatial import cKDTree

from cryer_load_pair_r1 import batches

TESTS = Path(__file__).resolve().parents[1]
TAG = "c04_sph_traction_witness_r1"
REFERENCE = TESTS / "outputs/cryer_tet_reference_r1.npz"
RECEIPT = TESTS / "logs" / (TAG + ".check.json")
H = float(np.float32(.0045))


def geometry():
    with np.load(REFERENCE) as z:
        x, faces = z["x0"], z["faces"]
        volumes = z["native_volume_m3"]
        assert len(x) == 37173 and len(faces) == 10302 and np.ptp(volumes) == 0
        assert np.array_equal(np.unique(faces), z["native_surface"])
        area = z["face_area_out"]
        native_ids = z["native_ids"]
    p, q, r = x[faces].transpose(1, 0, 2)
    check = np.cross(q-p, r-p)/2
    check *= np.sign(np.einsum("ij,ij->i", p, check))[:, None]
    assert np.max(abs(check-area)) < 1e-15
    nodes = np.zeros_like(x)
    for col in faces.T:
        np.add.at(nodes, col, area/3)
    moment = nodes.T @ x
    volume = np.trace(moment)/3
    assert np.max(abs(moment-volume*np.eye(3))) < 1e-16
    return x, nodes, volume, native_ids


def compact_divergence(x, tree, moving):
    """Map cap velocities to every influenced receiver, including its fixed neighbors."""
    affected = np.unique(np.concatenate(tree.query_ball_point(x[moving], 2*H)))
    local_id = np.full(len(x), -1, dtype=int)
    local_id[moving] = np.arange(len(moving))
    cols, vals, indptr = [], [], [0]
    donors = tree.query_ball_point(x[affected], 2*H)
    for i, js in zip(affected, donors):
        js = np.asarray(js)
        offsets = x[js] - x[i]
        # Constant V_j and the Wendland gradient prefactor cancel in the moment inverse.
        radial_weight = (1 - np.linalg.norm(offsets, axis=1)/(2*H))**3
        weighted = radial_weight[:, None]*offsets
        moment = weighted.T @ offsets
        deriv = weighted @ np.linalg.inv(moment)
        deriv[js == i] = -deriv.sum(axis=0)
        local = local_id[js]
        use = local >= 0
        cols.append((3*local[use, None] + np.arange(3)).ravel())
        vals.append(deriv[use].ravel())
        indptr.append(indptr[-1] + 3*use.sum())
    mat = csr_matrix((np.concatenate(vals), np.concatenate(cols), indptr),
                     shape=(len(affected), 3*len(moving)))
    return mat


def find_velocity(x, nodes):
    cap = np.flatnonzero(x[:, 2] > .035)
    mat = compact_divergence(x, cKDTree(x), cap)
    row_norm = np.sqrt(mat.multiply(mat).sum(axis=1).A1)
    valid = row_norm > 0
    scaled = mat[valid].multiply(1/row_norm[valid, None]).tocsr()
    target = nodes[cap].ravel().copy()
    target /= np.max(abs(target))
    # The regularization only selects the witness. Independent replay checks
    # the signed inequality over the full sphere without any solve tolerance.
    gram = (scaled @ scaled.T).toarray()
    gram.flat[::len(gram)+1] += 1e-10
    multiplier = solve(gram, scaled@target, assume_a="pos")
    local_v = (target - scaled.T@multiplier).reshape(-1, 3)
    local_v /= np.max(np.linalg.norm(local_v, axis=1))
    return cap, local_v


def full_replay(x, vel):
    tree = cKDTree(x)
    pairs = tree.query_pairs(2*H, output_type="ndarray")
    moment = np.zeros((len(x), 3, 3))
    slope = np.zeros_like(moment)
    for i, j, dr, grad in batches(x, pairs, H):
        dv = vel[j] - vel[i]
        for a in range(3):
            for b in range(3):
                for matrix, value in ((moment, -dr[:, a]*grad[:, b]),
                                      (slope, dv[:, a]*grad[:, b])):
                    matrix[:, a, b] += (np.bincount(i, value, minlength=len(x))
                                        + np.bincount(j, value, minlength=len(x)))
    correction = np.linalg.inv(moment)
    theta = np.einsum("nij,nij->n", slope, correction)
    affine_error = np.max(abs(moment@correction-np.eye(3)))
    assert affine_error < 1e-12
    return theta, affine_error, len(pairs)


def controls(x, ids, nodes, signed_v, theta):
    from c04_surface_work_r1 import DATA, facet_measures, outer_faces
    from cryer_p3_peak_shells import ordered

    state = ordered(DATA, 0, ["Posd", "Idp", "FSType", "PoroCurrentVolume"])
    assert np.array_equal(ids, state["Idp"]) and np.array_equal(x, state["Posd"])
    outer = np.isin(state["FSType"], (2, 3))
    hull_nodes, hull_volume, _ = facet_measures(x, outer, outer_faces(x[outer]))
    hull_flux = np.sum(hull_nodes*signed_v)
    facet_flux = np.sum(nodes*signed_v)
    with np.load(REFERENCE) as ref:
        assert np.array_equal(state["PoroCurrentVolume"], ref["native_volume_m3"])
        tet_flux = np.einsum("tjd,tjd->", ref["Ve_gradN"], signed_v[ref["tets"]])
        native_flux = ref["native_volume_m3"] @ theta
    assert hull_flux > 1e-8 and abs(tet_flux-facet_flux) < 1e-14
    part = DATA / "Part_0000.bi4"
    return dict(part0_sha256=hashlib.sha256(part.read_bytes()).hexdigest(),
                boundary_nodes=int(outer.sum()), independent_hull_volume_m3=hull_volume,
                independent_hull_flux_m3_s=hull_flux, retained_tet_boundary_flux_m3_s=facet_flux,
                tet_volume_integral_m3_s=float(tet_flux), equal_native_weight_integral_m3_s=native_flux,
                upper_bound_any_nonnegative_work_weights_of_hull_volume_m3_s=hull_volume*theta.max())


def graph_control(x, nodes):
    """Check the existing P1 lumped gradient as a feasible stencil on the original radius graph."""
    with np.load(REFERENCE) as ref:
        tet, grad, vol = ref["tets"], ref["Ve_gradN"], ref["Ve"]
    weights = np.bincount(tet.ravel(), weights=np.repeat(vol/4, 4), minlength=len(x))
    longest = max(np.linalg.norm(x[tet[:, i]]-x[tet[:, j]], axis=1).max()
                  for i, j in combinations(range(4), 2))
    moment = np.einsum("tja,tjb->tab", x[tet]-x[tet[:, :1]], grad)
    identities = np.zeros((len(x), 3, 3))
    areas = np.zeros_like(x)
    for j in range(4):
        np.add.at(identities, tet[:, j], moment/4)
        np.add.at(areas, tet[:, j], grad[:, j])
    affine_error = np.max(abs(identities/weights[:, None, None]-np.eye(3)))
    area_error = np.max(abs(areas-nodes))
    assert longest < 2*H and weights.min() > 0 and affine_error < 1e-12 and area_error < 1e-15
    return dict(tetrahedra=len(tet), largest_edge_m=longest, sph_support_m=2*H,
                min_work_volume_m3=weights.min(), max_work_volume_m3=weights.max(),
                work_volume_sum_m3=weights.sum(), max_nodal_affine_component_error=affine_error,
                max_nodal_constant_stress_area_component_error_m2=area_error)


def run(verify, save_controls, save_graph):
    start = time.perf_counter()
    x, nodes, volume, ids = geometry()
    digest = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    if verify:
        with RECEIPT.open(encoding="utf8") as stream:
            stored = json.load(stream)
        assert stored["geometry_sha256"] == digest
        cap = np.flatnonzero(x[:, 2] > .035)
        assert np.array_equal(ids[cap], stored["cap_material_ids"])
        local_v = np.asarray(stored["cap_velocity_m_s"])
    else:
        if RECEIPT.exists():
            raise FileExistsError(RECEIPT)
        cap, local_v = find_velocity(x, nodes)

    velocity = np.zeros_like(x)
    velocity[cap] = local_v
    flux = float(np.sum(nodes*velocity))
    # Subtract an affine expansion. Its SPH divergence is spatially constant.
    # A positive surface flux with negative divergence at every point
    # contradicts every nonnegative scalar choice of particle work volumes.
    shift = float(flux/(2*volume))
    signed_v = velocity - shift*x/3
    theta, affine_error, n_pairs = full_replay(x, signed_v)
    signed_flux = float(np.sum(nodes*signed_v))
    assert np.all(np.isfinite(theta)) and signed_flux > 1e-8 and theta.max() < -1e-5
    summary = dict(geometry_sha256=digest, native_ids=len(x), neighbor_pairs=n_pairs,
                   cap_nodes=len(cap), physical_volume_m3=volume, kernel_h_m=H,
                   unshifted_cap_surface_flux_m3_s=flux, affine_divergence_removed_s_inv=shift,
                   signed_min_divergence_s_inv=float(theta.min()),
                   signed_max_divergence_s_inv=float(theta.max()),
                   signed_surface_flux_m3_s=signed_flux, signed_traction_work_at_10kPa_W=-10000*signed_flux,
                   max_affine_component_error=affine_error,
                   elapsed_s=time.perf_counter()-start)
    if verify:
        for key in ("signed_max_divergence_s_inv", "signed_min_divergence_s_inv", "signed_surface_flux_m3_s"):
            assert abs(summary[key]-stored[key]) < 1e-10
        summary["controls"] = controls(x, ids, nodes, signed_v, theta)
        summary["support"] = graph_control(x, nodes)
        if save_controls:
            with (TESTS / "logs" / (TAG + ".controls.json")).open("x", encoding="utf8") as stream:
                json.dump(summary["controls"], stream, indent=2, allow_nan=False)
                stream.write("\n")
        if save_graph:
            with (TESTS / "logs" / (TAG + ".stencil.json")).open("x", encoding="utf8") as stream:
                json.dump(summary["support"], stream, indent=2, allow_nan=False)
                stream.write("\n")
    else:
        with RECEIPT.open("x", encoding="utf8") as stream:
            json.dump(dict(**summary, cap_material_ids=ids[cap].tolist(),
                           cap_velocity_m_s=local_v.tolist()), stream, allow_nan=False)
            stream.write("\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="Replay the stored velocity and both boundary controls")
    mode.add_argument("--save-controls", action="store_true", help="Replay and record controls at a fresh path")
    mode.add_argument("--save-stencil", action="store_true", help="Record the P1 radius-graph feasibility control")
    args = parser.parse_args()
    run(args.verify or args.save_controls or args.save_stencil, args.save_controls, args.save_stencil)
