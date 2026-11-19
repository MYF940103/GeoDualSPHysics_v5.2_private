"""Independently generate one CPU force-stage reference for the private 3-D Cryer program."""
import argparse
import json
import os
from pathlib import Path
for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[name]="1"
import numpy as np
from scipy.spatial import cKDTree
from cryer_tet_mechanics import TetMechanics


TAG="cryer_tet_step_reference_r1"
H=.0045
SOUND=35.80574408560461
ALPHA=.1


def artificial_viscosity(x,volume,rho,v,pairs,alpha=ALPHA,sound=SOUND,h=H):
    """Forces on original material IDs with frozen geometry and the compression-only AV."""
    mass=volume*rho
    result=np.zeros_like(x)
    power=0.; count=0
    for lo in range(0,len(pairs),50000):
        i,j=pairs[lo:lo+50000].T
        r=x[i]-x[j];dv=v[i]-v[j]
        dot=np.einsum("ij,ij->i",r,dv)
        use=dot<0
        if not use.any():continue
        i,j,r,dv,dot=i[use],j[use],r[use],dv[use],dot[use]
        r2=np.einsum("ij,ij->i",r,r)
        amu=h*dot/(r2+.01*h*h)
        pi=-alpha*sound*amu/(.5*(rho[i]+rho[j]))
        fac=-2.08891/h**5*np.maximum(1-np.sqrt(r2)/(2*h),0.)**3
        pairF=(-mass[i]*mass[j]*pi*fac)[:,None]*r
        for k in range(3):
            result[:,k]+=np.bincount(i,weights=pairF[:,k],minlength=len(x))
            result[:,k]-=np.bincount(j,weights=pairF[:,k],minlength=len(x))
        power+=np.sum(np.sum(dv*pairF,axis=1))
        count+=int(use.sum())
    measured=float(np.sum(result*v))
    if abs(measured-power)>2e-12*max(1.,abs(power)) or measured>1e-14:
        raise AssertionError("Non-positive pair work must match nodal work.")
    return result,dict(approaching_pairs=count,nodal_power_W=measured,
                       pair_power_W=power,net_force_N=float(np.linalg.norm(result.sum(axis=0))),
                       net_torque_Nm=float(np.linalg.norm(np.cross(x,result).sum(axis=0))))


def main(cache):
    tests=Path(__file__).resolve().parents[1]
    dest=tests/"outputs"/(TAG+".npz")
    check=tests/"logs"/(TAG+".check.json")
    if dest.exists() or check.exists():
        raise FileExistsError("Preserve existing independent CPU reference.")
    m=TetMechanics(cache);x=m.x;r=x/.05;rad=np.linalg.norm(r,axis=1)
    rng=np.random.default_rng(20261120)
    u=1.e-7*np.column_stack((r[:,0]+.27*r[:,1]*r[:,2],-.77*r[:,1]+.15*r[:,2]**2,
                              .31*r[:,2]-.37*r[:,0]*r[:,1]))
    v=1.e-3*rng.standard_normal(x.shape)+.006*x
    p=10000.*(1-rad**2)*(1+.13*r[:,0]-.09*r[:,2]+.07*r[:,0]*r[:,1])
    p[m.surface]=0.
    q=10000.
    pairs=cKDTree(x).query_pairs(2*H,output_type="ndarray")
    rho=m.mass/m.native_volume
    primitive={}
    for key,field in (("translation",np.broadcast_to([.001,-.002,.003],x.shape)),("dilation",.02*x)):
        reference,stat=artificial_viscosity(x,m.native_volume,rho,field,pairs)
        assert stat["approaching_pairs"]==0 and np.all(reference==0)
        primitive[key]=stat
    vf,stat=artificial_viscosity(x,m.native_volume,rho,v,pairs)
    assert stat["nodal_power_W"]<0 and stat["net_force_N"]<1e-10 and stat["net_torque_Nm"]<1e-11
    primitive["mixed_velocity"]=stat
    eps=m.strain(u);sigma=m.elastic_stress(eps)
    eff=m.internal_stress(sigma); pf=m.pressure_force(p); ext=m.surface_force(q)
    total=eff+pf+ext+vf; acc=total/m.mass[:,None]
    assert np.max(abs(m.acceleration(u,p,q)+vf/m.mass[:,None]-acc))<1e-9
    with dest.open("xb") as f:
        np.savez_compressed(f,native_ids=m.ids,x_m=x,u_m=u,v_m_s=v,p_Pa=p,q_Pa=q,native_mass_kg=m.mass,
            native_volume_m3=m.native_volume,geometric_dual_volume_m3=m.volume,strain=eps,stress_Pa=sigma,
            divergence_v_per_s=m.divergence(v),effective_force_N=eff,pressure_force_N=pf,surface_force_N=ext,
            viscous_force_N=vf,total_force_N=total,acceleration_m_s2=acc,viscous_acceleration_m_s2=vf/m.mass[:,None])
    with check.open("x",encoding="utf8") as f:
        json.dump(dict(points=m.n,pairs=len(pairs),H=H,alpha=ALPHA,c_m_s=SOUND,eta_squared_m2=.01*H*H,
            q_Pa=q,total_vector_acceleration_rms_m_s2=float(np.sqrt(np.mean(np.sum(acc*acc,axis=1)))),
            universal_inputs="Frozen reference particles, real mass and V0, binary64 pair arithmetic; native kernel uses float operations and directed summation. Stored manufactured u,v,p isolate port differences, with exact zero pressure on real exterior.",
            pressure_force_unit="N",force_reference=str(dest),units="N for each force, kg, m, Pa, m/s, m/s2",
            stress_columns="xx,yy,zz,xy,yz,xz; engineering shear strain, physical shear stress",
            av=primitive),f,indent=2,allow_nan=False)
    print(json.dumps(primitive,indent=2))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("cache",type=Path)
    main(ap.parse_args().cache)
