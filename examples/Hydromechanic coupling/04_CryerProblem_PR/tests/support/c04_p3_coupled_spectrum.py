"""Frozen three-dimensional nodal-mechanical / SPH-hydraulic pressure iteration, no trajectories."""
import json
from time import perf_counter
from cryer_coupled_shell_modes import T, np, RHOW, DP
from scipy.sparse.linalg import LinearOperator
from c04_p3_pressure_component import CryerSPHPressure, K, GAMMA
from cryer_tet_mechanics import TetMechanics

TAG="c04_p3_coupled_spectrum_r1"


def rms(x):
    return float(np.sqrt(np.mean(abs(x)**2)))


class Coupled:
    def __init__(self,p,m,drained):
        self.p,self.m=p,m
        self.drain=drained
        self.active=np.flatnonzero(~p.fs) if drained else np.arange(len(p.ids))
        self.n=len(self.active)
        self.op=LinearOperator((self.n,self.n),matvec=self.multiply,dtype=np.float64)

    def expand(self,q):
        if not self.drain:
            return q
        full=np.zeros(len(self.p.ids),dtype=q.dtype)
        full[self.active]=q
        return full

    def force_source(self,a):
        return RHOW*(self.m.divergence(a)+np.einsum("ij,ij->i",self.p.normal_lx,a))/self.p.S0

    def multiply(self,q):
        p,m=self.p,self.m
        field=self.expand(q)
        acc=m.pressure_force(field)/m.mass[:,None]
        z=p.E@field+self.force_source(acc)
        return z[self.active]

    def constant_moments(self,weight):
        # Exact coefficient row for the volume integral of Lp + rho Dtilde a(p);
        # integrate only closed rows to avoid confusing prescribed drainage flux with loss.
        assert not self.drain
        p,m=self.p,self.m
        u=p.S0*weight
        lp=p.E.T@u-u
        b=np.column_stack([D.T@weight for D in m.D])+p.normal_lx*weight[:,None]
        af=RHOW*sum(H.T@(b[:,k]/m.mass) for k,H in enumerate(m.HT))
        def summarize(v):
            return dict(sum_m=float(v.sum()),L1_m=float(np.linalg.norm(v,1)),max_m=float(abs(v).max()),
                        L1_per_volume_mneg2=float(np.linalg.norm(v,1)/weight.sum()),
                        max_native_id=int(p.ids[np.argmax(abs(v))]))
        return dict(pressure_constant_null=abs(lp.sum())/weight.sum(),
                    pressure_column_defect=summarize(lp),combined_pressure_mechanics_column_defect=summarize(lp+af),
                    acceleration_uniform_p_alone_integral_per_volume_mneg2=float(af.sum()/weight.sum()),
                    vector_acceleration_flux_coeff_L1_m2=float(np.sum(np.linalg.norm(b,axis=1))),
                    boundary_total_area_m2=float(np.linalg.norm(m.unit_surface_force,axis=1).sum()),
                    surface_only_acceleration_flux_coeff_fraction=float(np.linalg.norm(b[m.surface],axis=1).sum()/np.linalg.norm(b,axis=1).sum()))

    def probe(self,name,full):
        base=full[self.active]
        values=[];cur=base
        for k in range(1,7):
            cur=self.op@cur
            if k in (1,3,6):
                values.append(dict(round=k,l2_gain=float(np.linalg.norm(cur)/np.linalg.norm(base)),
                                   linf_gain=float(max(abs(cur))/max(abs(base)))))
        # Fixed mech/strain source, zero incoming history at this instant gives a unit
        # pressure impulse vs the matched history; this is a temporal error diagnostic.
        old=np.zeros_like(base); current=base
        tp=[]
        for k in range(1,7):
            pred=1.5*current-.5*old
            for _ in range(3):
                pred=self.op@pred
            old,current=current,pred
            if k in (1,3,6):
                tp.append(dict(complete_pressure_steps=k,l2_gain=float(np.linalg.norm(current)/np.linalg.norm(base))))
        return dict(field=name,each_round=values,frozen_temporal_impulse=tp)

    def arnoldi(self,maxdim,seed):
        rng=np.random.default_rng(seed)
        x=rng.normal(size=self.n)
        return self.arnoldi_start(maxdim,x)

    def arnoldi_start(self,maxdim,x):
        # Double MGS and a direct residual on the returned Ritz vector, including
        # discarded dimensions, so a finite subspace estimate is not a spectral bound.
        Q=np.zeros((self.n,maxdim+1),order="F")
        H=np.zeros((maxdim+1,maxdim))
        Q[:,0]=x/np.linalg.norm(x)
        for j in range(maxdim):
            vec=self.op@Q[:,j]
            V=Q[:,:j+1]
            for _ in range(2):
                h=V.T@vec
                H[:j+1,j]+=h
                vec-=V@h
            H[j+1,j]=np.linalg.norm(vec)
            if H[j+1,j]<1e-15:
                maxdim=j+1
                break
            Q[:,j+1]=vec/H[j+1,j]
        vals,vectors=np.linalg.eig(H[:maxdim,:maxdim])
        rec=[]
        for i in np.argsort(-abs(vals))[:4]:
            val=vals[i]
            z=Q[:,:maxdim]@vectors[:,i]
            y=self.op@z.real+1j*(self.op@z.imag)
            resid=np.linalg.norm(y-val*z)/np.linalg.norm(z)
            roots=np.roots([1,-1.5*val**3,.5*val**3])
            field=self.expand(z)
            rec.append(dict(lambda_real=float(val.real),lambda_imag=float(val.imag),resid=float(resid),
                error_field_max_native_id=int(self.p.ids[np.argmax(abs(field))]),
                surface_energy_fraction=float(np.linalg.norm(field[self.m.surface])**2/np.linalg.norm(field)**2),
                outer_two_shells_energy_fraction=float(np.linalg.norm(field[self.m.shells>=19])**2/np.linalg.norm(field)**2),
                frozen_P3_temporal_root_max=float(max(abs(roots))),three_round_factor=float(abs(val)**3)))
        return dict(dimension=maxdim,ritz=rec)


