"""Stage 21 real frozen root inputs and compare GenCase seed arrays without a solver launch."""
import copy
import json
from pathlib import Path
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

import hydro_frozen_xml_r1 as adapter
from upl_xml_gencase_r1 import contents, particles_from_bi4, parse, PROGRAM

T=adapter.SUITE/"04_CryerProblem_PR/tests"
WORK=T/"outputs/hydro_frozen_xml_r1"
RECEIPT=adapter.HERE/"hydro_frozen_xml_review_r1.json"


def check(flag,msg):
    if not flag:raise ValueError(msg)


def baseline_definition(case, name):
    old = case/"support/frozen_xml"/name
    if old.is_file():
        raw=old.read_bytes()
    elif (case/"support/hydro_frozen_plan_r2.json").is_file() and case.name.startswith("04_"):
        entries=json.loads((case/"support/hydro_frozen_plan_r2.json").read_text())
        with zipfile.ZipFile(case/entries[name]["archive"]) as archive:
            raw=archive.read(name)
    else:
        raw=(case/name).read_bytes()
    adapter.validate_template(name,raw)
    return raw


def gen_program(case,path):
    if case.name.startswith("08_"):
        revision=re.search(r"_r(\d+)_Def\.xml$",path.name).group(1)
        program=case/"support"/("runtime_r"+revision)/"GenCase_win64.exe"
        return program,"Matching package GenCase"
    if path.name.startswith("CaseCryer_TPI_P3_"):
        return PROGRAM,"Independent GenCase geometry check; P3 launcher uses its archived seed and three selectors"
    if path.name=="CaseCryerProblem_u_pl_nu030_r1_Def.xml":
        return PROGRAM,"Independent GenCase geometry check; u-pl r1 launcher copies its archived generated XML/BI4"
    return case/"support/bin/GenCase_win64.exe","Matching package GenCase"


def generate(folder,raw,program):
    if folder.exists():
        check((folder/"Case_Def.xml").read_bytes()==raw,"Existing staged input differs")
        previous=json.loads((folder/"gen.call.json").read_text())
        check(previous=={"command":[str(program),"Case_Def","Case","-save:all"],"exit":0},"Sealed GenCase call differs or failed")
        return parse((folder/"Case.xml").read_bytes()),particles_from_bi4(folder/"Case.bi4")
    folder.mkdir()
    adapter.write_new(folder/"Case_Def.xml",raw)
    cmd=[str(program),"Case_Def","Case","-save:all"]
    with (folder/"GenCase.log").open("xb") as f:
        p=subprocess.run(cmd,cwd=folder,stdout=f,stderr=subprocess.STDOUT)
    (folder/"gen.call.json").write_text(json.dumps(dict(command=cmd,exit=p.returncode)))
    p.check_returncode()
    return parse((folder/"Case.xml").read_bytes()),particles_from_bi4(folder/"Case.bi4")


def uncoupled(root,modern):
    root=copy.deepcopy(root)
    spec,hyd=adapter.nodes(root)
    for node in list(hyd):
        if node.tag in adapter.OLD+(adapter.MODEL,):hyd.remove(node)
    for node in list(spec):
        if node.tag in ("externalload","drainage"):spec.remove(node)
    return contents(spec)


def reject(name,raw,modern,phrase):
    try:adapter.restore(name,raw,modern)
    except ValueError as exc:
        check(phrase in str(exc),"Unexpected rejection: "+str(exc))
        return str(exc)
    raise ValueError("An unsupported modification was silently accepted: "+name)


