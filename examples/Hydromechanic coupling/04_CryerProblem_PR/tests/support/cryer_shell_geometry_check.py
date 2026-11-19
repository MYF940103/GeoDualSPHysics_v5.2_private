"""Independent topology, radial-reference and nonintersection controls on fixed material-shell triangles."""
import json
import numpy as np
import pandas as pd
from cryer_material_shell_volume import faces, volume
from cryer_shell_equilibrium import NATIVE, TESTS, R, SOIL, TOTAL, T_D, need, write

TAG="cryer_shell_geometry_r1"


def orient(points,tri):
    a,b,c=points[tri[:,0]],points[tri[:,1]],points[tri[:,2]]
    normals=np.cross(b-a,c-a)
    norms=np.linalg.norm(normals,axis=1)
    need(np.all(norms>0),"Degenerate triangle")
    return np.einsum("ij,ij->i",normals,a)/norms


def topology(tri,n):
    edges=np.vstack((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]))
    orientation=np.where(edges[:,0]<edges[:,1],1,-1)
    unique,inv,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    need(np.all(counts==2) and np.all(np.bincount(inv,weights=orientation)==0),"Open or inconsistently oriented edge")
    need(n-len(unique)+len(tri)==2,"Unexpected Euler characteristic")
    return len(unique)


def main():
    folder=TESTS/"figures"
    output=folder/(TAG+".csv"); result=TESTS/"logs"/(TAG+".check.json")
    need(not output.exists() and not result.exists(),"Preserve prior geometry evidence")
    prior=pd.read_csv(folder/"cryer_material_shell_volume_r1.csv",float_precision="round_trip")
    ids=pd.read_csv(NATIVE/"native_ids.csv",float_precision="round_trip").iloc[SOIL]
    x0=ids[["x0","y0","z0"]].to_numpy(); idx=np.rint(ids.r0_m.to_numpy()/.0025).astype(int)-1
    data=np.memmap(NATIVE/"common26.bin",offset=12,dtype="<f8",shape=(577,1+TOTAL*26),mode="r")
    vectors=x0/np.linalg.norm(x0,axis=1)[:,None]
    all_rows=[]
    # Three stages cover the strict shell geometry comparison and the early elastic response.
    for part in (64,65,408,417,576):
        x=data[part,1:].reshape(TOTAL,26)[SOIL,:3]
        by_shell=prior[prior.part==part].reset_index(drop=True)
        outer_radius=0.
        for i in range(20):
            mask=idx==i; a=x0[mask]; y=x[mask]; tri=faces(a); n=len(a)
            e=topology(tri,n)
            v0=volume(a,tri)
            # Spherical companion supplies linear 3u/r. Exact finite-scale polyhedral volume uses (1+u/r)^3.
            lambda_r=1+by_shell.reference_enclosed_eps.iloc[i]/3
            radial_ref=volume(a*lambda_r,tri)/v0-1
            exact_ref=lambda_r**3-1
            need(abs(radial_ref-exact_ref)<1e-12,"Analytical radial displacement control")
            plane=orient(y,tri)
            need(np.min(plane)>outer_radius,"Adjacent shell not independently certified as nested")
            radii=np.linalg.norm(y,axis=1)
            direction=y/radii[:,None]
            cos=np.einsum("ij,ij->i",vectors[mask],direction).clip(-1,1)
            actual=volume(y,tri)/v0-1
            need(abs(actual-by_shell.hull_enclosed_volume_change.iloc[i])<1e-13,"Shape review mismatch")
            all_rows.append(dict(part=part,tau_s=float(data[part,0]-T_D),r0_over_a=.05*(i+1),
                vertices=n,closed_edges=e,oriented_faces=len(tri),origin_min_face_plane_m=plane.min(),
                inner_shell_max_radius_m=outer_radius,nested_lower_bound_gap_m=plane.min()-outer_radius,
                maximum_angular_deflection_deg=np.rad2deg(np.arccos(cos)).max(),relative_polyhedron_geometry_error=v0/(4*np.pi*((i+1)*.0025)**3/3)-1,
                radial_analytical_fixture_error=radial_ref-exact_ref,measured_enclosed_change=actual))
            outer_radius=radii.max()
    write(output,all_rows)
    groups=[r for r in all_rows if r["inner_shell_max_radius_m"]>0]
    note=dict(snapshots=[64,65,408,417,576],shells=20,closed_surfaces=len(all_rows),positions_per_snapshot=len(x0),
        innermost_topology=[all_rows[0][k] for k in ("vertices","closed_edges","oriented_faces")],
        outermost_topology=[all_rows[-1][k] for k in ("vertices","closed_edges","oriented_faces")],
        min_certified_adjacent_gap_m=min(z["nested_lower_bound_gap_m"] for z in groups),
        max_angular_deflection_deg=max(r["maximum_angular_deflection_deg"] for r in all_rows),
        max_abs_radial_fixture_error=max(abs(r["radial_analytical_fixture_error"]) for r in all_rows),
        innermost_polyhedron_geometry_error=all_rows[0]["relative_polyhedron_geometry_error"])
    with result.open("x",encoding="utf8") as f: json.dump(note,f,indent=2)
    print(json.dumps(note,indent=2))


if __name__=="__main__":main()
