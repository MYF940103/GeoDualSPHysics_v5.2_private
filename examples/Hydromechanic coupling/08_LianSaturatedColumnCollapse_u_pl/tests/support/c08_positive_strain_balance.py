"""Compare measured pore pressure, volume and DP smooth-flow dilatancy on fixed material points."""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from c08_psi25_tpi_native import TESTS, CASE, SOIL_IDS, OPEN, DT, read_frame, require
from c08_psi25_tpi_mobilization import invariant_fields, source_properties
from c08_psi25_tpi_native import native, PRE

OUT = TESTS / "figures/c08_positive_strain_balance"
IDS = np.array([6918, 6919, 6920, 6868, 7010])
GAMMA = 1000 * 9.80665  # Dynamic pore row in the bound JSphGpu.cpp, distinct from mechanical gravity.
BETA, ALPHA = .04, .5
BULK = 19607844.


def integrated_dilation(old, new):
    """Integral of 3 sqrt(3) b(psi(k)) dk on the smooth plane-strain cone."""
    points, weights = np.polynomial.legendre.leggauss(8)
    radius = (new - old) * .5
    middle = (new + old) * .5
    result = np.zeros_like(middle)
    for t, w in zip(points, weights):
        psi = float(np.float32(np.deg2rad(2.5))) * np.exp(-float(np.float32(.2)) * (middle + radius*t))
        tangent = np.tan(psi)
        result += w * 3*np.sqrt(3)*tangent / np.sqrt(9+12*tangent*tangent)
    return radius * result


def write_csv(name, rows):
    with (OUT/name).open("x", newline="", encoding="utf8") as f:
        out = csv.DictWriter(f, fieldnames=rows[0])
        out.writeheader()
        out.writerows(rows)


