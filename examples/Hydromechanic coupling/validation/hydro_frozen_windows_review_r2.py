"""Audit real original launcher dependencies and recheck actual Windows-only XML dispatch."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import hydro_frozen_entry_stage_r1 as stage
import hydro_frozen_entry_review_r1 as live

V = stage.bridge.HERE
WORK = stage.STAGE / "winlex1"
OVERLAY = stage.STAGE / "winrelease"


def references_python(raw):
    lines = raw.decode("utf-8-sig").splitlines()
    return [t.strip() for t in lines if re.search(r"python",t,re.I)
            and not re.match(r"^\s*(rem\s|echo\s|#)",t,re.I)]


def run_script(work, name, output, expected, text=None):
    env = dict(os.environ, PATH=os.pathsep.join([os.environ["WINDIR"]+"\\System32",
                   os.environ["WINDIR"]+"\\System32\\WindowsPowerShell\\v1.0"]), PYTHON="absent_python.exe")
    assert shutil.which("python",path=env["PATH"]) is None
    ps = Path(os.environ["WINDIR"])/"System32/WindowsPowerShell/v1.0/powershell.exe"
    cmd = [str(ps),"-NoProfile","-ExecutionPolicy","Bypass","-File",str(work/"support"/stage.RUNTIME),
           "-Definition",name,"-OutFile",str(output)]
    result = subprocess.run(cmd, cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode!=expected or (text and text not in result.stdout.decode(errors="replace")):
        raise ValueError(f"Unexpected PowerShell exit/message for {name}: {result.returncode}: {result.stdout!r}")
    return result.returncode


def main():
    WORK.mkdir()
    archive_audits=[]
    cases={cid:next(stage.SUITE.glob(cid+"_*")) for cid in ("01","04","05","08")}
    packages=[stage.package_path(cases["04"],p) for p in sorted({z["archive"] for z in json.loads(
        (OVERLAY/cases["04"].name/"support"/stage.ARCHIVES).read_text()).values()})]
    packages.extend(cases["05"].glob("Lian_HGSPR_Windows_RTXA6000.zip"))
    packages.extend(sorted(cases["08"].glob("support/LianCollapse_upl_win64_r?.zip")))
    for package in packages:
        with zipfile.ZipFile(package) as ar:
            members=[n for n in ar.namelist() if n.lower().endswith(".bat") or
                (n.lower().endswith(".ps1") and ("/run_" in n or "/check_" in n))]
            commands={n:references_python(ar.read(n)) for n in members}
        if any(commands.values()):raise ValueError("Unexpected Python command in "+package.name)
        archive_audits.append(dict(package=package.name,launch_components_checked=members,python_commands=0))
    runtime=[]
    for cid in ("01","05","08"):
        case=cases[cid];copy=WORK/cid
        shutil.copytree(OVERLAY/case.name,copy)
        for namefile in copy.glob("*_Def.xml"):
            # Test real native PowerShell handling of both UTF-8 signature and Windows newlines.
            raw=namefile.read_bytes()
            namefile.write_bytes(b"\xef\xbb\xbf"+raw.replace(b"\n",b"\r\n"))
            old=copy/"support/frozen_xml"/namefile.name
            out=copy/("roundtrip_"+namefile.name)
            run_script(copy,namefile.name,out,0)
            if out.read_bytes()!=old.read_bytes():raise ValueError("Archive changed: "+namefile.name)
            runtime.append(namefile.name)
        if cid=="05":
            doc=stage.bridge.tree(raw); special,water=stage.bridge.nodes(doc)
            water.find(stage.bridge.MODEL).set("value","2")
            namefile.write_bytes(stage.bridge.emit(doc))
            reject=copy/"should_not_be_written.xml"
            run_script(copy,namefile.name,reject,1,"cannot represent this HydroMechModel")
            water.find(stage.bridge.MODEL).set("value","0")
            special.find("externalload").set("not_supported","1")
            namefile.write_bytes(stage.bridge.emit(doc))
            run_script(copy,namefile.name,reject,1,"Unrepresentable attribute")
            if reject.exists():raise ValueError("Rejected variant wrote a solver input")
    root=WORK/"04";live.populate(cases["04"],root,OVERLAY)
    p3="CaseCryer_TPI_P3_nu030_peak_r1"
    path=root/(p3+"_Def.xml")
    path.write_bytes(b"\xef\xbb\xbf"+path.read_bytes().replace(b"\n",b"\r\n"))
    text=live.call("x"+p3+"_win64_GPU.bat",root,WORK/"p3_CRLFBOM.log",0)
    if "passed preflight" not in text:raise ValueError("Genuine P3 BAT failed")
    originals={cid:{} for cid in ("01","05","08")}
    for cid,paths in (("01",list(cases["01"].glob("x*FreshPR*.bat"))),("05",list(cases["05"].glob("x*release*.bat"))),
                      ("08",list(cases["08"].glob("support/run_lian_collapse_shared_r[3-6]_win64.bat")))):
        for src in paths:originals[cid][src.name]=references_python(src.read_bytes())
    assert originals["01"] and all(originals["01"].values()) and originals["05"] and not any(originals["05"].values())
    assert len(originals["08"])==4 and all(originals["08"].values()) and len(archive_audits)==9
    report=dict(restricted_child_environment=dict(path="Windows system directories only",python="absent",where_python=None),
                original_root_launchers=originals,actual_original_portables=archive_audits,
                raw_legacy_bytes_verified_by_windows_runtime=runtime,
                C04_P3_real_BAT_with_CRLF_BOM=True,C05_unsupported_model_and_attribute_rejected_before_file_creation=True,
                no_python_full_count=9, no_python_preprocessing_total=10,solver_launches=0)
    (V/"hydro_frozen_windows_review_r2.json").write_text(json.dumps(report,indent=2))
    print("Archived launch paths checked:",len(archive_audits),"actual legacy byte roundtrips:",len(runtime),"real P3 check-only: passed")


if __name__=="__main__":
    main()

