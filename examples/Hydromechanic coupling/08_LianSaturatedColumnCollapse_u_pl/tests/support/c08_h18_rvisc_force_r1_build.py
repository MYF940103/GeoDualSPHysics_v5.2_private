"""Build one private fixed-state residual-force entry; never run force or solver."""
import argparse, os, shutil, subprocess, zipfile
from pathlib import Path
import c08_h18_pressure_feedback_r3_build as prior
m,T,L,S=prior.m,prior.T,prior.L,prior.S
TAG='c08_h18_rvisc_force_r1'
CPP,NOTE=T/'support'/(TAG+'.cpp'),T/'notes'/(TAG+'.md')
OUT=T/'outputs'/(TAG+'_build')
BASE,RHS,MODES=prior.BASE,prior.RHS,prior.MODES
RHS_CPP,MODE_CPP=prior.RHS_CPP,prior.MODE_CPP
OLD=T/'support/upl_c08_residual_visc_cpu_r2.cpp'

def block(s,a,b):
    m.need(s.count(a)==s.count(b)==1,'Original exact block anchors differ')
    return s[s.index(a):s.index(b)]

def fragments(archive):
    raw=RHS_CPP.read_bytes();force=MODE_CPP.read_bytes()
    access=b'class Probe:public JSphCpuSingle{';app=b'JAppInfo AppInfo("C08H18As03Rhs","r1","14-11-2026");'
    m.need(raw.count(access)==raw.count(app)==1,'Original RHS access/AppInfo anchors differ')
    newapp=b'JAppInfo AppInfo("C08H18RviscForce","r1","14-11-2026");'
    shared=raw.replace(access,access+b'\nprotected:',1).replace(app,newapp,1)
    m.need(shared.replace(access+b'\nprotected:',access,1).replace(newapp,app,1)==raw,'Unexpected original state/force source edit')
    pieces={'shared.inc':shared,
      'setup.inc':block(raw,b'    AppName=AppInfo.GetFullName();',b'    std::ofstream soil('),
      'rhs_literal.inc':block(raw,b'        // Literal original raw-FS source operation order,',b'        const auto H=z.gp+ai*rho;'),
      'interior_mask.inc':block(force,b'  std::vector<byte> InteriorMask()const{',b'  std::array<unsigned,2> GlobalModes(')}
    old=OLD.read_text(encoding='utf-8');now=CPP.read_text(encoding='utf-8')
    math=block(old,'static constexpr double Alpha=.1;','struct Snapshot{')
    graph=block(old,'  Graph MakeGraph()const{','public:\n  void Apply(){')
    m.need(graph.count('KERNEL_Cubic')==1 and graph.count('Cubic positive-weight graph required')==1,'Original graph kernel replacement differs')
    graph=graph.replace('KERNEL_Cubic','KERNEL_Wendland').replace('Cubic positive-weight graph required','Wendland positive-weight graph required')
    commit=block(old,'const auto byid=Map();std::vector<double> theta(Soil);','  void Manufactured(')
    manufactured=block(old,'  void Manufactured(','  void Execute(')
    members=graph+'public:\n  void Apply(){Need(Acec&&Rsigmac&&CorrMatc&&PoroThetac,\"Candidate requires complete original force scratch\");\n'+commit+manufactured
    pieces['rvisc_math.inc']=math.encode('utf-8');pieces['rvisc_members.inc']=members.encode('utf-8')
    m.need(all(members.count(q)==1 for q in (graph,commit,manufactured)) and all(now.count('../outputs/'+TAG+'_build/'+q)==1 for q in ('rvisc_math.inc','rvisc_members.inc')),'Exact original generated residual fragments/include ownership differs')
    with zipfile.ZipFile(archive['path']) as z:
      cpu=z.read('src/source/JSphCpu.cpp').decode('utf-8-sig')
      wall=z.read('src/source/JSphCpu_mdbc.cpp').decode('utf-8-sig')
    m.need(all(q in cpu for q in ('DynamicConductivitySpeedMax=0.;','if(DynamicPoreWall)ComputeDynamicPoreWallAccelerationCpu();','PorePressRatec[p1]=float(rate);')) and 'Reads finished native acceleration, never stationary-wall velocity or old Ace.' in wall,'Original repeatable Darcy wrapper/source differs')
    return pieces,dict(original_RHS=m.stat(RHS_CPP),original_modes=m.stat(MODE_CPP),original_residual_source=m.stat(OLD),shared_inverse_byte_equal=True,Graph_Fit_Evaluate_Stats_exact=True,MakeGraph_only_kernel_Cubic_to_Wendland=True,original_once_float_commit_and_budgets_exact=True,original_three_manufactured_fields_exact=True,original_LS_rank_gate_no_ridge=True,alpha=.1,new_physical_single_hook=False,repeat_zero_change_Darcy_bits_required=True,declared_force_calls=2,declared_Darcy_calls=6,declared_extra_Darcy_calls=4,physical_steps=0)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');m.need(p.parse_args().execution_authorized,'Root must fully review and admit build; no automatic component')
    check=L/(TAG+'.build.json');stages=(TAG+'.compile',TAG+'.link');m.need(not OUT.exists() and not check.exists() and all(not (L/(q+s)).exists() for q in stages for s in ('.call.json','.log')),'Existing failed/partial/complete build protected');before=[];calls=[]
    try:
      base=m.read(BASE);rhs=m.read(RHS);modes=m.read(MODES);pressurepath=L/'c08_h18_pressure_feedback_r3.check.json';pressure=m.read(pressurepath)
      m.need(base['passed'] and base['configuration']=='DebugCPU' and base['consumed_stats_unchanged'] and base['original_Single_no_hook'] and base['physical_objects_compiled']==0 and base['actual_link_objects']==87,'Original86-object DebugCPU source closure required')
      for receipt in (rhs,modes):
        c=m.read(m.bind(receipt['actual_call'])['path']);done=m.read(m.bind(receipt['completion'])['path']);m.need(receipt['passed'] and receipt['consumed_stats_unchanged'] and receipt['physical_steps']==0 and c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0 and c['ownership_failure'] is None and done['passed'],'Passed original RHS/modes required')
      m.need(pressure['passed'] and pressure['physical_steps']==0,'Passed defined-wall pressure component required')
      generated,proof=fragments(base['source_archive'])
      cpath,lpath=L/'c08_h18_as03_rhs_r1.compile.call.json',L/'c08_h18_as03_rhs_r1.link.call.json';c,l=m.read(cpath),m.read(lpath)
      m.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==l['actual_Popen_wait_exit']==l['actual_Win32_exit']==0 and c['ownership_failure'] is l['ownership_failure'] is None,'Original real compiler/link recipes required')
      objects=[m.bind(q) for q in base['retained_physical_objects']];headers=[m.bind(q) for q in base['archived_headers']];runtime=[m.bind(q) for q in base['runtime']]
      m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,'Exactly86 old physical objects/160 archived headers/7 runtime files required')
      before=[m.stat(q) for q in (Path(__file__),CPP,NOTE,OLD,RHS_CPP,MODE_CPP,Path(prior.__file__),BASE,RHS,MODES,pressurepath,cpath,lpath,T/'notes/upl_c08_rvisc90_decision_r1.md')]+objects+headers+runtime
      before += [m.bind(base[k]) for k in ('source_build','source_capture','source_archive','original_object_list')]
      for receipt in (rhs,modes):before += [m.bind(receipt[k]) for k in ('actual_call','completion','build')]
      rhsfile=(T/'outputs/c08_h18_as03_rhs_r1/soil_rhs.csv').resolve();before.append(m.bind(next(q for q in rhs['files'] if Path(q['path']).resolve()==rhsfile)))
      reviewpath=L/'c08_h18_as03n255_full3_review_r1.check.json';review=m.read(reviewpath);m.need(review['analysis_complete'] and review['consumed_stats_unchanged'] and review['actual_samples']==301,'Complete source301 native review required');before.append(m.stat(reviewpath));native=T/'outputs/c08_h18_as03n255_full3_r1/native_r1'
      for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
        target=(native/leaf).resolve();before.append(m.bind(next(q for q in review['consumed'] if Path(q['path']).resolve()==target)))
      inventory=m.read(m.bind(base['original_object_list'])['path']);tlog=m.bind(inventory['resolved_library_tlog']);before.append(tlog);libraries=[Path(q.strip('"')).resolve() for q in Path(tlog['path']).read_text(encoding='utf-16').splitlines() if not q.startswith('^') and q.lower().endswith('.lib')];before += [m.stat(q) for q in libraries]
      oldroot=Path(base['program']['path']).parent;ca=[str(CPP) if q==str(RHS_CPP) else q if q.lower().startswith('/i') else q.replace(str(oldroot),str(OUT)) for q in c['arguments']];exe=OUT/'C08H18RviscForceR1.exe';la=[q.replace(str(oldroot),str(OUT)).replace(Path(base['program']['path']).name,exe.name) for q in l['arguments']]
      roots=[Path(q[2:]).resolve() for q in ca if q.startswith('/I')];m.need(len(roots)==1 and ca.count(str(CPP))==1 and all(q in ca for q in ('/Od','/MTd','/RTC1','/fp:precise','/openmp','/std:c++17')),'Original CPU/header ABI required');headerroot=roots[0];final=[Path(q).resolve() for q in la if q.lower().endswith('.obj')]
      m.need(len(final)==len(set(final))==87 and set(final)=={Path(q['path']).resolve() for q in objects}|{(OUT/'entry.obj').resolve()},'One new entry+86 old physical objects only')
      setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);m.need(setup.returncode==0,'Original MSVC setup failed');env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')));m.need(env['VCTOOLSVERSION']=='14.36.32532' and libraries,'Matching MSVC/library ABI required');env.pop('CL',None);env.pop('_CL_',None);env['LIB']=';'.join(dict.fromkeys(str(q.parent) for q in libraries));before += [m.stat(c['program']),m.stat(l['program'])];m.verify(before);OUT.mkdir();includes=[]
      for name,content in generated.items():
        dest=OUT/name
        with dest.open('xb') as stream:stream.write(content)
        includes.append(m.stat(dest))
      before += includes;calls.append(m.invoke(stages[0],[c['program'],*ca],S/'VS',env));deps=m.read(OUT/'dependencies.json')['Data'];actual={Path(q).resolve() for q in deps['Includes']};names={Path(q['path']).name.lower() for q in headers}
      m.need(Path(deps['Source']).resolve()==CPP.resolve() and all(Path(q['path']).resolve() in actual for q in includes) and all((headerroot/q).resolve() in actual for q in ('JSph.h','JSphCpu.h','JSphCpuSingle.h','FunSphKernel.h')) and all(q.is_relative_to(headerroot) for q in actual if q.name.lower() in names) and all(not q.is_relative_to((S/'source').resolve()) for q in actual),'Frozen includes or public-header isolation failed')
      calls.append(m.invoke(stages[1],[l['program'],*la],S/'VS',env));copied=[]
      for q in runtime:
        dest=OUT/Path(q['path']).name;shutil.copy2(q['path'],dest);m.need(dest.read_bytes()==Path(q['path']).read_bytes(),'Runtime copy differs');copied.append(m.stat(dest))
      m.verify(before);m.save(check,dict(stage=TAG+'.build',passed=True,configuration='DebugCPU',program=m.stat(exe),source=m.stat(CPP),note=m.stat(NOTE),source_build=base['source_build'],source_capture=base['source_capture'],source_archive=base['source_archive'],original_object_list=base['original_object_list'],retained_physical_objects=objects,archived_headers=headers,runtime=copied,generated_includes=includes,dependencies=m.stat(OUT/'dependencies.json'),entry_derivation=proof,actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=0,original_Single_no_hook=True,calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=1,link_invocations=1,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,public_source_changed=False,canonical_programs_changed=False,physical_acceptance=False))
    except Exception as e:
      if not check.exists():m.save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))
      raise

if __name__=='__main__':main()
