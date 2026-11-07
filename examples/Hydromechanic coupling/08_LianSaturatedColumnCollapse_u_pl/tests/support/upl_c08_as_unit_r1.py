"""One explicit build or one zero-step AS component; author-only until root review."""
import argparse,csv,os,re,shutil,subprocess
from pathlib import Path
from mdbc_partition_components_r3 import invoke,stat,read,save,bind,need
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';TAG='upl_c08_as_unit_r1'
SOURCE=T/'support'/ (TAG+'.cpp');NOTE=T/'notes'/(TAG+'.json')
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.3/compute-sanitizer/compute-sanitizer.exe')
def build(backend):
 gpu=backend=='GPU';tag=TAG+'_'+backend+'_helper';out=T/'outputs'/tag;check=L/(tag+'.build.json');before=[];calls=[]
 need(not out.exists() and not check.exists(),'Existing helper or failed build protected')
 try:
  bp=L/('upl_c08_artstress_'+('Debug' if gpu else 'DebugCPU')+'_r1.build.json');b=read(bp);expected=113 if gpu else 87
  need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==expected,'Closed current AS Debug build required')
  before=[stat(bp),bind(b['program']),bind(b['source_capture']),bind(b['source_archive']),stat(SOURCE),stat(NOTE),stat(__file__),stat(T/'support/mdbc_partition_components_r3.py')]
  before += [bind(e) for e in read(b['source_capture']['path'])['files']]
  excluded={'main.obj'} if gpu else {'main.obj','jsphcpu.obj'};names={Path(e['path']).name.lower() for e in b['project_objects']};need(excluded<=names,'Required original main/CPU object missing')
  objects=[e for e in b['project_objects'] if Path(e['path']).name.lower() not in excluded];need(len(objects)==expected-len(excluded),'Unexpected object exclusion');before += [bind(e) for e in b['project_objects']]
  old='upl_noslip_'+('gpu' if gpu else 'cpu')+'_component_r1';oldroot=T/'outputs'/old;cp=L/(old+'_compile.call.json');lp=L/(old+'_link.call.json');c=read(cp);l=read(lp);before += [stat(cp),stat(lp)]
  need(c.get('actual_exit_code',c.get('exit_code'))==l.get('actual_exit_code',l.get('exit_code'))==0,'Passed same-backend compiler/link recipe required')
  oldsource=next(x for x in c['arguments'] if x.lower().endswith('.cpp'));exe=out/'component.exe'
  ca=[str(SOURCE) if x==oldsource else x.replace(str(oldroot),str(out)) for x in c['arguments']]
  if '/sourceDependencies' not in ca:ca += ['/sourceDependencies',str(out/'compile.dependencies.json')]
  la=[x.replace(str(oldroot),str(out)).replace(old+'.exe','component.exe') for x in l['arguments'] if not x.lower().endswith('.obj')]+[str(out/'helper.obj'),*[e['path'] for e in objects]]
  need('/Od' in ca and '/MTd' in ca and '/fp:precise' in ca and ('/D_WITHGPU' in ca)==gpu and sum(x.lower().endswith('.obj') for x in la)==len(objects)+1,'Debug flags or link closure differ')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed')
  env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
  out.mkdir();calls.append(invoke(tag+'.compile',[c['program'],*ca],S,env));calls.append(invoke(tag+'.link',[l['program'],*la],S,env));runtime=[]
  for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
   a=stat(oldroot/leaf);before.append(a);shutil.copy2(a['path'],out/leaf);d=stat(out/leaf);need((a['bytes'],a['mtime_ns'])==(d['bytes'],d['mtime_ns']),'Runtime copy stat differs');runtime.append(d)
  need(all(stat(e['path'])==e for e in before),'Consumed build input or object changed')
  save(check,dict(stage=tag,passed=True,program=stat(exe),source=stat(SOURCE),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=runtime,excluded_original_objects=sorted(excluded),project_objects_used=len(objects),actual_link_objects=len(objects)+1,calls=calls,consumed=before,consumed_stats_unchanged=True,component_invocations=0,SHA_scans=0,physical_acceptance=False))
 except Exception as e:
  if not check.exists():save(check,dict(stage=tag,passed=False,first_failure=str(e),calls=calls,consumed=before,SHA_scans=0))
  raise
def run(backend):
 gpu=backend=='GPU';tag=TAG+'_'+backend;out=T/'outputs'/tag;check=L/(tag+'.check.json');before=[];call=None
 need(not out.exists() and not check.exists(),'Existing component or failed result protected')
 try:
  bp=L/(TAG+'_'+backend+'_helper.build.json');b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'],'Closed matching component build required')
  before=[stat(bp),bind(b['program']),bind(b['source']),bind(b['source_build']),bind(b['source_capture']),bind(b['source_archive']),*[bind(e) for e in b['runtime']],stat(NOTE),stat(__file__)]
  exe=Path(b['program']['path']);argv=[str(exe),'--out',str(out)];sanlog=L/(tag+'.memcheck.log')
  if gpu:
   need(not sanlog.exists(),'Existing memcheck protected');before.append(stat(SAN));argv=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','99','--log-file',str(sanlog),*argv]
  call=invoke(tag+'.run',argv,exe.parent,target=exe if gpu else None);d=read(out/'completion.json')
  need(d['passed'] and d['stage']==TAG and d['backend']==backend and d['tensor_cases']==6 and d['modes']==4 and d['scalar_rows']==144 and d['tail_checks']==4 and d['physical_inputs_unchanged'] and d['pair_force_tested'] is False and d['physical_steps']==0,'Original component completion failed')
  with (out/'spectral.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
  need(len(rows)==144 and {r['mode'] for r in rows}=={'legacy','raw','epsilon0','preload_clear'} and len({(r['mode'],r['case'],r['component']) for r in rows})==144,'Component CSV coverage differs')
  if gpu:
   text=sanlog.read_text(encoding='utf-8');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',text);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',text)
   need(errors and leaks and all(int(x.replace(',',''))==0 for x in errors) and all(int(x.replace(',',''))==int(y.replace(',',''))==0 for x,y in leaks),'Memcheck errors/leaks missing or nonzero')
  need(all(stat(e['path'])==e for e in before),'Consumed component input changed')
  save(check,dict(stage=tag,passed=True,component_build=stat(bp),actual_call=call,native_completion=stat(out/'completion.json'),actual_completion=d,files=[stat(out/'spectral.csv')],memcheck_zero_errors_and_leaks=True if gpu else None,consumed=before,consumed_stats_unchanged=True,pair_force_tested=False,physical_steps=0,solver_invocations=0,physical_acceptance=False,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=tag,passed=False,first_failure=str(e),actual_call=call,consumed=before,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','run'));p.add_argument('backend',choices=('CPU','GPU'));p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root review');(build if a.action=='build' else run)(a.backend)
