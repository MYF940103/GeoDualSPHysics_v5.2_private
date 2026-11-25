"""Build the +2.5-degree private receiver from the validated C08 two-stage GPU executable's inputs."""
import difflib
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess

from c08_m0_coupled_baseline_gpu_r1 import BUILD as ORIGINAL
from c08_m0_gpu_coupled_r1 import CUDA, SRC, T, once


BASE = "a07ea522f4e17eae1363f7a58f39747877c5f98b"
OUT = T / "outputs/c08_psi25_tpi_build_r2"
EXE = OUT / "C08Psi25Tpi.exe"
RUNTIME = ("ChronoEngine.dll", "dsphchrono.dll", "vcomp140.dll", "DsphConfig.xml")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((ORIGINAL / "build.json").read_text())
    complete_program = ORIGINAL / "C08Collapse.exe"
    original = ORIGINAL / "JSph.cpp"
    if digest(original) != receipt["changed"]["JSph"]["changed"] or digest(complete_program) != receipt["exe"]:
        raise ValueError("The frozen receiver source or program changed")
    raw = subprocess.check_output(["git", "show", BASE + ":src/source/JSph.cpp"], cwd=SRC)
    if hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest() != receipt["changed"]["JSph"]["original"]:
        raise ValueError("The header checkout does not match the release's original source")
    lines = (ORIGINAL / "link.rsp").read_text().splitlines()
    objects = [Path(x.strip('"')) for x in lines[1:]]
    if (len(objects) != 113 or objects.count(ORIGINAL / "JSph.obj") != 1
            or ORIGINAL / "JSphGpuSingle.obj" not in objects
            or any(p.stat().st_mtime_ns > complete_program.stat().st_mtime_ns for p in objects)):
        raise ValueError("One or more original linker inputs changed")
    code = original.read_text(encoding="utf-8")
    admitted = once(code, "HydroMechConductivityCk==2. && SoilCte.dlt==0",
                    "HydroMechConductivityCk==2. && SoilCte.dlt==float(TORAD*2.5)\n"
                    "      && SoilCte.psiDecay==.2f && SoilCte.coh==5000.f && SoilCte.coh_r==1000.f && SoilCte.n_coh==5.f")
    admitted = once(admitted, "cfg->NstepsBreak==2000208 || cfg->NstepsBreak==2060200",
                    "cfg->NstepsBreak==2000208 || cfg->NstepsBreak==2060200 || cfg->NstepsBreak==2240200")
    cl, linker = shutil.which("cl.exe"), shutil.which("link.exe")
    if not cl or not linker:
        raise RuntimeError("Open the x64 VS developer shell")
    private = OUT / "JSph.cpp"
    diff = "".join(difflib.unified_diff(code.splitlines(True), admitted.splitlines(True),
                                        fromfile="original/JSph.cpp", tofile="psi25/JSph.cpp"))
    if OUT.exists():
        if (set(x.name for x in OUT.iterdir()) != {"JSph.cpp", "changes.diff"}
                or private.read_text(encoding="utf8") != admitted
                or (OUT / "changes.diff").read_text(encoding="utf8") != diff):
            raise FileExistsError(OUT)
    else:
        OUT.mkdir()
        private.write_text(admitted, encoding="utf8")
        (OUT / "changes.diff").write_text(diff, encoding="utf8")
    # JSph's member layout has changed since this program was linked. Reuse the layout from its commit.
    tree = subprocess.check_output(["git", "ls-tree", "-r", BASE, "src/source"], cwd=SRC.parent)
    entries = []
    for row in tree.decode().splitlines():
        mode, kind, oid, filename = row.split(maxsplit=3)
        if kind == "blob" and Path(filename).suffix.lower() in (".h", ".hpp", ".inl", ".cuh"):
            entries.append((oid, filename))
    query = "".join(oid+"\n" for oid, name in entries).encode("ascii")
    raw = subprocess.check_output(["git","cat-file","--batch"], input=query, cwd=SRC.parent)
    stream = io.BytesIO(raw)
    for oid, filename in entries:
        actual, kind, size = stream.readline().decode().split()
        if actual != oid or kind != "blob":
            raise ValueError("Unexpected header object " + filename)
        target = OUT / filename
        target.parent.mkdir(exist_ok=True, parents=True)
        payload = stream.read(int(size))
        if len(payload) != int(size) or stream.read(1) != b"\n":
            raise ValueError("Incomplete header " + filename)
        target.write_bytes(payload)
    obj = OUT / "JSph.obj"
    inc = OUT / "src/source"
    flags = ["/c", "/nologo", "/W3", "/O2", "/Zi", "/D_WITHGPU", "/DWIN32", "/D_CONSOLE",
             "/D_VC80_UPGRADE=0x0710", "/D_MBCS", "/Gm-", "/EHsc", "/MT", "/GS", "/fp:precise",
             "/Zc:wchar_t", "/Zc:forScope", "/Zc:inline", "/openmp", "/external:W3", "/Gd", "/TP", "/FC"]
    with (OUT / "compile.log").open("xb") as log:
        subprocess.run([cl, *flags, "/I"+str(inc), "/I"+str(CUDA / "include"),
                        "/Fo"+str(obj), "/Fd"+str(OUT/"private.pdb"), str(private)],
                       cwd=SRC / "VS", stdout=log, stderr=subprocess.STDOUT, check=True)
    objects[objects.index(ORIGINAL / "JSph.obj")] = obj
    head = lines[0]
    for key, suffix in (("OUT","exe"),("PDB","pdb"),("LTCGOUT","iobj"),("IMPLIB","lib")):
        head, count = re.subn("/"+key+r':"[^"]+"', lambda _: '/'+key+':"'+str(EXE.with_suffix("."+suffix))+'"', head)
        if count != 1:
            raise ValueError("Unexpected linker parameter "+key)
    rsp = OUT / "link.rsp"
    rsp.write_text(head+"\n"+"\n".join('"'+str(x)+'"' for x in objects), encoding="utf8")
    with (OUT / "link.log").open("xb") as log:
        subprocess.run([linker,"@"+str(rsp)], cwd=SRC / "VS", stdout=log, stderr=subprocess.STDOUT, check=True)
    for file in RUNTIME:
        shutil.copy2(ORIGINAL / file, OUT / file)
    (OUT / "build.json").write_text(json.dumps({"exe":str(EXE), "sha256":digest(EXE),
        "private_source_sha256":digest(private), "original_build":str(ORIGINAL / "build.json"),
        "header_commit":BASE, "unchanged_objects":112, "new_host_objects":1,
        "changed_cuda_objects":0, "caps":[2000208,2060200,2240200], "psi_degrees":2.5,
        "cohesion_Pa":5000, "residual_cohesion_Pa":1000, "cohesion_decay":5, "dilation_decay":.2,
        "stage":"built_pending_runtime", "solver_launched_by_builder":False}, indent=2), encoding="utf8")
    print(EXE)


if __name__ == "__main__":
    main()
