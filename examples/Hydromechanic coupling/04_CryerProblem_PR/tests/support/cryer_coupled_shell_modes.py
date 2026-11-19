"""Linear radial pressure-traction transfer on Cryer's actual, frozen 20-shell particle graph."""
import os
for key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key]="1"
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.integrate import solve_bvp
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree

T=Path(__file__).resolve().parents[1]
PREFIX="cryer_coupled_shell_modes_r1"
DP,R=.0025,.05
H=float(np.float32(.0045))
YOUNG,POISSON=2e6,float(np.float32(.3))
MU=YOUNG/(2*(1+POISSON))
LAM=YOUNG*POISSON/((1+POISSON)*(1-2*POISSON))
LONG=LAM+2*MU
N0,RHO,RHOW=float(np.float32(.3)),2100.,1000.
HYD=float(np.float32(1e-5))/(RHOW*9.80665)
DAMP=float(np.float32(float(np.float32(.00004))*np.sqrt(YOUNG/(((RHO-N0*RHOW)/(1-N0))*H**2))))
DT=2.**-19


def check(test,message):
    if not test: raise ValueError(message)


class Graph:
    def __init__(self):
        path=T/"outputs/upl_cryer_freebody_peak_GPU_r1_native/native_ids.csv"
        records=pd.read_csv(path,float_precision="round_trip")
        p=records.loc[records.is_soil==1]
        check(np.array_equal(p.id,np.arange(8,37181)),"Original material owners")
        self.x=x=p[["x0","y0","z0"]].to_numpy(copy=True)
        radius=np.linalg.norm(x,axis=1)
        self.radial=x/radius[:,None]
        self.shell=shell=np.rint(radius/DP).astype(int)-1
        self.count=np.bincount(shell)
        self.n=len(x)
        v=p.initial_native_volume_m3.to_numpy()
        check(np.unique(v).size==1 and np.max(abs(radius-(shell+1)*DP))<1e-14
              and self.count[0]==18 and self.count[-1]==5153 and len(self.count)==20,"Initial radius and volumes")
        self.volume=float(v[0])
        self.eye=np.eye(20)[shell]
        self.vec=self.radial[:,:,None]*self.eye[:,None,:]
        pairs=cKDTree(x).query_pairs(2*H,output_type="ndarray").astype(np.int32)
        check(len(pairs)==3392720,"Native particle support changed")
        i,j=pairs.T
        n=self.n
        d=x[i]-x[j]
        rr=np.einsum("ij,ij->i",d,d)
        fac=float(np.float32(-2.08891/H**4))/H*(1-np.sqrt(rr)/(2*H))**3
        # Raw gradient with native donor volume. Reverse directed row has opposite sign.
        pos=np.r_[i,j]; nb=np.r_[j,i]
        def adjacency(data):
            return coo_matrix((data,(pos,nb)),shape=(n,n)).tocsr()
        self.raw=[]
        for k in range(3):
            val=v[0]*fac*d[:,k]
            self.raw.append(adjacency(np.r_[val,-val]))
        self.rows=np.stack([np.asarray(g.sum(axis=1)).ravel() for g in self.raw],axis=1)
        moment=np.stack([g@x-self.rows[:,k,None]*x for k,g in enumerate(self.raw)],axis=2)
        self.C=np.linalg.inv(moment)
        self.condition=float(np.linalg.cond(moment).max())
        # LP = sum w_ij(p_i-p_j), with the same corrected pair at both ends.
        # Batch avoids two large gathers of per-node 3x3 matrices.
        w=np.empty(len(pairs))
        for start in range(0,len(pairs),50000):
            sl=slice(start,start+50000)
            ci=self.C[i[sl]]+self.C[j[sl]]
            zz=np.einsum("ni,nij,nj->n",d[sl],ci,d[sl])
            w[sl]=v[0]*fac[sl]*zz/(rr[sl]+float(np.float32(.01*H**2)))
        self.W=adjacency(np.r_[w,w])
        self.sumw=np.asarray(self.W.sum(axis=1)).ravel()
        self.lx=self.sumw[:,None]*x-self.W@x

    def grad(self,f):
        # Receiver index first; derivative direction last in the mathematical tensor.
        raw=[m@f-self.rows[:,k,None]*f for k,m in enumerate(self.raw)]
        return [sum(self.C[:,k,b,None]*raw[b] for b in range(3)) for k in range(3)]

    def div(self,v):
        return sum(self.grad(np.ascontiguousarray(v[:,a,:]))[a] for a in range(3))

    def project(self,f):
        return (self.eye.T@f)/self.count[:,None]

    def project_vec(self,a):
        return self.project(np.einsum("ni,nik->nk",self.radial,a))

    def assemble(self):
        B=self.eye
        theta_grad=[self.grad(np.ascontiguousarray(self.vec[:,a,:])) for a in range(3)]
        theta=sum(theta_grad[a][a] for a in range(3))
        au,ap=[],[]
        for a in range(3):
            f=np.zeros_like(B)
            for b in range(3):
                stress=MU*(theta_grad[a][b]+theta_grad[b][a])
                if a==b: stress=stress+LAM*theta
                f+=self.raw[b]@stress+self.rows[:,b,None]*stress
            au.append(f/RHO)
            ap.append(-(self.raw[a]@B+self.rows[:,a,None]*B)/RHO)
        self.Au=np.stack(au,axis=1)
        self.Ap=np.stack(ap,axis=1)
        self.load=(2*self.rows/RHO)[:,:,None]
        pg=self.grad(B)
        self.L=self.sumw[:,None]*B-self.W@B-sum(pg[k]*self.lx[:,k,None] for k in range(3))
        self.du=theta
        self.DAu,self.DAp,self.Dload=[self.div(v) for v in (self.Au,self.Ap,self.load)]
        self.K=self.project_vec(self.Au);self.P=self.project_vec(self.Ap);self.F=self.project_vec(self.load)
        self.D=self.project(theta)
        self.La=self.project(self.L)
        self.DK=self.project(self.DAu);self.DP=self.project(self.DAp);self.DF=self.project(self.Dload)
        r=DP*np.arange(1,21)
        affine=float(np.max(abs(theta@r-3)))
        Qeq=np.einsum("nik,k->ni",self.Au,r)/(3*LAM+2*MU)-self.load[:,:,0]
        uniform_p=self.Ap.sum(axis=2)+self.load[:,:,0]
        balance=float(np.max(np.abs(Qeq)))
        normload=float(np.max(abs(self.load)))
        exact_darcy=self.sumw[:,None]*self.x-self.W@self.x
        affine_lap=exact_darcy-sum(self.grad(self.x)[k]*self.lx[:,k,None] for k in range(3))
        pair_sum=float(np.max(abs(self.Au.sum(axis=0)))/np.max(abs(self.Au)))
        check(affine<1e-12 and balance/normload<1e-11 and np.max(abs(uniform_p))/normload<1e-12,
              "Affine or total traction equilibrium")
        check(np.max(abs(affine_lap))<1e-9 and np.max(abs(self.L.sum(axis=1)))<1e-8
              and pair_sum<1e-8,"Darcy patch or net-force check")
        return dict(affine_div_absolute=affine,hydrostatic_force_relative=balance/normload,
                    pressure_load_relative=float(np.max(abs(uniform_p))/normload),
                    matrix_net_force_relative=pair_sum,affine_Darcy_max_per_m=float(np.max(abs(affine_lap))),
                    moment_max_condition=self.condition,native_volume_ratio=self.n*self.volume/(4*np.pi*R**3/3))

    def harmonic(self,s,storage):
        # Post-open surface p=0. Keep the outer radial skeleton DOF and all surface donors.
        # Scale displacement by LONG/R for conditioning. Each unknown has units Pa.
        c=R/LONG; I=np.eye(20)
        a=s*(s+DAMP)*I-self.K
        left=(s*(1+HYD*RHOW*DAMP)*self.D-HYD*RHOW*self.DK)[:-1]
        right=(s*storage*I-HYD*(self.La+RHOW*self.DP))[:-1,:-1]
        full=np.block([[a*c,-self.P[:,:-1]],[left*c,right]])
        rhs=np.r_[self.F[:,0],(HYD*RHOW*self.DF)[:-1,0]]
        # Quasistatic-uniform forces and the hydraulic rows carry different units.
        scale=np.abs(full).max(axis=1)
        solution=np.linalg.solve(full/scale[:,None],rhs/scale)
        u,p=c*solution[:20],np.r_[solution[20:],0j]
        return u,p

    def leakage(self,s,u,p,storage):
        velocity=s*self.vec@u
        a=self.Au@u+self.Ap@p+self.load[:,:,0]-DAMP*velocity
        full_res=a-(s**2)*(self.vec@u)
        shell_r=np.sum(full_res*self.radial,axis=1)
        mean_r=(self.project(shell_r[:,None])[:,0])[self.shell]
        tangential=full_res-self.radial*shell_r[:,None]
        scalar=storage*s*(self.eye@p)+s*(1+HYD*RHOW*DAMP)*(self.du@u)
        scalar-=HYD*(self.L@p+RHOW*(self.DAu@u+self.DAp@p+self.Dload[:,0]))
        active=self.shell!=19
        check(np.max(abs(mean_r))<1e-7 and np.max(abs(self.project(scalar[:,None])[:-1]))<1e-9,
              "Projected coupled residual")
        rms=lambda y:float(np.sqrt(np.mean(abs(y)**2)))
        return dict(tangential_accel_rms_m_s2_per_Pa=float(np.sqrt(np.mean((abs(tangential)**2).sum(axis=1)))),
                    within_shell_radial_accel_rms_m_s2_per_Pa=rms(shell_r-mean_r),
                    within_shell_hydraulic_residual_rms_per_Pa_s=rms(scalar[active]),
                    shell_mean_accel_residual_max=float(np.max(abs(mean_r))))


