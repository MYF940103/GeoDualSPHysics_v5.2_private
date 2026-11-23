"""Audit true receiver policies, clocks, material state and pressure history across wall retirement."""
import argparse
import csv
import json
import struct
import numpy as np
from c08_m0_coupled_baseline_gpu_r1 import T,TAG,CAPS,mature
from c08_m0_coupled_deformed_r1 import _Cursor,read_item


def load(path,has_child):
    c=_Cursor(path.read_bytes(),64);tree=read_item(c,0,has_child);c.finish("complete actual C08 frame")
    part,=tree["children"];assert part["name"]==path.stem.upper()
    fields=part["arrays"];assert len(fields)==22 and all(np.isfinite(v).all() for v in fields.values())
    order=np.argsort(fields["Idp"])
    return part["values"],{k:v[order] for k,v in fields.items()},part["children"]


def signed_clock_bytes(path):
    with path.open("rb") as f: header=f.read(8192)
    clock=[]
    for key in (b"TimeStep",b"dterror"):
        tag=struct.pack("<I",len(key))+key+struct.pack("<I",12)  # JBinaryData double
        assert header.count(tag)==1
        i=header.index(tag)+len(tag)
        clock.append(header[i:i+8])
    return clock


def main(win,single=None):
    check=T/"logs"/(TAG+"_"+win+".check.json")
    outfile=T/"figures"/(TAG+"_"+win+"_native.csv")
    assert not check.exists() and not outfile.exists()
    sm,source,empty=load(mature.hold.PRE,False)
    assert not empty and sm["Step"]+1==2000000 and len(source["Idp"])==7060
    openstep=2000200;cap=CAPS[win]
    save=[2000001,2000002,2000199,2000200,*range(2000201,2000209),*range(2002200,cap+1,2000)]
    actual={2000000:sm["TimeStep"]}
    for i in range(2000001,cap+1): actual[i]=actual[i-1]+5e-6
    summary={};rows=[]
    for label,beta in (("b0",0.),("b004",.04)):
        if single and label!=single:continue
        name=TAG+"_"+win+"_"+label;folder=T/"outputs"/name
        receipt=T/"logs"/(name+".native.json")
        parts=sorted((folder/"data").glob("Part_????.bi4"))
        def stat_binding():
            return [(f.name,f.stat().st_size,f.stat().st_mtime_ns) for f in [folder/"Run.out",T/"logs"/(name+".call.json"),*parts]]
        # Adopt the first branch when it was reviewed while its peer was computing.
        if receipt.exists():
            assert not single
            read=json.loads(receipt.read_text())
            assert read["name"]==name and [tuple(v) for v in read["files"]]==stat_binding()
            summary[label]=read["summary"];rows.extend(read["native_rows"]);continue
        nrows=len(rows)
        call=json.loads((T/"logs"/(name+".call.json")).read_text());assert call["returncode"]==0 and call["cap"]==cap
        run=(folder/"Run.out").read_text(errors="replace")
        assert "C08Mature imported 7060 fixed 2060 material 5000" in run and "C08M0Release 2000200" in run
        prev=source["PorePress"][2060:];last=2000000;adjacent=0;native=[]
        prior_kappa=source["Kplastic"][2060:];initialV=source["PoroCurrentVolume"][2060:]/source["PoroVolumeRatio"][2060:]
        for n,path in enumerate(parts):
            m,a,children=load(path,True);h,=children
            step=int(m["Step"])+1;active=step>openstep;assert step==save[n]
            assert m["Nout"]==0 and m["HydroMechModel"]==2 and m["TimeStep"]==actual[step]
            assert m["dterror"]<=1e-14 and m["dtmin"]==m["dtmax"]==5e-6
            assert m["GravityPreloadPhase"]==active and m["GravityPreloadEventCompletedStep"]==openstep
            assert m["SoilDampingActive"]==(not active) and m["PoreShepardActive"]==(not active)
            assert m["DynamicArtificialStressPolicy"]=="ReleaseOnly" and m["DynamicArtificialStressActive"]==active
            assert m["DynamicArtificialStressCoef"]==np.float32(.3) and m["DynamicArtificialStressExp"]==np.float32(2.55)
            assert m["DynamicNoPenetrationPolicy"]=="FixedPlaneStageProjectionReleaseOnly" and m["DynamicNoPenetrationActive"]==active
            assert m["DynamicNoPenetrationReactionClosed"]==0 and m["GravityPreloadStateFile"]==str(mature.hold.PRE)
            if active:
                assert m["GravityPreloadActualTime"]==actual[openstep] and m["GravityPreloadActualCompletedStep"]==openstep
            ids=a["Idp"];b=1805 if active else 2060
            assert np.array_equal(ids,np.r_[0:b,2060:7060])
            assert a["Posd"][:b].tobytes()==source["Posd"][:b].tobytes()
            assert a["PorePress0"].tobytes()==source["PorePress0"][ids].tobytes()
            hs=h["values"];assert hs["CompletedUpdates"]==step and hs["Dt"]==5e-6 and hs["Valid"]==1
            assert hs["PreviousTime"]==actual[step-1] and hs["SavedTime"]==actual[step]
            assert hs["Scheme"]==("P3_B_alpha_half_beta_0p04" if beta else "P3_B_alpha_half_beta_zero")
            assert np.array_equal(h["arrays"]["Idp"],np.arange(2060,7060))
            pressure=a["PorePress"][b:];fs=np.isin(a["FSType"][b:],[2,3])
            assert np.all(pressure[fs]<=0)
            if step==last+1:
                assert h["arrays"]["PorePressPrev"].tobytes()==prev.tobytes();adjacent+=1
            prev=pressure;last=step;native.append(step)
            J=a["PoroVolumeRatio"][b:];n=a["PoroPorosity"][b:]
            assert np.all(J>0) and np.max(np.abs(n-(1-(1-float(np.float32(.35)))/J)))<2e-14
            kval=a["PoroHydraulicConductivity"][b:]
            assert np.max(np.abs(kval-float(np.float32(.0002))*np.exp((J-1)/(2*(1-float(np.float32(.35)))))))<2e-14
            assert np.allclose(a["PoroCurrentVolume"][b:],initialV*J,rtol=2e-14,atol=0)
            assert np.allclose(a["PoroMixtureDensity"][b:],1000.+1072.5/J,rtol=2e-14,atol=0)
            assert np.array_equal(a["ExcessPorePress"][b:],pressure-a["PorePress0"][b:])
            for st in ("kk","ij"):
                assert np.array_equal(a["Sigma_"+st][b:],a["SigmaState_"+st][b:].astype(np.float32))
            assert (a["Kplastic"][b:]>=prior_kappa).all()
            prior_kappa=a["Kplastic"][b:]
            # These axis-aligned faces are x=0 and z=0. Use the production registration tolerance 1e-6 dp.
            assert np.all(a["Posd"][b:,[0,2]]>=-1e-6*.04)
            if win=="w30" and step<=2000208:
                old=T/"outputs"/(TAG+"_short_"+label)/"data"/path.name
                om,oa,oh=load(old,True)
                assert m["TimeStep"]==om["TimeStep"] and m["dterror"]==om["dterror"] and m["Step"]==om["Step"]
                assert all(v.tobytes()==oa[k].tobytes() for k,v in a.items()) and h["arrays"]["PorePressPrev"].tobytes()==oh[0]["arrays"]["PorePressPrev"].tobytes()
            rows.append(dict(beta=beta,step=step,time_s=actual[step],tau_s=actual[step]-actual[openstep],
                n_FS=int(fs.sum()),p_neg=int((pressure<0).sum()),p_min_Pa=float(pressure.min()),p_max_Pa=float(pressure.max()),
                speedmax_m_s=float(np.linalg.norm(a["Vel"][b:],axis=1).max()),kappamax=float(a["Kplastic"][b:].max()),
                Jmin=float(J.min()),Jmax=float(J.max()),front_m=float(a["Posd"][b:,0].max())))
        assert native==save
        dt_count=round_count=filters=0;min_bound=1.
        for line in run.splitlines():
            if line.startswith("C08M0Dt "):
                step,stage,fixed,bound,*other=map(float,line.split()[1:]);assert step==2000001+dt_count//5
                assert stage==(0,1,0,0,0)[dt_count%5] and bound>=fixed==5e-6 and np.isfinite(other).all()
                dt_count+=1;min_bound=min(min_bound,bound)
            elif line.startswith("C08GpuRound "):
                step,r,filt=map(int,line.split()[1:]);assert step==2000001+round_count//3 and r==round_count%3+1
                assert filt==int(r==3 and step%40==0 and step<=openstep)
                filters+=filt;round_count+=1
        assert dt_count==5*(cap-2000000) and round_count==3*(cap-2000000) and filters==5
        summary[label]=dict(steps=cap-2000000,frames=len(save),native_history_actual_adjacent=adjacent,dt_checks=dt_count,
                           min_allowed_dt_s=min_bound,rounds=round_count,pre_shepard_calls=filters)
        if win=="w30":
            receipt.write_text(json.dumps(dict(name=name,files=stat_binding(),summary=summary[label],native_rows=rows[nrows:]),indent=2))
    if single:
        print(summary);return
    raw_prefix={}
    if win=="w30":
        for label in ("b0","b004"):
            old=T/"outputs"/(TAG+"_short_"+label)/"data"
            new=T/"outputs"/(TAG+"_w30_"+label)/"data"
            names=sorted(old.glob("Part_????.bi4"))
            assert len(names)==12
            for file in names:
                assert signed_clock_bytes(file)==signed_clock_bytes(new/file.name)
            raw_prefix[label]=len(names)
    with outfile.open("x",newline="") as fo:
        w=csv.DictWriter(fo,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    check.write_text(json.dumps(dict(step=cap,actual_AS_plane_transition_checked=True,actual_source=actual[2000000],
         release=actual[openstep],end=actual[cap],scope=win,branch=summary,raw_time_signed_dterror_prefix=raw_prefix),indent=2))
    print(check)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("window",choices=tuple(CAPS));p.add_argument("--single",choices=("b0","b004"))
    opt=p.parse_args();main(opt.window,opt.single)
