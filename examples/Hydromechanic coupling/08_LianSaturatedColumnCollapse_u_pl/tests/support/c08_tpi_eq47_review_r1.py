"""Review the two fixed C08 states. Each new pressure guess had a fresh force evaluation."""
import csv
from decimal import Decimal, localcontext
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

T = Path(__file__).resolve().parents[1]
TAG = "c08_tpi_eq47_rounds_r1"
DT = 5e-6


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def bits_equal(a, b, dtype):
    return np.asarray(a,dtype=dtype).tobytes() == np.asarray(b,dtype=dtype).tobytes()


def table(path, rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    run=json.loads((T/"logs"/(TAG+".run.json")).read_text(encoding="utf-8-sig"))
    dest=T/"figures"/TAG
    paths=[Path(str(dest)+s) for s in (".csv","_pairs.csv",".png")]
    receipt=T/"logs"/(TAG+".check.json")
    if any(p.exists() for p in [*paths,receipt]):
        raise FileExistsError("Existing review products")
    source=Path(run["rows"]["path"])
    assert run["passed"] and source.stat().st_size==run["rows"]["bytes"] and source.stat().st_mtime_ns==run["rows"]["mtime_ns"]
    data=pd.read_csv(source,float_precision="round_trip")
    assert len(data)==80000 and np.isfinite(data.to_numpy()).all()
    old=pd.read_csv(T/"outputs/c08_tpi_state_r1/soil.csv",float_precision="round_trip")
    old=old[old.leg=="baseline"].set_index(["part","native_id"]).sort_index()
    clocks=pd.read_csv(T/"outputs/c08_h18_as03n255_full3_r1/native_r1/clocks.csv",float_precision="round_trip").set_index("part")
    scores=[];pairs=[];nexact=0;checked=0
    for (part,beta),body in data.groupby(["part","beta"]):
        assert len(body)==20000 and part in (38,76) and beta in (0.,.04)
        control=old.loc[part]
        ids=np.arange(2060,7060);assert np.array_equal(ids,control.index)
        pos=control[["x_m","y_m","z_m"]].to_numpy()
        for phase in range(4):
            g=body[body["pass"]==phase].set_index("id").sort_index()
            assert np.array_equal(g.index,ids) and np.all(g.time_s==control.time_s)
            pn=g.pn.to_numpy();q=g.q.to_numpy();S=g.S.to_numpy();R=g.R.to_numpy()
            raw=g.q_next.to_numpy();fs=np.isin(g.fs,[2,3]);neg=pn<0
            acc=g[["ax","ay","az"]].to_numpy()
            assert bits_equal(pn,control.p_actual_Pa,"<f4") and np.all(S>0) and np.array_equal(g.fs,control.FS)
            if phase==0:
                assert bits_equal(q,pn,"<f4") and bits_equal(R,control.Rgamma_Pa_per_m_s,"<f8")
                assert bits_equal(S,control.S_LP_1_per_m_s,"<f8")
                assert bits_equal(acc,control[["Acex","Acey","Acez"]],"<f4")
                if beta==0.:
                    assert bits_equal(raw,control.p_conditional_raw_Pa,"<f4")
            else:
                assert bits_equal(q, np.where(fs&(last>0),0.,last) if phase==3 else last,"<f4")
            caps=int(np.sum(fs&(last>0))) if phase==3 else 0
            if phase<3:
                # Independent high-precision numerator, including the unrounded beta/dt.
                reference=[]
                d=Decimal.from_float
                with localcontext() as ctx:
                    ctx.prec=90
                    cap=d(float(beta))/d(DT)
                    for n,v,s,r in zip(pn,q,S,R):
                        c=cap if n<0 else Decimal(0)
                        reference.append(float((d(s)*d(v)+d(r)+c*d(n))/(d(s)+c)))
                expected=np.array(reference,dtype="<f4")
                actual=np.asarray(raw,dtype="<f4")
                assert bits_equal(actual,expected,"<f4")
                nexact+=len(raw)
            else:
                assert bits_equal(raw,q,"<f4")
            checked+=len(q)
            capacity=np.where(neg,beta/DT,0.)
            # R alone is the unregularized physical row; this is the defect of the modified equation.
            reg_residual=R+capacity*(pn-q)
            assert bits_equal(g.time_s.iloc[0],clocks.loc[part,"time_s"],"<f8")
            scores.append(dict(part=int(part),tau_s=float(clocks.loc[part,"tau_from_actual_release_s"]),actual_time_s=float(g.time_s.iloc[0]),
                beta=float(beta),evaluated_after_defects=phase,negative_old=int(neg.sum()),
                raw_residual_rms=rms(R),modified_residual_rms=rms(reg_residual),
                negative_pressure_change_rms_Pa=rms((q-pn)[neg]),all_pressure_change_rms_Pa=rms(q-pn),
                negative_pressure_change_max_abs_Pa=float(np.abs((q-pn)[neg]).max()),
                positive_old_change_rms_Pa=rms((q-pn)[~neg]),negative_pressure_min_Pa=float(q.min()),
                positive_FS_caps=caps,FS_positive_trial=int((fs&(q>0)).sum()),
                acceleration_change_rms_vector_m_s2=float(np.sqrt(np.mean(np.sum((acc-control[["Acex","Acey","Acez"]].to_numpy())**2,axis=1))))))
            for id1,id2 in [(4953,4954),(6767,6865)]:
                i,j=id1-2060,id2-2060
                delta=pos[j]-pos[i];sep=float(np.linalg.norm(delta))
                axis=delta/sep
                pairs.append(dict(part=int(part),beta=float(beta),evaluated_after_defects=phase,
                    id_i=id1,id_j=id2,distance_m=sep,
                    radial_relative_acceleration_m_s2=float((acc[j]-acc[i])@axis),
                    p_i_Pa=float(q[i]),p_j_Pa=float(q[j])))
            last=raw
    assert nexact==60000 and checked==80000
    table(paths[0],scores);table(paths[1],pairs)
    fig,axes=plt.subplots(2,3,figsize=(11,6.2),sharex=True)
    df=pd.DataFrame(scores)
    for panel,part in zip(axes,(38,76)):
        subset=df[df.part==part]
        for ax,field,ylabel in zip(panel,["negative_pressure_change_rms_Pa","raw_residual_rms","acceleration_change_rms_vector_m_s2"],
            ["Old-negative pressure change\nRMS (Pa)","Spatial residual RMS\n(Pa / (m s))","Acceleration change\nvector RMS (m/s²)"]):
            for beta,group in subset.groupby("beta"):
                ax.plot(group.evaluated_after_defects,group[field],marker="o" if beta==0 else "s",ls="-" if beta==0 else "--",label=f"β = {beta:g}")
            ax.set(ylabel=ylabel,xticks=range(4));ax.grid(alpha=.24)
        panel[0].set_title(f"Release +{subset.tau_s.iloc[0]:.6f} s",loc="left")
    axes[0,2].legend()
    for ax in axes[-1]: ax.set_xlabel("Pressure corrections applied")
    fig.suptitle("C08 • Three pressure corrections on two fixed material configurations")
    fig.tight_layout()
    fig.savefig(paths[2],dpi=170);plt.close(fig)
    with receipt.open("x",encoding="utf-8") as f:
        json.dump(dict(passed=True,source=run["rows"],frames=[38,76],soil_per_frame=5000,force_calls=16,
            frozen_force_rows=checked,decimal_float32_matches=nexact,results=scores,
            csv=[str(p.relative_to(T)) for p in paths[:2]],png=str(paths[2].relative_to(T)),
            history="cold pn=previous; compensated terms use fresh q from each defect",
            physical_steps=0,physical_acceptance=False),f,indent=2,allow_nan=False)


if __name__=="__main__":
    main()