def edits(path,raw,modern):
    name=path.name
    results={}
    altered=adapter.tree(modern)
    parameter=altered.find("execution/parameters/parameter[@key='TimeOut']")
    original_timeout=parameter.get("value");parameter.set("value","0.000123456")
    if name.startswith("CaseCryer") or name.startswith("CaseLianSaturated"):
        results["frozen_time_change_rejected"]=reject(name,raw,adapter.emit(altered),"Frozen release")
        hydraulic=adapter.tree(modern)
        water=adapter.nodes(hydraulic)[1];model=water.find(adapter.MODEL)
        model.set("value","0" if model.get("value")!="0" else "2")
        results["frozen_hydraulic_change_rejected"]=reject(name,raw,adapter.emit(hydraulic),"Frozen release")
    else:
        target=adapter.tree(adapter.restore(name,raw,adapter.emit(altered)))
        check(target.find("execution/parameters/parameter[@key='TimeOut']").get("value")=="0.000123456" and original_timeout!="0.000123456","Lost non-hydraulic edit")
        results["nonhydraulic_TimeOut_edit_propagated"]=True
        hydraulic=adapter.tree(modern);s,w=adapter.nodes(hydraulic)
        s.find("drainage").set("start","0.0123456")
        if s.find("externalload") is not None:
            s.find("externalload").set("q0","9876.5")
            s.find("externalload").set("ramptime","0.25")
        back=adapter.tree(adapter.restore(name,raw,adapter.emit(hydraulic)));_,b=adapter.nodes(back)
        check(b.find(adapter.DRAIN[1]).get("value")=="0.0123456","Lost start")
        if s.find("externalload") is not None:
            check(b.find(adapter.LOAD[1]).get("value")=="9876.5" and b.find(adapter.LOAD[2]).get("value")=="0.25","Lost load")
        results["legacy_hydraulic_edit_propagated"]={"start":"0.0123456"}
        if s.find("externalload") is not None:results["legacy_hydraulic_edit_propagated"].update(q0="9876.5",ramptime="0.25")
        w.find(adapter.MODEL).set("value","2")
        results["TPI_to_incompatible_legacy_rejected"]=reject(name,raw,adapter.emit(hydraulic),"HydroMechModel")
    return results


def main():
    # A re-review may reuse only independently sealed GenCase calls with identical commands and definition bytes.
    WORK.mkdir(exist_ok=True)
    results=[]
    for name,r in sorted(adapter.records().items(),key=lambda x:(x[1]["case"],x[0])):
        case,=adapter.SUITE.glob(r["case"]+"_*");path=case/name
        raw=baseline_definition(case,name);modern=adapter.modernize(name,raw);restored=adapter.restore(name,raw,modern)
        check(raw==restored,"Default bytes differ "+name)
        root=adapter.tree(modern)
        s,w=adapter.nodes(root);model,v=adapter.mode_values(s,w)
        check(not any(w.find(k) is not None for k in adapter.OLD),"Old keys remaining")
        program,scope=gen_program(case,path)
        check(program.is_file(),"Missing actual generator: "+str(program))
        item=WORK/(r["case"]+"_"+path.stem)
        item.mkdir(exist_ok=True)
        a,pa=generate(item/"modern",modern,program)
        b,pb=generate(item/"restored",restored,program)
        check(uncoupled(a,True)==uncoupled(b,False),"Unrelated special fields changed: "+name)
        for key in ("constants","particles","parameters"):
            check(contents(a.find("execution/"+key))==contents(b.find("execution/"+key)),key+" changed: "+name)
        check(pa.keys()==pb.keys() and "Idp" in pa,"Initial array names differ")
        for k in pa:
            check(pa[k].dtype==pb[k].dtype and pa[k].shape==pb[k].shape and pa[k].tobytes()==pb[k].tobytes(),k+" differs: "+name)
        ag,aw=adapter.nodes(a);bm,bw=adapter.nodes(b)
        check(adapter.mode_values(ag,aw)==(model,v) and adapter.original_model(name,bw)==model,"Effective model source mismatch")
        actual_modern=adapter.tree(adapter.modernize(name,ET.tostring(b)))
        gg,gwater=adapter.nodes(actual_modern)
        check(adapter.mode_values(gg,gwater)==(model,v),"Effective generated boundary/load or model mismatch")
        results.append(dict(case=r["case"],definition=name,registered_runtime=r["disposition"],model=model,
            original_bytes=len(raw),original_restored_bytes_identical=True,generator=str(program),generator_scope=scope,
            GenCase_exits=[0,0],native_start_count=len(pa["Idp"]),bitwise_initial_arrays=sorted(pa),edits=edits(path,raw,modern)))
        print(r["case"],name,model,len(pa["Idp"]),flush=True)
    check(len(results)==21,"Expected 21 frozen definitions")
    receipt=dict(cases=results,total_GenCase_calls=2*len(results),solver_calls=0,initial_particles_compared=sum(x["native_start_count"] for x in results),
                 staging=str(WORK),boundaries="Generated original physical geometry and applied XML schema; no solver or state handoff validation.")
    with RECEIPT.open("w",encoding="utf-8") as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
    print(RECEIPT)


if __name__=="__main__":main()
