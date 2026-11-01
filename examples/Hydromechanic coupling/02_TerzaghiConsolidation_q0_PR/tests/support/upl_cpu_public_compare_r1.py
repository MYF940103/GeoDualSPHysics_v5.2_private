"""Offline public/private native audit and scientific PNG/CSV; never invokes a solver."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.linalg import expm

T = Path(__file__).resolve().parents[1]
ROOT = T.parents[3]
PREFIX = "upl_cpu_public_compare_r1"
COL = ["x","y","z","vx","vy","vz","p","p0","J","theta","sxx","sxy","sxz","syy","syz","szz",
       "kplastic","FSType","normal_x","normal_y","normal_z","PosDiv","load_ax","load_ay","load_az","legacy_rho"]
A, N0, RHO, RW, KW, KAPPA = 2.**-9, .25, 2048., 1000., 67108864., 2*np.pi/.125
M = 89478488. + 4*134217728./3.
CU = np.sqrt((M+KW/N0)/RHO)
PS, US, K0 = (KW/N0)*A/CU, A/(CU*KAPPA), float(np.float32(.0001))
TIMES = np.arange(257)*2.**-23
INPUTS = {}
def need(ok, message):
    if not ok: raise RuntimeError(message)
def entry(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""): h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())
def remember(path):
    e = entry(path); INPUTS[e["path"].casefold()] = e; return e
def records(value):
    if isinstance(value, dict):
        if all(k in value for k in ("path","bytes","sha256")): yield value
        for item in value.values(): yield from records(item)
    elif isinstance(value, list):
        for item in value: yield from records(item)
def admitted(relative):
    path = T/relative
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    need(data.get("passed"), "Required completed check not passed: "+str(path))
    remember(path); return data
def frozen(path, receipt):
    actual = entry(path)
    matched = [r for r in records(receipt) if str(Path(r["path"]).resolve()).casefold() == actual["path"].casefold()]
    need(matched and all(r["bytes"]==actual["bytes"] and r["sha256"].lower()==actual["sha256"] for r in matched),
         "No exact current binding in retained receipt: "+str(path))
    INPUTS[actual["path"].casefold()] = actual
def physical(path, native):
    need(np.fromfile(path, dtype="<u4", count=3).tolist()==[native,26,257], "Wrong full native26 schema")
    need(path.stat().st_size == 12+257*(1+native*26)*8, "Wrong full binary extent")
    raw = np.memmap(path, dtype="<f8", mode="r", offset=12, shape=(257,1+native*26))
    need(np.array_equal(raw[:,0], TIMES), "Actual matched clocks differ; interpolation prohibited")
    state = raw[:,1:].reshape(257,native,26)
    need(np.isfinite(state).all(), "Nonfinite native field")
    return state
def half_metrics(c, h):
    dp=c[:,:,6]-h[:,:,6];du=c[:,:,:3]-h[:,:,:3];dv=c[:,:,3:6]-h[:,:,3:6]
    p=np.sqrt(np.mean(dp*dp,axis=1));u=1000*np.max(np.linalg.norm(du,axis=2),axis=1)
    normalized=np.column_stack((p/PS,np.sqrt(np.mean(np.sum(dv*dv,axis=2),axis=1))/A,
                               np.sqrt(np.mean(np.sum(du*du,axis=2),axis=1))/US))
    need(np.array_equal(c[0].view("<u8"),h[0].view("<u8")), "Same-model coarse/half initial bits differ")
    need(np.max(p)<=5 and np.max(u)<=.005 and np.max(normalized)<=1e-4, "Original absolute/normalized half gate failed")
    return p,u,normalized
def reference():
    # Same independently recomputed constant-k coupled continuum reference as the retained audit.
    d=(KW/N0)*K0/(RW*9.80665)
    aa=KAPPA*PS/(RHO*A)
    t=d*RW*KAPPA*A/PS*aa
    matrix=np.array([[0,A/US,0,0],[0,0,-aa,aa],[0,M*KAPPA*A/PS,0,0],
                     [0,-(KW/N0)*KAPPA*A/PS,-t,-d*KAPPA**2+t]])
    return np.array([(expm(matrix*s)@np.array([0.,1.,0.,0.]))[[3,1,0]] for s in TIMES])
def modes(state):
    phase=KAPPA*state[0,:,0];cs=np.cos(phase);sn=np.sin(phase)
    jj=state[:,:,8];nn=1-(1-N0)/jj
    return dict(p=2*np.mean(state[:,:,6]*cs,axis=1)/PS,
                J=np.max(abs(jj-1),axis=1), n=np.max(abs(nn-N0),axis=1),
                nn=nn, k=None, phase=phase, cs=cs, sn=sn)
def constant_errors(state, refs, wall):
    phase=KAPPA*state[0,:,0];band=np.minimum(state[0,:,0],.0625-state[0,:,0])<=2*float(np.float32(1.8/512))
    if wall: need(band.sum()==256, "Original fixed near-wall material band changed")
    out=[];near=[]
    for i in range(257):
        p=state[i,:,6]/PS-refs[i,0]*np.cos(phase)
        v=state[i,:,3:6].copy()/A;v[:,0]-=refs[i,1]*np.sin(phase)
        u=(state[i,:,:3]-state[0,:,:3])/US;u[:,0]-=refs[i,2]*np.sin(phase)
        square=np.column_stack((p*p,np.sum(v*v,axis=1),np.sum(u*u,axis=1)))
        out.append(np.sqrt(square.mean(axis=0)))
        if wall: near.append(np.sqrt(square[band].mean(axis=0)))
    ep=float(modes(state)["p"][-1]/refs[-1,0]-1)
    out=np.array(out);near=np.array(near) if wall else None
    if wall:
        need(np.max(out)<=.01 and np.max(near)<=.01 and abs(ep)<=.01,
             "Original constant-wall1% full/near/endpoint objective failed")
    return out,near,ep
def line_number(path, needle):
    lines=path.read_text(encoding="utf-8-sig").splitlines()
    found=[i+1 for i,line in enumerate(lines) if needle in line]
    need(found, "Source-attribution statement lost its evidence: "+needle)
    return found

def main():
    outputs=[T/"figures"/(PREFIX+".png"),T/"figures"/(PREFIX+"_history.csv"),
             T/"figures"/(PREFIX+"_raw_initial.csv"),T/"notes"/(PREFIX+".md")]
    final=T/"logs"/(PREFIX+".check.json")
    need(not any(p.exists() for p in outputs+[final]), "Fresh analysis outputs required; no overwrites")
    remember(__file__)
    admitted("logs/upl_cpu_public_off_r2.check.json")
    admitted("logs/upl_cpu_public_OFF_r1.exact.check.json")
    admitted("logs/upl_cpu_public_debug_wall_evolving_smoke_r1.review.check.json")
    for label in ("drainage","fixed_zero","gravity","hydro_off","model_invalid","model_master_off",
                  "model_missing_ck","periodic_crossinc","pore_safety_overflow","spr_conflict","wall_noslip"):
        admitted("logs/upl_cpu_public_reject_r1_"+label+".run.json")
    groups=[
        ("periodic_constant",512,0,"upl_p3_spatial_wave_ReleaseCPU_r5_n32_","logs/upl_p3_spatial_wave_ReleaseCPU_r5.check.json"),
        ("wall_constant",1024,256,"upl_p3_wall_wave_ReleaseCPU_r4_k1_","logs/upl_p3_wall_wave_ReleaseCPU_r4.check.json"),
        ("wall_evolving",1024,256,"upl_p3_perm_time_wall_ReleaseCPU_r2_on_","logs/upl_p3_perm_time_wall_ReleaseCPU_r2.check.json")]
    refs=reference();runs={};comparisons=[];initial_rows=[];halves={};accuracy={};histories={}
    for kind,native,fixed,oldbase,oldcheck in groups:
        old=admitted(oldcheck); ownhalf=admitted("logs/upl_cpu_public_"+kind+"_r1.half.check.json")
        frozen(ownhalf["completion"]["path"],ownhalf)
        actualpair={}
        for tag in ("c","h"):
            label=kind+"_"+tag
            current=admitted("logs/upl_cpu_public_"+label+"_r1.review.check.json")
            folder=T/("outputs/upl_cpu_public_review_r1_"+label)
            cp=folder/"physical.bin";private=T/("outputs/"+oldbase+tag)/"physical.bin"
            frozen(cp,current);frozen(private,old)
            frozen(folder/"complete.json",current);frozen(folder/"native_ids.csv",current);frozen(folder/"fixed_ids.csv",current)
            complete=json.loads((folder/"complete.json").read_text())
            need(complete["native_count"]==native and complete["fixed_count"]==fixed and complete["samples"]==257,
                 "Canonical completed native identity mismatch")
            ids=list(csv.DictReader((folder/"native_ids.csv").open(newline="",encoding="utf-8")))
            need([int(r["native_id"]) for r in ids]==list(range(fixed,fixed+native)), "Canonical native-ID row order changed")
            c,p=physical(cp,native),physical(private,native)
            need(np.array_equal(c[0,:,:3].view("<u8"),p[0,:,:3].view("<u8")), "Initial material coordinates do not identify same particles")
            different=c.view("<u8")!=p.view("<u8")
            initial_count=different[0].sum(axis=0);evolved_count=different[1:].sum(axis=(0,1))
            for j in np.flatnonzero(initial_count):
                signed_zero=bool(np.all(c[0,different[0,:,j],j]==0)&np.all(p[0,different[0,:,j],j]==0))
                initial_rows.append(dict(group=kind,tag=tag,column=int(j),name=COL[j],
                    native_bit_mismatches=int(initial_count[j]),max_abs_numeric_delta=float(np.max(abs(c[0,:,j]-p[0,:,j]))),
                    signed_zero_only=signed_zero))
            comparisons.append(dict(group=kind,tag=tag,native_ids=native,samples=257,columns=26,
                raw_full257_bitwise_equal=bool(not different.any()),
                initial_bit_mismatches_per_column=initial_count.astype(int).tolist(),
                initial_max_abs_numeric_delta_per_column=np.max(abs(c[0]-p[0]),axis=0).tolist(),
                evolved_samples1_to256_all26_bitwise_equal=bool(not evolved_count.any()),
                evolved_bit_mismatches_per_column=evolved_count.astype(int).tolist(),
                ID_matching="Canonical explicit contiguous native IDs + exactly equal initial material XYZ; retained private row order is source-checked ID order",
                canonical=entry(cp),private=entry(private)))
            # No fields are removed or normalized in the raw equality result above.
            need(not evolved_count.any(), "Evolved private equivalence failed; preserve raw data")
            actualpair[tag]=c; mm=modes(c)
            mm["k"]=K0*np.exp((c[:,:,8]-1)/((1-N0)*2**-13)) if kind=="wall_evolving" else np.full(c[:,:,8].shape,K0)
            runs[label]=mm
        hp,hu,hn=half_metrics(actualpair["c"],actualpair["h"])
        oldhalf=json.loads(Path(ownhalf["completion"]["path"]).read_text())
        need(abs(float(hp.max())-oldhalf["max_pressure_RMS_Pa"])<=1e-12, "Independent half RMS differs from sealed half comparator")
        halves[kind]=dict(pressure_RMS_Pa=float(hp.max()),displacement_max_mm=float(hu.max()),
                         normalized_maxima=hn.max(axis=0).tolist(),original_gates_passed=True)
        for tag in ("c","h"):
            mm=runs[kind+"_"+tag];state=actualpair[tag]
            errs=near=None;ep=None
            if kind!="wall_evolving":
                errs,near,ep=constant_errors(state,refs,kind=="wall_constant")
                accuracy[kind+"_"+tag]=dict(global_normalized_RMS_max=errs.max(axis=0).tolist(),
                    fixed_near_wall_normalized_RMS_max=None if near is None else near.max(axis=0).tolist(),
                    endpoint_pressure_relative_error=ep,one_percent_hard_objective=(kind=="wall_constant"))
            histories[kind+"_"+tag]=dict(p=hp,u=hu,norm=hn,errors=errs,near=near)
    effect={}
    for tag in ("c","h"):
        cpath=T/("outputs/upl_cpu_public_review_r1_wall_constant_"+tag)/"physical.bin"
        vpath=T/("outputs/upl_cpu_public_review_r1_wall_evolving_"+tag)/"physical.bin"
        c=physical(cpath,1024);v=physical(vpath,1024)
        # Same material initial values; neither option delta nor signed-zero semantics are half/theory errors.
        dp=np.sqrt(np.mean((c[:,:,6]-v[:,:,6])**2,axis=1))
        effect[tag]=dict(max_pressure_RMS_Pa=float(dp.max()),history=dp,
            max_material_displacement_mm=float(1000*np.linalg.norm(c[:,:,:3]-v[:,:,:3],axis=2).max()))
    threshold=max(.001,10*halves["wall_evolving"]["pressure_RMS_Pa"])
    need(effect["c"]["max_pressure_RMS_Pa"]>threshold, "Original resolved variable-k effect failed")
    # Source-attribution evidence, separate from the failed strict raw257 equivalence gate.
    source=T/"outputs/upl_cpu_public_source_r3"
    cpu_single=source/"JSphCpuSingle.cpp";cpu=source/"JSphCpu.cpp";init=ROOT/"src/source/JDsInitialize.cpp"
    spatial=T/"support/upl_p3_spatial_wave_harness_r2.cpp";wall=T/"support/upl_p3_perm_wall_r1.cpp"
    for p in (cpu_single,cpu,init,spatial,wall): remember(p)
    attribution=dict(canonical_initial_save=line_number(cpu_single,"  SaveData();"),
        canonical_SaveData_tracking=line_number(cpu_single,"    ComputeFreeSurfaceTracking();"),
        actual_force_tracking=line_number(cpu_single,"  ComputeFreeSurfaceTracking();"),
        PosDiv_initial_zero=line_number(cpu,"memset(PosDivc,0"),
        private_spatial_direct_snapshot=line_number(spatial,"StateGuard(dt,false);WriteFrame(binary,Snapshot());"),
        private_wall_direct_snapshot=line_number(wall,"Guard(dt,false);Write(binary,Snapshot());"),
        initializer_signed_zero=line_number(init,"velrhop[p].y=dir.y*v1;"),
        explanation="Canonical initial SaveData refreshes position-based surface diagnostic PosDiv; private initial direct snapshot does not. XML direction*v initialization can produce signed zero transverse components; private periodic fixture assigns positive0. PosDiv is not a stored input in dynamic-pressure/J integration; force path refreshes tracking before using its associated operators. Observed evolved equality does not retroactively pass the failed raw257 gate.")
    raw_pass=all(r["raw_full257_bitwise_equal"] for r in comparisons)
    evolved_pass=all(r["evolved_samples1_to256_all26_bitwise_equal"] for r in comparisons)
    with outputs[1].open("x",newline="",encoding="utf-8") as out:
        names=["group","tag","time_s","pressure_mode_over_Pstar","max_abs_J_minus1","max_abs_n_minus_n0","min_k_over_k0","max_k_over_k0",
               "own_half_pressure_RMS_Pa","own_half_displacement_max_mm","own_half_p_RMS_over_Pstar","own_half_v_vector_RMS_over_A","own_half_u_vector_RMS_over_Ustar",
               "constant_reference_pressure_mode_over_Pstar","constant_global_p_RMS","constant_global_v_RMS","constant_global_u_RMS"]
        w=csv.writer(out);w.writerow(names)
        for kind,_,_,_,_ in groups:
            for tag in ("c","h"):
                m=runs[kind+"_"+tag];h=histories[kind+"_"+tag]
                for i,time in enumerate(TIMES):
                    refrow=[None]*4 if kind=="wall_evolving" else [refs[i,0],*h["errors"][i]]
                    w.writerow([kind,tag,time,m["p"][i],m["J"][i],m["n"][i],m["k"][i].min()/K0,m["k"][i].max()/K0,
                                h["p"][i],h["u"][i],*h["norm"][i],*refrow])
    with outputs[2].open("x",newline="",encoding="utf-8") as out:
        w=csv.DictWriter(out,fieldnames=["group","tag","column","name","native_bit_mismatches","max_abs_numeric_delta","signed_zero_only"])
        w.writeheader();w.writerows(initial_rows)
    colors={"periodic_constant":"#2474b5","wall_constant":"#328657","wall_evolving":"#c65a39"}
    labels={"periodic_constant":"Periodic constant k","wall_constant":"Wall constant k","wall_evolving":"Wall evolving k(J)"}
    fig,axes=plt.subplots(2,3,figsize=(13.4,8.0),constrained_layout=True)
    x=TIMES*1e6
    for kind,_,_,_,_ in groups:
        for tag in ("c","h"):
            m=runs[kind+"_"+tag];color=colors[kind]
            style=dict(color=color,lw=1.6 if tag=="h" else .8,ls="-" if tag=="h" else ":")
            for ax,key in zip(axes[0],("p","J","n")):
                ax.plot(x,m[key],**style,label=labels[kind] if tag=="h" else None)
        hn=histories[kind+"_h"]["norm"]
        axes[1,2].plot(x,1e6*hn.max(axis=1),color=colors[kind],label=labels[kind])
    axes[0,0].plot(x,refs[:,0],"k--",lw=1.2,label="Constant-k linear reference only")
    axes[0,0].set_ylabel("Pressure cosine mode / P*");axes[0,0].legend(fontsize=7)
    axes[0,1].set_ylabel("Maximum |J - 1|");axes[0,2].set_ylabel("Maximum |n - n0|")
    kk=runs["wall_evolving_h"]["k"]/K0
    axes[1,0].fill_between(x,kk.min(axis=1),kk.max(axis=1),color=colors["wall_evolving"],alpha=.22,label="Evolving wall spatial min/max")
    axes[1,0].plot(x,kk.min(axis=1),color=colors["wall_evolving"],lw=1)
    axes[1,0].plot(x,kk.max(axis=1),color=colors["wall_evolving"],lw=1)
    axes[1,0].axhline(1,color="k",ls="--",lw=1,label="Constant k / k0")
    axes[1,0].set_ylabel("Hydraulic conductivity / k0");axes[1,0].legend(fontsize=7)
    axes[1,1].plot(x,effect["c"]["history"],color=colors["wall_evolving"],label="Model1 - model0 coarse RMS")
    axes[1,1].plot(x,histories["wall_evolving_h"]["p"],color="#2474b5",label="Model1 own coarse/half RMS")
    axes[1,1].axhline(threshold,color="k",ls="--",lw=1,label="Predeclared resolved-effect threshold")
    axes[1,1].set_ylabel("Pressure comparison RMS [Pa]");axes[1,1].legend(fontsize=7)
    axes[1,2].set_ylabel("Max normalized p/v/u half RMS [ppm]")
    axes[1,2].legend(fontsize=7);axes[1,2].text(.02,.96,"Original normalized half limit:100 ppm\n(off-scale); all absolute limits also checked",transform=axes[1,2].transAxes,va="top",fontsize=7)
    for ax in axes.flat:
        ax.set_xlabel("Actual time [microseconds]");ax.grid(alpha=.22);ax.ticklabel_format(axis="y",style="sci",scilimits=(-3,3))
    fig.suptitle("Limited public CPU dynamic seepage: native saved-field review\nSolid:half dt; dotted:coarse dt. Full raw257 private equivalence FAILS at initial diagnostics; evolved256 all26 bits exact.",fontsize=11)
    fig.savefig(outputs[0],dpi=180);plt.close(fig)
    p32=accuracy["periodic_constant_h"]["endpoint_pressure_relative_error"]
    wc=accuracy["wall_constant_h"]
    report="# Public CPU bounded native comparison\n\n"
    report+="完整257帧原始26列对照：未通过（6组均false）；没有删列、改写原值或放宽门槛。\n\n"
    report+="全部6组第1–256个演化保存时刻的26列逐位一致。初始帧的PosDiv最大差为1.9906867742538452；周期场另有vy/vz各256个signed-zero差，数值差均为0。源头是正式SaveData先刷新自由表面诊断，而旧私有fixture初态直接Snapshot；这不使原始全程等价门槛转为通过，也不继承私有墙面通量/负控验收。\n\n"
    report+=f"周期32列半步终点孔压模态相对连续参考误差：{100*p32:.8f}%；没有新增1%周期场门槛。\n\n"
    report+=f"常k固定墙半步：全域p/v/u归一化RMS最大值{wc['global_normalized_RMS_max']}；近墙{wc['fixed_near_wall_normalized_RMS_max']}；终点孔压误差{100*wc['endpoint_pressure_relative_error']:.8f}%，原1%目标通过（独立重算），不等于一般墙面/物理发行验收。\n\n"
    report+=f"墙面变k粗步对常k孔压RMS最大差{effect['c']['max_pressure_RMS_Pa']:.12g}Pa；自身半步{halves['wall_evolving']['pressure_RMS_Pa']:.12g}Pa；原非空阈值{threshold:.12g}Pa，通过。参数差不是半步误差或理论误差；变k没有编造解析真值。\n\n"
    report+="所有原5Pa/.005mm与归一化1e-4半步门槛均重算通过。仅为小振幅、零重力、固定平行FreeSlip/周期CPU的有界窗口；GPU、重启、一般边界和完整物理发行均未由此接纳。\n"
    with outputs[3].open("x",encoding="utf-8") as out: out.write(report)
    for e in INPUTS.values(): need(entry(e["path"])==e,"Analysis input changed while reading")
    result=dict(passed=True,passed_scope="Offline analysis/evolved implementation/standalone native half and bounded objective audit only; NOT strict whole-private equivalence",
        complete_private_raw26_equivalence_passed=raw_pass,preregistered_full_raw26_equivalence_gate_passed=raw_pass,
        audited_evolved_samples1_to256_all26_equivalence_passed=evolved_pass,
        raw_initial_values_or_columns_modified=False,any_raw_field_masked=False,thresholds_relaxed=False,
        private_wall_flux_or_negative_control_inherited=False,
        comparisons=comparisons,initial_differences=initial_rows,half=halves,constant_reference=accuracy,
        variable_k_effect={tag:{k:v for k,v in values.items() if k!="history"} for tag,values in effect.items()},
        resolved_effect_threshold_Pa=threshold,source_attribution=attribution,inputs=list(INPUTS.values()),
        outputs=[entry(p) for p in outputs],figure_encoding="Explicit static scientific PNG; spatial k range is variation, not statistical uncertainty",
        physical_acceptance=False,full_formal_or_general_boundary_admission=False,raw_BI4_or_binary_cloud_backup_claimed=False)
    with final.open("x",encoding="utf-8") as out: json.dump(result,out,indent=2,ensure_ascii=False,allow_nan=False);out.write("\n")
    print(json.dumps(dict(analysis_passed=True,complete_private_raw26_equivalence_passed=raw_pass,
        evolved_all26_exact=evolved_pass,constant_reference=accuracy,half=halves,
        effect_pressure_RMS_Pa=effect["c"]["max_pressure_RMS_Pa"],effect_threshold_Pa=threshold),indent=2))
if __name__=="__main__":
    try: main()
    except Exception as error:
        print("HELD offline analysis; no solver rerun: "+str(error),file=sys.stderr)
        raise