def main():
    path=T/"logs"/(TAG+".json")
    if path.exists():
        raise FileExistsError(path)
    p=CryerSPHPressure.load()
    m=TetMechanics(T/"outputs/cryer_tet_reference_r1.npz")
    assert np.array_equal(np.flatnonzero(p.fs),m.surface) and np.array_equal(p.ids,m.ids)
    out=dict(role="Frozen small-strain particle pressure and matched nodal mechanics. No physical solver or continuum certification.",
             scope="Pressure-only perturbations at held displacement/velocity/theta/external load. Their temporal predictor is conditional; the complete evolving body/velocity trajectory has further feedback.",
             dimensions=dict(n=len(m.ids),surface=len(m.surface),shells=np.unique(m.shells).tolist()))
    for drain in (False,True):
        c=Coupled(p,m,drain)
        stats={}
        fa=m.surface_force(10000)/m.mass[:,None]
        # Applied pressure and uniform pore pressure must cancel via the same geometric surface.
        pa=m.pressure_force(np.full(m.n,10000))/m.mass[:,None]
        stats["uniform_closed_body_pressure_load_acceleration_residual_m_s2"]=rms(pa+fa)
        load=c.force_source(fa)[c.active]
        z=np.zeros(c.n)
        startup=[]
        for k in range(1,4):
            z=c.op@z+load
            startup.append(dict(round=k,min_Pa=float(z.min()),max_Pa=float(z.max()),rms_Pa=rms(z),mean_Pa=float(z.mean())))
        stats["sudden_10kPa_load_first_three_rounds_zero_theta_not_linear_ramp"]=startup
        if not drain:
            stats["closed_integrated_residual"]={"Vdual":c.constant_moments(m.volume),"Vnative":c.constant_moments(m.native_volume)}
        fields={"constant_pressure_at_fixed_external_traction":np.ones(m.n),
                "highest_shell_parity":np.where(m.shells%2,1.,-1.),"cartesian_cos_pi_x_over_dp":np.cos(np.pi*m.x[:,0]/DP),
                "random":np.random.default_rng(20261120).choice([-1.,1.],m.n)}
        if not drain:
            fields["boundary_only"]=p.fs.astype(float)
        else:
            fields["outermost_active_shell_only"]=(m.shells==max(m.shells[~p.fs])).astype(float)
        stats["probes"]=[c.probe(name,v) for name,v in fields.items()]
        stats["arnoldi"]=c.arnoldi(55,1729)
        stats["source_oriented_arnoldi"]=c.arnoldi_start(35,load)
        print(drain,stats["arnoldi"]["ritz"][0],flush=True)
        out["open" if drain else "closed"]=stats
    with path.open("x") as f:json.dump(out,f,indent=2,allow_nan=False)
    print(path,flush=True)


if __name__=="__main__":
    main()
