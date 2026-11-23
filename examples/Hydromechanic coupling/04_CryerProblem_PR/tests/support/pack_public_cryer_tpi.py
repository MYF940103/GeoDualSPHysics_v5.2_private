"""Review the GenCase seed and assemble the portable public 1-Tv Cryer input and runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

CASE=Path(__file__).resolve().parents[2]
BIN=CASE.parents[2]/"bin/windows"
NAME="CaseCryer_TPI_nu030_1Tv"
BAT="x"+NAME+"_win64_GPU.bat"
PROGRAM="DualSPHysics5.2_GEO_win64.exe"
ZIP=CASE/"Cryer_public_SPH_TPI_nu030_1Tv_Windows_RTXA6000.zip"
SEED=CASE/"tests/outputs/cryer_tpi_1tv_gencase"
REVIEW=CASE/"tests/logs/cryer_public_1tv_seed.json"
sys.path.insert(0,str(CASE.parent/"validation"))
from hydro_public_xml_r1 import read_part


def need(value,message):
    if not value:raise ValueError(message)


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def stage_path(release_sha):
    return CASE/"tests/outputs"/("Cryer Public SPH TPI 1Tv "+release_sha[:12])


def structure(node):
    attrs=tuple(sorted((k,v) for k,v in node.attrib.items() if k not in ("comment","units_comment","_rem")))
    return node.tag,attrs,(node.text or "").strip(),tuple(map(structure,node))


def seed_review():
    old=ET.parse(CASE/"CaseCryer_TPI_P3_nu030_full_r1_Def.xml")
    new=ET.parse(CASE/(NAME+"_Def.xml"))
    generated=ET.parse(SEED/(NAME+".xml"))
    for key in ("casedef","execution/parameters","execution/special/timeout","execution/special/soils"):
        need(structure(old.find(key))==structure(new.find(key)),"Frozen full input differs at "+key)
    modern=ET.parse(CASE/"CaseCryerProblem_u_pl_nu030_Def.xml")
    for key in ("drainage","externalload","hydromechanics"):
        path="execution/special/"+key
        base=modern.find(path)
        if key=="hydromechanics":base.find("HydroMechModel").set("value","2")
        need(structure(base)==structure(new.find(path))==structure(generated.find(path)),"Generated selector/material/BC differs at "+key)
    native=CASE/"CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"/"CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"/"CaseCryer_TPI_P3_nu030_peak_r1.bi4"
    test=SEED/(NAME+".bi4")
    with tempfile.TemporaryDirectory() as directory:
        # The seed payload is a native PART_0000. The generic reader derives that
        # item name from the filename for result frames.
        alias=Path(directory)/"Part_0000.bi4"
        shutil.copyfile(test,alias); root,meta,arrays=read_part(alias)
        shutil.copyfile(native,alias); base,oldmeta,olda=read_part(alias)
    for a,b,allowed in ((root,base,{"CaseName","Date","RunCode"}),(meta,oldmeta,set())):
        need(a.keys()==b.keys() and all(np.array_equal(a[k],b[k]) for k in a.keys()-allowed),"Native seed header differs")
    need(root["CaseNfixed"]==8 and root["CaseNfluid"]==37173 and arrays.keys()==olda.keys() and
         all(arrays[k].dtype==olda[k].dtype and arrays[k].tobytes()==olda[k].tobytes() for k in arrays),
         "Original native sphere differs")
    receipt=dict(case=NAME,soil=37173,fixed=8,arrays_bitwise_equal=list(arrays),old_seed=str(native.relative_to(CASE)),
                 generated_seed=str(test.relative_to(CASE)),definition_sha256=sha(CASE/(NAME+"_Def.xml")),
                 gencase_sha256=sha(BIN/"GenCase_win64.exe"),generated_xml_sha256=sha(SEED/(NAME+".xml")))
    with REVIEW.open("x",encoding="utf-8") as f:json.dump(receipt,f,indent=2)


def stage(release_sha):
    dest=stage_path(release_sha)
    need(sha(BIN/PROGRAM)==release_sha,"GPU Release hash differs from the approved build")
    need(json.loads(REVIEW.read_text())["definition_sha256"]==sha(CASE/(NAME+"_Def.xml")),"GenCase review differs")
    dest.mkdir(exist_ok=False)
    files={n:CASE/n for n in (BAT,NAME+"_Def.xml","LICENSE","support/check_public_cryer_tpi.ps1")}
    files["README.md"]=CASE/"README_Cryer_TPI_nu030_1Tv.md"
    for n in (PROGRAM,"GenCase_win64.exe","PartVTK_win64.exe","DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll"):
        files["bin/"+n]=BIN/n
    for n in ("msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"):
        files["bin/"+n]=CASE/"support/bin_cryer_tpi_p3_r1"/n
    for name,source in files.items():
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    notices=[]
    for tool in ("GenCase_win64.exe","PartVTK_win64.exe"):
        banner=subprocess.run([str(dest/"bin"/tool),"-h"],cwd=dest,capture_output=True,check=True).stdout.decode("ascii",errors="replace")
        end=banner.index("THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.")
        notices.append(banner[:end+len("THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.")].strip())
    (dest/"Tool notices.txt").write_text("\n\n".join(notices)+"\n",encoding="utf-8")
    names=sorted([*files,"Tool notices.txt"])
    manifest=dict(case=NAME,model=2,release_sha256=release_sha,files={n:sha(dest/n) for n in names})
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(dest)


def pack(release_sha):
    dest=stage_path(release_sha)
    smoke=dest/"tests/outputs/cryer_tpi_1tv_smoke_gpu"
    manifest=json.loads((dest/"manifest.json").read_text())
    need(release_sha==manifest["release_sha256"]==sha(BIN/PROGRAM),"Release changed")
    subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",
                    str(dest/"support/check_public_cryer_tpi.ps1"),str(smoke),"2"],check=True)
    run=(smoke/"Run.out").read_text(errors="replace")
    need("HydroMechModel=2" in run and "Finished execution (code=0)" in run,"Smoke log is not public TPI")
    sys.path.insert(0,str(CASE/"support"))
    from plot_public_cryer_tpi import public_history
    history=public_history(smoke/"data",[0,2])
    need(len(history)==2 and history[-1]["completed_step"]==2,"Smoke native analysis failed")
    vtk=(smoke/"particles/PartFluid_0001.vtk").read_bytes()
    need(b"PorePress" in vtk and b"37173" in vtk,"Fluid VTK lacks particle count or pressure")
    need(not ZIP.exists() and not ZIP.with_suffix(".zip.sha256").exists(),"Preserve existing package")
    names=[*manifest["files"],"manifest.json"]
    with tempfile.TemporaryDirectory(dir=ZIP.parent) as directory:
        candidate=Path(directory)/ZIP.name
        with zipfile.ZipFile(candidate,"x",zipfile.ZIP_DEFLATED) as z:
            for name in names:
                if name in manifest["files"]:need(sha(dest/name)==manifest["files"][name],"Changed release file "+name)
                z.write(dest/name,name)
        with zipfile.ZipFile(candidate) as z:
            need(z.testzip() is None and sorted(z.namelist())==sorted(names) and
                 all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest["files"].items()),"Archive integrity")
        checksum=candidate.with_suffix(".zip.sha256")
        checksum.write_text(sha(candidate)+"  "+ZIP.name+"\n",encoding="ascii")
        candidate.rename(ZIP);checksum.rename(ZIP.with_suffix(".zip.sha256"))
    print(ZIP)


if __name__=="__main__":
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("action",choices=("seed-review","stage","pack"))
    args.add_argument("--release-sha",help="SHA-256 of the reviewed public GPU Release")
    opt=args.parse_args()
    if opt.action=="seed-review":seed_review()
    else:
        need(opt.release_sha is not None and len(opt.release_sha)==64,"Supply reviewed GPU Release SHA-256")
        (stage if opt.action=="stage" else pack)(opt.release_sha.lower())
