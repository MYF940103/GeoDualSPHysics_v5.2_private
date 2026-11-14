"""Author-only: build one zero-step entry with the existing86 frozen schema2 CPU objects."""
import argparse, os, shutil, subprocess, zipfile
from pathlib import Path
import c08_h18_late_rhs_r1_build as prior

m,T,L,S=prior.m,prior.T,prior.L,prior.S
TAG='c08_h18_work_conjugacy_r2';CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md')
OUT=T/'outputs'/(TAG+'_build');BASE=L/'c08_h18_late_rhs_r1.build.json'
RUN=L/'c08_h18_as03n255_full3_r1.run.json';NATIVE=L/'c08_h18_as03n255_full3_native_r1.check.json';REVIEW=L/'c08_h18_as03n255_full3_review_r1.check.json'


def entry_proof(archive):
    original=T/'support/c08_h18_as03_pair_force_r1.cpp';raw=original.read_bytes();new=CPP.read_bytes()
    head=raw[:raw.index(b'  struct SwitchScope')].replace(b'// Author-only four-state actual-CPU pair force/RHS audit; no time or material update.',b'// Author-only actual-CPU zero-step work-conjugacy audit; no time or material update.',1).replace(b'C08H18As03PairForce',b'C08H18WorkConjugacy',1)
    declarations=b'void GetStrainSpinRateTensor_sym(tfloat3,tfloat3,tfloat3,tsymatrix3f&,tfloat3&);\nvoid GetStressRateTensor_Elastic(tsymatrix3f,tfloat3,tsymatrix3f,const float,const float,tsymatrix3f&);\n'
    head=head.replace(b'class Probe:public JSphCpuSingle{',declarations+b'class Probe:public JSphCpuSingle{',1)
    m.need(new.startswith(head),'Original pair-tool typed22 reader/Restore/Map/Copy/Ledger/Roles/Unchanged must remain literal')
    with zipfile.ZipFile(archive['path']) as z: cpu=z.read('src/source/JSphCpu.cpp').decode('utf-8-sig')
    anchors=('const double coeff=porovol2/pororhot1;','const double pw=double(porepress[p1])+double(porepress[p2]);','const double artmass=porovol2/pororhot1*double(powf(ratio,ArtificialStressExp));','const double pi_visc=(-double(visco)*double(cbar)*double(amubar)/robar)*mass2;','const float volp2=(PorosityFeedback? -float(porovol2): -massp2/velrhop2.w);','if(observeporosity)porosity_thetap1+=divv;','GetStressRateTensor_Elastic(e_tensorp1,w_tensorp1_xy_yz_xz,sigmap1,modulus_K,modulus_G,rsigmap1);')
    m.need(all(cpu.count(q)==1 for q in anchors),'Archived actual raw force/corrected stress/theta source differs')
    return dict(original_entry=m.stat(original),typed22_and_state_lifecycle_exact=True,selected_parts=[38,76,92,300],baseline_force_calls=4,additional_OFF_runs=0,frozen_force_anchors=list(anchors),stress_rate_uses_original_linked_CPU_symbols=True,independent_raw_corrected_stencil_and_virtual_soil_only=True,physical_steps=0,public_source_modified=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args();m.need(args.execution_authorized,'Author-only until root full-read; build admits no component run')
    check=L/(TAG+'.build.json');stages=(TAG+'.compile',TAG+'.link');m.need(not OUT.exists() and not check.exists() and all(not (L/(q+s)).exists() for q in stages for s in ('.call.json','.log')),'Existing complete/partial build protected');before=[];calls=[]
    try:
        base,run,native,review=(m.read(q) for q in (BASE,RUN,NATIVE,REVIEW))
        m.need(base['passed'] and base['configuration']=='DebugCPU' and base['consumed_stats_unchanged'] and base['original_Single_no_hook'] and base['physical_objects_compiled']==0 and base['actual_link_objects']==87,'Passed original schema2/late-RHS86-object closure required')
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged'] and run['actual_exit']==run['actual_Win32_exit']==run['actual_tool_exit']==0 and run['actual_steps']==2600000 and run['saved_frames']==301 and run['AS_coefficient']==.3 and run['AS_exponent']==2.55 and run['geometry_profile']=='bedroles' and not run['keep_bed_overlap'] and run['hdp']==1.8 and run['fixed_dt_s']==5e-6,'Only the completed original AS03 full301 is admitted')
        m.need(run['source_archive']==base['source_archive'] and run['source_capture']==base['source_capture'],'Actual CPU object archive and GPU-program source closure must coincide')
        m.need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1 and review['analysis_complete'] and review['consumed_stats_unchanged'] and review['actual_samples']==301 and review['exact_matched_option_rows']==301 and review['prefix_proof']['compared_records']==90 and review['prefix_proof']['all22_arrays_and_actual_time_bytes_equal'] and not review['physical_acceptance'],'Complete separately reviewed native301 and real90 prefix required')
        derivation=entry_proof(base['source_archive']);root=Path(base['program']['path']).parent
        cpath,lpath=L/'c08_h18_late_rhs_r1.compile.call.json',L/'c08_h18_late_rhs_r1.link.call.json';c,l=m.read(cpath),m.read(lpath)
        m.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==l['actual_Popen_wait_exit']==l['actual_Win32_exit']==0 and c['ownership_failure'] is l['ownership_failure'] is None,'Actual original compiler/link recipes must be successful')
        objects=[m.bind(q) for q in base['retained_physical_objects']];headers=[m.bind(q) for q in base['archived_headers']];runtime=[m.bind(q) for q in base['runtime']]
        m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,'Exact original physical object/header/runtime inventories required')
        headerroot=root/'headers/src/source';rawbase=m.read(m.bind(base['original_object_list'])['path']);library_tlog=m.bind(rawbase['resolved_library_tlog']);libraries=[Path(q.strip('"')).resolve() for q in Path(library_tlog['path']).read_text(encoding='utf-16').splitlines() if not q.startswith('^') and q.lower().endswith('.lib')]
        before=[m.stat(q) for q in (Path(__file__),CPP,NOTE,T/'support/c08_h18_as03_pair_force_r1.cpp',Path(prior.__file__),BASE,RUN,NATIVE,REVIEW,cpath,lpath)]+objects+headers+runtime+[library_tlog]+[m.stat(q) for q in libraries]
        before += [m.bind(base[k]) for k in ('source_build','source_capture','source_archive','dependencies','original_object_list')]+[m.bind(run[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','actual_call','planned_steps','native_profile')]+[m.bind(native[k]) for k in ('actual_call','native_completion','metadata','reader_build')]
        folder=T/'outputs/c08_h18_as03n255_full3_r1/native_r1'
        for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
            target=(folder/leaf).resolve();before.append(m.bind(next(q for q in review['consumed'] if Path(q['path']).resolve()==target)))
        for receipt in (run,native):
            call=m.read(m.bind(receipt['actual_call'])['path']);m.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Actual owned input call failed')
        ca=[str(CPP) if q==str(T/'support/c08_h18_late_rhs_r1.cpp') else q if q.lower().startswith('/i') else q.replace(str(root),str(OUT)) for q in c['arguments']]
        exe=OUT/'C08H18WorkConjugacyR1.exe';la=[q.replace(str(root),str(OUT)).replace(Path(base['program']['path']).name,exe.name) for q in l['arguments']]
        m.need(sum(q==str(CPP) for q in ca)==1 and all(q in ca for q in ('/Od','/MTd','/fp:precise','/openmp','/RTC1','/std:c++17')) and '/I'+str(headerroot) in ca,'Exact frozen headers and original CPU ABI required')
        linked={Path(q).resolve() for q in la if q.lower().endswith('.obj')};m.need(len(linked)==87 and linked=={Path(q['path']).resolve() for q in objects}|{(OUT/'entry.obj').resolve()},'Only new entry plus86 unchanged physical objects allowed')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);m.need(setup.returncode==0,'Original MSVC environment setup failed')
        env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION']=='14.36.32532' and libraries,'Same frozen compiler/library ABI required');env.pop('CL',None);env.pop('_CL_',None);env['LIB']=';'.join(dict.fromkeys(str(q.parent) for q in libraries));before += [m.stat(c['program']),m.stat(l['program'])];m.verify(before)
        OUT.mkdir();calls.append(m.invoke(stages[0],[c['program'],*ca],S/'VS',env));deps=m.read(OUT/'dependencies.json')['Data'];includes={Path(q).resolve() for q in deps['Includes']};names={Path(q['path']).name.lower() for q in headers}
        m.need(Path(deps['Source']).resolve()==CPP.resolve() and all(headerroot/q in includes for q in ('JSph.h','JSphCpu.h','JSphCpuSingle.h','FunSphKernel.h')) and all(q.is_relative_to(headerroot) for q in includes if q.name.lower() in names) and all(not q.is_relative_to(S/'source') for q in includes),'No current public header may leak into the build')
        calls.append(m.invoke(stages[1],[l['program'],*la],S/'VS',env));copied=[]
        for q in runtime:
            dest=OUT/Path(q['path']).name;shutil.copy2(q['path'],dest);m.need(dest.read_bytes()==Path(q['path']).read_bytes(),'Runtime copy differs');copied.append(m.stat(dest))
        m.verify(before);m.save(check,dict(stage=TAG+'.build',passed=True,configuration='DebugCPU',program=m.stat(exe),source=m.stat(CPP),note=m.stat(NOTE),source_build=base['source_build'],source_capture=base['source_capture'],source_archive=base['source_archive'],original_object_list=base['original_object_list'],retained_physical_objects=objects,archived_headers=headers,runtime=copied,dependencies=m.stat(OUT/'dependencies.json'),entry_derivation=derivation,actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=0,original_Single_no_hook=True,source_run=m.stat(RUN),source_native=m.stat(NATIVE),source_review=m.stat(REVIEW),calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=1,link_invocations=1,component_invocations=0,solver_invocations=0,GPU_actions=0,physical_acceptance=False,canonical_programs_changed=False,public_source_changed=False,SHA_scans=0))
    except Exception as error:
        if not check.exists():m.save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,GPU_actions=0,physical_acceptance=False))
        raise


if __name__=='__main__':main()