def continuum(s,storage,tolerance):
    # Dynamic radial Biot equations. U=LONG*u/R, e=LONG*div(u), P=p, B=R*dp/dr.
    # A unit compressive traction drives the drained sphere, including -cd*v in mechanics.
    A=np.array([[0,1,0,0],[RHO*R**2*s*(s+DAMP)/LONG,0,0,1],[0,0,0,1],
                [0,R**2*s*(1/HYD-RHOW*s)/LONG,R**2*storage*s/HYD,0]],dtype=complex)
    zero=np.zeros((4,4))
    real=np.block([[A.real,-A.imag],[A.imag,A.real]])
    singular=np.diag([-2,0,0,-2,-2,0,0,-2])
    def bc(lo,hi):
        return np.array([lo[0],lo[3],hi[2],hi[1]-4*MU/LONG*hi[0]-hi[2]+1,
                         lo[4],lo[7],hi[6],hi[5]-4*MU/LONG*hi[4]-hi[6]])
    x=np.linspace(0,1,101)
    out=solve_bvp(lambda x,y:real@y,bc,x,np.zeros((8,len(x))),S=singular,tol=tolerance,max_nodes=10000)
    check(out.success,out.message)
    values=out.sol(np.arange(1,21)/20)
    return R/LONG*(values[0]+1j*values[4]),values[2]+1j*values[6],len(out.x)


