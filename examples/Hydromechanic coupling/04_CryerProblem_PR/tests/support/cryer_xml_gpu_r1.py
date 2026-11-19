"""Relink the checked private row GPU solver with the three private XML host translation units."""
import argparse
import csv
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import upl_tpi_cryer_gpu_build_r1 as vs
from cryer_row_gpu_r1 import OUT, LOG, PREFIX, call, identity, load, need, save, verify


TAG = 'cryer_xml_gpu_r1'
HOST = ('JSph.cpp', 'JSphGpu.cpp', 'JSphGpuSingle.cpp')
SELECTOR = 'HydroMechPressureIntegrator'
REJECTIONS = {
    'invalid': SELECTOR+' requires 0 (explicit Kw) or 1 (TPI)',
    'duplicate': 'Duplicate '+SELECTOR,
    'legacy': SELECTOR+' must be selected in XML',
    'dynamic0': SELECTOR+'=1 requires HydroMech=1 and HydroMechDynamicSeepage=1',
    'restart': SELECTOR+'=1 requires a fresh start',
    'wrongnode': 'Place '+SELECTOR+' inside special/hydromechanics',
}
CASES = ('controlA','controlB','missing','zero','one',*REJECTIONS)


def build(source):
    source = source.resolve(strict=True)
    need(source.is_relative_to(OUT) and all((source/f).is_file() for f in HOST), 'Private XML sources required')
    folder = OUT/(TAG+'_Release')
    receipt = LOG/(folder.name+'.build.json')
    base = OUT/(PREFIX+'_Release')
    row = load(LOG/(base.name+'.build.json'))
    full = load(LOG/'upl_tpi_cryer_gpu_Release_r1.build.json')
    old = load(LOG/'cryer_p3_gpu_r2_Release.build.json')
    need(row['passed'] and full['passed'] and not receipt.exists() and not folder.exists(), 'Existing or invalid build')
    out = folder/'out'
    out.mkdir(parents=True)
    batch = verify(full['environment_batch'])
    raw = subprocess.check_output(['cmd.exe','/d','/c',str(batch)], encoding='mbcs')
    env = {k.upper():v for k,v in (x.split('=',1) for x in raw.splitlines() if '=' in x and not x.startswith('='))}
    for k in ('CL','_CL_','LINK','_LINK_'):
        env.pop(k, None)
    recipe = verify(full['actual_tlogs']['CL.command.1.tlog'])
    commands = vs.cl_commands(recipe)
    expected = {Path(e['path']).resolve():e for e in [*row['retained'],row['new_cuda_object']]}
    need(len(expected)==111, 'Original GPU object closure')
    program = out/Path(row['program']['path']).name
    result = dict(passed=False, calls=[], program_base=row['program'], source=str(source),
                  host_sources=[identity(source/f) for f in HOST], vs_commands=identity(recipe),
                  input_link_recipe=identity(base/'link.rsp'), retained=[], replaced=[])
    try:
        changed = {}
        for leaf in HOST:
            obj = folder/(Path(leaf).stem+'.obj')
            original = commands[leaf.casefold()]['flags']
            flags = []
            i = 0
            while i<len(original):
                arg = original[i]
                if arg.casefold()=='/sourcedependencies':
                    flags.extend([arg,str(folder/(leaf+'.deps.json'))])
                    i+=2
                    continue
                if arg.casefold().startswith('/fo'):
                    arg = '/Fo'+str(obj)
                elif arg.casefold().startswith('/fd'):
                    arg = '/Fd'+str(folder/'hostcompile.pdb')
                flags.append(arg)
                i+=1
            need(vs.normalize_cl(flags)[0]==vs.normalize_cl(original)[0], 'CL numerical flags')
            record = call([old['compiler'], *flags,str(source/leaf)], source,env,folder/(leaf+'.log'))
            result['calls'].append(record)
            need(record['win32_exit']==record['popen_exit']==0 and obj.is_file(), 'Compile '+leaf)
            changed[obj.name.casefold()] = obj
        flags = vs.b.windows_argv((base/'link.rsp').read_text(encoding='utf-16'))
        for i, arg in enumerate(flags):
            key = arg.casefold()
            if key.startswith('/out:'):
                flags[i]='/OUT:'+str(program)
            elif key.startswith(('/pdb:','/implib:','/ltcgout:','/ilk:')):
                flag,path=arg.split(':',1)
                flags[i]=flag+':'+str(folder/Path(path).name)
            elif not arg.startswith('/') and key.endswith('.obj'):
                path=Path(arg).resolve(strict=True)
                entry=expected.pop(path)
                need(identity(path)==entry, 'Base object changed '+str(path))
                obj=changed.pop(path.name.casefold(),None)
                if obj:
                    flags[i]=str(obj)
                    result['replaced'].append(dict(old=entry,new=identity(obj)))
                else:
                    result['retained'].append(entry)
        need(not changed and not expected and len(result['retained'])==108 and row['new_cuda_object'] in result['retained'], 'Final link closure')
        rsp=folder/'link.rsp'
        rsp.write_text(subprocess.list2cmdline(flags),encoding='utf-16')
        record=call([old['linker'],'@'+str(rsp)],folder,env,folder/'link.log')
        result['calls'].append(record)
        need(record['win32_exit']==record['popen_exit']==0 and program.is_file(),'GPU relink')
        for entry in old['runtime']:
            src=base/'out'/Path(entry['path']).name
            shutil.copy2(src,out/src.name)
            need(identity(src)['sha256']==identity(out/src.name)['sha256'],'Runtime copy '+src.name)
        result.update(passed=True,program=identity(program))
    finally:
        save(receipt,result)
    print(program,flush=True)


