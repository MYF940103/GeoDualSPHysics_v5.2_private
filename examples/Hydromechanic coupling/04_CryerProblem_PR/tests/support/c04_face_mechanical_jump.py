"""Mechanical virtual-work test on the genuine Voronoi faces touching the drained shell."""
import csv
import hashlib
import json
import os
import time
from pathlib import Path

for env in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[env]="2"
import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree
from cryer_tet_mechanics import TetMechanics

T = Path(__file__).resolve().parents[1]
TAG = "c04_face_mechanical_jump"
GEOM = T/"outputs/cryer_tet_reference_r1.npz"
SURFACE = T/"outputs/cryer_voronoi_surface_r1.npz"
Q = 10000.
H = float(np.float32(.0045))


def gradients(x,sites):
    """Wendland-weighted difference fit on original material neighbors, on demand."""
    tree = cKDTree(x)
    all_cols,all_values,counts = [],[],[]
    for start in range(0,len(sites),128):
        centers=sites[start:start+128]
        donors=tree.query_ball_point(x[centers],2*H)
        size=np.array([len(js) for js in donors])
        ii=np.repeat(np.arange(len(centers)),size)
        jj=np.concatenate(donors)
        r=x[jj]-x[centers[ii]]
        w=(1.-np.linalg.norm(r,axis=1)/(2*H))**3
        wr=w[:,None]*r
        head=np.r_[0,np.cumsum(size)[:-1]]
        mom=np.add.reduceat(r[:,:,None]*wr[:,None,:],head,axis=0)
        grad=np.einsum("ni,nij->nj",wr,np.linalg.inv(mom)[ii])
        grad[jj==centers[ii]]=-np.add.reduceat(grad,head,axis=0)
        all_cols.append(jj);all_values.append(grad);counts.extend(size)
    cols=np.concatenate(all_cols).astype("i4")
    values=np.concatenate(all_values)
    ptr=np.r_[0,np.cumsum(counts)].astype("i4")
    return [sparse.csr_matrix((values[:,k].copy(),cols,ptr),shape=(len(sites),len(x)))
            for k in range(3)]


def scatter(rows,values,n):
    return np.column_stack([np.bincount(rows,v,minlength=n) for v in values.T])


class SurfaceFaces:
    def __init__(self,m):
        with np.load(SURFACE) as f:
            assert np.array_equal(f["ids"],m.ids) and np.array_equal(f["surface_slots"],m.surface)
            self.i,self.j,self.a,self.center=(f[k] for k in ("i","j","area_vec_m2","center_m"))
            self.bi,self.ba,self.bc,tri=(f[k] for k in ("b_i","b_area_vec_m2","b_center_m","b_tri"))
            self.vol=f["volume_m3"]
        with np.load(GEOM) as f:
            self.btri=f["faces"][tri]
        self.n=m.n; self.s=m.surface
        self.sites=np.unique(np.r_[self.i,self.j])
        local=np.full(self.n,-1,dtype=int);local[self.sites]=np.arange(len(self.sites))
        self.li,self.lj=local[self.i],local[self.j]
        self.G=gradients(m.x,self.sites)
        sep=m.x[self.j]-m.x[self.i]
        en=sep/np.linalg.norm(sep,axis=1)[:,None]
        off=self.center-(m.x[self.i]+m.x[self.j])/2
        self.normal_offset_max=float(abs(np.sum(off*en,axis=1)).max())
        self.d=off-en*np.sum(off*en,axis=1)[:,None]
        p=m.x[self.btri]
        basis=p[:,1:]-p[:,:1]
        mat=basis@basis.transpose(0,2,1)
        rhs=np.einsum("nka,na->nk",basis,self.bc-p[:,0])
        coeff=np.linalg.solve(mat,rhs[:,:,None])[:,:,0]
        self.bary=np.column_stack((1-coeff.sum(axis=1),coeff))
        assert np.max(abs((p*self.bary[:,:,None]).sum(axis=1)-self.bc))<1e-12
        assert self.bary.min()>-1e-8
        self.cross=m.shells[self.j]!=20
        self.unique=self.cross|(self.i<self.j)
        assert self.cross.sum()==19089 and self.normal_offset_max<1e-12

    def sample(self,v):
        interp=(v[self.i]+v[self.j])/2
        for k,G in enumerate(self.G):
            grad=G@v
            interp+=self.d[:,k,None]*(grad[self.li]+grad[self.lj])/2
        boundary=np.einsum("nva,nv->na",v[self.btri],self.bary)
        return interp,boundary

    def wall_force(self,bforce):
        result=np.zeros((self.n,3))
        for k in range(3):
            result+=scatter(self.btri[:,k],bforce*self.bary[:,k,None],self.n)
        return result

    def pressure(self,p,corrected=True):
        # Each unique interface transfers a shared force once. Interior/interior
        # differences vanish for the tested fields, which are constant inside shell 20.
        f=((p[self.i]-p[self.j])*self.unique/2)[:,None]*self.a
        result=scatter(self.i,f,self.n)+scatter(self.j,f,self.n)
        if corrected:
            for k,G in enumerate(self.G):
                fk=f*self.d[:,k,None]
                work=scatter(self.li,fk,len(self.sites))+scatter(self.lj,fk,len(self.sites))
                result+=G.T@work
        return result+self.wall_force(p[self.bi,None]*self.ba)

    def cell_gradient(self,v):
        internal,boundary=self.sample(v)
        out=np.zeros((self.n,3,3))
        for row in range(3):
            out[:,row,:]=(scatter(self.i,(internal[:,row]-v[self.i,row])[:,None]*self.a,self.n)
                          +scatter(self.bi,(boundary[:,row]-v[self.bi,row])[:,None]*self.ba,self.n))
        return out[self.s]/self.vol[:,None,None]


