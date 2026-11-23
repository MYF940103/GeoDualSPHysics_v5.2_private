"""Check each native state and the actual material-point beta switch after a real C08 release."""
import csv
import io
import json

import numpy as np
from c08_m0_coupled_deformed_r1 import released,T,TAG,PART


def rms(values):
    return float(np.sqrt(np.mean(np.asarray(values,dtype=float)**2)))


def per_id(arrays):
    order=np.argsort(arrays["Idp"])
    return {name:value[order] for name,value in arrays.items()}


def main():
    out=T/"logs"/(TAG+".check.json")
    table=T/"figures"/(TAG+"_pairs.csv")
    assert not table.exists() and not out.exists()
    sm,raw,empty=released(PART)
    assert not empty
    src=per_id(raw);states={"b0":[src],"b004":[src]};gate={}
    s=slice(1805,None)
    neg=src["PorePress"][s]<0.
    assert neg.sum()==1125 and sm["Step"]+1==2076001
    steps=np.arange(2076002,2076010)
    for label,beta in (("b0",0.),("b004",.04)):
        name=TAG+"_"+label;folder=T/"outputs"/name
        assert json.loads((T/"logs"/(name+".call.json")).read_text())["returncode"]==0
        run=(folder/"Run.out").read_text(errors="replace")
        assert "import_exact=6805 fixed=1805 soil=5000" in run
        rows=lambda p:np.array([[float(w) for w in line.split()[1:]] for line in run.splitlines() if line.startswith(p+" ")])
        rounds,dt=rows("C08M0Round"),rows("C08M0Dt")
        assert rounds.shape==(24,9) and dt.shape==(40,8)
        assert np.array_equal(rounds[:,0],np.repeat(steps,3)) and np.array_equal(dt[:,0],np.repeat(steps,5))
        assert np.array_equal(rounds[:,1],np.tile([1,2,3],8)) and np.array_equal(dt[:,1],np.tile([0,1,0,0,0],8))
        assert (rounds[:,2]==beta).all() and (rounds[:,3]==5000).all() and (rounds[:,8]==0).all()
        assert np.array_equal(rounds[:,7],np.where(rounds[:,1]==3,rounds[:,6],0))
        assert (dt[:,2]==5e-6).all() and (dt[:,3]>=dt[:,2]).all()
        time=sm["TimeStep"];maxJ=0.;maxk=0.;frames=sorted((folder/"data").glob("Part_????.bi4"))
        assert len(frames)==8
        for i,path in enumerate(frames):
            meta,arrays,hh=released(path,True)
            h,=hh;a=per_id(arrays);prev=states[label][-1]
            assert meta["Step"]+1==steps[i] and meta["dterror"]<=1e-14
            assert h["values"]["Scheme"]==("P3_B_alpha_half_beta_0p04" if beta else "P3_B_alpha_half_beta_zero")
            assert h["values"]["CompletedUpdates"]==steps[i] and h["values"]["PreviousTime"]==time
            time+=5e-6
            assert time==h["values"]["SavedTime"]==meta["TimeStep"] and h["values"]["Valid"]==1
            assert np.array_equal(h["arrays"]["Idp"],np.arange(2060,7060))
            assert h["arrays"]["PorePressPrev"].tobytes()==prev["PorePress"][s].tobytes()
            negatives=int(np.count_nonzero(prev["PorePress"][s]<0))
            assert np.all(rounds[3*i:3*i+3,4]==negatives)
            assert a["PorePress0"].tobytes()==src["PorePress0"].tobytes()
            assert a["Posd"][:1805].tobytes()==src["Posd"][:1805].tobytes()
            assert (a["Kplastic"][s]>=prev["Kplastic"][s]).all()
            p=a["PorePress"][s];fs=np.isin(a["FSType"][s],[2,3])
            assert np.all(p[fs]<=0) and fs.sum()==rounds[i*3+2,5]
            J=a["PoroVolumeRatio"][s];por=a["PoroPorosity"][s]
            n0=float(np.float32(.35));k0=float(np.float32(.0002))
            ej=float(np.max(np.abs(por-(1-(1-n0)/J))));ek=float(np.max(np.abs(a["PoroHydraulicConductivity"][s]-k0*np.exp((J-1)/(2*(1-n0))))))
            assert ej<1e-14 and ek<1e-14 and np.all(J>0)
            maxJ=max(maxJ,ej);maxk=max(maxk,ek);states[label].append(a)
        gate[label]={"pressure_rounds":24,"dt_checks":40,"min_allowed_dt_s":float(dt[:,3].min()),
           "negative_sources_by_update":rounds[::3,4].astype(int).tolist(),"native_history_rows":40000,
           "n_ledger_max":maxJ,"k_ledger_max_m_s":maxk,"end":time}
    results=[]
    for i in range(1,9):
        a,b=states["b0"][i],states["b004"][i]
        p=a["PorePress"][s].astype(float);q=b["PorePress"][s].astype(float);q0=src["PorePress"][s].astype(float)
        dv=b["Vel"][s].astype(float)-a["Vel"][s]
        row=dict(update=i,completed=int(steps[i-1]),beta0_p_min_Pa=float(p.min()),beta004_p_min_Pa=float(q.min()),
           beta0_neg_count=int(np.sum(p<0)),beta004_neg_count=int(np.sum(q<0)),
           p_pair_rms_Pa=rms(q-p),p_pair_absmax_Pa=float(np.abs(q-p).max()),p_pair_initial_neg_rms_Pa=rms((q-p)[neg]),
           p_pair_initial_nonneg_rms_Pa=rms((q-p)[~neg]),beta0_initial_neg_delta_rms_Pa=rms((p-q0)[neg]),
           beta004_initial_neg_delta_rms_Pa=rms((q-q0)[neg]),beta0_pressure_change_rms_Pa=rms(p-q0),
           beta004_pressure_change_rms_Pa=rms(q-q0),v_pair_vec_rms_m_s=rms(np.linalg.norm(dv,axis=1)),
           position_pair_max_mm=float(1e3*np.linalg.norm(b["Posd"][s]-a["Posd"][s],axis=1).max()),
           kappa_pair_max=float(np.max(np.abs(b["Kplastic"][s].astype(float)-a["Kplastic"][s].astype(float)))))
        results.append(row)
    with table.open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    out.write_text(json.dumps(dict(source=str(PART),source_time_s=sm["TimeStep"],source_psi_deg=0,source_initial_negative=1125,
        scope="Finite-Kw deformed GPU snapshot switched to M0; source prehistory cold; private CPU8-step distinct trajectories.",
        branch_gate=gate,steps=results),indent=2))
    print(out);print(json.dumps(results[-1]))


if __name__=="__main__":
    main()
