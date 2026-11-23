"""Independent fixed-reference Cryer volume, traction, pressure-work and posterior flux audit."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from c04_p3_pressure_component import K, GAMMA
from cryer_coupled_shell_modes import T, np, RHOW, DAMP, DT
from cryer_tet_mechanics import TetMechanics
from cryer_tet_darcy_spectrum import assemble
from cryer_pair_window import viscosity_matrix


def surface_vol(x,f,avec):
    return np.einsum("ij,ij->",x[f].mean(axis=1),avec)/3.


def exact_face_rms(t,weights):
    # Exact integral of squared affine traction on planar P1 faces.
    norm2=(np.sum(t*t,axis=(1,2))+np.sum(t.sum(axis=1)**2,axis=1))/12.
    return float(np.sqrt(np.average(norm2,weights=weights)))


class Audit:
    def __init__(self):
        geom=T/"outputs/cryer_tet_reference_r1.npz"
        self.m=m=TetMechanics(geom);self.K=assemble(geom)[-1]
        with np.load(geom) as z:
            self.t=z["tets"];self.V=z["Ve"];self.G=z["Ve_gradN"]
            self.f=z["faces"];self.area=z["face_area_out"]
        self.A=np.linalg.norm(self.area,axis=1);self.normal=self.area/self.A[:,None]
        triangles=m.x[self.f]
        from_indices=.5*np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        self.sign=np.sign(np.einsum("ij,ij->i",from_indices,self.area))
        assert np.max(abs(from_indices*self.sign[:,None]-self.area))<1.e-15
        self.b=m.pressure_force(np.ones(m.n))
        self.surf=np.zeros(m.n,dtype=bool);self.surf[m.surface]=True
        # Lookup by unordered native face, independent of orientation or tetra slot.
        wanted={tuple(sorted(row)):i for i,row in enumerate(self.f)}
        self.owner=np.full(len(self.f),-1)
        for side in ((0,1,2),(0,1,3),(0,2,3),(1,2,3)):
            ft=self.t[:,side]
            ii=np.flatnonzero(np.all(self.surf[ft],axis=1))
            for elem in ii:
                q=wanted.get(tuple(sorted(ft[elem])))
                if q is not None:
                    assert self.owner[q]<0
                    self.owner[q]=elem
        assert np.all(self.owner>=0)
        self.av=viscosity_matrix(m)
        self.ref_vol=float(self.V.sum())

    def avacc(self,v):
        m=self.m
        W=self.av
        a=np.zeros_like(v)
        for start in range(0,m.n,640):
            end=min(start+640,m.n); ptr=W.indptr[start:end+1]
            sl=slice(ptr[0],ptr[-1])
            i=np.repeat(np.arange(start,end),np.diff(ptr)); j=W.indices[sl]
            xij=m.x[i]-m.x[j];d=np.minimum(0,np.einsum("ij,ij->i",xij,v[i]-v[j]))
            a[start:end]=np.add.reduceat((W.data[sl]*d)[:,None]*xij,ptr[:-1]-ptr[0],axis=0)
        return a

    def audit(self,path,work=False):
        m=self.m;f=self.f;V=self.V;t=self.t
        with np.load(path) as z:
            step=int(z["step"]);assert path.stem==f"state_{step}"
            assert np.array_equal(m.ids,z["ids"]) and len(m.ids)==37173
            p=z["p"];u=z["u"];v=z["v"];s=z["stress"];J=z["J"];old=z["previous"]
            program=Path(z["program"].item()).name
        assert program=="cryer_weak_window.dll" and all(np.isfinite(a).all() for a in [p,u,v,s,J,old])
        assert step>=4096 and np.all(J>1.-float(np.float32(.3)))
        open_=step>4096
        if open_: assert np.all(p[self.surf]==0.) and np.all(old[self.surf]==0.)
        x=m.x;xp=x+u;X=xp[f]
        avec=.5*np.cross(X[:,1]-X[:,0],X[:,2]-X[:,0])*self.sign[:,None]
        A=np.linalg.norm(avec,axis=1)
        # All recorded u and v are values on the original mesh. No extrapolated face displacement.
        gradU=np.einsum("tki,tkj->tij",u[t],self.G)/V[:,None,None]
        det=np.linalg.det(np.eye(3)+gradU)
        vf=surface_vol(xp,f,avec);tc=float(V@det)
        vlin=float(np.einsum("ij,ij->",self.b,u));vflux=float(np.einsum("ij,ij->",self.b,v))
        dV=float(V@(det-1.))
        dJ=float(m.volume@(J-1.))
        dJn=float(m.native_volume@(J-1.))
        theta=m.divergence(v)
        qt=10000.;hyd=K/GAMMA
        # Independent reconstruction at the saved full state. Endpoint AV from the solver
        # was frozen before the last three pressure updates. That substage AV is not saved.
        a=(m.internal_stress(s)+m.pressure_force(p)+m.surface_force(qt))/m.mass[:,None]+self.avacc(v)-DAMP*v
        kp=self.K@p
        fluxA=RHOW*sum(H@a[:,j] for j,H in enumerate(m.HT))
        residual=kp+fluxA+1/hyd*m.volume*theta
        sourceOut=-hyd*float(residual[self.surf].sum())
        interior=~self.surf
        gradp=np.einsum("tk,tkj->tj",p[t],self.G)/V[:,None]
        # One-sided trace from the unique adjacent tetra, using P1 boundary interpolation of a.
        qface=-hyd*(gradp[self.owner]+RHOW*a[f].mean(axis=1))
        qfaceout=float(np.einsum("ij,ij->",qface,self.area))
        # Direct nodal traction of the physical stress on each face normal (exact squared integral).
        sf=s[f];n=self.normal[:,None,:]
        tr=np.stack([np.sum(sf[:,:,k]*n,axis=2) for k in ([0,3,5],[3,1,4],[5,4,2])],axis=2)
        tr+=(qt-p[f])[:,:,None]*n
        tn=(tr*n).sum(axis=2)[:,:,None]
        transverse=tr-tn*n
        ref_power=-qt*vflux; deform_power=-qt*float(np.einsum("ij,ij->",v[f].mean(axis=1),avec))
        center=m.shells==1
        unit=x/np.linalg.norm(x,axis=1)[:,None]
        ur=np.einsum("ij,ij->i",u,unit);tcpress=p-s[:,:3].mean(axis=1)
        # Robustly measure radial magnitude and area-weighted normal displacement of actual triangles.
        output=dict(step=step,time_s=step*DT,tau_s=(step-4096)*DT,original_program=program,ids=len(m.ids),nodes_fs=int(self.surf.sum()),faces=len(f),
          initial_geometric_volume_m3=self.ref_vol,initial_native_volume_m3=float(m.native_volume.sum()),
          J_volume_change_geometric_quadrature_m3=dJ,J_volume_change_native_quadrature_m3=dJn,
          volume_change_by_tet_determinants_m3=dV,volume_by_surface_m3=vf,volume_by_tets_m3=tc,
          signed_volume_rate_bT_v_m3_s=vflux,fixed_volume_rate_by_Vdual_div_v_m3_s=float(m.volume@theta),
          current_surface_outward_velocity_m3_s=-deform_power/qt,
          linear_volume_change_bT_u_m3=vlin,deformed_area_m2=float(A.sum()),reference_area_m2=float(self.A.sum()),
          area_weighted_reference_surface_normal_inward_mm=-1000*vlin/self.A.sum(),
          surface_mean_inward_radial_mm=-1000*float(ur[self.surf].mean()),
          deformed_J_element_minmax=[float(det.min()),float(det.max())],J_node_minmax=[float(J.min()),float(J.max())],
          effective_volume_minus_linear_sigma_consistency_RMS_Pa=float(np.sqrt(np.mean((s[:,:3].mean(axis=1)-(m.lam+2*m.mu/3)*m.divergence(u))**2))),
          P0_storage="initial pressure field P0 is not stored in this private checkpoint",
          surface_pressure_absmax_Pa=float(np.max(abs(p[self.surf]))),surface_history_absmax_Pa=float(np.max(abs(old[self.surf]))),
          all_p_minmax_Pa=[float(p.min()),float(p.max())],fixed18_p_Pa=float(p[center].mean()),center18_effective_compression_Pa=float(-s[center,:3].mean()),
          center18_total_compression_Pa=float(tcpress[center].mean()),total_compression_volume_weighted_Pa=float(np.average(tcpress,weights=m.volume)),
          fixed_face_total_traction_RMS_Pa=exact_face_rms(tr,self.A),fixed_face_normal_traction_RMS_Pa=exact_face_rms(tn,self.A),
          fixed_face_shear_traction_RMS_Pa=exact_face_rms(transverse,self.A),
          fixed_surface_pressure_power_W=ref_power,deformed_surface_pressure_power_W=deform_power,
          constant_q_reference_traction_potential_work_from_undeformed_J=-qt*vlin,
          constant_q_current_surface_comparison_work_from_undeformed_J=-qt*dV,
          weak_dirichlet_reaction_out_m3_s=(sourceOut if open_ else None),
          raw_one_sided_normal_Darcy_out_m3_s=qfaceout,
          global_consolidation_outward_volume_expectation_m3_s=-vflux,
          posterior_interior_continuity_integrated_rate_m3_s=float(hyd*residual[interior].sum()),
          posterior_interior_weak_residual_RMS_per_s=float(np.sqrt(np.mean((hyd*residual[interior]/m.volume[interior])**2))),
          stored_water_volume_change_M0_fixed_solid_geometric_m3=dJ,
          current_geometric_minus_integrated_ledger_m3=dV-dJ,
          files=str(path.resolve().relative_to(T)).replace(chr(92),"/"))
        if work:
            strainrate=m.strain(v)
            pw=float(np.sum(m.volume*p*theta))
            sw=float(-np.einsum("i,ik,ik->",m.volume,s,strainrate))
            pforce=m.pressure_force(p);sforce=m.internal_stress(s)
            pfwork=float(np.sum(v*pforce));sfwork=float(np.sum(v*sforce))
            acquired=np.einsum("ik,ik,i->",a,v,m.mass)
            avpower=float(np.sum(v*(m.mass[:,None]*self.avacc(v))))
            damppower=float(-DAMP*np.sum(m.mass[:,None]*v*v))
            def mean_dot(x,y):
                return float(np.einsum("i,ij,ij->",V,x,y))
            amean=a[t].mean(axis=1)
            gradtotal=gradp+RHOW*amean
            spending=hyd*mean_dot(gradtotal,gradtotal)
            cross=hyd*RHOW*mean_dot(gradtotal,amean)
            pmean=float(np.average(p,weights=m.volume))
            sigmaMean=float(np.average(s[:,:3].mean(axis=1),weights=m.volume))
            mi=a-self.avacc(v)+DAMP*v
            virial=float(np.einsum("i,ij,ij->",m.mass,m.x,mi)/(3*self.ref_vol))
            bulk=m.lam+2*m.mu/3
            geometric_s_approx=(self.ref_vol/self.A.sum())*(qt-pmean)/bulk
            output["affine_volume_virial"]=dict(
                volume_weighted_p_Pa=pmean,unweighted_p_Pa=float(p.mean()),volume_mean_tensile_stress_Pa=sigmaMean,
                volume_weighted_total_compression_minus_applied_Pa=pmean-sigmaMean-qt,
                inertia_minus_AV_and_damping_dilation_work_per_3V_Pa=virial,
                independent_dilation_virtual_work_residual_Pa=pmean-sigmaMean-qt-virial,
                inferred_quasistatic_inward_from_geometric_mean_p_mm=1000*geometric_s_approx,
                actual_area_normal_inward_mm=-1000*vlin/self.A.sum(),
                scope="Moment identity is algebraic on the fixed linear geometry; using the quasistatic estimate neglects inertia and stress-rate/strain mismatch.")
            output["posterior_power"]=dict(
                pore_body_work_W=pfwork,by_volume_pressure_strain_rate_W=pw,
                effective_stress_work_W=sfwork,by_volume_contracted_strain_rate_W=sw,
                AV_work_W=avpower,damping_work_W=damppower,
                applied_face_work_W=ref_power,inertial_work_W=float(acquired),
                mechanical_work_identity_error_W=float(acquired-(pfwork+sfwork+avpower+damppower+ref_power)),
                element_Darcy_quadratic_W=spending,liquid_acceleration_cross_W=cross,
                nonzero_continuity_pressure_work_W=hyd*float(p@residual),
                residual_power_identity_W=pw+spending-cross-hyd*float(p@residual),
                elastic_energy_from_nodal_strain_u_J=float(m.elastic_energy(u)),
                soil_kinetic_energy_J=.5*float(np.sum(m.mass[:,None]*v*v)),
                note="Dissipation here is a constitutive nonnegative quadratic of posterior element-mean acceleration. The liquid-acceleration cross term and finite three-sweep pressure residual remain; this endpoint identity is not a global time-integrated energy certificate.")
        return output


def main(args):
    out=T/"logs"/(f"c04_weak_checkpoint_budget_{args.label}_r1.json")
    if out.exists():raise FileExistsError(out)
    obj=Audit()
    rows=[obj.audit(p,work=(args.label=="peak")) for p in args.state]
    for r in rows:
        assert abs(r["volume_by_tets_m3"]-r["volume_by_surface_m3"])<1.e-15
        assert abs(r["signed_volume_rate_bT_v_m3_s"]-r["fixed_volume_rate_by_Vdual_div_v_m3_s"])<1.e-15
    scope=("Point-in-time work and reaction on the actual reference faces. The mass matrix retains native particle mass. Geometric and native quadratures are separately reported. At constant load and fixed reference pressure, work after opening is exactly -q [b^Tu(t)-b^Tu(tD)]. The checkpoint contains no true substage acceleration, frozen endpoint AV or per-step face flux. The reconstructed instantaneous full-state reaction and one-sided unaveraged P1 gradient trace can differ. Neither is a cumulative native fluid mass balance. J is a separate nodal time integration; the P1 element determinant comes from saved displacement.")
    with out.open("x") as f:json.dump(dict(checkpoints=rows,scope=scope),f,indent=2,allow_nan=False)
    print(out)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("label",choices=("opening","peak"))
    p.add_argument("state",type=Path,nargs="+")
    main(p.parse_args())




