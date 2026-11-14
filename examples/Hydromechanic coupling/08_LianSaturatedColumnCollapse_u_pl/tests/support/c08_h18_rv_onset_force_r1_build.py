"""Build only the closed ten-state RV onset CPU entry; never execute it."""
import argparse,csv,os,shutil,subprocess,zipfile
from pathlib import Path
import c08_h18_rvisc_force_r1_build as old
m,T,L,S=old.m,old.T,old.L,old.S
TAG="c08_h18_rv_onset_force_r1";CPP=T/"support"/(TAG+".cpp");NOTE=T/"notes"/(TAG+".md");OUT=T/"outputs"/(TAG+"_build")
BASE=L/"c08_h18_rvisc_force_r1.build.json"
LOC=L/"c08_h18_rv_localization_review_r1.check.json"
SELECT=T/"configs"/(TAG+".selection.csv")
CATALOG=T/"figures/c08_h18_rv_localization_review_r1_representative_selection.csv"
PARTS=(40,42,43,76,90);STEPS=(2080001,2084001,2086001,2152001,2180000)

def table(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def replace_once(text,a,b):
    m.need(text.count(a)==1,"Nonunique mechanical shared91 transformation: "+a);return text.replace(a,b,1)
def fragments(base):
    original={Path(q["path"]).name:Path(m.bind(q)["path"]) for q in base["generated_includes"]}
    m.need(set(original)=={"shared.inc","setup.inc","rhs_literal.inc","interior_mask.inc","rvisc_math.inc","rvisc_members.inc"},"Original six frozen fragments differ")
    raw=original["shared.inc"].read_text(encoding="utf-8");marker="public:\n  void Execute(";m.need(raw.count(marker)==1,"Original protected Probe prefix boundary differs")
    shared=raw[:raw.index(marker)]+"};\n"
    changes=[('JAppInfo AppInfo("C08H18RviscForce","r1","14-11-2026");','JAppInfo AppInfo("C08H18RvOnsetForce","r1","15-11-2026");'),
      ('Soil=5000,Samples=301;','Soil=5000,Samples=91;'),
      ('Parts[2]={38,76},Steps[2]={2076001,2152001};','Parts[5]={40,42,43,76,90},Steps[5]={2080001,2084001,2086001,2152001,2180000};'),
      ('unsigned part,completed;double time;','unsigned part,completed;double time;std::string raw_clock;'),
      ('Need(bool(std::getline(clocks,line)),"Missing native clocks");','Need(bool(std::getline(clocks,line))&&line=="part,file,time_s,tau_from_actual_release_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,native_IDs,phase","Original complete11-column native clock schema required");'),
      ('time=std::stod(c[2]);found=true;','time=std::stod(c[2]);raw_clock=line;Need(std::stoul(c[5])==completed-1&&std::stod(c[6])==.000005&&Finite(std::stod(c[7]))&&std::stod(c[7])<=1e-14&&std::stoul(c[8])==0&&std::stoul(c[9])==Total&&std::stoul(c[10])==1,"Actual selected saved/signed/native clock policy differs");found=true;')]
    for a,b in changes:shared=replace_once(shared,a,b)
    shared=shared.replace("full301","closed91")
    with zipfile.ZipFile(m.bind(base["source_archive"])["path"]) as z:cpu=z.read("src/source/JSphCpu.cpp").decode("utf-8-sig")
    start="static void ComputeSymmetricEigen3D(";end="static tsymatrix3f ComputeBuiArtificialStress("
    m.need(cpu.count(start)==cpu.count(end)==1,"Original diagnostic spectrum anchors differ")
    eigen=cpu[cpu.index(start):cpu.index(end)];eigen=replace_once(eigen,"ComputeSymmetricEigen3D","DiagnosticEigen3D")
    out={"shared91.inc":shared.encode("utf-8"),"eigen.inc":eigen.encode("utf-8")}
    for k in ("setup.inc","rhs_literal.inc","interior_mask.inc","rvisc_math.inc"):out[k]=original[k].read_bytes()
    text=CPP.read_text(encoding="utf-8");m.need(all(text.count("../outputs/"+TAG+"_build/"+k)==1 for k in out),"All six current fragments must be actually included once")
    return out,dict(original_fragments=[m.stat(q) for q in original.values()],shared_protected_prefix_only=True,shared91_mechanical_replacements=changes,
      shared_unused_ancestor_Execute_and_main_removed=True,setup_and_literal_and_math_exact=True,original_eigen_diagnostic_only=True,
      CPUcell_graph_in_new_entry=True,no_allpairs_graph_scan=True,selected_parts=list(PARTS),actual_force_calls=10,actual_Darcy_calls=30,
      zero_change_CPU_Darcy_bits_required=50000,external_GPU_RHS_bit_rows=0,physical_steps=0,material_return_calls=0)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("--execution-authorized",action="store_true");m.need(a.parse_args().execution_authorized,"Root must full-read and separately admit this build only")
    check=L/(TAG+".build.json");stages=(TAG+".compile",TAG+".link");m.need(not OUT.exists() and not check.exists() and all(not (L/(q+s)).exists() for q in stages for s in (".call.json",".log")),"Prior output/partial/build protected");before=[];calls=[]
    try:
      base=m.read(BASE);m.need(base["passed"] and base["configuration"]=="DebugCPU" and base["consumed_stats_unchanged"] and base["original_Single_no_hook"] and base["actual_link_objects"]==87 and base["physical_objects_compiled"]==0,"Original passed86-object source closure required")
      loc=m.read(LOC);m.need(loc["passed"] and loc["consumed_stats_unchanged"],"Passed localization and immutable source data required")
      m.need(Path(m.bind(loc["selection"])["path"]).resolve()==CATALOG.resolve(),"Actual localization selection binding differs")
      selected=table(SELECT);catalog=table(CATALOG);m.need(selected and list(selected[0])==["case","part","completed_step","time_s","id_i","id_j","selection_rule"],"Exact root-unique seven-column selection required")
      allowed={(min(int(q["id_i"]),int(q["id_j"])),max(int(q["id_i"]),int(q["id_j"])),q["source_case"]+":"+q["selection_rule"]) for q in catalog};m.need(0<len(allowed)<=8,"Closed reviewed representative union differs")
      keys=set();coverage=set()
      for q in selected:
        p=int(q["part"]);i,j=sorted((int(q["id_i"]),int(q["id_j"])));key=(q["case"],p,i,j)
        m.need(q["case"] in ("original","rv") and p in PARTS and int(q["completed_step"])==STEPS[PARTS.index(p)] and (i,j,q["selection_rule"]) in allowed and key not in keys,"Root selection outside actual aliases/states/representatives");keys.add(key);coverage.add((q["case"],p))
      m.need(coverage=={(c,p)for c in ("original","rv")for p in PARTS} and len(selected)<=80,"All ten closed states required, no generalized selection")
      pairset={(i,j)for _,_,i,j in keys};m.need(keys=={(c,p,i,j)for c in ("original","rv")for p in PARTS for i,j in pairset},"Each selected material pair must be tracked in both trajectories/all five states")
      reviewpath=L/"c08_h18_rv_window_review_r1.check.json";review=m.read(reviewpath);m.need(review["passed"] and review["analysis_complete"] and review["consumed_stats_unchanged"] and review["actual_matched_native_states"]==91,"Passed91-state same-clock window review required")
      native_receipts=[review["reference_native"],review["native_receipt"]]
      for entry in native_receipts:
        nr=m.read(m.bind(entry)["path"]);m.need(nr["passed"] and nr["consumed_stats_unchanged"],"Both actual native receipts required")
      before=[m.stat(q)for q in (Path(__file__),CPP,NOTE,BASE,LOC,SELECT,CATALOG,reviewpath,Path(old.__file__))]
      before += [m.bind(loc[k])for k in ("catalog","selection")]+[m.bind(q)for q in native_receipts]
      # Reuse existing native review seals, no reader/decode/full binary scan/SHA.
      for directory in (T/"outputs/c08_h18_as03_n255_r1/native_r1",T/"outputs/c08_h18_rv_window_GPU_r2/native_r1"):
        for leaf in ("typed22.bin","typed22_layout.csv","clocks.csv"):
          path=(directory/leaf).resolve();entry=next((q for q in review["consumed"] if Path(q["path"]).resolve()==path),None);m.need(entry is not None,"Window review native input stat missing");before.append(m.bind(entry))
        for leaf in ("completion.json","bedkeep_metadata.json"):before.append(m.stat(directory/leaf))
        layout=table(directory/"typed22_layout.csv");wanted=[("Idp","uint32",1,4),("Posd","float64",3,24),("Vel","float32",3,12),("Sigma_kk","float32",3,12),("Sigma_ij","float32",3,12),("FSNormal","float32",3,12),("HydroMechLoadAce","float32",3,12),("native_Rhop","float32",1,4),("Kplastic","float32",1,4),("PorePress","float32",1,4),("PorePress0","float32",1,4),("ExcessPorePress","float32",1,4),("SigmaState_kk","float64",3,24),("SigmaState_ij","float64",3,24),("FSType","uint32",1,4),("PoroVolumeRatio","float64",1,8),("PoroPorosity","float64",1,8),("PoroThetaLastStage","float64",1,8),("PoroCurrentVolume","float64",1,8),("PoroMixtureDensity","float64",1,8),("PoroHydraulicConductivity","float64",1,8),("PosDiv","float32",1,4)];m.need([(q["array"],q["type"],int(q["components"]),int(q["bytes_per_particle"]))for q in layout]==wanted,"Original exact22 typed field order/dtypes differ")
        clocks=table(directory/"clocks.csv");m.need(len(clocks)==91,"Original91 clocks required")
        alias="rv" if "rv_window" in str(directory) else "original"
        for q in selected:
          if q["case"]==alias:m.need(float(q["time_s"])==float(clocks[int(q["part"])]["time_s"]) and int(q["completed_step"])==int(clocks[int(q["part"])]["completed_step"]),"Root selection actual clock differs")
      generated,proof=fragments(base);before += proof["original_fragments"]
      cpath,lpath=[Path(m.bind(q)["path"])for q in base["calls"]];c,l=m.read(cpath),m.read(lpath);m.need(c["actual_Popen_wait_exit"]==c["actual_Win32_exit"]==l["actual_Popen_wait_exit"]==l["actual_Win32_exit"]==0 and c["ownership_failure"] is l["ownership_failure"] is None,"Actual original CL/link0 recipes required")
      objects=[m.bind(q)for q in base["retained_physical_objects"]];headers=[m.bind(q)for q in base["archived_headers"]];runtime=[m.bind(q)for q in base["runtime"]];m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,"Exactly86 physical objects/160 frozen headers/7runtime required")
      before += objects+headers+runtime+[m.stat(cpath),m.stat(lpath)]+[m.bind(base[k])for k in ("source_build","source_capture","source_archive","original_object_list")]
      inventory=m.read(m.bind(base["original_object_list"])["path"]);tlog=m.bind(inventory["resolved_library_tlog"]);before.append(tlog);libraries=[Path(q.strip('"')).resolve()for q in Path(tlog["path"]).read_text(encoding="utf-16").splitlines()if not q.startswith("^") and q.lower().endswith(".lib")];before += [m.stat(q)for q in libraries]
      oldroot=Path(base["program"]["path"]).parent;oldcpp=Path(base["source"]["path"]);ca=[str(CPP)if q==str(oldcpp)else q if q.lower().startswith("/i")else q.replace(str(oldroot),str(OUT))for q in c["arguments"]];exe=OUT/"C08H18RvOnsetForceR1.exe";la=[q.replace(str(oldroot),str(OUT)).replace(Path(base["program"]["path"]).name,exe.name)for q in l["arguments"]]
      roots=[Path(q[2:]).resolve()for q in ca if q.startswith("/I")];m.need(len(roots)==1 and ca.count(str(CPP))==1 and all(q in ca for q in ("/Od","/MTd","/RTC1","/fp:precise","/openmp","/std:c++17")),"Original CPU/header ABI required");headerroot=roots[0];final=[Path(q).resolve()for q in la if q.lower().endswith(".obj")];m.need(len(final)==len(set(final))==87 and set(final)=={Path(q["path"]).resolve()for q in objects}|{(OUT/"entry.obj").resolve()},"One new entry+86 original objects only")
      setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);m.need(setup.returncode==0,"Original MSVC setup failed");env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v)for k,v in(q.split("=",1)for q in setup.stdout.decode("mbcs").splitlines()if "=" in q and not q.startswith("=")));m.need(env["VCTOOLSVERSION"]=="14.36.32532" and libraries,"Matching original MSVC/library ABI required");env.pop("CL",None);env.pop("_CL_",None);env["LIB"]=";".join(dict.fromkeys(str(q.parent)for q in libraries));before += [m.stat(c["program"]),m.stat(l["program"])];m.verify(before);OUT.mkdir();includes=[]
      for name,content in generated.items():
        path=OUT/name
        with path.open("xb")as f:f.write(content)
        includes.append(m.stat(path))
      before += includes;calls.append(m.invoke(stages[0],[c["program"],*ca],S/"VS",env));deps=m.read(OUT/"dependencies.json")["Data"];actual={Path(q).resolve()for q in deps["Includes"]};names={Path(q["path"]).name.lower()for q in headers}
      m.need(Path(deps["Source"]).resolve()==CPP.resolve() and all(Path(q["path"]).resolve()in actual for q in includes) and all((headerroot/q).resolve()in actual for q in ("JSph.h","JSphCpu.h","JSphCpuSingle.h","FunSphKernel.h")) and all(q.is_relative_to(headerroot)for q in actual if q.name.lower()in names) and all(not q.is_relative_to((S/"source").resolve())for q in actual),"Actual frozen includes/public-header isolation failed")
      calls.append(m.invoke(stages[1],[l["program"],*la],S/"VS",env));copied=[]
      for q in runtime:
        dest=OUT/Path(q["path"]).name;shutil.copy2(q["path"],dest);m.need(dest.read_bytes()==Path(q["path"]).read_bytes(),"Runtime copy differs");copied.append(m.stat(dest))
      m.verify(before);m.save(check,dict(stage=TAG+".build",passed=True,configuration="DebugCPU",program=m.stat(exe),source=m.stat(CPP),note=m.stat(NOTE),source_build=base["source_build"],source_capture=base["source_capture"],source_archive=base["source_archive"],original_object_list=base["original_object_list"],retained_physical_objects=objects,archived_headers=headers,runtime=copied,generated_includes=includes,dependencies=m.stat(OUT/"dependencies.json"),entry_derivation=proof,localization_check=m.stat(LOC),root_selection=m.stat(SELECT),actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=0,original_Single_no_hook=True,calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=1,link_invocations=1,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,public_source_changed=False,canonical_programs_changed=False,physical_acceptance=False))
    except Exception as error:
      if not check.exists():m.save(check,dict(stage=TAG+".build",passed=False,first_failure=str(error),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))
      raise

if __name__=="__main__":main()
