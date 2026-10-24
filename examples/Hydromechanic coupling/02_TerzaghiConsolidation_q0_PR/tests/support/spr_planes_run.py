"""Prepare/run independent multi-plane manufactured fields; no formal input writes."""
from pathlib import Path
import argparse
import json
import hashlib
import math
import subprocess
import xml.etree.ElementTree as ET
from mdbc_plane_prepare import render

TESTS=Path(__file__).resolve().parents[1]
REPO=TESTS.parents[3]
TAG="spr_planes_r1"


def bound(path):
    path=Path(path)
    with path.open("rb") as stream:
        return dict(path=str(path),sha256=hashlib.file_digest(stream,"sha256").hexdigest().upper())


def xml(geometry,mode):
    root=ET.fromstring(render("3d_h" if geometry=="edge3" else "2d_h",mode)[0])
    main=root.find("casedef/geometry/commands/mainlist")
    wall,soil=main.findall("drawbox")
    wall.find("point").set("x","-0.025");wall.find("size").set("x","0.12")
    soil.find("point").set("x","0.005");soil.find("size").set("x","0.09")
    index=list(main).index(main.find("setmkfluid"))
    side=ET.fromstring('<drawbox><boxfill>solid</boxfill><point x="-0.025" y="0" z="0.005" /><size x="0.02" y="0" z="0.09" /></drawbox>')
    if geometry=="edge3":side.find("point").set("y","-0.075");side.find("size").set("y","0.15")
    main.insert(index,ET.Element("setmkbound",mk="1"));main.insert(index+1,side)
    plane=ET.fromstring('<boundnormal_plane mkbound="1"><point x="0" y="0" z="0" /><normal x="1" y="0" z="0" /><maxdisth v="2" /><clear v="true" /></boundnormal_plane>')
    if geometry=="wedge2":
        plane.find("normal").set("x","0.8660254037844386");plane.find("normal").set("z","0.5")
        # Draw the inclined solid band in its final coordinates. A post-draw
        # rotation would let the later fluid drawing erase the unrotated wall.
        index=list(main).index(side);main.remove(side);sidepoints=ET.Element("drawpoints")
        for k in range(10):
            z=.005+.01*k
            for i in range(-10,2):
                x=.005+.01*i;distance=math.cos(math.pi/6)*x+.5*z
                if -.03<distance<0:
                    ET.SubElement(sidepoints,"point",x=format(x,".17g"),y="0",z=format(z,".17g"))
        main.insert(index,sidepoints)
        # Fill the actual oblique half-space, not a rectangular soil patch with
        # an unrelated vertical free edge between the soil and inclined wall.
        index=list(main).index(soil);main.remove(soil);points=ET.Element("drawpoints")
        # Extra soil support above the finite inclined-wall endpoint separates
        # the corner test from a wall/free-surface termination test.
        for k in range(16):
            z=.005+.01*k
            for i in range(-8,11):
                x=.005+.01*i;u=x+math.tan(math.pi/6)*z
                if .005-1e-12<=u<=.105-1e-12:
                    ET.SubElement(points,"point",x=format(x,".17g"),y="0",z=format(z,".17g"))
        main.insert(index,points)
    root.find("execution/special/initialize").append(plane)
    ET.indent(root,space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding="unicode")+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",required=True);parser.add_argument("--geometry",nargs="+",default=["corner2","wedge2","edge3"])
    parser.add_argument("--tag",default=TAG);args=parser.parse_args()
    assert set(args.geometry)<={"corner2","wedge2","edge3"} and args.tag.replace("_","").isalnum()
    build=json.loads(Path(args.build).read_text(encoding="utf-8-sig"))
    exe=TESTS/"outputs"/Path(args.build).name.replace(".build.json","")/"spr_planes.exe"
    assert bound(exe)["sha256"]==build["exe_sha256"]
    result=dict(diagnostic_completed=False,inputs=[bound(__file__),bound(args.build),bound(exe)],runs=[])
    receipt=TESTS/"logs"/(args.tag+".check.json");assert not receipt.exists()
    try:
        for geometry in args.geometry:
            for mode in (1,2,3):
                name=f"{args.tag}_{geometry}_s{mode}";definition=TESTS/"configs"/(name+"_Def.xml")
                generated=TESTS/"outputs"/(name+"_input");out=TESTS/"outputs"/name
                assert not any(p.exists() for p in (definition,generated,out))
                with definition.open("x",encoding="utf8") as stream:stream.write(xml(geometry,mode))
                generated.mkdir();prefix=generated/name
                genlog=TESTS/"logs"/(name+".gencase.log")
                with genlog.open("xb") as stream:
                    subprocess.run([str(REPO/"bin/windows/GenCase_win64.exe"),str(definition.with_suffix("")),str(prefix),"-save:all"],stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                blocks=ET.parse(prefix.with_suffix(".xml")).findall("execution/particles/fixed")
                expected_side=(480 if geometry=="edge3" else 30)
                if geometry=="wedge2":
                    expected_side=len(ET.fromstring(xml(geometry,mode)).findall("casedef/geometry/commands/mainlist/drawpoints")[0])
                assert [int(b.get("count")) for b in blocks]==[624 if geometry=="edge3" else 39,expected_side],"GenCase erased/changed a wall block"
                log=TESTS/"logs"/(name+".log")
                command=[str(exe),"-cpu","-ompthreads:1",str(prefix),str(out),"-dirdataout","data","-sv:none"]
                with log.open("xb") as stream:
                    process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
                assert process.returncode==0,(name,"setup/fixture failure; inspect log")
                record=json.loads((out/"planes_complete.json").read_text())
                record.update(name=name,geometry=geometry,slip_mode=mode,exit_code=process.returncode,definition=bound(definition),log=bound(log),outputs=[bound(p) for p in out.iterdir() if p.is_file()])
                result["runs"].append(record)
                print(name,json.dumps({k:record[k] for k in ("passed","active_wall_count","wall_count","affine_bad_components","consumer_max")}),flush=True)
        result["diagnostic_completed"]=True;result["passed"]=all(x["passed"] for x in result["runs"])
    finally:
        with receipt.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2)


if __name__=="__main__":main()