def main():
    graph=Graph()
    checks=graph.assemble()
    blocks={key:getattr(graph,key) for key in ("K","P","F","D","La","DK","DP","DF","count")}
    metrics=[]; radial=[]
    for model,storage in (("M0",0.),("finite_Kw",N0/2e8)):
        for freq in (.5,3,10,50):
            s=2j*np.pi*freq
            u,p=graph.harmonic(s,storage)
            refu,refp,nodes=continuum(s,storage,3e-7)
            tighter_u,tighter_p,_=continuum(s,storage,1e-7)
            check(np.max(abs(tighter_p-refp))<2e-6 and np.max(abs(tighter_u-refu))<1e-13,"Continuum refinement")
            def trap(step):
                sd=2j*np.tan(freq*np.pi*step)/step
                return graph.harmonic(sd,storage)[1]
            err_dt=float(abs(trap(DT)[0]-p[0]));err_half=float(abs(trap(DT/2)[0]-p[0]))
            leak=graph.leakage(s,u,p,storage)
            metrics.append(dict(model=model,frequency_Hz=freq,center_amplitude=abs(p[0]),
                continuum_center_amplitude=abs(refp[0]),center_amplitude_relative_error_pct=100*(abs(p[0])/abs(refp[0])-1),
                center_phase_error_deg=np.angle(p[0]/refp[0],deg=True),center_complex_spatial_defect=abs(p[0]-refp[0]),
                center_trapezoidal_dt_defect=err_dt,center_trapezoidal_half_defect=err_half,
                centered_time_defect_ratio=err_dt/err_half if err_half else None,
                continuum_refine_absmax=float(np.max(abs(tighter_p-refp))),continuum_nodes=nodes,**leak))
            for j in range(20):
                radial.append(dict(model=model,frequency_Hz=freq,shell=j+1,r_over_a=(j+1)/20,native_count=graph.count[j],
                    p_real=p[j].real,p_imag=p[j].imag,continuum_p_real=refp[j].real,continuum_p_imag=refp[j].imag,
                    u_real_m_per_Pa=u[j].real,u_imag_m_per_Pa=u[j].imag,
                    continuum_u_real_m_per_Pa=refu[j].real,continuum_u_imag_m_per_Pa=refu[j].imag))
    folder=T/"figures";file=lambda suffix:folder/(PREFIX+suffix)
    receipt=T/"logs"/(PREFIX+".check.json")
    targets=[file(s) for s in ("_transfer.csv","_shells.csv","_blocks.npz",".png")]+[receipt]
    check(not any(p.exists() for p in targets),"Retained result already exists")
    df=pd.DataFrame(metrics)
    df.to_csv(targets[0],index=False);pd.DataFrame(radial).to_csv(targets[1],index=False)
    np.savez(targets[2],**blocks)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout="constrained")
    for model,grp in df.groupby("model",sort=False):
        for ax,col in zip(axes,("center_amplitude_relative_error_pct","center_phase_error_deg","center_complex_spatial_defect")):
            ax.plot(grp.frequency_Hz,grp[col],marker="o",label=model)
        axes[2].plot(grp.frequency_Hz,grp.center_trapezoidal_dt_defect,ls="--",marker="x",label=model+" time")
    for ax in axes:
        ax.set_xscale("log");ax.set_xlabel("Traction frequency (Hz)");ax.grid(alpha=.25)
    axes[0].set_ylabel("Center amplitude error (%)");axes[1].set_ylabel("Center phase difference (deg)")
    axes[2].set_yscale("log");axes[2].set_ylabel("Center complex transfer difference");axes[2].legend(fontsize=8)
    axes[0].legend();fig.savefig(targets[3],dpi=160);plt.close(fig)
    receipt.write_text(json.dumps(dict(passed=True,soil_ids=37173,undirected_pairs=3392720,
        material_shells=20,pressure_dofs=19,frequencies_Hz=[.5,3,10,50],sources=["upl_cryer_freebody_peak_GPU_r1_native/native_ids.csv"],
        storage_models=["M0","finite Kw=2e8"],mechanical_damping_per_s=DAMP,dt_s=DT,checks=checks,
        nonlinear_solver_runs=0,physical_acceptance=False,actual_P3_time_integration=False,
        assumptions=["linear harmonic perturbation about uniform drained equilibrium, not preload startup",
        "fixed uniform particle masses/volumes, native positions, angularly unresolved displacement and pressure",
        "full unprojected discrete acceleration feeds Darcy; drainage p=0 on outer shell",
        "same continuously linearized nodal stress, no intermediate float rounding or nonlinear AV",
        "trapezoid time symbol is a diagnostic control; it does not measure actual P3 error"]),indent=2)+"\n")
    print(df[["model","frequency_Hz","center_amplitude_relative_error_pct","center_phase_error_deg","center_trapezoidal_dt_defect"]])


if __name__=="__main__":
    main()
