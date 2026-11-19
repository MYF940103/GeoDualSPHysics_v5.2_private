"""Offline P3 endpoint replay on original Debug step 2 and Release step 64; no SPH solver."""
import json
from time import perf_counter
from c04_p3_pressure_component import CryerSPHPressure, K, CACHE, T, RHOW, np, pd
from cryer_coupled_shell_modes import Graph, DT, DAMP, H
from cryer_p3_verify_r1 import snapshot

OUT=T/"logs/c04_p3_pressure_component_r1.json"


def error(v):
    x=np.asarray(v,dtype=np.float64)
    return dict(rms=float(np.sqrt(np.mean(x*x))),absmax=float(np.max(abs(x))))


def divergence(g,a):
    return g.div(a[:,:,None])[:,0]


def original_forces(g,arrays,t):
    j=arrays["PoroVolumeRatio"][8:].astype(float)
    v=arrays["Vel"][8:].astype(float)
    rho=RHOW+(2100-RHOW)/j
    kk=arrays["SigmaState_kk"][8:]
    # The archive stores shear as xy,yz,xz.
    xy,yz,xz=arrays["SigmaState_ij"][8:].T
    a=np.zeros_like(v)
    jgrad=np.column_stack([G@j for G in g.raw])
    qload=float(np.float32(10000*min(t/(2**-8),1)))
    fload=(2*qload/rho[:,None])*jgrad
    a+=fload-DAMP*v
    sigma=[[kk[:,0],xy,xz],[xy,kk[:,1],yz],[xz,yz,kk[:,2]]]
    for i in range(3):
        for d in range(3):
            field=sigma[i][d]
            a[:,i]+=(g.raw[d]@(j*field)+field*jgrad[:,d])/rho
    # Original compression-only AV. All pairs in fixed material support.
    cs=float(np.float32(35.80574408560461))
    W=g.W
    for start in range(0,g.n,512):
        end=min(start+512,g.n)
        rowptr=W.indptr[start:end+1]
        loc=slice(rowptr[0],rowptr[-1])
        i=np.repeat(np.arange(start,end),np.diff(rowptr))
        n=W.indices[loc]
        dx=g.x[i]-g.x[n]
        mu=np.minimum(0,np.einsum("ij,ij->i",v[i]-v[n],dx))*H/(np.einsum("ij,ij->i",dx,dx)+np.float32(.01*H**2))
        coeff=float(np.float32(.1))*cs*mu*j[n]*rho[n]/((rho[i]+rho[n])/2)
        for d in range(3):
            a[start:end,d]+=np.add.reduceat(g.raw[d].data[loc]*coeff,rowptr[:-1]-rowptr[0])

    def with_pressure(p):
        p=np.asarray(p,dtype=np.float64)
        return a-np.column_stack([(G@(j*p)+p*jgrad[:,d])/rho for d,G in enumerate(g.raw)])
    return with_pressure,dict(source_load_Pa=qload,load_ace_vs_actual_m_s2=error(fload-arrays["HydroMechLoadAce"][8:]))


