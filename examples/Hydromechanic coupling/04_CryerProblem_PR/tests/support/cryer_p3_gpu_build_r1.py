"""Build the private Cryer P3 host upgrade using its own verified Debug/Release VS recipes."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import upl_tpi_cryer_gpu_build_r1 as original
from cryer_p3_gpu_prepare_r1 import T, DST

def stat(p):
    p=Path(p).resolve()
    return dict(path=str(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)

def verify(e):
    if stat(e['path'])!=e:
        raise RuntimeError('Frozen input differs: '+e['path'])
    return Path(e['path'])

def run(argv,cwd,env,log):
    with log.open('xb') as out:
        proc=subprocess.Popen(argv,stdout=out,stderr=subprocess.STDOUT,cwd=cwd,env=env)
        rc=proc.wait()
    if rc: raise RuntimeError(f'{argv[0]} exit {rc}: {log}')
    return dict(argv=argv,pid=proc.pid,returncode=rc,log=stat(log))

def build(config,tag):
    tag='cryer_p3_gpu_'+tag+'_'+config
    folder=T/'outputs'/tag
    folder.mkdir(exist_ok=False)
    receipt=T/'logs'/(tag+'.build.json')
    base=T/'logs'/('upl_tpi_cryer_gpu_'+config+'_r1.build.json')
    b=json.loads(base.read_text(encoding='utf-8-sig'))
    if not b['passed'] or b['object_count']!=111:raise RuntimeError('Unqualified original')
    out=folder/'out';out.mkdir()
    tools=Path(r'D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532\bin\Hostx64\x64')
    old={p.name.casefold():p for p in (verify(e) for e in b['objects'])}
    cl_path=verify(b['actual_tlogs']['CL.command.1.tlog'])
    ln_path=verify(b['actual_tlogs']['link.command.1.tlog'])
    cmds=original.cl_commands(cl_path)
    ln=original.b.windows_argv(' '.join(ln_path.read_text(encoding='utf-16').splitlines()[1:]))
    env_path=verify(b['environment_batch'])
    text=subprocess.check_output(['cmd.exe','/d','/c',str(env_path)],encoding='mbcs')
    env={k.upper():v for k,v in (x.split('=',1) for x in text.splitlines() if '=' in x and not x.startswith('='))}
    for k in ['CL','_CL_','LINK','_LINK_']:env.pop(k,None)
    info=dict(passed=False,config=config,original_receipt=stat(base),source=str(DST),compiler=str(tools/'cl.exe'),linker=str(tools/'link.exe'),objects_total=111,retained_objects=[],calls=[])
    try:
        changed={}
        for leaf in ['JSphGpu.cpp','JSphGpuSingle.cpp']:
            obj=folder/(Path(leaf).stem+'.obj')
            flags=[];skip=False
            for item in cmds[leaf.casefold()]['flags']:
                if skip: skip=False;continue
                key=item.lower()
                if key=='/sourcedependencies':
                    flags.extend([item,str(folder/(leaf+'.deps.json'))]);skip=True
                elif key.startswith('/fo'):flags.append('/Fo'+str(obj))
                elif key.startswith('/fd'):flags.append('/Fd'+str(folder/'hostcompile.pdb'))
                else:flags.append(item)
            argv=[str(tools/'cl.exe'),*flags,str(DST/leaf)]
            info['calls'].append(run(argv,DST,env,folder/(leaf+'.log')))
            changed[obj.name.casefold()]=obj
        program=out/Path(b['program']['path']).name
        linkflags=[]
        for item in ln:
            key=item.casefold()
            if key.startswith('/out:'):item='/OUT:'+str(program)
            elif key.startswith(('/pdb:','/implib:','/ltcgout:','/ilk:')):
                flag,path=item.split(':',1);item=flag+':'+str(folder/Path(path).name)
            elif not key.startswith('/') and key.endswith('.obj'):
                name=Path(item).name.casefold()
                if name in changed:item=str(changed.pop(name))
                else:
                    item=str(old[name]);info['retained_objects'].append(stat(item))
            linkflags.append(item)
        if changed or len(info['retained_objects'])!=109:raise RuntimeError('Object reuse count differs')
        rsp=folder/'link.rsp'
        rsp.write_text(subprocess.list2cmdline(linkflags),encoding='utf-16')
        info['calls'].append(run([str(tools/'link.exe'),'@'+str(rsp)],folder,env,folder/'link.log'))
        info['runtime']=[]
        for entry in b['runtime']:
            src=verify(entry['destination']);dest=out/src.name
            shutil.copy2(src,dest);info['runtime'].append(stat(dest))
        info.update(program=stat(program),passed=True,actual_pressure_CUDA='Original C04 XYZ free-body producer',cuda_arch='compute_86 and sm_86',no_solver_run=True)
    except Exception as ex:
        info['error']=str(ex)
    with receipt.open('x',encoding='utf8') as f:json.dump(info,f,indent=2)
    print(receipt,info.get('error','OK'),flush=True)
    if not info['passed']:raise SystemExit(1)

if __name__=='__main__':
    build(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'r1')

