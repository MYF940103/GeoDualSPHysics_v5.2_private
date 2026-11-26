"""Read C08TpiRow1 captures and independently reconstruct the actual three endpoint rounds."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from c08_psi25_tpi_native import TESTS, RELEASE_IDS, require

STEPS = (2060200, 2176200, 2240200)
TARGETS = (6868, 6918, 6919, 6920, 7010)
OPEN = 2000200
OUT = TESTS/"figures/c08_positive_actual_rows"
FIELDS = [
    ("id", "u4", 1), ("posxy", "f8", 2), ("posz", "f8", 1), ("code", "typecode", 1),
    ("fs", "u4", 1), ("C", "f8", 9), ("J", "f8", 1), ("p", "f4", 1),
    ("ace", "f4", 3), ("normal", "f4", 3), ("mode", "u1", 1), ("theta", "f8", 1),
    ("rate", "f4", 1), ("source", "f4", 1), ("previous", "f4", 1), ("next", "f4", 1),
]


def read_capture(path, step, rnd):
    a = {}
    with path.open("rb") as f:
        m = json.loads(f.readline(8192))
        n, b = m["np"], m["npb"]
        require(m["schema"]=="C08TpiRow1" and m["step"]==step and m["round"]==rnd and
                (n,b,m["first_soil_id"])==(6805,1805,2060), "Snapshot owner or step mismatch")
        for key,typ,width in FIELDS:
            name, dt, raw_count, components = f.readline(256).decode("ascii").split()
            count = int(raw_count)
            expected = b if key=="mode" else (n-b if key in ("theta","rate","source","previous","next") else n)
            require(name==key and ((dt in ("u2","u4")) if typ=="typecode" else dt==typ)
                    and int(components)==width and count==expected, "Unexpected array "+key)
            dtype = np.dtype("<"+dt)
            raw = f.read(count*width*dtype.itemsize)
            require(len(raw)==count*width*dtype.itemsize, "Truncated array "+key)
            v = np.frombuffer(raw,dtype=dtype)
            a[key] = v if width==1 else v.reshape(count,width)
        require(f.read()==b"END\n","Missing end marker or extra bytes")
    require(np.array_equal(np.sort(a["id"][:b]),RELEASE_IDS[:b]) and
            np.array_equal(np.sort(a["id"][b:]),RELEASE_IDS[b:]),"Fixed/soil ID registry")
    mask = 0x1800 if a["code"].dtype.itemsize==2 else 0x30000
    special = 0xe000 if a["code"].dtype.itemsize==2 else 0xe0000000
    require(not np.any(a["code"]&special) and not np.any(a["code"][:b]&mask)
            and np.all((a["code"][b:]&mask)==mask),"Ghost, non-soil, or non-fixed particle")
    require((m["dt_s"],m["rhow"],m["kw"],m["Ck"])==(5e-6,1000.,1e9,2.)
            and m["gamma"]==m["rhow"]*9.80665 and m["solid0"]==1.-float(np.float32(.35))
            and m["k0"]==float(np.float32(.0002)) and m["h"]==float(np.float32(.072))
            and m["vol0"]==float(np.float32(3.316))/2072.5, "Unexpected C08 material/constants")
    return m,a


def predict(pn, prev, iterate, S, R, dt):
    require(np.isfinite(S) and S>0,"Invalid diagonal")
    beta = .04/dt if pn<0 else 0.
    alpha = pn+.5*(pn-prev)
    written = iterate+(R+beta*(alpha-iterate))/(S+beta)
    return alpha,beta,written,np.float32(written)


def factor(rr2, h):
    # Replicate the native GetKernelWendland_Fac(float rr2) operation order.
    rad = np.sqrt(rr2.astype("f4"))
    q = rad/np.float32(h)
    v = np.float32(1)-np.float32(.5)*q
    b = np.float32(-2.7852/(h*h*h))
    fac = (b*q*v*v*v/rad).astype(float)
    # CUDA -use_fast_math uses approximate float sqrt and reciprocal division.
    # Absolute envelope near the kernel cutoff (a relative bound on (1-q/2)^3 breaks down).
    eps = np.finfo("f4").eps
    abs_v = abs(v.astype(float))
    dv = 4*eps*q.astype(float) + eps*abs_v
    df = abs(float(b))/h * ((abs_v+dv)**3*(1+16*eps) - abs_v**3)
    return fac,df


def reconstruct(m,a,i):
    b = m["npb"]
    pts = np.column_stack((a["posxy"][:,0], a["posz"]))
    d0 = pts[i]-pts
    r20 = np.sum(d0*d0,axis=1)
    eligible = (r20<=m["kernel_size2"]) & (r20>=np.float32(1e-18))
    # Soil first, fixed second, as in the CUDA group loop. Within each group
    # the sum order can differ from cell search, so double sums have roundoff.
    js = np.r_[np.flatnonzero(eligible[b:])+b,np.flatnonzero(eligible[:b])]
    bed = js<b
    require(len(js)>0 and np.all(a["mode"][js[bed]]==1), "Inactive/unexpected wall in stencil")
    d = d0[js]
    rr2 = r20[js]
    h=m["h"]
    fac,df=factor(rr2,h)
    C=a["C"].reshape(-1,3,3)
    spatial=(0,2)
    ci=C[i][np.ix_(spatial,spatial)]
    cj=C[js][:,spatial][:,:,spatial]
    Gi=d@ci.T
    Gj=np.einsum("ijk,ik->ij",cj,d)
    v=m["vol0"]*a["J"][js]
    dp=float(a["p"][i])-a["p"][js].astype(float)
    dJ=a["J"][js]-a["J"][i]
    ai=a["ace"][i,spatial].astype(float)
    da=a["ace"][js][:,spatial].astype(float)-ai
    weight0=v*np.sum(d*(Gi+Gj),axis=1)/(rr2+m["eta2"])
    weight=weight0*fac
    vg0=v[:,None]*Gi
    vg=vg0*fac[:,None]
    lp=weight*dp
    lx=d*weight[:,None]
    gp=-vg*dp[:,None]
    gradJ=vg*dJ[:,None]
    div_a=np.sum(vg*da,axis=1)
    big_lx=lx.sum(axis=0)
    big_gp=gp.sum(axis=0)
    big_gradJ=gradJ.sum(axis=0)
    J=float(a["J"][i])
    n=1-m["solid0"]/J
    k=m["k0"]*np.exp((J-1)/(m["solid0"]*m["Ck"]))
    dk=k/(m["solid0"]*m["Ck"])
    rho=m["rhow"]
    sf=a["fs"][i] in (2,3)
    S=-k*weight.sum()
    theta=float(a["theta"][i-b])
    volumetric=-m["gamma"]*theta
    # Attribute the pressure Taylor and grad-k/p products to each gp donor
    # while holding the full lx and gradJ. Attribute the accel-chain by gradJ donor.
    pieces={
        "pressure_lap":k*lp,
        "pressure_taylor":np.zeros_like(lp) if sf else -k*(gp@big_lx),
        "acc_div":k*rho*div_a,
        "acc_fs":k*rho*(lx@ai) if sf else np.zeros_like(lp),
        "chain_p":dk*(gp@big_gradJ),
        "chain_acc":dk*rho*(gradJ@ai),
    }
    group={f"{key}_{location}":float(terms[mask].sum()) for key,terms in pieces.items()
           for location,mask in (("soil",~bed),("wall",bed))}
    pressure=float((pieces["pressure_lap"]+pieces["pressure_taylor"]).sum())
    acceleration=float((pieces["acc_div"]+pieces["acc_fs"]).sum())
    chain_p=float(pieces["chain_p"].sum())
    chain_a=float(pieces["chain_acc"].sum())
    R=volumetric+pressure+acceleration+chain_p+chain_a
    direct_lap=lp.sum()+rho*div_a.sum()+(rho*np.dot(ai,big_lx) if sf else -np.dot(big_gp,big_lx))
    independent=volumetric+k*direct_lap+dk*np.dot(big_gradJ,big_gp+rho*ai)
    direct_mag=abs(volumetric)+sum(np.abs(ts).sum() for ts in pieces.values())
    require(abs(R-independent)<=128*np.finfo(float).eps*(direct_mag+1.),"Group decomposition mismatch")
    # Propagate the single-precision gradient factor uncertainty through linear
    # sums and the two bilinear products on the SAME state. No physical fit tolerance.
    e_w=abs(weight0)*df
    e_gp=(abs(vg0)*abs(dp[:,None])*df[:,None]).sum(axis=0)
    e_j=(abs(vg0)*abs(dJ[:,None])*df[:,None]).sum(axis=0)
    e_lx=(abs(d)*e_w[:,None]).sum(axis=0)
    e_lp=abs(dp)@e_w
    e_da=np.sum(abs(vg0*da)*df[:,None])
    e_bilinear=(rho*abs(ai)@e_lx if sf else
                abs(big_gp)@e_lx + abs(big_lx)@e_gp + e_gp@e_lx)
    e_chain=e_j@(abs(big_gp)+rho*abs(ai))+abs(big_gradJ)@e_gp+e_j@e_gp
    err_R=k*(e_lp+rho*e_da+e_bilinear)+dk*e_chain+128*len(js)*np.finfo(float).eps*(1+direct_mag)
    rate=float(a["rate"][i-b])
    r_rate=rate*n*m["gamma"]/m["kw"]
    rounded_rate=np.float32(m["kw"]*R/(n*m["gamma"]))
    from_f32=abs(float(np.spacing(np.float32(rate))))*.5*n*m["gamma"]/m["kw"]
    residual_error=abs(r_rate-R)
    idx=int(a["id"][i])-m["first_soil_id"]
    pn,prev,q,observed=map(float,(a["source"][idx],a["previous"][idx],a["p"][i],a["next"][idx]))
    alpha,beta,unrounded,pred=predict(pn,prev,q,S,R,m["dt_s"])
    denominator=S+beta
    delta=dict(delta_vol_Pa=volumetric/denominator,delta_pressure_Pa=pressure/denominator,
               delta_acceleration_Pa=acceleration/denominator,delta_chain_pressure_Pa=chain_p/denominator,
               delta_chain_acceleration_Pa=chain_a/denominator,delta_history_Pa=(beta/denominator)*(alpha-q))
    require(abs(q+sum(delta.values())-unrounded)<=64*np.finfo(float).eps*
            (1.+abs(q)+sum(map(abs,delta.values()))), "Pressure-increment decomposition")
    require(residual_error <= err_R+from_f32, f"Rate/residual failed: step {m['step']} r{m['round']} "
            f"ID {a['id'][i]} error {residual_error:g} > {err_R+from_f32:g} Pa/(m s)")
    require(pred.tobytes()==np.float32(observed).tobytes(), f"Raw next float differs: step {m['step']} "
            f"r{m['round']} ID {a['id'][i]} observed {observed:g}, rebuilt {pred!r} ({float(pred)-observed:g} Pa)")
    return dict(step=m["step"],round=m["round"],time_start_s=m["time_start_s"],
                nominal_release_s=(m["step"]-OPEN)*m["dt_s"],id=int(a["id"][i]),fs=int(a["fs"][i]),
                soil_donors=int((~bed).sum()),fixed_donors=int(bed.sum()),n=n,k_m_s=k,theta_s_inv=theta,
                p_n_Pa=pn,p_prev_Pa=prev,iterate_Pa=q,predicted_history_Pa=alpha,
                next_native_Pa=observed,next_rebuilt_Pa=float(pred),next_rebuilt_before_f32_Pa=unrounded,
                beta_over_dt=beta,S_per_m_s=S,S_weight_envelope_per_m_s=k*e_w.sum(),
                R_vol=volumetric,R_pressure=pressure,R_acceleration=acceleration,R_chain_pressure=chain_p,
                R_chain_acceleration=chain_a,R_sum=R,R_from_float_rate=r_rate,R_abs_difference=residual_error,
                R_roundoff_envelope=err_R+from_f32,rate_native_Pa_s=rate,rate_rebuilt_f32_Pa_s=float(rounded_rate),
                fixed_R_sum=sum(g for key,g in group.items() if key.endswith("_wall")),
                native_round_change_Pa=observed-q,float_write_change_Pa=observed-unrounded,**delta,**group)


def fixtures():
    # Activation is by committed p_n, irrespective of the sign of the trial iterate.
    require(predict(0.,-1.,-10.,2.,4.,5e-6)[3]==np.float32(-8.),
            "p_n=0 must take the unregularized row")
    expected=(2.*1.+.5+8000.*(-4.5))/(2.+8000.)
    require(predict(-4.,-3.,1.,2.,.5,5e-6)[3]==np.float32(expected),
            "Negative history must be retained for a positive pressure iterate")
    # Four equal-radius donors about the centre, one is a fixed bed particle.
    # C=I and V0 normalize the first moment. Independent prescribed-gradient results.
    h=float(np.float32(.072))
    r=.04
    fac=float(factor(np.array([r*r]),h)[0][0])
    vol0=1/(-2*fac*r*r)
    m=dict(npb=1,first_soil_id=10,step=1,round=1,dt_s=5e-6,time_start_s=0.,h=h,
           kernel_size2=(2*h)**2,eta2=(.1*h)**2,vol0=vol0,solid0=.65,rhow=1000.,
           kw=1e9,gamma=9806.65,k0=.0002,Ck=2.)
    x=np.array([0.,0.,r,-r,0.])
    z=np.array([-r,0.,0.,0.,r])
    i=1
    a=dict(id=np.array([0,10,11,12,13]),posxy=np.column_stack((x,np.zeros(5))),posz=z,
           C=np.tile(np.eye(3).ravel(),(5,1)),mode=np.ones(1),theta=np.zeros(4),rate=np.zeros(4,"f4"),
           fs=np.zeros(5),previous=np.zeros(4,"f4"),next=np.zeros(4,"f4"))
    wbase=vol0*(2*fac*r*r)/(r*r+m["eta2"])
    for variable,force_gradient,fs,base in [(False,0.,0,2000.),(False,2.,0,-2000.),
                                             (True,0.,0,-2000.),(True,0.,2,-2000.)]:
        a["J"]=1.+(x if variable else 0.*x)
        a["fs"][i]=fs
        a["p"]=np.full(5,base,"f4")
        a["source"]=np.full(4,base,"f4")
        a["previous"][:]=base-10.
        a["ace"]=np.column_stack((3.+force_gradient*x,np.zeros(5),4.+force_gradient*z)).astype("f4")
        # Use actual stored floats for the manufactured linear acceleration gradient.
        trace_a=(float(a["ace"][2,0])-float(a["ace"][3,0]) +
                 float(a["ace"][4,2])-float(a["ace"][0,2]))/(2*r)
        k=m["k0"]
        qdiv=k*m["rhow"]*trace_a
        gradk_acc=(k/(m["Ck"]*m["solid0"]))*3*m["rhow"] if variable else 0.
        fs_acc=k*m["rhow"]*3*(-2*r*r*wbase) if variable and fs else 0.
        expected_R=qdiv+gradk_acc+fs_acc
        S=-4*k*wbase
        a["rate"][i-1]=m["kw"]/(.35*m["gamma"])*expected_R
        expected_next=predict(base,base-10.,base,S,expected_R,m["dt_s"])[3]
        a["next"][i-1]=expected_next
        row=reconstruct(m,a,i)
        require(abs(row["R_acceleration"]-qdiv-fs_acc)<1e-9 and
                abs(row["R_chain_acceleration"]-gradk_acc)<1e-9 and
                abs(row["S_per_m_s"]-S)<1e-10 and
                abs(row["R_pressure"])+abs(row["R_chain_pressure"])<1e-12,
                "Manufactured acceleration/chain/free-surface terms")
    # Convex quadratic pressure in x, determinant and first moment well conditioned.
    a["J"]=np.ones(5)
    a["fs"][i]=0
    a["ace"][:]=0.
    a["p"]=np.asarray(2000.+5000*x*x,dtype="f4")
    a["source"][:]=2000.
    a["previous"][:]=2000.
    R=m["k0"]*(-2*wbase)*float(a["p"][2]-a["p"][i])
    a["rate"][0]=m["kw"]/(.35*m["gamma"])*R
    a["next"][0]=predict(2000.,2000.,2000.,S,R,m["dt_s"])[3]
    row=reconstruct(m,a,i)
    require(abs(row["R_sum"]-R)<1e-12 and row["R_pressure"]>0, "Quadratic pressure sign")


def probe_table(data, step_limit):
    path=data/"C08TpiRoundProbe.csv"
    with path.open(encoding="ascii",newline="") as f:
        groups={}
        for r in csv.DictReader(f):
            # During an in-progress read a later CSV row can be partially written.
            if step_limit is not None and int(r["step"])>step_limit:
                break
            key=(int(r["step"]),int(r["round"]),int(r["id"]))
            require(key not in groups and key[2] in TARGETS and key[1] in (1,2,3),
                    "Duplicate or invalid scalar observer owner")
            groups[key]={k:float(v) for k,v in r.items()}
    cap=step_limit if step_limit is not None else STEPS[-1]
    expected=[OPEN+d for d in sorted(set(range(1,9))|{70,139,140,141}|set(range(2000,240001,2000)))
              if OPEN+d<=cap]
    require(set(groups)=={(s,r,i) for s in expected for r in (1,2,3) for i in TARGETS},
            "Scalar schedule incomplete")
    previous_time=-np.inf
    for s in expected:
        time=groups[s,1,TARGETS[0]]["time_start_s"]
        require(time>previous_time, "Scalar clocks out of order")
        previous_time=time
        for ident in TARGETS:
            p1=groups[s,1,ident]
            for rnd in range(1,4):
                p=groups[s,rnd,ident]
                expected_post=min(p["next_Pa"],0.) if rnd==3 and p["fs_after"] in (2,3) else p["next_Pa"]
                require(p["dt_s"]==5e-6 and p["time_start_s"]==time and p["p_n_Pa"]==p1["p_n_Pa"]
                        and p["p_prev_Pa"]==p1["p_prev_Pa"] and p["post_Pa"]==expected_post
                        and p["beta_active"]==int(p1["p_n_Pa"]<0.), "Probe clock/history/projection")
                if rnd>1:
                    require(p["iterate_Pa"]==groups[s,rnd-1,ident]["post_Pa"],"Probe iteration link")
            if (s-1,3,ident) in groups:
                old=groups[s-1,3,ident]
                require(p1["p_n_Pa"]==old["post_Pa"] and p1["p_prev_Pa"]==old["p_n_Pa"],
                        "Consecutive committed pressure history link")
    return groups


def inspect(data,step,probes):
    rows=[]
    previous_source=previous_previous=previous_next=None
    for rnd in (1,2,3):
        header,a=read_capture(data/f"C08TpiRow_{step}_r{rnd}.bin",step,rnd)
        b=header["npb"]
        if previous_source is not None:
            require(np.array_equal(previous_source,a["source"]) and np.array_equal(previous_previous,a["previous"]),
                    "Old material histories changed between rounds")
            soil_id=a["id"][b:]-header["first_soil_id"]
            require(np.array_equal(previous_next[soil_id],a["p"][b:]),"Full soil iteration link")
        previous_source,previous_previous,previous_next=a["source"],a["previous"],a["next"]
        for ident in TARGETS:
            i,=np.flatnonzero(a["id"]==ident)
            row=reconstruct(header,a,int(i))
            scalar=probes[step,rnd,ident]
            require(all(row[u]==scalar[v] for u,v in [
                ("step","step"),("round","round"),("time_start_s","time_start_s"),("id","id"),
                ("fs","fs_before"),("theta_s_inv","theta_s_inv"),("p_n_Pa","p_n_Pa"),
                ("p_prev_Pa","p_prev_Pa"),("iterate_Pa","iterate_Pa"),("next_native_Pa","next_Pa"),
                ("rate_native_Pa_s","rate_Pa_s")]), "Snapshot and scalar probe differ")
            row["post_projection_Pa"]=scalar["post_Pa"]
            rows.append(row)
    return rows


def write_report(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    csv_path,fig_path=OUT/"three_rounds.csv",OUT/"three_rounds.png"
    require(not csv_path.exists() and not fig_path.exists(), "Retained products exist")
    OUT.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,3,figsize=(12.7,6.4),constrained_layout=True)
    for col,step in enumerate(STEPS):
        window=[r for r in rows if r["step"]==step]
        last=[r for r in window if r["round"]==3]
        x=np.arange(len(last))
        for shift,(key,label) in enumerate((("R_vol","Volume strain"),("R_pressure","Pressure"),
                                            ("R_acceleration","Acceleration"),("chain","Variable k"))):
            values=[r[key] if key!="chain" else r["R_chain_pressure"]+r["R_chain_acceleration"] for r in last]
            axes[0,col].bar(x+.16*(shift-1.5),values,.16,label=label)
        axes[0,col].scatter(x,[r["R_sum"] for r in last],marker="_",s=65,c="black",label="Net residual")
        axes[0,col].axhline(0,linewidth=.7,color="0.3")
        axes[0,col].set_xticks(x,[str(r["id"]) for r in last],fontsize=8)
        axes[0,col].set_title(f'{last[0]["nominal_release_s"]:.2f} s after release')
        for ident in TARGETS:
            rr=[r for r in window if r["id"]==ident]
            axes[1,col].plot(range(4),np.array([rr[0]["iterate_Pa"]]+[r["next_native_Pa"] for r in rr])/1000,
                             marker=".",label=str(ident))
        axes[1,col].set_xticks(range(4),["Input","1","2","3"])
        axes[1,col].grid(True,alpha=.18)
        axes[1,col].set_xlabel("Endpoint pressure iteration")
    axes[0,0].set_ylabel("Round 3 residual term [Pa/(m s)]")
    axes[1,0].set_ylabel("Pressure before surface projection [kPa]")
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc="outside upper center",ncol=5,fontsize=9)
    axes[1,0].legend(ncol=2,fontsize=7,title="Material ID",title_fontsize=7)
    fig.savefig(fig_path,dpi=175)
    plt.close(fig)
    with csv_path.open("x",encoding="utf8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0])
        w.writeheader()
        w.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--fixture",action="store_true")
    modes.add_argument("--inspect-step",type=int,choices=STEPS)
    modes.add_argument("--complete",action="store_true")
    parser.add_argument("--data",type=Path)
    opts=parser.parse_args()
    fixtures()
    if opts.fixture:
        print("Passed manufactured constant, linear acceleration, pressure curvature and variable-k/FS checks")
        return
    require(opts.data is not None and opts.data.is_dir(),"Provide the owned snapshot output directory")
    if opts.complete:
        with (opts.data/"Run.out").open("rb") as f:
            f.seek(max(0,(opts.data/"Run.out").stat().st_size-65536))
            require(b"Finished execution (code=0)" in f.read(),"Solver completion absent")
        with (opts.data/"Run.csv").open(newline="",encoding="utf8",errors="replace") as f:
            handle,=list(csv.DictReader(f,delimiter=";"))
        require((int(handle["Steps"]),int(handle["PartFiles"]),int(handle["PartsOut"]))==
                (STEPS[-1],133,0),"Actual terminal steps, PART count or exclusions differ")
    probes=probe_table(opts.data,opts.inspect_step)
    rows=[]
    for step in ((opts.inspect_step,) if opts.inspect_step else STEPS):
        rows.extend(inspect(opts.data,step,probes))
    print(f'{len(rows)} actual rows, max residual error {max(r["R_abs_difference"] for r in rows):.6g} Pa/(m s); '
          f'all {len(rows)} next-pressure binary32 values match')
    for r in rows:
        if r["id"]==6918:
            print(" ".join(f'{k}={r[k]:.8g}' for k in
                          ("step","round","R_vol","R_pressure","R_acceleration","R_chain_pressure",
                           "R_chain_acceleration","R_sum","next_native_Pa")))
    if opts.complete:
        write_report(rows)


if __name__=="__main__":
    main()
