"""Two actually edited GenCase inputs, and the archive/compiled P3 mapping."""
import hashlib
import json
from pathlib import Path

import hydro_frozen_xml_r1 as a
import hydro_frozen_xml_review_r1 as verify


def main():
    outputs=[]
    for cls in ("01","05"):
        name,row=next((n,r) for n,r in a.records().items() if r["case"]==cls)
        case,=a.SUITE.glob(cls+"_*");src=case/name;raw=verify.baseline_definition(case,name)
        modern=a.tree(a.modernize(name,raw));s,w=a.nodes(modern)
        s.find("drainage").set("start","0.0123456")
        modern.find("execution/parameters/parameter[@key='TimeOut']").set("value","0.000123456")
        if cls=="05":
            s.find("externalload").set("q0","9876.5");s.find("externalload").set("ramptime","0.25")
        restored=a.restore(name,raw,a.emit(modern))
        program,_=verify.gen_program(case,src)
        staged=verify.WORK/(cls+"_"+src.stem)/"changed_legacy"
        gen,particles=verify.generate(staged,restored,program)
        g,h=a.nodes(gen)
        expected=(.0123456,.000123456)
        actual=(float(h.find(a.DRAIN[1]).get("value")),float(gen.find("execution/parameters/parameter[@key='TimeOut']").get("value")))
        a.need(actual==expected,"Actual generated control data lost modified clocks")
        result=dict(case=cls,generated_drainage_start_s=actual[0],generated_TimeOut_s=actual[1],particle_count=len(particles["Idp"]),gen_exit=0)
        if cls=="05":
            q,r=(float(h.find(k).get("value")) for k in a.LOAD[1:])
            a.need((q,r)==(9876.5,.25),"Actual generated strip load lost edit")
            result.update(generated_q0=q,generated_ramp_s=r)
        try:a.restore(name,raw+b" ",a.emit(modern))
        except ValueError as e:a.need("template differs" in str(e),"Wrong template not detected");result["wrong_template_rejected"]=True
        else:raise ValueError("Unexpected unbound template")
        outputs.append(result)
    p3=next(a.SUITE.glob("04_*"))/"support/cryer_tpi_p3_package_r1.json"
    m=json.loads(p3.read_text(encoding="utf-8-sig"))
    desired={"UPL_TPI_GPU_R1":"B","UPL_TPI_P3_ROWS_R1":"3","UPL_TPI_M0_DT_R1":"EQ40_RH1"}
    a.need(m["scheme"]=="B" and m["rounds"]==3 and m["selectors"]==desired,"Original P3 launcher contract changed")
    pinned=json.loads(a.TEMPLATES.read_text(encoding="utf-8"))
    profile_files={r["name"]:r for r in m["files"]}
    for name,entry in pinned.items():
        if name.startswith("CaseCryer_TPI_P3_"):
            a.need(entry["sha256"]==profile_files[name]["sha256"],"P3 manifest original differs")
    out={"gen_program_calls":2,"solver_launches":0,"edited_inputs":outputs,"p3_manifest":m["package_id"],
         "p3_required_selectors":desired,"original_P3_2_XML_hashes_match_package":True}
    dest=a.HERE/"hydro_frozen_xml_edits_r1.json"
    with dest.open("x",encoding="utf-8") as f:json.dump(out,f,indent=2)
    print(dest)


if __name__=="__main__":main()