def run():
    rows, intervals = [], []
    props = source_properties(native(PRE)[0])
    ix = np.searchsorted(SOIL_IDS, IDS)
    require(np.array_equal(SOIL_IDS[ix], IDS), "Unexpected material IDs")
    for branch in ("b0", "b004"):
        tag = "c08_psi25_tpi_paper_"+branch+"_r1"
        receipt = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
        require(receipt["passed"] and receipt["frames"]==132, "Unreviewed input")
        sealed = {name:(n,t) for name,n,t in receipt["files"]}
        data = TESTS/"outputs"/tag/"data"
        times, states = [], []
        for part in range(4,133):
            f = data/f"Part_{part:04d}.bi4"
            st = f.stat()
            require(sealed[str(f.relative_to(CASE))]==(st.st_size,st.st_mtime_ns), "Input identity changed")
            m,a,hist,pminus = read_frame(f)
            step=m["Step"]+1
            require(hist["SavedTime"]==m["TimeStep"] and np.array_equal(a["Idp"][-5000:],SOIL_IDS), "History mismatch")
            a={key:v[-5000:][ix] for key,v in a.items()}
            p = a["PorePress"].astype(float)
            stress,q,capacity = invariant_fields(a,props)
            kappa = a["Kplastic"].astype(float)
            J = a["PoroVolumeRatio"]
            if part==4:
                require(step==OPEN, "Wrong closed state")
                Jopen, kopen, sopen = J.copy(), kappa.copy(), stress.copy()
            tau=m["TimeStep"]-receipt["release_time_s"]
            plastic=integrated_dilation(kopen,kappa)
            elastic=-(stress-sopen)/BULK
            for j,idp in enumerate(IDS):
                rows.append(dict(run=branch,part=part,step=step,tau_s=tau,id=int(idp),
                    p_kPa=p[j]/1000,previous_p_kPa=pminus[ix[j]]/1000,J=J[j],
                    log_volume_since_open=np.log(J[j]/Jopen[j]),smooth_plastic_volume=plastic[j],
                    elastic_volume=elastic[j],smooth_plus_elastic=plastic[j]+elastic[j],
                    kappa=kappa[j],p_eff_kPa=stress[j]/1000,q_kPa=q[j]/1000,
                    yield_margin_Pa=capacity[j]-q[j],fs=int(a["FSType"][j]),
                    theta_native=a["PoroThetaLastStage"][j],conductivity=a["PoroHydraulicConductivity"][j]))
            times.append(tau)
            states.append((p.copy(),pminus[ix].astype(float),J.copy(),kappa.copy(),stress.copy(),a["FSType"].copy()))
        if branch!="b004": continue
        for t0,t1 in ((.20,.30),(.30,.60),(.60,.88),(.88,1.20),(.20,.88)):
            i0,i1=(int(np.argmin(abs(np.asarray(times)-t))) for t in (t0,t1))
            require(abs(times[i0]-t0)<DT and abs(times[i1]-t1)<DT,"Unmatched clock")
            p0,prev0,j0,k0,s0,_=states[i0]
            p1,prev1,j1,k1,s1,_=states[i1]
            for j, idp in enumerate(IDS):
                observed = (p1[j]-p0[j])/1000
                logj=np.log(j1[j]/j0[j])
                correction=ALPHA*((p1[j]-prev1[j])-(p0[j]-prev0[j]))/1000
                # Exact sum of linear history increments if the beta branch was active on every step.
                # Intermediate 5-us switches and the third-iterate residual are not stored in these frames.
                pressure_integral=BETA*((1-ALPHA)*observed + correction)*1000
                source_integral=-GAMMA*logj
                intervals.append(dict(id=int(idp),start_tau=times[i0],end_tau=times[i1],
                    saved_frames=i1-i0+1,saved_interior_and_negative=sum(
                        s[0][j]<0 and s[1][j]<0 and s[5][j] not in (2,3) for s in states[i0:i1+1]),
                    delta_p_kPa=observed,log_volume=logj,smooth_plastic_volume=integrated_dilation(k0,k1)[j],
                    elastic_volume=-(s1[j]-s0[j])/BULK,
                    no_flow_dilation_reference_kPa=source_integral/(1000*BETA*(1-ALPHA))-correction/(1-ALPHA),
                    history_endpoint_term_kPa=correction,
                    history_integral_Pa_m=pressure_integral,volume_source_integral_Pa_m=source_integral,
                    remaining_integral_if_always_active_Pa_m=pressure_integral-source_integral))
    OUT.mkdir(exist_ok=False)
    write_csv("material.csv", rows)
    write_csv("intervals.csv", intervals)
    fig,axes=plt.subplots(1,3,figsize=(12.3,3.9),layout="constrained")
    for branch,label,color in (("b0","β = 0","#84786b"),("b004","β = 0.04","#216699")):
        v=[r for r in rows if r["run"]==branch and r["id"]==6918]
        x=[r["tau_s"] for r in v]
        axes[0].plot(x,[r["p_kPa"] for r in v],color=color,label=label)
        axes[1].plot(x,[100*r["log_volume_since_open"] for r in v],color=color,label=label)
        axes[1].plot(x,[100*r["smooth_plus_elastic"] for r in v],color=color,ls="--")
        axes[2].plot(x,[r["p_eff_kPa"] for r in v],color=color,label=label)
    for ax,title,unit in zip(axes,["Gauge pore pressure","Volume change from wall opening","Mean effective compression"],
                             ["Pressure (kPa)","Logarithmic volume strain (%)","Stress (kPa)"]):
        ax.set(title=title,xlabel="Time after wall removal (s)",ylabel=unit)
        ax.grid(alpha=.22)
    axes[0].legend()
    axes[1].plot([],[],color="k",label="From J")
    axes[1].plot([],[],color="k",ls="--",label="Smooth DP flow + elastic")
    axes[1].legend(handles=axes[1].get_lines()[-2:],fontsize=8)
    fig.suptitle("C08  ·  Positive pressure cap  ·  Material ID 6918")
    fig.savefig(OUT/"strain_pressure.png",dpi=175)
    plt.close(fig)


if __name__=="__main__":
    run()
