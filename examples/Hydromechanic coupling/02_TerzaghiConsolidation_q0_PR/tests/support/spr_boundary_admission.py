"""Real-program one-step controls and expected SPR admission rejections.

No promotion of corners, curves, motion or NoPen; no production edits.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from mdbc_plane_prepare import render

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
BIN = REPO/"bin/windows"
TAG = "spr_boundary_admission_r1"
CASES = ("plane2", "corner2", "edge3", "curve2", "sphere3", "translate2", "rotate3", "nopen2", "nopen3")
MESSAGES = {
    "corner2": "coplanar horizontal bottom-wall normals",
    "edge3": "coplanar horizontal bottom-wall normals",
    "curve2": "one coplanar, consistently oriented fixed wall",
    "sphere3": "one coplanar, consistently oriented fixed wall",
    "translate2": "fresh fixed-wall elastic cases only",
    "rotate3": "fresh fixed-wall elastic cases only",
    "nopen2": "no per-mk slip/NoPen/artificial stress",
    "nopen3": "no per-mk slip/NoPen/artificial stress",
}


def bound(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        return dict(path=str(path), sha256=hashlib.file_digest(stream, "sha256").hexdigest().upper())


def variant(key):
    dim = 3 if key.endswith("3") else 2
    root = ET.fromstring(render("3d_h" if dim == 3 else "2d_h", 2)[0])
    main = root.find("casedef/geometry/commands/mainlist")
    initialize = root.find("execution/special/initialize")
    if key.startswith(("corner", "edge")):
        # Separate side-wall mk avoids an ambiguous double normal at the join.
        index = list(main).index(main.find("setmkfluid"))
        side = ET.fromstring('<drawbox><boxfill>solid</boxfill><point x="-0.105" y="0" z="-0.025" /><size x="0.02" y="0" z="0.12" /></drawbox>')
        if dim == 3:
            side.find("point").set("y", "-0.075");side.find("size").set("y", "0.15")
        main.insert(index, ET.Element("setmkbound", mk="1"));main.insert(index+1, side)
        initialize.append(ET.fromstring('<boundnormal_plane mkbound="1"><point x="-0.08" y="0" z="0" /><normal x="1" y="0" z="0" /><maxdisth v="2" /><clear v="true" /></boundnormal_plane>'))
    if key.startswith(("curve", "sphere")):
        wall = main.find("drawbox");index = list(main).index(wall);main.remove(wall)
        main.insert(index, ET.fromstring('<drawsphere radius="0.08"><point x="0" y="0" z="0.04" /><layers vdp="-0.5,-1.5" /></drawsphere>'))
        soil = main.find("drawbox")
        soil.find("point").attrib.update(x="-0.015", y="-0.015" if dim==3 else "0", z="0.025")
        soil.find("size").attrib.update(x="0.03", y="0.03" if dim==3 else "0", z="0.03")
        initialize.clear()
        initialize.append(ET.fromstring('<boundnormal_sphere mkbound="0"><center x="0" y="0" z="0.04" /><radius v="0.08" /><inside v="true" /><maxdisth v="2" /><clear v="true" /></boundnormal_sphere>'))
    if key.startswith(("translate", "rotate")):
        motion = ET.SubElement(root.find("casedef"), "motion")
        obj = ET.SubElement(motion, "objreal", ref="0")
        ET.SubElement(obj, "begin", mov="1", start="0")
        if key.startswith("translate"):
            op=ET.SubElement(obj,"mvrect",id="1",duration="1")
            ET.SubElement(op,"vel",x="0.001",y="0",z="0")
        else:
            op=ET.SubElement(obj,"mvrot",id="1",duration="1",anglesunits="degrees")
            ET.SubElement(op,"vel",ang="1")
            ET.SubElement(op,"axisp1",x="0",y="0",z="0")
            ET.SubElement(op,"axisp2",x="0",y="1",z="0")
    if key.startswith("nopen"):
        root.find("execution/parameters/parameter[@key='NoPenetration']").set("value","1")
    return root


def run(command, log, cwd):
    with log.open("xb") as stream:
        process=subprocess.Popen(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code=process.wait(timeout=90)
        finally:
            if process.poll() is None: process.kill();process.wait()
    return dict(command=command,pid=process.pid,exit_code=code,owned_exited=process.poll() is not None,log=bound(log))


def main():
    receipt=TESTS/"logs"/(TAG+".check.json")
    assert not receipt.exists(), "Retain the existing test"
    sources=[Path(__file__).resolve(),TESTS/"support/mdbc_plane_prepare.py",TESTS/"configs/CaseMdbcPlane_Def.xml"]
    sources += [REPO/"src/source"/f for f in ("JSphCpuSingle.cpp","JSphGpuSingle.cpp","JSphCpu.cpp","JSphGpu.cpp")]
    inputs=[bound(p) for p in sources]+[bound(BIN/n) for n in ("GenCase_win64.exe","DualSPHysics5.2CPU_win64.exe","DualSPHysics5.2_GEO_win64.exe")]
    result=dict(passed=False,utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,runs=[],production_changed=False,
                scope="One-step input controls and expected admission rejections only; not complex-boundary physical acceptance")
    try:
        for key in CASES:
            for enabled in (0,1):
                label=f"{TAG}_{key}_{enabled}"
                definition=TESTS/"configs"/(label+"_Def.xml")
                folder=TESTS/"outputs"/(label+"_input")
                assert not definition.exists() and not folder.exists()
                root=copy.deepcopy(variant(key))
                root.find("execution/parameters/parameter[@key='SoilBoundaryDerivativeSPR']").set("value",str(enabled))
                ET.indent(root,space="  ")
                with definition.open("x",encoding="utf8") as stream:
                    stream.write('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding="unicode")+'\n')
                folder.mkdir();prefix=folder/label
                gen=run([str(BIN/"GenCase_win64.exe"),str(definition.with_suffix("")),str(prefix),"-save:all"],TESTS/"logs"/(label+".gencase.log"),TESTS/"configs")
                assert gen["exit_code"]==0,(key,"GenCase")
                for backend in ("CPU","GPU"):
                    name=label+"_"+backend.lower();out=TESTS/"outputs"/name
                    assert not out.exists()
                    args=[str(BIN/("DualSPHysics5.2CPU_win64.exe" if backend=="CPU" else "DualSPHysics5.2_GEO_win64.exe")),"-cpu" if backend=="CPU" else "-gpu"]
                    if backend=="CPU":args.append("-ompthreads:1")
                    args += [str(prefix),str(out),"-dirdataout","data","-svres","-sv:none"]
                    item=dict(case=key,spr=enabled,backend=backend,definition=bound(definition),gencase=gen)
                    result["runs"].append(item)
                    item.update(run(args,TESTS/"logs"/(name+".log"),BIN))
                    text=(TESTS/"logs"/(name+".log")).read_text(encoding="utf8",errors="replace")
                    expected=enabled and key!="plane2"
                    if expected:
                        assert item["exit_code"]!=0 and MESSAGES[key] in text,(key,backend,"Wrong rejection")
                        assert not (out/"data/Part_0001.bi4").exists(),"Rejected input advanced"
                    else:
                        assert item["exit_code"]==0 and "Finished execution" in text,(key,backend,"Control failed")
                    item.update(passed=True,expected_rejection=bool(expected),output_hashes=[bound(p) for p in out.rglob("*") if p.is_file()])
                    print(name+" PASS "+("rejected" if expected else "one-step control"),flush=True)
        for item in inputs:assert bound(item["path"])["sha256"]==item["sha256"]
        result.update(passed=True,finished_utc=datetime.now(timezone.utc).isoformat())
    finally:
        with receipt.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2)


if __name__=="__main__":
    main()
