"""Bounded Voronoi cells of the actual Cryer exterior material points on the tetrahedral hull."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

for key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection, cKDTree


TESTS = Path(__file__).resolve().parents[1]
CACHE = TESTS/"outputs/cryer_tet_reference_r1.npz"
TAG = "cryer_voronoi_surface_r1"
DP = .0025
# Computations use dimensionless offsets relative to each generator.
LENGTH_TOL = 3e-11
AREA_TOL = 2e-13


def demand(condition, message):
    if not condition:
        raise ArithmeticError(message)


def ordered_face(points, normal):
    """Order coplanar vertices anticlockwise about the given outward unit vector."""
    e0 = np.eye(3)[np.argmin(abs(normal))]
    e1 = np.cross(normal,e0)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(normal,e1)
    relative = points-points.mean(axis=0)
    return points[np.argsort(np.arctan2(relative@e2, relative@e1))]


def polygon(points, normal):
    """Oriented area and centroid of an already ordered planar polygon."""
    if len(points) < 3:
        return None
    valid = np.linalg.norm(points-np.roll(points,1,axis=0),axis=1)>1e-12
    points = points[valid]
    if len(points) < 3:
        return None
    origin = points.mean(axis=0)
    rel = points-origin
    following = np.roll(rel,-1,axis=0)
    weights = .5*np.cross(rel,following)@normal
    area = weights.sum()
    if abs(area) <= AREA_TOL:
        return None
    center = origin + np.sum(weights[:,None]*(rel+following),axis=0)/(3*area)
    if area < 0:
        points = points[::-1]
    return abs(area),center,points


def clip_triangle(points, normals, distances):
    """Voronoi bisectors clip a physical triangle without combining coplanar triangles."""
    gap = points@normals.T-distances
    if np.any(gap.min(axis=0)>LENGTH_TOL):
        return np.empty((0,3))
    for k in np.flatnonzero(gap.max(axis=0)>1e-13):
        curr = points@normals[k]-distances[k]
        curr[abs(curr)<=1e-13] = 0.
        inside = curr<=0
        if not inside.any():
            return np.empty((0,3))
        if inside.all():
            continue
        nxt = np.roll(points,-1,axis=0)
        other = np.roll(curr,-1)
        cross = inside!=np.roll(inside,-1)
        result = []
        for a in range(len(points)):
            if inside[a]:
                result.append(points[a])
            if cross[a]:
                result.append(points[a]+(nxt[a]-points[a])*(curr[a]/(curr[a]-other[a])))
        points = np.asarray(result)
    return points


class SurfaceGeometry:
    def __init__(self,path=CACHE):
        with np.load(path) as ref:
            self.x,self.ids,self.s,self.faces,self.av = (ref[k] for k in
                    ("x0","native_ids","native_surface","faces","face_area_out"))
            self.total_volume = ref["Ve"].sum()
        x,f = self.x,self.faces
        self.tri = x[f]
        self.cf = self.tri.mean(axis=1)
        self.area = np.linalg.norm(self.av,axis=1)
        self.normal = self.av/self.area[:,None]
        self.plane = np.einsum("ij,ij->i",self.normal,self.tri[:,0])/DP
        self.cover = np.linalg.norm(self.tri-self.cf[:,None],axis=2).max()
        self.sites = cKDTree(x)
        self.btree = cKDTree(self.cf)
        demand(np.array_equal(self.ids,np.arange(8,37181)) and
               np.array_equal(np.unique(f),self.s) and len(self.s)==5153 and len(f)==10302,
               "Cryer exterior/ID identity")
        # The largest dot product on a fixed-radius sphere is attained by its nearest angular site.
        radii = np.linalg.norm(x[self.s],axis=1)
        demand(np.max(abs(radii-.05))<1e-14,"Outer radius changed")
        near = cKDTree(x[self.s]).query(.05*self.normal)[1]
        self.max_plane_violation = max(0.,np.max(np.einsum("ij,ij->i",self.normal,
                                               x[self.s[near]]-self.tri[:,0])))
        demand(self.max_plane_violation<1e-12*DP and np.min(self.plane)*DP>.0475,
               "Original exterior is a supporting convex hull")
        inside = np.ones(len(x),dtype=bool)
        inside[self.s]=False
        demand(np.linalg.norm(x[inside],axis=1).max()<np.min(self.plane)*DP,
               "Interior points violate the physical hull")

    def cell(self,i):
        xi = self.x[i]
        ids = np.asarray(sorted(self.sites.query_ball_point(xi,2.75*DP)),dtype=int)
        ids = ids[ids!=i]
        delta = (self.x[ids]-xi)/DP
        distance = np.linalg.norm(delta,axis=1)
        n = delta/distance[:,None]
        b = .5*distance
        trial_faces = np.asarray(sorted(self.btree.query_ball_point(xi,2.75*DP)),dtype=int)
        gap = self.plane-self.normal@(xi/DP)
        nn = np.concatenate((n,self.normal[trial_faces]))
        bb = np.concatenate((b,gap[trial_faces]))
        seed = -.05*xi/np.linalg.norm(xi)
        demand(np.max(nn@seed-bb)<-.01, f"Lost interior witness for slot {i}")
        poly = HalfspaceIntersection(np.column_stack((nn,-bb)),seed)
        verts = poly.intersections
        hull = ConvexHull(verts)
        radius = np.linalg.norm(verts,axis=1).max()
        # Unused generators have bisector distance >2.75/2. For physical planes farther
        # than radius, Cauchy's inequality proves every vertex is inside. Check the rest.
        demand(2*radius<2.75-LENGTH_TOL,f"Uncertified omitted generator at slot {i}")
        near = np.flatnonzero(gap<=radius+LENGTH_TOL)
        omitted = np.setdiff1d(near,trial_faces,assume_unique=True)
        cut = np.max(verts@self.normal[omitted].T-gap[omitted]) if len(omitted) else -radius
        demand(cut<LENGTH_TOL,f"An omitted physical plane cuts slot {i}, gap={cut}")
        # Site face polygons. Count each positive-area facet once even where a bisector
        # meets a hull edge with multiple coincident intersection vertices.
        inner = []
        active = abs(verts@n.T-b)<LENGTH_TOL
        for k in np.flatnonzero(active.sum(axis=0)>=3):
            face = polygon(ordered_face(verts[active[:,k]],n[k]),n[k])
            if face is not None:
                area,c,v = face
                inner.append((i,ids[k],area*DP**2,n[k]*area*DP**2,xi+DP*c,xi+DP*v))
        boundary = []
        # A triangle that touches the certified cell must have its center within
        # cell radius + the largest triangle center-to-vertex distance.
        candidates = sorted(self.btree.query_ball_point(xi,radius*DP+self.cover+LENGTH_TOL*DP))
        for k in candidates:
            v = clip_triangle((self.tri[k]-xi)/DP,n,b)
            face = polygon(v,self.normal[k])
            if face is not None:
                area,c,v = face
                boundary.append((i,k,area*DP**2,self.normal[k]*area*DP**2,xi+DP*c,xi+DP*v))
        demand(len(inner)>=3 and boundary,f"Missing cell faces at {i}")
        faces = inner+boundary
        area_vec = np.stack([r[3] for r in faces])
        centers = np.stack([r[4] for r in faces])
        volume = hull.volume*DP**3
        # Integral of x_j n_k is V delta_jk. Use centroid of each actual face.
        affine = (centers-xi).T@area_vec
        volume_flux = np.trace(affine)/3
        affine_rel = np.linalg.norm(affine-volume*np.eye(3))/volume
        balance = np.linalg.norm(area_vec.sum(axis=0))/sum(r[2] for r in faces)
        demand(volume>0 and affine_rel<1e-7 and balance<1e-8,
               f"Open cell at slot {i}, affine={affine_rel}, area={balance}")
        return inner,boundary,volume,(radius,cut,affine_rel,balance,abs(volume_flux/volume-1))


def pack(records):
    i,j,a,vec,c,v = zip(*records)
    return (np.asarray(i,dtype=np.int32),np.asarray(j,dtype=np.int32),np.asarray(a),
            np.stack(vec),np.stack(c),np.r_[0,np.cumsum([len(p) for p in v])],np.concatenate(v))


def main(probe=False):
    dest = TESTS/"outputs"/(TAG+".npz")
    receipt = TESTS/"logs"/(TAG+".check.json")
    if not probe and (dest.exists() or receipt.exists()):
        raise FileExistsError(TAG)
    started = perf_counter()
    m = SurfaceGeometry()
    s = m.s
    if probe:
        s = np.unique(np.r_[s[::321],s[-1],s[np.argmax(m.x[s,2])],s[np.argmin(m.x[s,2])]])
    interior,wall,volumes,metrics = [],[],[],[]
    for count,i in enumerate(s,1):
        inside,outside,v,met = m.cell(i)
        interior.extend(inside)
        wall.extend(outside)
        volumes.append(v)
        metrics.append(met)
        if count%1000==0:
            print(f"{count}/{len(s)} boundary cells: {perf_counter()-started:.1f} s",flush=True)
    met = np.max(metrics,axis=0)
    if probe:
        print("Subset",len(s),len(interior),len(wall),met,flush=True)
        return
    i,j,a,vec,c,ptr,vertices = pack(interior)
    bi,bt,ba,bv,bc,bptr,bvertices = pack(wall)
    vol = np.asarray(volumes)
    edge = {(int(ii),int(jj)):k for k,(ii,jj) in enumerate(zip(i,j))}
    demand(len(edge)==len(i),"Duplicate directed face")
    face_err = center_err = 0.
    reciprocal = np.flatnonzero(np.isin(j,m.s))
    for k in reciprocal:
        rev = edge[(int(j[k]),int(i[k]))]
        face_err = max(face_err,np.linalg.norm(vec[k]+vec[rev]))
        center_err = max(center_err,np.linalg.norm(c[k]-c[rev]))
    err = np.bincount(bt,ba,minlength=len(m.faces))-m.area
    area_rel = np.max(abs(err)/m.area)
    bmoment = np.column_stack([np.bincount(bt,ba*(bc[:,k]-m.cf[bt,k]),minlength=len(m.faces))
                               for k in range(3)])
    moment_rel = np.max(np.linalg.norm(bmoment,axis=1)/(DP*m.area))
    # Boundary integral gives total volume of the original occupied hull independently.
    hull_volume = np.einsum("ij,ij->",bc,bv)/3
    hull_rel = abs(hull_volume/m.total_volume-1)
    wall_net = np.linalg.norm(bv.sum(axis=0))/sum(ba)
    demand(face_err<1e-8*DP**2 and center_err<1e-7*DP,
           "Surface/surface reciprocal internal faces")
    demand(area_rel<1e-8 and moment_rel<1e-8 and hull_rel<1e-10 and wall_net<1e-10,
           "Physical wall triangle fan coverage or total hull volume")
    dist = np.linalg.norm(m.x[i]-m.x[j],axis=1)
    with dest.open("xb") as fp:
        np.savez_compressed(fp,ids=m.ids,surface_slots=s,volume_m3=vol,
                           i=i,j=j,area_m2=a,area_vec_m2=vec,center_m=c,
                           transmissibility_m=a/dist,ptr=ptr,vertices_m=vertices,
                           b_i=bi,b_tri=bt,b_area_m2=ba,b_area_vec_m2=bv,b_center_m=bc,
                           b_ptr=bptr,b_vertices_m=bvertices)
    hashes = {}
    for path in (CACHE,Path(__file__),dest):
        with path.open("rb") as fp:
            hashes[str(path.relative_to(TESTS))] = hashlib.file_digest(fp,"sha256").hexdigest()
    result = dict(passed=True,material_ids=len(m.ids),surface_count=len(s),
                  original_triangles=len(m.faces),finite_volume_min_m3=vol.min(),
                  finite_volume_max_m3=vol.max(),finite_boundary_cell_volume_sum_m3=vol.sum(),
                  original_hull_volume_m3=m.total_volume,wall_flux_volume_m3=hull_volume,
                  original_hull_area_m2=m.area.sum(),wall_area_sum_m2=ba.sum(),
                  original_hull_plane_max_violation_m=m.max_plane_violation,
                  cell_radius_max_over_dp=met[0],omitted_site_bisector_min_distance_over_dp=1.375,
                  omitted_hull_plane_max_checked_signed_gap_over_dp=met[1],
                  cell_max_affine_flux_relative=met[2],cell_max_net_area_relative=met[3],
                  cell_max_divergence_volume_relative=met[4],wall_triangle_max_area_relative=area_rel,
                  wall_triangle_max_center_moment_relative=moment_rel,total_wall_vector_relative=wall_net,
                  hull_volume_relative=hull_rel,directed_faces=len(i),surface_surface_directed=len(reciprocal),
                  surface_interior_directed=len(i)-len(reciprocal),boundary_triangle_patches=len(ba),
                  reciprocal_area_vec_max_m2=face_err,reciprocal_center_max_m=center_err,
                  conventions="i, j, b_i, surface_slots are zero-based original geometry slots. "
                              "ids[slot] is the native material ID. b_tri indexes original triangular faces. "
                              "Vertices in each [ptr[k]:ptr[k+1]] run anticlockwise about its outward area vector. "
                              "Interior cells and surface-to-interior reciprocity belong to the full-geometry assembly.",
                  seconds=perf_counter()-started,sha256=hashes)
    with receipt.open("x",encoding="utf8") as fp:
        json.dump(result,fp,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2),flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe",action="store_true",help="Check a deterministic small subset without writing")
    main(ap.parse_args().probe)