def short(profile):
    b = profile in ('controlB','one') or profile in REJECTIONS
    control = profile.startswith('control')
    tag = TAG+'_'+profile
    folder = OUT/tag
    receipt = LOG/(tag+'.run.json')
    need(not receipt.exists() and not folder.exists(), 'Existing XML short run')
    build_result = load(LOG/((PREFIX if control else TAG)+'_Release.build.json'))
    exe = Path(build_result['program']['path'])
    need(build_result['passed'] and identity(exe)==build_result['program'], 'GPU program binding')
    old = load(LOG/('cryer_p3_gpu_'+('b64' if b else 'default128')+'_r1.run.json'))
    xml,bi4 = [verify(e) for e in old['inputs'][2:]]
    value = {'zero':0, 'one':1, **dict.fromkeys(REJECTIONS,1), 'invalid':2}.get(profile)
    if value is not None:
        seed = OUT/(tag+'_seed')
        seed.mkdir()
        # Keep the generated case style and all other XML bytes intact.
        raw = xml.read_bytes()
        marker = b'                <HydroMech value="'
        need(raw.count(marker)==1,'Hydromechanics selector insertion point')
        newline = b'\r\n' if b'\r\n' in raw else b'\n'
        xmlpath = seed/xml.name
        line = f'                <{SELECTOR} value="{value}" />'.encode()+newline
        if profile=='wrongnode':
            soils=b'            <soils>'+newline
            need(raw.count(soils)==1,'Soils element')
            raw=raw.replace(soils,soils+line)
        else:
            raw = raw.replace(marker,line*(2 if profile=='duplicate' else 1)+marker)
        if profile=='dynamic0':
            active=b'<HydroMechDynamicSeepage value="1"'
            need(raw.count(active)==1,'Dynamic seepage element')
            raw=raw.replace(active,b'<HydroMechDynamicSeepage value="0"')
        xmlpath.write_bytes(raw)
        shutil.copy2(bi4,seed/bi4.name)
        need(identity(bi4)['sha256']==identity(seed/bi4.name)['sha256'],'Seed BI4 copy')
        xml=xmlpath
    parent='soils' if profile=='wrongnode' else 'hydromechanics'
    element = ET.parse(xml).find('execution/special/'+parent+'/'+SELECTOR)
    need((element.get('value') if element is not None else None)==(str(value) if value is not None else None),'XML value')
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith('UPL_TPI_')}
    if profile=='controlB':
        env.update(old['tpi_environment'])
    elif profile=='legacy':
        env['UPL_TPI_GPU_R1']='A'
    args = [str(exe),'-gpu','-stable',str(xml.with_suffix('')),str(folder),'-dirdataout','data','-svres','-nsteps:2']
    if profile=='restart':
        restart=OUT/(TAG+'_one')/'data'
        need((restart/'Part_0001.bi4').is_file(),'Real saved restart state')
        args.extend(['-partbegin:1',str(restart)])
    console = LOG/(tag+'.console.log')
    record = call(args,exe.parent,env,console)
    record.update(passed=False,profile=profile,program=identity(exe),input_xml=identity(xml),
                  input_bi4=identity(xml.with_suffix('.bi4')),dt=old['dt'],
                  tpi_environment={k:v for k,v in env.items() if k.upper().startswith('UPL_TPI_')})
    try:
        if profile in REJECTIONS:
            need(record['win32_exit']==record['popen_exit']!=0 and REJECTIONS[profile] in console.read_text(errors='replace')
                 and not any((folder/'data').glob('Part_*.bi4')),'Invalid selector rejection before first PART')
            record['rejection']=REJECTIONS[profile]
        else:
            need(record['win32_exit']==record['popen_exit']==0,'GPU solver exit')
            if not control:
                need(SELECTOR+'='+str(int(b)) in console.read_text(errors='replace'),'Active XML selector log')
            with (folder/'Run.csv').open(encoding='utf-8-sig',newline='') as f:
                row,=csv.DictReader(f,delimiter=';')
            need(tuple(int(row[k]) for k in ('Steps','PartFiles','PartsOut','Np'))==(2,2,0,37181),'GPU summary')
            record.update(loop_s=float(row['TSimul']),device=row['Hardware'])
        record['passed']=True
    finally:
        save(receipt,record)
    print(profile,'passed',flush=True)


