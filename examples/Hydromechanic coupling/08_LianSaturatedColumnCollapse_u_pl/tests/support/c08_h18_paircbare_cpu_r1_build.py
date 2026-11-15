"""Build one private paired-C/bare CPU component; never execute it."""
import argparse, csv, os, shutil, subprocess, zipfile
from pathlib import Path
import c08_h18_joint_darcy_probe_r1_build as joint
import c08_fs_affine_cpu_r1_build as recipes
m,T,L,S=joint.m,joint.T,joint.L,joint.S
TAG='c08_h18_paircbare_cpu_r1'
LSTAR_CHECK=L/'c08_h18_lstar_cpu_on_r1.check.json'
AUTHOR_BASE=T/'support/c08_h18_lstar_cpu_r1.cpp'
AUTHOR_BUILDER=T/'support/c08_h18_lstar_cpu_r1_build.py'
CPP=T/'support'/(TAG+'.cpp'); NOTE=T/'notes'/(TAG+'.md')
BASE=L/'c08_h18_joint_darcy_probe_r1.build.json'
GATE=L/'c08_h18_joint_darcy_probe_r1.check.json'
OLD_W='          const double w=vol2*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr2+double(Eta2));'
NEW_W='          const double w=vol2*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/rr2;'
PRIVATE_W=NEW_W
ASM_OLD='const double w=v*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr+double(Eta2));'
ASM_NEW='const double w=v*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/rr;'
ASM_BLOCK=ASM_NEW
LEAVES=('manufactured.csv','summary.csv','walls.csv','baseline.csv','restore_route.csv','selected_clocks.csv')

def one(text,a,b):
    m.need(text.count(a)==1,'Unique source anchor required: '+a[:120]);return text.replace(a,b,1)

def fragments(base):
    expected={'shared91.inc','setup.inc','gradient_math.inc','gradient_velocity.inc','gradient_volume.inc','gradient_theta.inc','reference_control.inc','rhs_expression.inc'}
    paths={Path(e['path']).name:Path(m.bind(e)['path'])for e in base['generated_includes']}
    m.need(set(paths)==expected,'Exactly passed eight joint fragments required')
    content={k:p.read_bytes()for k,p in paths.items()};s=content['shared91.inc'].decode('utf-8')
    s=one(s,'JAppInfo AppInfo("C08H18JointDarcyProbe","r1","15-11-2026");','JAppInfo AppInfo("C08H18PairCBareCpu","r1","15-11-2026");')
    old=s;s=one(s,ASM_OLD,ASM_BLOCK);m.need(one(s,ASM_BLOCK,ASM_OLD)==old,'Paired-C/bare Assemble must reverse exactly');content['shared91.inc']=s.encode('utf-8')
    cpp=CPP.read_text(encoding='utf-8')
    m.need(all(cpp.count('#include "'+k+'"')==1 for k in expected),'Eight independent fragments must actually be included once')
    m.need(cpp.count('Interaction_Forces(INTERSTEP_SymCorrector)')==cpp.count('ComputeDynamicPorePressureRateCpu();')==cpp.count('ComputeFreeSurfaceTracking();')==1,'Closed actual API lifecycle differs')
    m.need('controlBits==570000'in cpp and 'F(PorePressRatec[i],r.rate,'not in cpp and 'SameFile'not in cpp and 'pair_C_bare_enabled'in cpp and 'actualRateBits==30000'in cpp,'Visible57 upstream controls/new literal rate bits; no old-rate or OFF-byte claim')
    return content,dict(original_fragments=[m.stat(p)for p in paths.values()],unchanged_numeric_fragments=sorted(expected-{'shared91.inc'}),shared_changes=['AppInfo diagnostic name','same paired-C bare denominator as private physical source'],original_route_14=True,physical_steps=0)

def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))

