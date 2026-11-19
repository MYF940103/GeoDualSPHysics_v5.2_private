"""Matching nodal virtual strain, momentum, traction and actual-acceleration Darcy divergence."""
import os
for env_key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[env_key]="1"
import json
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from cryer_coupled_shell_modes import T, DP, R, RHO, MU, LAM, Graph


def check(condition,message):
    if not condition: raise ValueError(message)


def assemble():
    mesh=np.load(T/"outputs/cryer_tet_reference_r1.npz")
    x=mesh["x0"];t=mesh["tets"];ve=mesh["Ve"];g=mesh["Ve_gradN"]
    faces=mesh["faces"];av=mesh["face_area_out"];mass=mesh["native_mass_kg"]
    n=len(x);shell=mesh["material_shell"]-1;B=np.eye(20)[shell]
    check(np.array_equal(mesh["native_ids"],np.arange(8,37181)) and np.array_equal(np.unique(shell),np.arange(20))
          and len(t)==209117 and len(faces)==10302,"Original volume mesh and materials")
    normal=x/np.linalg.norm(x,axis=1)[:,None]
    u=normal[:,:,None]*B[:,None,:]
    dual=np.bincount(t.ravel(),weights=np.repeat(ve/4,4),minlength=n)
    shell_vol=B.T@dual;shell_mass=B.T@mass
    check(np.all(dual>0) and abs(dual.sum()-ve.sum())<1e-15,"Positive dual volume")
    nt=len(t)
    # Each incident tetrahedron contributes int(N_i)=V_e/4 to receiver i.
    recv=coo_matrix((np.full(4*nt,.25),(t.ravel(),np.repeat(np.arange(nt),4))),
                    shape=(n,nt)).tocsr()
    g_int=[];grad=[]
    for axis in range(3):
        integrated=coo_matrix((g[:,:,axis].ravel(),(np.repeat(np.arange(nt),4),t.ravel())),
                              shape=(nt,n)).tocsr()
        g_int.append(integrated)
        grad.append((recv@integrated).multiply((1/dual)[:,None]).tocsr())
    affine=max(np.max(abs(op@x-np.eye(3)[i])) for i,op in enumerate(grad))
    check(affine<1e-11,"Affine strain recovery")
    # Virtual work of each stress component and full native six-stress tensor.
    z=x/R
    test_v=np.column_stack((z[:,0]*z[:,1]+.3*z[:,2]**2,
                            np.sin(z[:,0]+.2*z[:,2]),z[:,0]**2*z[:,1]-.2*z[:,2]))
    test_s=.2+z[:,0]-.4*z[:,1]**2+.1*np.cos(3*z[:,2])
    strain=np.stack([op@test_v for op in grad],axis=2)
    force_work=[]
    for a,b in ((0,0),(1,1),(2,2),(0,1),(0,2),(1,2)):
        force=np.zeros_like(x)
        # Independently scatter integrated cell traction from the average nodal stress.
        cell=test_s[t].mean(axis=1)
        np.add.at(force[:,a],t.ravel(),-(cell[:,None]*g[:,:,b]).ravel())
        if a!=b:
            np.add.at(force[:,b],t.ravel(),-(cell[:,None]*g[:,:,a]).ravel())
        virtual=-np.sum(dual*test_s*(strain[:,a,b] if a==b else strain[:,a,b]+strain[:,b,a]))
        actual=np.sum(force*test_v)
        norm=np.linalg.norm(test_v)*np.linalg.norm(force)
        discrepancy=abs(actual-virtual)/max(norm,1e-30)
        torque=np.linalg.norm(np.cross(x,force).sum(axis=0))/(R*np.linalg.norm(force,axis=1).sum())
        balance=np.linalg.norm(force.sum(axis=0))/np.linalg.norm(force,axis=1).sum()
        check(max(discrepancy,torque,balance)<2e-13,"Six stress work/force/torque")
        force_work.append(dict(component="xyz"[a]+"xyz"[b],force_work=actual,
            minus_stress_work=virtual,normalized_error=discrepancy,net_force_relative=balance,net_torque_relative=torque))
    gradient=[[op@u[:,a,:] for op in grad] for a in range(3)]
    theta=sum(gradient[a][a] for a in range(3))
    fu=np.zeros_like(u);fp=np.zeros_like(u)
    for a in range(3):
        fp[:,a,:]=grad[a].T@(dual[:,None]*B)
        for b in range(3):
            stress=MU*(gradient[a][b]+gradient[b][a])
            if a==b:stress+=LAM*theta
            fu[:,a,:]-=grad[b].T@(dual[:,None]*stress)
    del gradient
    ext=np.zeros_like(x)
    for j in range(3):np.add.at(ext,faces[:,j],-av/3)
    r=DP*np.arange(1,21);unit_traction=float(np.max(abs(ext)))
    hydro=float(np.max(abs(fu@r/(3*LAM+2*MU)-ext))/unit_traction)
    coupled=float(np.max(abs(fp.sum(axis=2)+ext))/unit_traction)
    check(max(hydro,coupled)<1e-10,"True pressure and stress boundary traction equilibrium")
    def project_force(force):
        return B.T@np.einsum("na,nak->nk",normal,force)/shell_mass[:,None]
    def project_scalar(field):
        return (B.T@(dual[:,None]*field))/shell_vol[:,None]
    def divergence(accel):
        return sum(grad[a]@accel[:,a,:] for a in range(3))
    K=project_force(fu);P=project_force(fp);F=project_force(ext[:,:,None])
    D=project_scalar(theta)
    DK=project_scalar(divergence(fu/mass[:,None,None]))
    DA=project_scalar(divergence(fp/mass[:,None,None]))
    DF=project_scalar(divergence(ext[:,:,None]/mass[:,None,None]))
    # Full native acceleration enters the hydraulic strain operator before any shell average.
    stiffness=-shell_mass[:,None]*K
    symmetry=float(np.max(abs(stiffness-stiffness.T))/np.max(abs(stiffness)))
    dual_p=float(np.max(abs(shell_mass[:,None]*P-(shell_vol[:,None]*D).T))/
                 np.max(abs(shell_mass[:,None]*P)))
    eig=np.linalg.eigvalsh(stiffness)
    check(symmetry<2e-12 and dual_p<2e-12 and eig.min()>0,"Reduced elastic and pressure work")
    lpfe=np.zeros((20,20))
    for weighted_g in g_int:
        dgu=weighted_g@B
        lpfe-=dgu.T@(dgu/ve[:,None])
    lpfe/=shell_vol[:,None]
    # Keep the original particle Darcy operator, including its affine correction and
    # exterior donors. Integrate its native scalar rows with candidate geometric dual volumes.
    graph=Graph()
    check(np.array_equal(graph.x,x),"Node ordering of true Darcy and tetrahedra")
    gp=graph.grad(B)
    rows=graph.sumw[:,None]*B-graph.W@B-sum(gp[k]*graph.lx[:,k,None] for k in range(3))
    lpsph=project_scalar(rows)
    saved=np.load(T/"figures/cryer_coupled_shell_modes_r1_blocks.npz")
    darcy_sanity=float(np.max(abs(graph.project(rows)-saved["La"]))/np.max(abs(saved["La"])))
    check(darcy_sanity<5e-13,"Underlying original Darcy graph unchanged")
    del graph
    common=dict(K=K,P=P,F=F,D=D,DK=DK,DP=DA,DF=DF,count=np.bincount(shell))
    quality=dict(soil_ids=n,tetrahedra=len(t),surface_triangles=len(faces),mesh_volume_m3=float(ve.sum()),
                 native_volume_to_tet_volume=float(mass.sum()/(RHO*ve.sum())),affine_gradient_error=affine,
                 hydrostatic_traction_relative=hydro,pressure_traction_relative=coupled,six_component_work=force_work,
                 radial_skeleton_symmetric_relative=symmetry,radial_coupled_pressure_work_relative=dual_p,
                 shell_stiffness_extreme_eigenvalues_N_per_m=[float(eig.min()),float(eig.max())],
                 original_Darcy_reconstruction_relative=darcy_sanity,
                 original_inertia="unaltered native particle masses",
                 hydraulic_mass="geometric nodal lump Vdual, constant properties",
                 material="each material ID retains a single nodal strain and stress; pressure force uses same transpose",
                 actual_SPH_solver_changes=False)
    return common,lpsph,lpfe,quality


def main():
    prefix="cryer_shell_tet_pair_r1"
    targets=[T/"figures"/(prefix+"_"+name+".npz") for name in ["sph","p1"]]
    receipt=T/"logs"/(prefix+".check.json")
    check(not any(p.exists() for p in [*targets,receipt]),"Retained math results exist")
    blocks,lp_sph,lp_p1,quality=assemble()
    for path,lap in zip(targets,[lp_sph,lp_p1]):
        np.savez(path,**blocks,La=lap)
    receipt.write_text(json.dumps(quality,indent=2)+"\n",encoding="utf8")
    print(json.dumps(quality))


if __name__=="__main__":
    main()