def check(profile):
    from cryer_p3_verify_r1 import audit, EXPECTED_TYPES
    from cryer_p3_sidecar_review_r1 import inspect
    tag=TAG+'_'+profile
    folder=OUT/tag
    b=profile=='one'
    control=TAG+('_controlB' if b else '_controlA')
    reference=OUT/control
    run=load(LOG/(tag+'.run.json'))
    base=load(LOG/(control+'.run.json'))
    need(run['passed'] and base['passed'] and not run['tpi_environment'] and run['dt']==base['dt'], 'Binding')
    frames=audit(folder/'data',[0,2],run['dt'],reference/'data',exact=True,p3_sidecars=b)
    sidecars={p.name:identity(p)['sha256'] for p in folder.glob('UplTpi*')}
    old={p.name:identity(p)['sha256'] for p in reference.glob('UplTpi*')}
    need(sidecars==old and bool(sidecars)==b,'Pressure/clock ledgers')
    result=dict(passed=True,profile=profile,program=run['program'],control=base['program'],dt=run['dt'],
                native_fields=list(EXPECTED_TYPES),native_saves=frames,signed_dterror_bitwise_equal=True,
                byte_equal_sidecars=sidecars)
    if b:
        result['sidecar_checks']=inspect(folder,2)
    save(LOG/(tag+'.check.json'),result)
    print(profile,'matched',len(EXPECTED_TYPES),'native arrays',len(sidecars),'sidecars',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    cmds=parser.add_subparsers(dest='action',required=True)
    cmds.add_parser('build').add_argument('source',type=Path)
    cmds.add_parser('run').add_argument('profile',choices=CASES)
    cmds.add_parser('check').add_argument('profile',choices=['missing','zero','one'])
    args=parser.parse_args()
    if args.action=='build':
        build(args.source)
    elif args.action=='run':
        short(args.profile)
    else:
        check(args.profile)
