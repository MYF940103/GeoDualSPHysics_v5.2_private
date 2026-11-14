"""Build only one private fixed-state entry +86 original CPU objects; never run it."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path
import c08_h18_as03_rhs_r1_build as prior

m,T,L,S=prior.m,prior.T,prior.L,prior.S
TAG="c08_tpi_state_r1"
CPP,NOTE=T/"support"/(TAG+".cpp"),T/"notes"/(TAG+".md")
OUT=T/"outputs"/(TAG+"_build")
BASE,GATE=L/"c08_h18_as03_rhs_r1.build.json",L/"c08_h18_as03_rhs_r1.check.json"
RHS_CPP,FB_CPP=T/"support/c08_h18_as03_rhs_r1.cpp",T/"support/c08_h18_pressure_feedback_r3.cpp"
RUN,NATIVE,REVIEW=(L/q for q in ("c08_h18_as03n255_full3_r1.run.json","c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json"))

def block(raw,begin,end):
    m.need(raw.count(begin)==raw.count(end)==1,"Unique frozen fragment anchors differ")
    a,b=raw.index(begin),raw.index(end);m.need(a<b,"Fragment order differs");return raw[a:b]

def fragments():
    raw,feedback=RHS_CPP.read_bytes(),FB_CPP.read_bytes()
    changes=[(b'class Probe:public JSphCpuSingle{',b'class Probe:public JSphCpuSingle{\nprotected:'),
        (b'JAppInfo AppInfo("C08H18As03Rhs","r1","14-11-2026");',b'JAppInfo AppInfo("C08TpiStateR1","r1","14-11-2026");'),
        (b'struct Sums{double lp=0,da=0,lpabs=0,daabs=0;',b'struct Sums{double sumw=0,lp=0,da=0,lpabs=0,daabs=0;'),
        (b'double dj){lp+=w*dp;',b'double dj){sumw+=w;lp+=w*dp;')]
    shared=raw
    for old,new in changes:
        m.need(shared.count(old)==1,"Diagnostic-only Sums/access transform differs")
        shared=shared.replace(old,new,1)
    inverse=shared
    for old,new in reversed(changes):
        m.need(inverse.count(new)==1,"Inverse transform ambiguous");inverse=inverse.replace(new,old,1)
    m.need(inverse==raw,"Original loader/Assemble numerical body changed beyond independent sumw")
    generated={"shared.inc":shared,
        "setup.inc":block(raw,b'    AppName=AppInfo.GetFullName();',b'    std::ofstream soil('),
        "rhs_literal.inc":block(raw,b'        // Literal original raw-FS source operation order,',b'        const auto H=z.gp+ai*rho;'),
        "reference.inc":block(feedback,b'static std::vector<std::string> Csv(',b'static std::vector<int> ReadPhase(')}
    return generated,dict(original_rhs=m.stat(RHS_CPP),reference_source=m.stat(FB_CPP),
        transforms=[dict(before=a.decode(),after=b.decode(),count=1) for a,b in changes],inverse_byte_equal=True,
        original_LP_gradient_chain_source_order_unchanged=True,new_sumw_independent_diagnostic=True,
        original_actual_force_and_restore_used=True,parts=[38,76],max_force_calls=4,physical_steps=0)

def bound_file(receipt,path):
    return m.bind(next(q for q in receipt["files"] if Path(q["path"]).resolve()==path.resolve()))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--execution-authorized",action="store_true")
    m.need(parser.parse_args().execution_authorized,"Separate root build admission required")
    check=L/(TAG+".build.json");stages=(TAG+".compile",TAG+".link")
    m.need(not OUT.exists() and not check.exists() and all(not (L/(q+s)).exists() for q in stages for s in (".call.json",".log")),"Existing partial/failed/complete build protected")
    before=[];calls=[]
    try:
        base,rhs,run,native,review=map(m.read,(BASE,GATE,RUN,NATIVE,REVIEW))
        m.need(base["passed"] and base["configuration"]=="DebugCPU" and base["consumed_stats_unchanged"]
            and base["original_Single_no_hook"] and base["physical_objects_compiled"]==0 and base["actual_link_objects"]==87
            and base["source"]==m.stat(RHS_CPP),"Original AS03 86-object/source build required")
        actual=m.read(m.bind(rhs["actual_call"])["path"]);done=m.read(m.bind(rhs["completion"])["path"])
        m.need(rhs["passed"] and rhs["consumed_stats_unchanged"] and rhs["component_invocations"]==1 and rhs["physical_steps"]==0
            and actual["actual_Popen_wait_exit"]==actual["actual_Win32_exit"]==0 and done["passed"]
            and done["source_parts"]==[38,76] and done["actual_force_calls"]==2 and done["literal_final_float_bits_matched"]==10000,"Passed exact two-state RHS baseline required")
        m.need(run["passed"] and run["solver_completed"] and run["actual_steps"]==2600000 and run["saved_frames"]==301
            and run["AS_coefficient"]==.3 and run["AS_exponent"]==2.55 and run["geometry_profile"]=="bedroles"
            and not run["keep_bed_overlap"] and run["source_archive"]==base["source_archive"]
            and run["source_capture"]==base["source_capture"],"Actual full301 original AS03/schema2 source closure required")
        m.need(native["passed"] and native["consumed_stats_unchanged"] and native["reader_invocations"]==1
            and review["analysis_complete"] and review["consumed_stats_unchanged"] and review["actual_samples"]==301,"Reviewed full301 native required")
        fbbuild=L/"c08_h18_pressure_feedback_r3.build.json";fb=m.read(fbbuild)
        m.need(fb["passed"] and fb["source"]==m.stat(FB_CPP) and fb["source_archive"]==base["source_archive"],"Frozen passed reference-parser source required")
        generated,proof=fragments()
        cpath,lpath=L/"c08_h18_as03_rhs_r1.compile.call.json",L/"c08_h18_as03_rhs_r1.link.call.json"
        c,link=map(m.read,(cpath,lpath))
        m.need(c["actual_Popen_wait_exit"]==c["actual_Win32_exit"]==link["actual_Popen_wait_exit"]==link["actual_Win32_exit"]==0
            and c["ownership_failure"] is link["ownership_failure"] is None,"Actual original CL/link recipes required")
        objects=[m.bind(q) for q in base["retained_physical_objects"]];headers=[m.bind(q) for q in base["archived_headers"]];runtime=[m.bind(q) for q in base["runtime"]]
        m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,"Original 86 objects/160 headers/7 runtime required")
        before=[m.stat(q) for q in (Path(__file__),CPP,NOTE,RHS_CPP,FB_CPP,Path(prior.__file__),BASE,GATE,RUN,NATIVE,REVIEW,fbbuild,cpath,lpath)]+objects+headers+runtime
        before += [m.bind(base[k]) for k in ("source_build","source_capture","source_archive","original_object_list")]
        before += [m.bind(rhs[k]) for k in ("actual_call","completion","build")]
        before.append(bound_file(rhs,T/"outputs/c08_h18_as03_rhs_r1/soil_rhs.csv"))
        for key in ("program","source_pre_file","input_xml","actual_call","planned_steps","native_profile"):
            before.append(m.bind(run[key]))
        nr=T/"outputs/c08_h18_as03n255_full3_r1/native_r1"
        for leaf in ("typed22.bin","typed22_layout.csv","clocks.csv"):
            before.append(m.bind(next(q for q in review["consumed"] if Path(q["path"]).resolve()==(nr/leaf).resolve())))
        oldroot=Path(base["program"]["path"]).parent
        objlist=m.read(m.bind(base["original_object_list"])["path"]);liblog=m.bind(objlist["resolved_library_tlog"]);before.append(liblog)
        libs=[Path(q.strip('"')).resolve() for q in Path(liblog["path"]).read_text(encoding="utf-16").splitlines() if not q.startswith("^") and q.lower().endswith(".lib")]
        before += [m.stat(q) for q in libs]
        ca=[str(CPP) if q==str(RHS_CPP) else q if q.lower().startswith("/i") else q.replace(str(oldroot),str(OUT)) for q in c["arguments"]]
        exe=OUT/"C08TpiStateR1.exe";la=[q.replace(str(oldroot),str(OUT)).replace(Path(base["program"]["path"]).name,exe.name) for q in link["arguments"]]
        roots=[Path(q[2:]).resolve() for q in ca if q.startswith("/I")];final=[Path(q).resolve() for q in la if q.lower().endswith(".obj")]
        m.need(len(roots)==1 and sum(q==str(CPP) for q in ca)==1 and all(q in ca for q in ("/Od","/MTd","/RTC1","/fp:precise","/openmp","/std:c++17")),"Original compiler/header ABI required")
        m.need(len(final)==len(set(final))==87 and set(final)=={Path(q["path"]).resolve() for q in objects}|{(OUT/"entry.obj").resolve()},"Only1 new entry plus86 original physical objects allowed")
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode==0,"Original MSVC environment setup failed")
        env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v) for k,v in (q.split("=",1) for q in setup.stdout.decode("mbcs").splitlines() if "=" in q and not q.startswith("=")))
        m.need(env["VCTOOLSVERSION"]=="14.36.32532" and libs,"Matching compiler/library ABI required")
        env.pop("CL",None);env.pop("_CL_",None);env["LIB"]=";".join(dict.fromkeys(str(q.parent) for q in libs))
        before += [m.stat(c["program"]),m.stat(link["program"])];m.verify(before);OUT.mkdir();includes=[]
        for name,content in generated.items():
            dest=OUT/name
            with dest.open("xb") as f:f.write(content)
            includes.append(m.stat(dest))
        before += includes;calls.append(m.invoke(stages[0],[c["program"],*ca],S/"VS",env))
        deps=m.read(OUT/"dependencies.json")["Data"];inc={Path(q).resolve() for q in deps["Includes"]};hr=roots[0];names={Path(q["path"]).name.lower() for q in headers}
        m.need(Path(deps["Source"]).resolve()==CPP.resolve() and all(Path(q["path"]).resolve() in inc for q in includes)
            and all((hr/q).resolve() in inc for q in ("JSph.h","JSphCpu.h","JSphCpuSingle.h","FunSphKernel.h"))
            and all(q.is_relative_to(hr) for q in inc if q.name.lower() in names) and all(not q.is_relative_to((S/"source").resolve()) for q in inc),"Actual frozen includes missing or public-header leak")
        calls.append(m.invoke(stages[1],[link["program"],*la],S/"VS",env));copied=[]
        for entry in runtime:
            dest=OUT/Path(entry["path"]).name;shutil.copy2(entry["path"],dest);m.need(dest.read_bytes()==Path(entry["path"]).read_bytes(),"Frozen runtime copy differs");copied.append(m.stat(dest))
        m.verify(before)
        m.save(check,dict(stage=TAG+".build",passed=True,configuration="DebugCPU",program=m.stat(exe),source=m.stat(CPP),note=m.stat(NOTE),
            source_build=base["source_build"],source_capture=base["source_capture"],source_archive=base["source_archive"],original_object_list=base["original_object_list"],
            retained_physical_objects=objects,archived_headers=headers,runtime=copied,generated_includes=includes,entry_derivation=proof,dependencies=m.stat(OUT/"dependencies.json"),
            actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=0,original_Single_no_hook=True,source_RHS=m.stat(GATE),source_full_run=m.stat(RUN),source_native=m.stat(NATIVE),source_review=m.stat(REVIEW),
            allowed_parts=[38,76],component_max_actual_force_calls=4,conditional_cold_row_only=True,S_LP_not_full_operator_diagonal=True,calls=calls,consumed=before,consumed_stats_unchanged=True,
            compile_invocations=1,link_invocations=1,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,public_source_changed=False,no_automatic_component=True,physical_acceptance=False))
    except Exception as error:
        if not check.exists():m.save(check,dict(stage=TAG+".build",passed=False,first_failure=str(error),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=="__main__":main()