def metrics(m,f,name):
    a=f/m.mass[:,None]
    en=m.x/np.linalg.norm(m.x,axis=1)[:,None]
    radial=np.sum(a*en,axis=1)
    tangent=np.linalg.norm(a-radial[:,None]*en,axis=1)
    angular=radial.copy()
    for k in range(1,21):
        mask=m.shells==k
        angular[mask]-=radial[mask].mean()
    groups=[(str(k),m.shells==k) for k in range(1,21)]+[("1-18",m.shells<19)]
    rms=lambda a:np.sqrt(np.mean(a*a))
    rows=[]
    for key,mask in groups:
        aa=np.linalg.norm(a[mask],axis=1)
        rows.append(dict(method=name,material_shell=key,ids=int(mask.sum()),outward_mean_m_s2=radial[mask].mean(),
                         radial_angular_sd_m_s2=rms(angular[mask]),radial_angular_variance_m2_s4=np.mean(angular[mask]**2),
                         tangent_vector_rms_m_s2=rms(tangent[mask]),angular_vector_rms_m_s2=rms(np.hypot(angular[mask],tangent[mask])),
                         vector_rms_m_s2=rms(aa),vector_max_m_s2=aa.max(),
                         l1_force_N=np.linalg.norm(f[mask],axis=1).sum()))
    return rows


