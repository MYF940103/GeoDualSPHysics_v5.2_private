"""Audit the unprojected hydraulic and skeletal force phases and actual M0 histories."""
from pathlib import Path
import csv
import io
import json
import sys

import numpy as np
from c08_m0_coupled_hold_r1 import OUT, PRE, TAG

T = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(T.parents[1]/"04_CryerProblem_PR/tests/support"))
from public_tpi_regression import read_with_history


def rows(text, prefix):
    return np.array([[float(v) for v in line.split()[1:]]
                     for line in text.splitlines() if line.startswith(prefix+" ")])


def main():
    check = T/"logs"/(TAG+".check.json")
    table = T/"figures"/(TAG+"_phases.csv")
    assert not check.exists()
    run = (OUT/"Run.out").read_text(errors="replace")
    call = json.loads((T/"logs"/(TAG+".call.json")).read_text())
    assert call["returncode"]==0 and "C08M0Hold import_exact all=7060 fixed=2060 source_order=by_id before_first_M0_force" in run
    assert "C08M0Hold imported_completed=2000000" in run and "right_wall=retained history=cold_actual_p" in run
    r, dt, rounds = [rows(run, prefix) for prefix in ("C08M0HoldR", "C08M0Dt", "C08M0Round")]
    assert r.shape==(1000,12) and dt.shape==(1000,8) and rounds.shape==(600,9)
    steps = np.arange(2000001,2000201)
    for array, phases in ((r,5),(dt,5),(rounds,3)):
        assert np.isfinite(array).all() and np.array_equal(array[:,0],np.repeat(steps,phases))
    assert np.array_equal(r[:,1],np.tile([0,0,1,1,1],200))
    assert np.array_equal(dt[:,1],np.tile([0,1,0,0,0],200))
    assert np.array_equal(rounds[:,1],np.tile([1,2,3],200))
    assert (r[:,2]==4900).all() and (r[:,10:]>0).all() and (r[:,11]>=r[:,10]).all()
    assert (dt[:,2]==5e-6).all() and (dt[:,2]<=dt[:,3]).all()
    assert (rounds[:,2]==0).all() and (rounds[:,3]==5000).all() and (rounds[:,4]==0).all()
    assert (rounds[:,5]==100).all() and np.array_equal(rounds[:,7],np.where(rounds[:,1]==3,rounds[:,6],0))
    assert np.array_equal(rounds[:,8],(rounds[:,1]==3)&(rounds[:,0]%40==0))
    _, source_meta, source_arrays, old_history = read_with_history(PRE)
    assert old_history is None and len(source_arrays)==22
    prev_step=source_meta["Step"]+1
    t=source_meta["TimeStep"]
    prev_p=source_arrays["PorePress"][np.argsort(source_arrays["Idp"])][2060:]
    fixed_p0=source_arrays["PorePress0"][np.argsort(source_arrays["Idp"])]
    ledger=[];saved=[]
    for part in sorted((OUT/"data").glob("Part_????.bi4")):
        _, meta, a, child=read_with_history(part)
        assert set(a)==set(source_arrays) and len(a["Idp"])==7060 and meta["Nout"]==0 and meta["dterror"]<=1e-14
        step=meta["Step"]+1
        h=child["values"]
        assert step>prev_step and h["CompletedUpdates"]==step and h["Scheme"]=="P3_B_alpha_half_beta_zero"
        assert h["Valid"]==1 and h["Dt"]==5e-6
        q=t
        for _ in range(step-prev_step):
            q=t
            t+=5e-6
        assert meta["TimeStep"]==h["SavedTime"]==t and h["PreviousTime"]==q
        order=np.argsort(a["Idp"])
        assert fixed_p0.tobytes()==a["PorePress0"][order].tobytes()
        ai=child["arrays"]
        hp=ai["PorePressPrev"][np.argsort(ai["Idp"])]
        assert np.array_equal(np.sort(ai["Idp"]),np.arange(2060,7060))
        if prev_step+1==step:
            assert hp.tobytes()==prev_p.tobytes()
            ledger.append(step)
        prev_p=a["PorePress"][order][2060:];prev_step=step
        saved.append(step)
    assert saved[:2]==steps[:2].tolist() and saved[-1]==steps[-1] and ledger[0]==steps[0]
    header=["completed","phase","nonFS","a_gravity_rms_m_s2","a_gravity_max_m_s2","interior_R_rms_Pa_m_s",
            "interior_R_max_Pa_m_s","interior_R_over_S_rms_Pa","interior_R_over_S_max_Pa","abs_variable_k_chain_max",
            "k_min_m_s","k_max_m_s","allowed_dt_s","positive_variable_k_speed_m_s"]
    phases=["n","h","endpoint1","endpoint2","endpoint3"]
    with io.StringIO(newline="") as fo:
        writer=csv.writer(fo);writer.writerow(header)
        for i,x in enumerate(r):
            writer.writerow([int(x[0]),phases[i%5],int(x[2]),*x[3:],dt[i,3],dt[i,7]])
        encoded=fo.getvalue().encode()
    if table.exists():
        assert table.read_bytes()==encoded
    else:
        table.write_bytes(encoded)
    data=dict(imported_ids=7060,soil=5000,retained_fixed=2060,completed=200,source_time=source_meta["TimeStep"],
       end=t,dt_s=5e-6,native_parts=len(saved),saved_completed=saved,actual_adjacent_history_checked_at=ledger,
       pressure_rounds=600,structural_Hydraulic_dt_checks=1000,min_allowed_dt_s=float(dt[:,3].min()),
       shepard_calls=int(rounds[:,8].sum()),negative_source_total=int(rounds[:,4].sum()),
       nonFS=4900,phases=phases,metric_order=header[3:12],
       first_n=r[0,3:].tolist(),last_n=r[-5,3:].tolist(),last_endpoint_before_third_update=r[-1,3:].tolist(),
       max_each_phase=[r[p::5,3:].max(axis=0).tolist() for p in range(5)],
       scope="One closed 1 ms change of pressure equation with cold pprev=p. No release or negative active material.")
    check.write_text(json.dumps(data,indent=2,default=lambda v: v.item()))
    print(check)


if __name__=="__main__":
    main()
