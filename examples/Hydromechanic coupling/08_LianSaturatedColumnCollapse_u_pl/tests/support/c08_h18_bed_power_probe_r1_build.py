"""Build one six-force zero-step power observer; never execute it."""
import argparse,csv,os,shutil,subprocess,zipfile
from pathlib import Path
import c08_h18_rv_radial_candidate_r1_build as old
m,T,L,S=old.m,old.T,old.L,old.S
TAG='c08_h18_bed_power_probe_r1';CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md');OUT=T/'outputs'/(TAG+'_build')
BASE=L/'c08_h18_bed_gradient_probe_r1.build.json';REVIEW=L/'c08_h18_bed_gradient_review_r1.check.json'
PARTS=tuple(range(28,35));STEPS=tuple(2000001+2000*p for p in PARTS)
def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def replace_once(s,a,b):m.need(s.count(a)==1,'Nonunique closed-source transformation: '+a);return s.replace(a,b,1)
def between(s,a,b):
    m.need(s.count(a)==s.count(b)==1,'Original literal source anchors differ');i=s.index(a);j=s.index(b,i);return s[i:j]
def function(s,signature):
    m.need(s.count(signature)==1,'Unique original helper required: '+signature);i=s.index(signature);b=s.index('{',i);depth=1;j=b+1
    while depth and j<len(s):
        depth+=(s[j]=='{')-(s[j]=='}');j+=1
    m.need(depth==0,'Unclosed original helper');return s[i:j]+'\n'