def run():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rec=T/"logs"/(TAG+".json"); csvfile=T/"figures"/(TAG+".csv"); figfile=csvfile.with_suffix(".png")
    if any(path.exists() for path in (rec,csvfile,figfile)):
        raise FileExistsError(TAG)
    start=time.perf_counter()
    m=TetMechanics(GEOM); x=m.x
    face=SurfaceFaces(m)
    p=np.where(m.shells==20,0.,Q)
    external=m.surface_force(Q)
    forces={"P1":m.pressure_force(p)+external,
            "face midpoint":face.pressure(p,False)+external,
            "face centroid":face.pressure(p)+external}
    rows=[r for name,f in forces.items() for r in metrics(m,f,name)]
    reference=json.loads((T/"logs/c04_drain_jump_channels.json").read_text(encoding="utf8"))
    previous=reference["cases"] if "cases" in reference else reference
    if "ideal" not in previous:
        previous=reference["records"]
    for r in rows[:20]:
        old=previous["ideal"]["acceleration_m_s2"]["mechanical"][r["material_shell"]]
        assert abs(old["radial_angular_rms"]-r["radial_angular_sd_m_s2"])<1e-8
    rigid=np.cross([.4,-.2,.65],x)+[.12,-.03,.06]
    sample,wall=face.sample(x)
    grad=face.cell_gradient(x)
    affine=float(np.max(abs(grad-np.eye(3))))
    r,rb=face.sample(rigid)
    rigid_error=max(abs(r-np.cross([.4,-.2,.65],face.center)-[.12,-.03,.06]).max(),
                    abs(rb-np.cross([.4,-.2,.65],face.bc)-[.12,-.03,.06]).max())
    checks=dict(all_directed_neighbor_faces=len(face.i),jump_faces=int(face.cross.sum()),
                outer_polygon_patches=len(face.bi),surface_cells=len(m.surface),ls_sites=len(face.sites),
                tangential_offset_max_m=np.linalg.norm(face.d,axis=1).max(),
                normal_offset_max_m=face.normal_offset_max,wall_barycentric_min=face.bary.min(),
                face_affine_xyz_error_m=abs(sample-face.center).max(),boundary_affine_xyz_error_m=abs(wall-face.bc).max(),
                surface_cell_gradient_all_axes_max=affine,rigid_face_velocity_max_m_s=rigid_error)
    assert affine<2e-10 and checks["face_affine_xyz_error_m"]<1e-12 and rigid_error<1e-12
    # Each uniform total-stress tensor has zero interior traction jump.
    # Independent original hull forces test the other side of the boundary identity.
    tensor_errors={}
    for a in range(3):
        for b in range(a,3):
            stress=np.zeros((3,3));stress[a,b]=stress[b,a]=Q
            patch=face.wall_force(face.ba@stress.T)
            reference_force=(-m.unit_surface_force)@stress.T
            tensor_errors["xyz"[a]+"xyz"[b]]=np.max(abs(patch-reference_force))
    assert max(tensor_errors.values())<1e-9
    checks["six_constant_tensor_nodal_max_N"]=tensor_errors
    v=x/.05 + np.column_stack((x[:,1]*x[:,2],x[:,2]**2-x[:,0]**2,x[:,0]*x[:,1]))/(.05**2)
    p_nonuniform=np.full(m.n,Q)
    u=x[m.surface]/.05
    p_nonuniform[m.surface]=Q*(.25+.13*u[:,0]+.19*u[:,1]*u[:,2])
    dv=face.cell_gradient(v)
    _,bv=face.sample(v)
    base=Q*np.einsum("ij,ij->",bv,face.ba)
    for name,field in (("ideal",p),("angular_surface",p_nonuniform)):
        f=face.pressure(field)
        internal=base+np.sum((field[m.surface]-Q)*face.vol*np.trace(dv,axis1=1,axis2=2))
        diff=abs(np.einsum("ij,ij->",f,v)-internal)
        combined=f+external
        checks[name+"_pressure_power_difference_W"]=diff
        checks[name+"_net_force_N"]=np.linalg.norm(combined.sum(axis=0))
        checks[name+"_net_torque_Nm"]=np.linalg.norm(np.cross(x,combined).sum(axis=0))
        checks[name+"_rigid_power_W"]=abs(np.einsum("ij,ij->",combined,rigid))
        assert max(diff,checks[name+"_net_force_N"],checks[name+"_net_torque_Nm"],checks[name+"_rigid_power_W"])<1e-9
    with csvfile.open("x",encoding="utf8",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(1,3,figsize=(12,3.8),layout="constrained")
    for name,color,marker in (("P1","#46515d","o"),("face midpoint","#b98335","^"),("face centroid","#17698b","s")):
        series=[r for r in rows if r["method"]==name and r["material_shell"] in ("15","16","17","18","19","20")]
        for ax,col in zip(axes,("outward_mean_m_s2","radial_angular_sd_m_s2","tangent_vector_rms_m_s2")):
            ax.plot([int(r["material_shell"]) for r in series],[r[col] for r in series],color=color,marker=marker,ms=4,label=name)
    for ax,tit in zip(axes,("Mean outward acceleration","Radial standard deviation","Tangential RMS")):
        ax.set(title=tit,xlabel="Material shell",ylabel="Acceleration (m/s²)",xticks=range(15,21));ax.grid(alpha=.23)
    axes[0].legend()
    fig.savefig(figfile,dpi=165);plt.close(fig)
    hashes={str(path.relative_to(T)):hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (GEOM,SURFACE,Path(__file__).resolve(),csvfile,figfile)}
    with rec.open("x",encoding="utf8") as file:
        json.dump(dict(checks=checks,sha256=hashes,seconds=time.perf_counter()-start,
                       material_ids=m.n,native_mass_kg=m.mass.sum(),wendland_h_m=H,
                       arithmetic="double; actual initial geometry and native mass; no time integration",
                       test_field="p=10000 Pa in shells 1-19; p=0 on shell 20; q_ext=10000 Pa; effective stress/velocity=0",
                       complete_interior_cell_gradients_measured=False),file,indent=2,allow_nan=False)
    for row in rows:
        if row["material_shell"] in ("19","20","1-18"):
            print(row)
    print(json.dumps(checks,indent=2))


if __name__=="__main__":
    run()
