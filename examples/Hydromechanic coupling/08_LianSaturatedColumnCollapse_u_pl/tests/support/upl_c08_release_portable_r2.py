"""Extract the delivered ZIP once; test help and three actual GenCase inputs. No physical solve."""
import ctypes,datetime,importlib.util,json,subprocess,time,zipfile,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import numpy as np
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_release_portable_r2';OUT=T/'outputs/upl_c08_release_portable_r1';CHECK=L/(TAG+'.check.json')
def need(b,s):
    if not b:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
def invoke(label,argv,cwd):
    log=L/(TAG+'_'+label+'.log');call=L/(TAG+'_'+label+'.call.json');need(not log.exists() and not call.exists(),'Existing actual invocation protected');start=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic();program=stat(argv[0])
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        ft=[w.FILETIME() for _ in range(4)];created=bool(K.GetProcessTimes(int(p._handle),*[ctypes.byref(x) for x in ft]));size=w.DWORD(32768);image=ctypes.create_unicode_buffer(size.value);observed=bool(K.QueryFullProcessImageNameW(int(p._handle),0,image,ctypes.byref(size)))
        rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    result=dict(label=label,passed=got and rc==code.value==0,issued_argv=argv,cwd=str(cwd),PID=p.pid,creation_filetime_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime if created else None,actual_image_observed_before_wait=image.value if observed else None,issued_absolute_program=program,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,started_utc=start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(log),physical_solver_updates=0)
    save(call,result);need(result['passed'] and stat(argv[0])==program and (not observed or Path(image.value).samefile(argv[0])),'Actual portable invocation failed: '+label);return stat(call)
need(OUT.is_dir() and not CHECK.exists(),'Adopt only retained r1 extraction; protect existing r2 check')
archive=C/'support/LianCollapse_upl_win64_r1.zip';manifest=read(C/'support/server_manifest_r1.json');package='LianCollapse_upl_win64_r1';expected=[package+'/'+r['entry'] for r in manifest['files']]+[package+'/support/server_manifest_r1.json',package+'/support/SHA256SUMS_r1.txt']
with zipfile.ZipFile(archive) as z:
    need(z.namelist()==expected,'ZIP whitelist differs')
    for name in z.namelist():need((OUT/name).resolve().is_relative_to(OUT.resolve()),'ZIP target escapes validation workspace')
    need(all((OUT/i.filename).is_file() and (OUT/i.filename).stat().st_size==i.file_size for i in z.infolist()),'Adopted CRC-checked r1 extraction is incomplete')
root=OUT/package;runtime=root/'support/runtime';calls=[];geometries=[]
for backend,exe in (('CPU','DualSPHysics5.2CPU_win64.exe'),('GPU','DualSPHysics5.2_GEO_win64.exe')):
    calls.append(invoke('help_'+backend,[str(runtime/exe),'-h'],root));text=(L/(TAG+'_help_'+backend+'.log')).read_text(encoding='utf-8',errors='replace');need('dualsphysics' in text.lower() and len(text)>500,'Actual help output absent')
spec=importlib.util.spec_from_file_location('retained_geometry_reader',T/'support/lian_collapse_geometry_review_r1.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);vtk=module.vtk
old=T/'outputs/lian_collapse_geometry_r1/CaseLianSaturatedColumnCollapse_geometry_r1';oldxyz,oldfields=vtk(Path(str(old)+'_All.vtk'));oldnormxyz,oldnormfields=vtk(Path(str(old)+'_Normals.vtk'))
for group,coh,psi,sf in (('psi0',5000,0,0),('psi2p5',5000,2.5,.2),('psim5',7500,-5,.2)):
    stem='CaseLianSaturatedColumnCollapse_'+group+'_r1';seedout=T/'outputs'/('upl_c08_formal_geometry_'+group+'_r1');need(not seedout.exists(),'Existing generated seed protected');seedout.mkdir();prefix=seedout/stem
    calls.append(invoke('GenCase_'+group,[str(runtime/'GenCase_win64.exe'),str(root/(stem+'_Def')),str(prefix),'-save:all'],root))
    r=ET.parse(str(prefix)+'.xml').getroot();particles=r.find('execution/particles');need(particles is not None and int(particles.get('np'))==7060,'Generated particle registry differs');blocks=[x for x in particles if x.tag in ('fixed','fluid')];need([(x.tag,int(x.get('mk')),int(x.get('count'))) for x in blocks]==[('fixed',10,255),('fixed',11,1545),('fixed',12,260),('fluid',1,5000)],'Actual generated MK/counts differ')
    xyz,fields=vtk(Path(str(prefix)+'_All.vtk'));normxyz,normfields=vtk(Path(str(prefix)+'_Normals.vtk'))
    need(np.array_equal(xyz,oldxyz) and set(fields)==set(oldfields) and all(np.array_equal(fields[k],oldfields[k]) for k in fields),'Actual generated VTK geometry/IDs differs from retained geometry')
    need(np.array_equal(normxyz,oldnormxyz) and set(normfields)==set(oldnormfields) and all(np.array_equal(normfields[k],oldnormfields[k]) for k in normfields),'Actual generated VTK normals differ')
    soils={q.tag:q.get('value') for q in r.findall('.//soils/*')};hm={q.tag:q.get('value') for q in r.findall('.//hydromechanics/*')};params={q.get('key'):q.get('value') for q in r.findall('.//parameter')};event=r.find('.//gravitypreload');slip={int(q.get('mkbound')):int(q.get('slipmode')) for q in r.findall('.//mdbcslip/bound')}
    need(all(float(soils[k])==v for k,v in dict(coh=coh,dlt=psi,DilationDecay=sf,coh_r=1000,n_coh=5,MaterialReturn=1).items()),'Generated material settings differ');need(hm['HydroMechConductivityModel']=='1' and float(hm['HydroMechConductivityCk'])==2 and float(params['TimeMax'])==13 and float(params['TimeOut'])==.01 and float(params['DtFixed'])==2.5e-6 and float(event.get('time'))==10 and event.get('release_mkbound')=='2' and slip=={0:3,1:2,2:3},'Generated hydromechanical/event/slip settings differ')
    need(all(Path(str(prefix)+s).is_file() for s in ('.xml','.bi4','_Normals.nbi4')),'Actual fresh GenCase seed incomplete');geometries.append(dict(group=group,total=7060,soil=5000,fixed=2060,actual_VTK_geometry_and_normals_equal_retained=True,double_BI4_bit_equality_claimed=False,source=str(root/(stem+'_Def.xml')),seed=str(prefix)))
save(CHECK,dict(stage=TAG,passed=True,adopted_r1_CRC_checked_extraction=True,r1_observation_failure=stat(L/'upl_c08_release_portable_r1.observation_failure.json'),archive=stat(archive),manifest=stat(C/'support/server_manifest_r1.json'),extracted_root=str(root),calls=calls,GenCase_groups=geometries,CPU_GPU_help_exit0=True,payload_entries=len(expected),physical_solver_updates=0,full13s_physical_acceptance=False,extra_SHA_scans=0))
print(json.dumps(dict(passed=True,check=str(CHECK),actual_GenCase_groups=3,actual_help_programs=2,physical_solver_updates=0)),flush=True)
