"""Independently join the open interior mesh to the clipped Cryer surface cells."""
import json
from pathlib import Path

import numpy as np

from cryer_voronoi_flux import CACHE, T, TAG


def main():
    target = T / "logs/cryer_voronoi_join_r1.json"
    if target.exists():
        raise FileExistsError(target)
    with np.load(CACHE) as m, np.load(T / ("outputs/" + TAG + ".npz")) as a, np.load(
            T / "outputs/cryer_voronoi_surface_r1.npz") as b:
        ids, x = m["native_ids"], m["x0"]
        if not np.array_equal(ids,a["ids"]) or not np.array_equal(ids,b["ids"]):
            raise ValueError("ID order differs between the three input geometries")
        surf = m["native_surface"]
        core = a["interior_slots"]
        if not (np.array_equal(np.sort(np.r_[core,surf]),np.arange(len(x))) and
                np.array_equal(surf,b["surface_slots"])):
            raise ValueError("Surface or interior membership mismatch")
        volume = np.empty(len(ids))
        volume[core], volume[surf] = a["interior_volume_m3"], b["volume_m3"]
        e1, ar1 = a["edges"], a["area_m2"]
        e2 = np.column_stack([b["i"],b["j"]])
        ar2 = b["area_m2"]
        surface = np.zeros(len(x),dtype=bool)
        surface[surf] = True
        def common(edges, areas):
            mask = surface[edges[:,0]] != surface[edges[:,1]]
            pairs = np.sort(edges[mask],axis=1)
            order = np.lexsort((pairs[:,1],pairs[:,0]))
            return pairs[order],areas[mask][order]
        ea, sa = common(e1, ar1)
        eb, sb = common(e2, ar2)
        if not np.array_equal(ea,eb) or len(ea) != 19089:
            raise ArithmeticError("Interface topology differs")
        extra = surface[e2[:,1]] & (e2[:,0] < e2[:,1])
        edges = np.vstack([e1,e2[extra]])
        area = np.r_[ar1,ar2[extra]]
        i,j = edges.T
        dx = x[j]-x[i]
        face = dx * (area/np.linalg.norm(dx,axis=1))[:,None]
        # Verify closure using independently pieced geometric areas, no row normalization.
        residual = np.zeros_like(x)
        np.add.at(residual,i,face)
        np.add.at(residual,j,-face)
        np.add.at(residual,b["b_i"],b["b_area_vec_m2"])
        hull = m["Ve"].sum()
        net = np.linalg.norm(residual,axis=1).max()
        max_area_diff = abs(sa-sb).max()
        if not (np.all(area>0) and np.all(volume>0) and net<1e-16 and
                max_area_diff<1e-16 and abs(volume.sum()-hull)<1e-15):
            raise ArithmeticError("Full bounded-cell geometry failed")
        result = dict(material_ids=len(ids), undirected_faces=len(edges),
                      interior_surface_reciprocal_pairs=len(ea), min_area_m2=float(area.min()),
                      max_reciprocal_interface_area_error_m2=float(max_area_diff),
                      max_node_area_closure_m2=float(net), sum_cell_volumes_m3=float(volume.sum()),
                      hull_volume_m3=float(hull), absolute_volume_difference_m3=float(abs(volume.sum()-hull)),
                      scope="Exact original sites, bounded by original planar surface; static geometry only.")
    with target.open("x") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
