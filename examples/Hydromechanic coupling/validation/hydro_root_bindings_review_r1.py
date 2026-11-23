"""Inventory actual root source XML and launch bindings; no solver, build or mutation of case data."""
from collections import Counter
import ctypes
import datetime
import json
import msvcrt
from pathlib import Path
import re
import xml.etree.ElementTree as ET

OUT=Path(__file__).resolve().parent
SUITE=OUT.parent
ARCHIVE=SUITE/"04_CryerProblem_PR/tests/logs/drainage_public_roots_r1.check.json"
SUFFIXES={".obj",".iobj",".ipdb",".pdb",".ilk"}
SYMBOLS=("HydroMechDynamicSeepage","HydroMechTopLoadMode","HydroMechTopLoadQ0","HydroMechTopLoadRampTime",
         "HydroMechDrainage","HydroMechDrainageFixedGrid","HydroMechDrainageStartTime","HydroMechFreeSeepage",
         "HydroMechFreeSurfaceDrainage","HydroMechFreeSurfaceDrainageStartTime")


def lines(path):
    raw=path.read_bytes()
    for enc in ("utf-8-sig","cp932","gb18030"):
        try:return raw.decode(enc).splitlines()
        except UnicodeDecodeError:pass
    return raw.decode("latin1").splitlines()


def rel(path):return path.relative_to(SUITE).as_posix()


def binding(xml, prior):
    tree=ET.parse(xml)
    special=tree.find(".//execution/special")
    if special is None:raise ValueError(str(xml))
    hydro=special.find("hydromechanics")
    if hydro is None:hydro=special.find("soils")
    if hydro is None:raise ValueError(str(xml))
    tags={ch.tag:dict(ch.attrib).get("value") for ch in hydro if ch.tag in SYMBOLS}
    mode=hydro.find("HydroMechModel")
    load=special.find("externalload"); drain=special.find("drainage")
    disp=prior.get(xml.name,{}).get("disposition")
    modern=disp in ("migrated","public implicit default") or xml.name=="CaseCryer_TPI_nu030_1Tv_Def.xml"
    scope="public hydraulic XML" if modern else "keep original XML and runtime"
    if not disp and xml.name!="CaseCryer_TPI_nu030_1Tv_Def.xml":raise ValueError("Unreviewed new root input: "+xml.name)
    return dict(xml=rel(xml),legacy_present=tags,public_schema=modern,disposition=scope,
        model_tag_value=None if mode is None else mode.get("value"),
        externalload=None if load is None else load.attrib,drainage=None if drain is None else drain.attrib,
        prior_evidence=disp or "new public TPI server input after 52-definition drainage audit")


def launch(bat):
    case=bat.parent
    visited=set()
    def walk(path):
        if path in visited:return []
        visited.add(path);body=lines(path);matches=[]
        for i,line in enumerate(body,1):
            s=line.strip()
            if not s or s.lower().startswith(("rem ","::","#")):continue
            if re.search(r'(?i)\b(?:dirbin|solver|gencase|dualsphysics(?:cpu|gpu)?|bin|runtime|case|name)\s*=|DualSPHysics[^ ]*\.exe|\bcall\s|\.ps1\b|\.py\b|exit /b 2',s):
                matches.append([rel(path),i,s])
            for name in re.findall(r'(?i)\b([a-z0-9_]+\.(?:bat|ps1))\b',s):
                candidate=next((p for p in (case/"support"/name,case/name) if p.is_file()),None)
                if candidate is not None and candidate not in visited:matches.extend(walk(candidate))
        return matches
    return dict(bat=rel(bat),invocations=walk(bat))


