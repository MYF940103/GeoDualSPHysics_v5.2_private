"""Build and run the two-state Cryer-independent C08 component with retained DebugCPU objects."""
import os
from pathlib import Path
import shutil
import subprocess

import c08_h18_wend_matrix_r1 as m

TAG = "c08_tpi_eq47_rounds_r1"
T = m.T
L = m.L


def main():
    old = m.read(L/"c08_tpi_state_r1.build.json")
    assert old["passed"] and m.read(L/"c08_tpi_state_r1.check.json")["passed"]
    old_exe = Path(m.bind(old["program"])["path"])
    build = T/"outputs"/(TAG+"_build")
    output = T/"outputs"/TAG
    src = T/"support"/(TAG+".cpp")
    tool_calls = [m.read(m.bind(item)["path"]) for item in old["calls"]]
    assert not output.exists() and not build.exists() and len(tool_calls)==2
    for dep in old["retained_physical_objects"]+old["runtime"]+old["generated_includes"]:
        m.bind(dep)
    obj_receipt = m.read(m.bind(old["original_object_list"])["path"])
    libfile = Path(m.bind(obj_receipt["resolved_library_tlog"])["path"])
    libs = [Path(q.strip('"')).resolve() for q in libfile.read_text(encoding="utf-16").splitlines()
            if not q.startswith("^") and q.lower().endswith(".lib")]
    setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                           stdout=subprocess.PIPE, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    env = {k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in (q.split("=",1) for q in setup.stdout.decode("mbcs").splitlines()
                                          if "=" in q and not q.startswith("=")))
    assert env["VCTOOLSVERSION"]=="14.36.32532" and libs
    env["LIB"]=";".join(dict.fromkeys(str(p.parent) for p in libs))
    env.pop("CL",None); env.pop("_CL_",None)
    env["OMP_NUM_THREADS"]="1"
    build.mkdir()
    calls=[]
    exe = build/"C08Eq47Rounds.exe"
    for suffix,record in zip(("compile","link"),tool_calls):
        args=[str(src) if a==old["source"]["path"] else a.replace(str(old_exe),str(exe)).replace(str(old_exe.parent),str(build))
              for a in record["arguments"]]
        if suffix=="link":
            objects=[Path(a).resolve() for a in args if a.lower().endswith(".obj")]
            assert len(objects)==87 and set(objects)=={Path(o["path"]).resolve() for o in old["retained_physical_objects"]}|{build/"entry.obj"}
        calls.append(m.invoke(TAG+"."+suffix,[record["program"],*args],T.parents[3]/"src/VS",env))
    for dep in old["runtime"]:
        shutil.copy2(dep["path"],build/Path(dep["path"]).name)
    full=T/"outputs/c08_h18_as03n255_full3_r1"
    seed=full/full.name
    call=m.invoke(TAG+".component",[str(exe),"-cpu","-ompthreads:1","-stable","-svres","-mdbc_freeslip:1",
                                    str(seed),str(output)],T.parent,env)
    calls.append(call)
    for item in calls:
        record=m.read(item["path"])
        assert record["actual_Popen_wait_exit"]==record["actual_Win32_exit"]==0
    m.save(L/(TAG+".run.json"),dict(passed=True,source=m.stat(src),program=m.stat(exe),calls=calls,
          retained_build=m.stat(L/"c08_tpi_state_r1.build.json"),rows=m.stat(output/"rows.csv"),
          physical_steps=0,physical_objects_rebuilt=0))


if __name__=="__main__":
    main()