def review_state(g,model,label,step):
    folder=T/"outputs"/label
    cols=["part","native_id","source_time_s","pn_Pa","previous_Pa","endpoint_q_actual_float_Pa","S_1_per_m_s",
          "Rgamma_Pa_per_m_s","raw_final_float_Pa","theta_endpoint_1_per_s","source_drained","endpoint_drained"]
    rounds=[]
    for r in (1,2,3):
        frame=pd.read_csv(folder/f"UplTpiP3GpuR1.round{r}.csv",usecols=cols,float_precision="round_trip")
        f=frame.loc[frame.part==1]
        assert np.array_equal(f.native_id,model.ids) and not f.source_drained.any() and not f.endpoint_drained.any()
        assert np.all(f.source_time_s==(step-1)*DT)
        rounds.append(f)
    arr,_=snapshot(folder/"data/Part_0001.bi4",1,step,DT)
    first=rounds[0]
    pn=first.pn_Pa.to_numpy();pm=first.previous_Pa.to_numpy()
    predictor=model.predict(pn,pm,False)
    assert np.array_equal(predictor,first.endpoint_q_actual_float_Pa.astype(np.float32))
    theta=first.theta_endpoint_1_per_s.to_numpy()
    acc,stats=original_forces(g,arr,(step-1)*DT)
    Strue=first.S_1_per_m_s.to_numpy()
    diagnostics=[]
    tic=perf_counter()
    actual_model_steps=list(model.rounds(pn,pm,theta,acc,lambda a:divergence(g,a),False))
    measured=perf_counter()-tic
    for i,f in enumerate(rounds):
        q=f.endpoint_q_actual_float_Pa.to_numpy(); true=f.raw_final_float_Pa.to_numpy(dtype=np.float32)
        obswrite=(q+f.Rgamma_Pa_per_m_s.to_numpy()/f.S_1_per_m_s.to_numpy()).astype(np.float32)
        assert np.array_equal(obswrite,true)
        if i: assert np.array_equal(q,rounds[i-1].raw_final_float_Pa.to_numpy())
        # Also drive each round with its actual stored pressure to distinguish
        # intra-round propagation from errors in geometry/force approximations.
        a=acc(q)
        p=model.sweep(q,theta,a,divergence(g,a),False)
        diagnostics.append(dict(round=i+1,recorded_update_bit_exact=True,
            driven_Pa=error(p.astype(float)-true),continuous_rounded_feedback_Pa=error(actual_model_steps[i].astype(float)-true),
            actual_q_step_Pa=error(true-q)))
    assert np.array_equal(rounds[-1].raw_final_float_Pa.to_numpy(dtype=np.float32),arr["PorePress"][8:])
    result=dict(archive=label,completed_step=step,source_time_s=(step-1)*DT,saved_time_s=step*DT,
        material_nodes=g.n,closed_surface_ids=int(model.fs.sum()),predictor_bit_exact=True,
        actual_final_native_bit_exact=True,step_endpoint_three_rounds_wall_s=measured,
        max_displacement_m=np.linalg.norm(arr["Posd"][8:]-g.x,axis=1).max(),
        S_relative_error=error(K*model.S0/Strue-1),rounds=diagnostics,**stats)
    return result


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    g=Graph()
    m=CryerSPHPressure.load(CACHE)
    res=[]
    for name,step in (("cryer_p3_gpu_debug2_r1",2),("cryer_p3_gpu_b64_r1",64)):
        row=review_state(g,m,name,step)
        print(name,row["rounds"],flush=True)
        res.append(row)
    z=np.zeros(g.n);va=np.zeros((g.n,3))
    q=np.full(g.n,10000,dtype=np.float32)
    closed=m.sweep(q,z,va,z,False)
    assert np.array_equal(closed,q)
    opened=[]
    for q in m.rounds(q,q,z,lambda q:va,lambda a:z,True):
        assert np.all(q[m.fs]==0)
        opened.append(dict(interior_min_Pa=float(q[~m.fs].min()),interior_max_Pa=float(q[~m.fs].max())))
    body=dict(shape=list(m.E.shape),nonzeros=int(m.E.nnz),S0_minmax_per_m2=[float(m.S0.min()),float(m.S0.max())],
              k_m_s=K,gamma_N_m3=RHOW*9.80665,constant10000_closed=True,
              open_pure_hydraulic_uniform_initial_zero_force_fixture=opened,
              archived_closed_state_replays=res,
              clock="2^-19 s. Linear q0 ramp at original n clock to 2^-8 s. Completed 4096 saved tD remains pre-open; source n=4096 onward is drained.",
              history="P3 cold pn/pm=0; predict pn+.5(pn-pm); three float pressure writes with fresh pressure force and div(a) each round; commit actual source pn only once.",
              scope="Fixed initial soil graph, uniform reference volumes in pressure rows; initial FS type/normal frozen. Replay uses saved endpoint stress, velocity, J, actual theta; forces recomputed on reference positions in double with AV and damping. Native CUDA updates positions, volumes, normals and uses mixed float accumulation. No coupled trajectory or server validation.")
    with OUT.open("x") as f:
        json.dump(body,f,indent=2,allow_nan=False)
    print(OUT,flush=True)


if __name__=="__main__":
    main()