def storage():
    d=next(SUITE.glob("08_*/tests/outputs"))
    # NTFS allocation. Multiple hard links to one inode count once.
    class FileStandardInfo(ctypes.Structure):
        _fields_=[("AllocationSize",ctypes.c_longlong),("EndOfFile",ctypes.c_longlong),
                  ("NumberOfLinks",ctypes.c_ulong),("DeletePending",ctypes.c_ubyte),("Directory",ctypes.c_ubyte)]
    get=ctypes.WinDLL("kernel32",use_last_error=True).GetFileInformationByHandleEx
    get.argtypes=(ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong)
    get.restype=ctypes.c_int
    seen=set();entries=[]
    for directory in sorted(x for x in d.glob("c08_m0*") if x.is_dir() and ("build" in x.name or x.name=="c08_m0_release_history_r1")):
        files=[];lbytes=abytes=0
        for x in directory.glob("**/*"):
            if not x.is_file() or x.suffix.lower() not in SUFFIXES:continue
            st=x.stat()
            if (st.st_dev,st.st_ino) in seen:continue
            seen.add((st.st_dev,st.st_ino))
            info=FileStandardInfo()
            with x.open("rb") as stream:
                if not get(msvcrt.get_osfhandle(stream.fileno()),1,ctypes.byref(info),ctypes.sizeof(info)):
                    raise ctypes.WinError(ctypes.get_last_error())
            if info.EndOfFile!=st.st_size:raise RuntimeError("Build product size changed: "+str(x))
            alloc=info.AllocationSize
            files.append(dict(name=x.relative_to(directory).as_posix(),logical_B=st.st_size,allocated_B=alloc))
            lbytes+=st.st_size;abytes+=alloc
        entries.append(dict(directory=rel(directory),logical_B=lbytes,allocated_B=abytes,files=files))
    return entries


def main():
    prior=json.loads(ARCHIVE.read_text(encoding="utf-8-sig"))["definitions"]
    by={x["definition"]:x for x in prior}
    inventory=[];launchers=[];post=[]
    for case in sorted(x for x in SUITE.iterdir() if re.match(r"0[1-8]_",x.name) and x.is_dir()):
        inventory.extend(binding(xml,by) for xml in sorted(case.glob("*_Def.xml")))
        launchers.extend(launch(x) for x in sorted(case.glob("*.bat")))
        for x in sorted({*case.joinpath("support").glob("*.py"),*case.joinpath("support").glob("*.ps1")}):
            hits=[]
            for i,line in enumerate(lines(x),1):
                present=[s for s in SYMBOLS if s in line]
                special=[s for s in ("externalload","special/drainage","find('drainage'","find(\"drainage\"","HydroMechModel") if s in line]
                if present or special:hits.append(dict(line=i,keys=present+special))
            if hits:post.append(dict(script=rel(x),source_keys=hits))
    stats=storage()
    payload=dict(recorded=datetime.datetime.now().astimezone().isoformat(),prior_definitions=len(prior),
        current_definitions=len(inventory),current_launchers=len(launchers),current_public=sum(x["public_schema"] for x in inventory),
        legacy_tag_counts=dict(Counter(k for x in inventory for k in x["legacy_present"])),
        cases=inventory,BATs_and_transitive_commands=launchers,support_source_keys=post,current_C08_build_intermediates=stats,
        build_intermediate_logical_B=sum(x["logical_B"] for x in stats),build_intermediate_allocated_B=sum(x["allocated_B"] for x in stats),
        removed_B=0,notes=["Actual allocation for named build intermediates only; retain all until dependencies and formal packaging are complete.",
        "Launch evidence includes explicit path, variable expressions and case wrappers. A script that name-checks an executable is not itself a version test.",
        "Original source inputs and saved generated XML/BI4, packages, PDBs needed for ongoing debugging, source capture and active link inputs remain protected."])
    dst=OUT/"hydro_root_bindings_review_r1.json"
    with dst.open("w",encoding="utf-8") as f:json.dump(payload,f,ensure_ascii=False,indent=2)
    print("roots",len(inventory),"BAT",len(launchers),"public",payload["current_public"],"intermediate",payload["build_intermediate_logical_B"],payload["build_intermediate_allocated_B"])


if __name__=="__main__":main()
