"""Build two private X0 overlays with original VS/MSVC recipes; never run a solver."""
import argparse, ctypes, ctypes.wintypes as wt, os, shutil, subprocess
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T,L=m.T,m.L
S=T.parents[3]/'src'
TAG='c08_tpi_x0_build_r1'
PREP=L/'c08_tpi_x0_r1.prepare.json'
SOURCE=T/'outputs/c08_tpi_x0_r1_build'
BASES={'DebugCPU':('c08_h18_restore_DebugCPU_r1.build.json',Path(os.environ['TEMP'])/'c08_restore_cpu_r1/DebugCPU/int'),
       'ReleaseCPU':('c08_preload_schema2_ReleaseCPU_r1.build.json',Path(os.environ['TEMP'])/'c08_schema2_build_r1/ReleaseCPU/int')}

def argv(text):
    parse=ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes=[wt.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
    parse.restype=ctypes.POINTER(wt.LPWSTR)
    count=ctypes.c_int();p=parse('dummy.exe '+text,ctypes.byref(count))
    m.need(bool(p),'Windows command parsing failed')
    try:return [p[i] for i in range(1,count.value)]
    finally:ctypes.windll.kernel32.LocalFree(p)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('configuration',choices=BASES)
    p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    m.need(a.execution_authorized,'Independent root build admission required')
    tag=TAG+'_'+a.configuration;out=T/'outputs'/tag;check=L/(tag+'.check.json')
    m.need(not out.exists() and not check.exists(),'Existing build, including failure, protected')
    before=[];calls=[]
    try:
        receipt,intdir=BASES[a.configuration];basepath=L/receipt;base=m.read(basepath)
        prep=m.read(PREP);m.need(prep['passed'],'Prepared private overlays required')
        m.need(base['passed'] and base['configuration']==a.configuration and base['consumed_stats_unchanged'],'Original successful VS build required')
        physical=L/'c08_h18_as03_rhs_r1.build.json';closure=m.read(physical)
        m.need(closure['passed'] and closure['source_archive']==base['source_archive'],'Original frozen schema2 closure required')
        headers=[m.bind(q) for q in closure['archived_headers']]
        m.need(len(headers)==160,'Exactly original160 archived headers required')
        headerroot=Path(next(q['path'] for q in headers if Path(q['path']).name=='JSphCpu.h')).parent
        tlog=intdir/'DualSPHysics.tlog';clog=tlog/'CL.command.1.tlog';llog=tlog/'link.command.1.tlog';liblog=tlog/'link.read.1.tlog'
        lines=clog.read_text(encoding='utf-16').splitlines();commands={Path(lines[i][1:]).name.upper():argv(lines[i+1]) for i in range(0,len(lines),2)}
        linklines=llog.read_text(encoding='utf-16').splitlines();linkargs=argv(' '.join(linklines[1:]));objects=[Path(q).resolve() for q in linkargs if q.lower().endswith('.obj')]
        m.need(len(objects)==len(set(objects))==87 and {p.name.lower() for p in objects}>={'main.obj','jsphcpu.obj','jsphcpusingle.obj'},'Original authoritative87-object link required')
        libs=[Path(q.strip('"')).resolve() for q in liblog.read_text(encoding='utf-16').splitlines() if not q.startswith('^') and q.lower().endswith('.lib')]
        sources=[SOURCE/'JSphCpu.cpp',SOURCE/'JSphCpuSingle.cpp',SOURCE/'c08_tpi_x0_r1.h',SOURCE/'source_diff.json']
        runtime=[m.bind(q['destination']) if 'destination' in q else m.bind(q) for q in base['runtime']]
        before=[m.stat(q) for q in [Path(__file__),T/'notes/c08_tpi_x0_build_r1.md',PREP,basepath,physical,clog,llog,liblog,*sources,*objects,*libs]]+headers+runtime
        before += [m.bind(base[q]) for q in ('program','actual_call','source_capture','source_archive')]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode==0,'Original MSVC environment failed')
        env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION']=='14.36.32532' and libs,'Original MSVC/library ABI required')
        env.pop('CL',None);env.pop('_CL_',None);env['LIB']=';'.join(dict.fromkeys(str(q.parent) for q in libs))
        toolroot=Path(env['VCTOOLSINSTALLDIR'])/'bin/Hostx64/x64';cl=toolroot/'cl.exe';link=toolroot/'link.exe';before += [m.stat(cl),m.stat(link)]
        m.verify(before);out.mkdir();newobjects=[];dependency_files=[]
        for leaf in ('JSphCpu.cpp','JSphCpuSingle.cpp'):
            ca=commands[leaf.upper()];m.need(ca[-1].upper().endswith('\\'+leaf.upper()),'Original per-source command differs')
            ca=[q for q in ca[:-1] if not q.lower().startswith(('/fo','/fd'))]
            m.need('/fp:precise' in ca and '/openmp' in ca and ('/MTd' in ca if a.configuration=='DebugCPU' else '/MT' in ca),'Original CPU floating-point/runtime recipe required')
            dep=out/(leaf+'.dependencies.json');obj=out/(Path(leaf).stem+'.obj');newobjects.append(obj)
            ca += ['/std:c++17','/D_HAS_STD_BYTE=0','/I'+str(headerroot),'/Fo'+str(obj),'/Fd'+str(out/(leaf+'.pdb')),'/sourceDependencies',str(dep),str(SOURCE/leaf)]
            calls.append(m.invoke(tag+'.'+Path(leaf).stem,[str(cl),*ca],S/'VS',env))
            data=m.read(dep)['Data'];includes={Path(q).resolve() for q in data['Includes']}
            m.need(Path(data['Source']).resolve()==(SOURCE/leaf).resolve() and (SOURCE/'c08_tpi_x0_r1.h').resolve() in includes,'Private helper/source not compiled')
            m.need(all((headerroot/q).resolve() in includes for q in ('JSph.h','JSphCpu.h')) and all(not q.is_relative_to((S/'source').resolve()) for q in includes),'Public live headers consumed')
            dependency_files.append(m.stat(dep))
        exe=out/('DualSPHysics5.2CPU_win64_debug.exe' if a.configuration=='DebugCPU' else 'DualSPHysics5.2CPU_win64.exe')
        replacements={q.name.lower():q for q in newobjects};la=[]
        for q in linkargs:
            low=q.lower()
            if low.endswith('.obj'):la.append(str(replacements.get(Path(q).name.lower(),Path(q))))
            elif low.startswith('/out:'):la.append('/OUT:'+str(exe))
            elif low.startswith(('/pdb:','/implib:','/ltcgout:')):
                prefix=q.split(':',1)[0];ext={ '/pdb':'.pdb','/implib':'.lib','/ltcgout':'.iobj'}[prefix.lower()];la.append(prefix+':'+str(out/('candidate'+ext)))
            else:la.append(q)
        final=[Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        m.need(len(final)==87 and len(set(final))==87 and len(set(final)&set(objects))==85 and all(q.resolve() in final for q in newobjects),'Exactly two replacements and85 old objects required')
        calls.append(m.invoke(tag+'.link',[str(link),*la],S/'VS',env));copied=[]
        for q in runtime:
            dst=out/Path(q['path']).name;shutil.copy2(q['path'],dst);m.need(dst.read_bytes()==Path(q['path']).read_bytes(),'Runtime byte copy differs');copied.append(m.stat(dst))
        m.verify(before)
        m.save(check,dict(stage=tag,passed=True,configuration=a.configuration,program=m.stat(exe),original_program=base['program'],source_archive=base['source_archive'],source_capture=base['source_capture'],private_source=[m.stat(q) for q in sources],original_CL_tlog=m.stat(clog),original_LINK_tlog=m.stat(llog),actual_link_objects=87,original_objects_retained=85,private_objects=2,header_ABI_changed=False,dependencies=dependency_files,runtime=copied,calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=2,link_invocations=1,solver_invocations=0,public_source_changed=False,canonical_programs_changed=False,SHA_scans=0,physical_acceptance=False))
    except Exception as error:
        if not check.exists():m.save(check,dict(stage=tag,passed=False,first_failure=str(error),calls=calls,consumed=before,partial_outputs_preserved=True,solver_invocations=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()