def fragments(base):
    allpaths={Path(e['path']).name:Path(m.bind(e)['path'])for e in base['generated_includes']}
    names={'shared91.inc','setup.inc','gradient_math.inc','gradient_velocity.inc','gradient_volume.inc','gradient_theta.inc'}
    m.need(names<=set(allpaths),'Passed gradient source fragments required');paths={k:allpaths[k]for k in names};out={k:p.read_bytes()for k,p in paths.items()}
    shared=out['shared91.inc'].decode('utf-8');shared=replace_once(shared,'JAppInfo AppInfo("C08H18BedGradientProbe","r1","15-11-2026");','JAppInfo AppInfo("C08H18BedPowerProbe","r1","15-11-2026");');out['shared91.inc']=shared.encode('utf-8')
    archive=m.bind(base['source_archive'])
    with zipfile.ZipFile(archive['path'])as z:cpu=z.read('src/source/JSphCpu.cpp').decode('utf-8').replace('\r\n','\n')
    out['momentum_literal.inc']=between(cpu,'              const double coeff=porovol2/pororhot1;','            }\n            else{\n            const float prsxx').encode('utf-8')
    text=CPP.read_text(encoding='utf-8');m.need(all(text.count('../outputs/'+TAG+'_build/'+k)==1 for k in out),'Exactly seven closed include references required')
    m.need(text.count('Interaction_Forces(INTERSTEP_SymCorrector)')==1 and 'ComputeDynamicPorePressureRateCpu();'not in text and 'CommitRV('not in text and 'MaterialReturn('not in text,'Only the one selected-state original force call site allowed')
    proof=dict(original_fragments=[m.stat(p)for p in paths.values()],original_source_archive=archive,unchanged_numeric_fragments=sorted(names-{'shared91.inc'}),shared_change='AppInfo diagnostic name only; original seven-state restore/sort route retained',momentum_literal_source='JSphCpu.cpp2315-2322',momentum_literal_equations_changed=False,split_method='same literal helper, separately float-accumulated original / p=0 / sigma=0; explicit residual, no mixed-Ace subtraction',trajectory_labels=['original','radial'],restored_parts=list(PARTS),force_parts=[29,30,31],restore_CellDivide_calls=14,sorting_only_states=8,actual_force_calls=6,actual_Darcy_calls=6,external_CPU_control_rows=30000,external_CPU_control_scalar_bits=1740000,physical_steps=0,material_return_calls=0,filter_calls=0,RV_commits=0,GPU_stage_bit_truth=False)
    return out,proof

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');m.need(p.parse_args().execution_authorized,'Independent root build-only admission required')
    check=L/(TAG+'.build.json');stages=(TAG+'.compile',TAG+'.link');m.need(not OUT.exists()and not check.exists()and all(not(L/(q+s)).exists()for q in stages for s in('.call.json','.log')),'Old build/partial protected')
    before=[];calls=[]
    try:
      base=m.read(BASE);m.need(base['passed']and base['configuration']=='DebugCPU'and base['consumed_stats_unchanged']and base['actual_link_objects']==87 and base['physical_objects_compiled']==0 and base['original_Single_no_hook'],'Original86-physical-object closure required')
      review=m.read(REVIEW);m.need(review['passed']and review['analysis_complete']and review['consumed_stats_unchanged']and review['actual_states']==14 and review['actual_soil_rows']==70000 and review['actual_gradient_columns']==87,'Passed complete bed-gradient scientific/control review required')
      before=[m.stat(q)for q in(Path(__file__),CPP,NOTE,BASE,REVIEW,Path(old.__file__))]
      roots=[T/'outputs/c08_h18_as03_n255_r1/native_r1',T/'outputs/c08_h18_rv_radial_window_GPU_r1/native_r1']
      for root in roots:
        for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):
          path=(root/leaf).resolve();matches=[e for e in review['consumed']if Path(e['path']).resolve()==path]
          m.need(matches and all(e==matches[0]for e in matches),'One original native seal required: '+str(path));before.append(m.bind(matches[0]))
        for leaf in('completion.json','bedkeep_metadata.json'):before.append(m.stat(root/leaf))
        layout=table(root/'typed22_layout.csv');m.need(len(layout)==22 and sum(int(q['bytes_per_particle'])for q in layout)==212,'Original complete22 layout required')
        clocks=table(root/'clocks.csv');m.need(len(clocks)==91,'Original complete91 clocks required')
        for part,step in zip(PARTS,STEPS):m.need(int(clocks[part]['part'])==part and int(clocks[part]['completed_step'])==step and int(clocks[part]['saved_step'])==step-1 and float(clocks[part]['dt_s'])==.000005 and float(clocks[part]['signed_dterror_s'])<=1e-14,'Closed actual selected clock differs')
      before.append(m.bind(review['source_component']))
      for leaf in('gradient.csv','soil.csv','completion.json'):
        path=(T/'outputs/c08_h18_bed_gradient_probe_r1'/leaf).resolve();matches=[e for e in review['consumed']if Path(e['path']).resolve()==path]
        m.need(matches and all(e==matches[0]for e in matches),'Original sealed CPU control required: '+str(path));before.append(m.bind(matches[0]))
      generated,proof=fragments(base);before+=proof['original_fragments']
      cpath,lpath=[Path(m.bind(q)["path"])for q in base["calls"]];c,l=m.read(cpath),m.read(lpath);m.need(c["actual_Popen_wait_exit"]==c["actual_Win32_exit"]==l["actual_Popen_wait_exit"]==l["actual_Win32_exit"]==0 and c["ownership_failure"] is l["ownership_failure"] is None,"Actual original CL/link0 recipes required")
      objects=[m.bind(q)for q in base["retained_physical_objects"]];headers=[m.bind(q)for q in base["archived_headers"]];runtime=[m.bind(q)for q in base["runtime"]];m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,"Exactly86 physical objects/160 frozen headers/7runtime required")
      before += objects+headers+runtime+[m.stat(cpath),m.stat(lpath)]+[m.bind(base[k])for k in ("source_build","source_capture","source_archive","original_object_list")]
      inventory=m.read(m.bind(base["original_object_list"])["path"]);tlog=m.bind(inventory["resolved_library_tlog"]);before.append(tlog);libraries=[Path(q.strip('"')).resolve()for q in Path(tlog["path"]).read_text(encoding="utf-16").splitlines()if not q.startswith("^") and q.lower().endswith(".lib")];before += [m.stat(q)for q in libraries]
      oldroot=Path(base["program"]["path"]).parent;oldcpp=Path(base["source"]["path"]);ca=[str(CPP)if q==str(oldcpp)else q if q.lower().startswith("/i")else q.replace(str(oldroot),str(OUT))for q in c["arguments"]];exe=OUT/"C08H18BedPowerProbeR1.exe";la=[q.replace(str(oldroot),str(OUT)).replace(Path(base["program"]["path"]).name,exe.name)for q in l["arguments"]]
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
      m.verify(before);m.save(check,dict(stage=TAG+".build",passed=True,configuration="DebugCPU",program=m.stat(exe),source=m.stat(CPP),note=m.stat(NOTE),source_build=base["source_build"],source_capture=base["source_capture"],source_archive=base["source_archive"],original_object_list=base["original_object_list"],retained_physical_objects=objects,archived_headers=headers,runtime=copied,generated_includes=includes,dependencies=m.stat(OUT/"dependencies.json"),entry_derivation=proof,physical_native_review=m.stat(REVIEW),actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=0,original_Single_no_hook=True,calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=1,link_invocations=1,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,public_source_changed=False,canonical_programs_changed=False,physical_acceptance=False))
    except Exception as e:
      if not check.exists():m.save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))
      raise
if __name__=='__main__':main()