def dependencies(path,source,headerroot,headers,generated):
    data=m.read(path)['Data'];actual={Path(q).resolve()for q in data['Includes']};names={Path(q['path']).name.lower()for q in headers}
    m.need(Path(data['Source']).resolve()==source.resolve(),'Actual CL dependency source differs')
    m.need(all(Path(q['path']).resolve()in actual for q in generated),'Actual entry omitted a private fragment')
    m.need(all(q.is_relative_to(headerroot)for q in actual if q.name.lower()in names)and all(not q.is_relative_to((S/'source').resolve())for q in actual),'Frozen header ABI/public-header isolation failed')
    for leaf in('JSph.h','JSphCpu.h','FunSphKernel.h'):
        m.need((headerroot/leaf).resolve()in actual,'Missing authoritative frozen header: '+leaf)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();m.need(a.execution_authorized,'Independent root build-only admission required')
    mode='pair_C_bare';tag=TAG;out=T/'outputs'/(tag+'_build');check=L/(tag+'.build.json');stages=(tag+'.physical_compile',tag+'.entry_compile',tag+'.link')
    m.need(not out.exists()and not check.exists()and all(not(L/(q+s)).exists()for q in stages for s in('.call.json','.log')),'Old successful/failed/partial build protected')
    before=[];calls=[]
    try:
        base=m.read(BASE);gate=m.read(GATE);adopted=m.read(LSTAR_CHECK)
        m.need(adopted['passed']and adopted['consumed_stats_unchanged']and adopted['upstream_scalar_bits']==570000 and adopted['actual_rate_float_bits']==30000 and adopted['physical_steps']==0 and adopted['solver_invocations']==0,'Passed actual receiver-C/bare implementation fixture required')
        m.need(base['passed']and base['configuration']=='DebugCPU'and base['consumed_stats_unchanged']and base['actual_link_objects']==87 and base['physical_objects_compiled']==0 and base['original_Single_no_hook'],'Passed original joint object closure required')
        m.need(gate['passed']and gate['consumed_stats_unchanged']and gate['physical_steps']==0 and gate['material_return_calls']==0 and gate['filter_calls']==0,'Original sealed joint implementation check required')
        m.need(m.bind(gate['build'])==m.stat(BASE),'Original joint check/build binding differs')
        before=[m.stat(q)for q in(Path(__file__),CPP,NOTE,BASE,GATE,LSTAR_CHECK,AUTHOR_BASE,AUTHOR_BUILDER,Path(joint.__file__),Path(recipes.__file__))]
        for key in('completion','actual_call'):before.append(m.bind(gate[key]));before.append(m.bind(adopted[key]))
        before.append(m.bind(adopted['build']))
        for leaf in LEAVES:
            matches=[q for q in gate['files']if Path(q['path']).name==leaf];m.need(len(matches)==1,'One original sealed physical CSV required: '+leaf);before.append(m.bind(matches[0]))
        comp=m.read(gate['completion']['path']);m.need(comp['passed']and comp['manufactured_rows']==60000 and comp['actual_rate_float_bit_rows']==30000 and comp['external_CPU_baseline_scalar_bits']==580000 and comp['total_original_Darcy_API_calls']==8,'Complete original actual/literal joint coverage required')
        original_call=m.read(gate['actual_call']['path']);m.need(original_call['actual_Popen_wait_exit']==original_call['actual_Win32_exit']==0 and original_call['ownership_failure']is None,'Actual original joint process exit required')
        fragments_out,proof=fragments(base);before+=proof['original_fragments']
        objects=[m.bind(q)for q in base['retained_physical_objects']];headers=[m.bind(q)for q in base['archived_headers']];runtime=[m.bind(q)for q in base['runtime']]
        m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,'86 original physical/160 headers/7 runtime closure required')
        cpu=[q for q in objects if Path(q['path']).name.lower()=='jsphcpu.obj'];m.need(len(cpu)==1,'Exactly one original JSphCpu object required');retained=[q for q in objects if q!=cpu[0]];m.need(len(retained)==85,'Only original JSphCpu may be replaced')
        before+=objects+headers+runtime+[m.bind(base[k])for k in('source_build','source_capture','source_archive','original_object_list')]
        restored=m.read(base['source_build']['path']);m.need(restored['passed']and restored['restored_original_source']and restored['configuration']=='DebugCPU'and restored['actual_link_objects']==87,'Current restored schema2 CPU source required')
        inventory=m.read(base['original_object_list']['path']);ct=m.bind(inventory['authoritative_CL_tlog']);lt=m.bind(inventory['authoritative_LINK_tlog']);rt=m.bind(inventory['resolved_library_tlog']);before += [ct,lt,rt]
        cpu_blocks=[q for q in recipes.blocks(Path(ct['path']))if len(q[0])==1 and Path(q[0][0]).name.lower()=='jsphcpu.cpp'];m.need(len(cpu_blocks)==1,'Unique actual authoritative JSphCpu CL recipe required')
        physargs=recipes.arguments(' '.join(cpu_blocks[0][1]))
        cpath,lpath=[Path(m.bind(q)['path'])for q in base['calls']];c,l=m.read(cpath),m.read(lpath);before += [m.stat(cpath),m.stat(lpath)]
        m.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==l['actual_Popen_wait_exit']==l['actual_Win32_exit']==0 and c['ownership_failure']is l['ownership_failure']is None,'Actual joint entry CL/link recipes required')
        roots=[Path(q[2:]).resolve()for q in c['arguments']if q.startswith('/I')];m.need(len(roots)==1,'One archived160 header root required');headerroot=roots[0]
        m.need(all(Path(q['path']).resolve().is_relative_to(headerroot)for q in headers),'All160 headers must belong to the one frozen root')
        archive=Path(base['source_archive']['path'])
        with zipfile.ZipFile(archive)as z:
            raw=z.read('src/source/JSphCpu.cpp')
            for q in headers:
                path=Path(q['path']);member='src/source/'+path.relative_to(headerroot).as_posix();m.need(z.read(member)==path.read_bytes(),'Archived header bytes differ from full schema2 capture: '+member)
        m.need(NEW_W==OLD_W.replace('/(rr2+double(Eta2));','/rr2;')and ASM_NEW==ASM_OLD.replace('/(rr+double(Eta2));','/rr;'),'Only Eta denominator may change; pair-C numerator preserved')
        text=raw.decode('utf-8');private=one(text,OLD_W,PRIVATE_W)
        m.need(one(private,PRIVATE_W,OLD_W).encode('utf-8')==raw,'Private physical source must reverse byte-for-byte to original full archive')
        m.need(text.count(OLD_W)==1 and text.count('lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);')==1,'Only exact source LP+Lx weight anchor may change')
        for rootsource in(T/'outputs/c08_h18_as03_n255_r1/native_r1',T/'outputs/c08_h18_rv_radial_window_GPU_r1/native_r1'):
            for leaf in('typed22.bin','typed22_layout.csv','clocks.csv','completion.json','bedkeep_metadata.json'):
                path=(rootsource/leaf).resolve();matches=[q for q in base['consumed']if Path(q['path']).resolve()==path];m.need(matches and all(q==matches[0]for q in matches),'Passed native dependency absent from original build: '+str(path));before.append(m.bind(matches[0]))
            layout=table(rootsource/'typed22_layout.csv');clocks=table(rootsource/'clocks.csv');m.need(len(layout)==22 and sum(int(q['bytes_per_particle'])for q in layout)==212 and len(clocks)==91,'Unchanged complete native22/91 required')
        libraries=[Path(q.strip('"')).resolve()for q in Path(rt['path']).read_text(encoding='utf-16').splitlines()if not q.startswith('^')and q.lower().endswith('.lib')];m.need(libraries,'Exact original resolved libraries required');before += [m.stat(q)for q in libraries]
        physical=out/'JSphCpu.cpp';newobj=out/'JSphCpu.obj';exe=out/'C08H18PairCBareCpuR1.exe';oldroot=Path(base['program']['path']).parent
        ca=[str(CPP)if q==base['source']['path']else q if q.lower().startswith('/i')else q.replace(str(oldroot),str(out))for q in c['arguments']]
        ca += ['/I'+str(out),'/DC08_H18_PAIR_C_BARE=1']
        src=[i for i,q in enumerate(physargs)if Path(q).name.lower()=='jsphcpu.cpp'];m.need(len(src)==1,'One physical CPU source token required');physargs[src[0]]=str(physical)
        for prefix,target in(('/Fo',newobj),('/Fd',out/'physical_compile.pdb')):
            ix=[i for i,q in enumerate(physargs)if q.lower().startswith(prefix.lower())];m.need(len(ix)==1,'One physical output flag required');physargs[ix[0]]=prefix+str(target)
        physargs += ['/I'+str(headerroot),'/DC08_H18_PAIR_C_BARE=1','/sourceDependencies',str(out/'physical_dependencies.json')]
        for argv in(ca,physargs):m.need(all(q in argv for q in('/Od','/MTd','/RTC1','/fp:precise','/openmp'))and not any('_WITHGPU'in q for q in argv),'Original CPU ABI/FP/OpenMP flags required')
        la=[]
        for q in l['arguments']:
            if q.lower().endswith('.obj')and Path(q).resolve()==Path(cpu[0]['path']).resolve():la.append(str(newobj))
            else:la.append(q.replace(str(oldroot),str(out)).replace(Path(base['program']['path']).name,exe.name))
        linked=[Path(q).resolve()for q in la if q.lower().endswith('.obj')];m.need(len(linked)==len(set(linked))==87 and set(linked)=={Path(q['path']).resolve()for q in retained}|{newobj.resolve(),(out/'entry.obj').resolve()},'Exactly85 retained+new JSphCpu+new entry link required')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);m.need(setup.returncode==0,'Original MSVC setup failed');env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v)for k,v in(q.split('=',1)for q in setup.stdout.decode('mbcs').splitlines()if'='in q and not q.startswith('=')));m.need(env['VCTOOLSVERSION']=='14.36.32532','Matching original MSVC ABI required');env.pop('CL',None);env.pop('_CL_',None);env['LIB']=';'.join(dict.fromkeys(str(q.parent)for q in libraries));before += [m.stat(c['program']),m.stat(l['program'])]
        m.verify(before);out.mkdir();generated=[]
        with physical.open('x',encoding='utf-8',newline='')as f:f.write(private)
        generated.append(m.stat(physical))
        for name,content in fragments_out.items():
            path=out/name
            with path.open('xb')as f:f.write(content)
            generated.append(m.stat(path))
        before+=generated
        calls.append(m.invoke(stages[0],[c['program'],*physargs],S/'VS',env));dependencies(out/'physical_dependencies.json',physical,headerroot,headers,[])
        calls.append(m.invoke(stages[1],[c['program'],*ca],S/'VS',env));dependencies(out/'dependencies.json',CPP,headerroot,headers,generated[1:])
        calls.append(m.invoke(stages[2],[l['program'],*la],S/'VS',env));copied=[]
        for q in runtime:
            dest=out/Path(q['path']).name;shutil.copy2(q['path'],dest);m.need(dest.read_bytes()==Path(q['path']).read_bytes(),'Runtime copy differs');copied.append(m.stat(dest))
        m.verify(before);m.save(check,dict(stage=tag+'.build',passed=True,configuration='DebugCPU',mode=mode,pair_C_bare_enabled=True,receiver_C_bare_enabled=False,old_full_CSV_byte_comparison_performed=False,program=m.stat(exe),source=m.stat(CPP),private_physical_source=m.stat(physical),private_physical_object=m.stat(newobj),note=m.stat(NOTE),source_build=base['source_build'],source_capture=base['source_capture'],source_archive=base['source_archive'],original_object_list=base['original_object_list'],original_JSphCpu_object=cpu[0],retained_physical_objects=retained,archived_headers=headers,runtime=copied,generated_includes=generated[1:],dependencies=[m.stat(out/q)for q in('physical_dependencies.json','dependencies.json')],entry_derivation=proof,original_implementation_check=m.stat(GATE),adopted_Lstar_fixture_check=m.stat(LSTAR_CHECK),entry_authoring_base=m.stat(AUTHOR_BASE),only_pressure_weight_denominator_changed=True,paired_numerator_preserved=True,exact_reversible_private_w_block=True,changed_Darcy_terms=['LP','Lx'],unchanged_Darcy_terms=['Gp','Da','gradJ','chain','FS'],physical_source_from_full_schema2_archive=True,actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=1,retained_original_objects=85,original_Single_no_hook=True,calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=2,link_invocations=1,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,public_source_changed=False,canonical_programs_changed=False,physical_acceptance=False))
    except Exception as e:
        if not check.exists():m.save(check,dict(stage=tag+'.build',passed=False,mode=mode,first_failure=str(e),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()
