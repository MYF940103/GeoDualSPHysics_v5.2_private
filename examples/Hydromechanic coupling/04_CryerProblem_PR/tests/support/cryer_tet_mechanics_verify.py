"""Component verification on the actual 3-D Cryer native material layout."""
import argparse
import json
import os
from pathlib import Path
import time
for name in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[name]="1"
import numpy as np
from cryer_tet_mechanics import TetMechanics
from cryer_shell_equilibrium import TESTS,Q,R,need,write

TAG="cryer_tet_mechanics_component_r1"
DT=2.**-19


def main(cache):
    target=TESTS/"logs"/(TAG+".check.json")
    table=TESTS/"figures"/(TAG+"_modes.csv")
    history=TESTS/"figures"/(TAG+"_free_pulse.csv")
    need(not any(file.exists() for file in (target,table,history)),"Preserve earlier receipts")
    start=time.perf_counter();m=TetMechanics(cache);setup=time.perf_counter()-start
    x=m.x;M=m.mass;V=m.volume;nn=m.n
    rng=np.random.default_rng(20261120);axes=np.eye(3)
    six=[]
    def test_strain(field,ref):
        eps=m.strain(field)
        err=float(abs(eps-ref).max());need(err<1e-9,"Exact manufactured small strain")
        return err
    for j,a in enumerate(axes):
        for label,u in ((f"translation{j}",np.tile(a,(nn,1))),(f"rotation{j}",np.cross(a,x))):
            err=test_strain(u,np.zeros(6))
            ff=m.internal_stress(m.elastic_stress(m.strain(u)))
            six.append(dict(mode=label,max_abs_strain=err,max_nodal_force_N=float(np.linalg.norm(ff,axis=1).max())))
    affine=[]
    for j,(i,k) in enumerate(((0,0),(1,1),(2,2),(0,1),(1,2),(0,2))):
        u=np.zeros_like(x)
        if i==k:u[:,i]=x[:,i]
        else:u[:,i]=x[:,k]/2;u[:,k]=x[:,i]/2
        affine.append(test_strain(u,np.eye(6)[j]))
    need(abs(m.divergence(x)-3).max()<1e-10,"Uniform dilation")
    u=rng.standard_normal((nn,3))*1.e-5
    v=rng.standard_normal((nn,3));p=rng.standard_normal(nn)*1e4
    sigma=rng.standard_normal((nn,6))*1.e4
    nodal=np.sum(v*m.internal_stress(sigma))
    integrated=-np.sum(V*np.sum(sigma*m.strain(v),axis=1))
    pwork=np.sum(v*m.pressure_force(p));pexp=np.sum(V*p*m.divergence(v))
    need(abs(nodal-integrated)<1e-10 and abs(pwork-pexp)<1e-10,"General virtual work and pressure signs")
    f=m.internal_stress(sigma)
    net=np.linalg.norm(f.sum(axis=0));torque=np.linalg.norm(np.cross(x,f).sum(axis=0))
    need(net<1e-10 and torque<1e-10,"Discrete linear and angular momentum")
    ru=m.internal_stress(m.elastic_stress(m.strain(u)))
    rv=m.internal_stress(m.elastic_stress(m.strain(v)))
    reciprocity=np.sum(ru*v)-np.sum(rv*u)
    need(abs(reciprocity)<1e-8 and abs(.5*np.sum(ru*u)+m.elastic_energy(u))<1e-9,"Elastic symmetry and energy")
    tf=m.surface_force(Q)
    work=np.sum(x*tf);theory=-3*Q*V.sum()
    need(abs(work-theory)<1e-10,"Actual pressure load work on uniform dilation")
    closed=m.pressure_force(np.full(nn,Q))+tf
    need(np.linalg.norm(closed/M[:,None],axis=1).max()<1e-7,"Undrained total traction balance")

    # Bound ||M^-1/2 B^T W C B M^-1/2||_2 using its absolute row-sum majorant,
    # computed by nonnegative multiplications rather than forming the two-hop stiffness.
    inv=1/np.sqrt(M); vp=np.tile(inv,(3,1)).T
    gd=[abs(D)@vp for D in m.D]
    epsabs=np.column_stack((gd[0][:,0],gd[1][:,1],gd[2][:,2],gd[0][:,1]+gd[1][:,0],
                            gd[1][:,2]+gd[2][:,1],gd[0][:,2]+gd[2][:,0]))
    # All entries of this material's engineering stiffness C are nonnegative (nu=.30).
    ws=m.elastic_stress(epsabs)
    upper=float(np.max(inv[:,None]*(abs(m.HT[0])@ws[:,[0,3,5]]+abs(m.HT[1])@ws[:,[3,1,4]]
                             +abs(m.HT[2])@ws[:,[5,4,2]])))
    def stiffness(q):
        return -inv[:,None]*m.internal_stress(m.elastic_stress(m.strain(inv[:,None]*q)))
    q=rng.standard_normal((nn,3));q/=np.linalg.norm(q)
    for i in range(80):
        kq=stiffness(q);q=kq/np.linalg.norm(kq)
    kq=stiffness(q);ray=float(np.sum(q*kq));res=float(np.linalg.norm(kq-ray*q))
    need(0<ray<=upper and DT*np.sqrt(upper)<2,"Guaranteed elastic central-difference step limit")
    # Block modes use original material IDs in shells 17 and 18.
    er=x/np.linalg.norm(x,axis=1)[:,None]
    shell=m.shells
    alternating=np.where(shell==17,1,np.where(shell==18,-1,0))
    phi=np.arctan2(x[:,1],x[:,0])
    modes=[]
    for label,disp in (("radial_linear",x/R),("alternating_radial_17_18",er*alternating[:,None]),
                       ("angular_alternating_17_18",er*(alternating*np.cos(14*phi))[:,None])):
        ff=m.internal_stress(m.elastic_stress(m.strain(disp)));energy=m.elastic_energy(disp)
        denom=np.sum(M*np.sum(disp*disp,axis=1))
        freq2=2*energy/denom
        need(0<freq2<=upper and abs(2*energy+np.sum(disp*ff))<max(1e-10,1e-11*energy),"Mode stiffness and work")
        modes.append(dict(mode=label,effective_frequency_Hz=np.sqrt(freq2)/(2*np.pi),
            elastic_energy_J_at_unit_m=energy,mass_norm_kg_at_unit_m=denom,
            net_N=np.linalg.norm(ff.sum(axis=0)),torque_Nm=np.linalg.norm(np.cross(x,ff).sum(axis=0))))
    disp=er*(1e-7*alternating*np.cos(14*phi))[:,None];vel=np.zeros_like(disp)
    acc=lambda uu:m.internal_stress(m.elastic_stress(m.strain(uu)))/M[:,None]
    a=acc(disp);energy0=m.elastic_energy(disp);hist=[]
    for step in range(129):
        if step%8==0:
            kin=.5*np.sum(M*np.sum(vel*vel,axis=1));ela=m.elastic_energy(disp)
            hist.append(dict(step=step,time_s=step*DT,kinetic_J=kin,elastic_J=ela,
                relative_energy=(kin+ela)/energy0-1,net_momentum=np.linalg.norm(np.sum(M[:,None]*vel,axis=0)),
                angular_momentum=np.linalg.norm(np.sum(np.cross(x,M[:,None]*vel),axis=0))))
        if step<128:
            vel+=DT/2*a;disp+=DT*vel;a=acc(disp);vel+=DT/2*a
    max_drift=max(abs(h["relative_energy"]) for h in hist)
    need(max_drift<(DT*np.sqrt(upper)/2)**2+1e-8,"Bounded free elastic pulse energy drift")
    speed={}
    for name,op in (("strain",lambda:m.strain(disp)),("pressure_force",lambda:m.pressure_force(p)),
                    ("elastic_force",lambda:acc(disp)),("divergence",lambda:m.divergence(vel))):
        op();t0=time.perf_counter()
        for _ in range(15):op()
        speed[name]=(time.perf_counter()-t0)/15
    write(table,modes);write(history,hist)
    summary=dict(cache=str(cache),material_count=nn,volume_m3=V.sum(),mass_kg=M.sum(),E_Pa=m.young,
        poisson=m.poisson,dt_s=DT,csr_entries_per_gradient=m.D[0].nnz,setup_s=setup,wall_s=time.perf_counter()-start,
        six_rigid_modes=six,six_affine_max_abs_strain_errors=affine,general_stress_work_W=nodal,
        stress_virtual_work_error_W=nodal-integrated,pressure_virtual_work_error_W=pwork-pexp,
        random_stress_net_N=net,random_stress_torque_Nm=torque,elastic_reciprocity_error_W=reciprocity,
        dilation_load_work_W=work,independent_dilation_load_work_W=theory,
        closed_max_acceleration_m_s2=np.linalg.norm(closed/M[:,None],axis=1).max(),
        omega2_upper_majorant=upper,largest_omega2_Rayleigh_lower=ray,Ritz_residual=res,
        guaranteed_elastic_step_s=2/np.sqrt(upper),largest_possible_elastic_step_s=2/np.sqrt(ray),
        dt_fraction_of_guaranteed_limit=DT*np.sqrt(upper)/2,free_pulse_max_relative_energy_drift=max_drift,
        warmed_single_thread_seconds_per_call=speed,
        scope="Fixed undeformed 3-D reference, linear isotropic solid, native nodal masses, geometric dual volumes, consistent nodal stress/strain and surface traction. The stability bound and unloaded pulse cover mechanics only.")
    with target.open("x",encoding="utf8") as f:json.dump(summary,f,indent=2,allow_nan=False)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("cache",type=Path)
    main(ap.parse_args().cache)
