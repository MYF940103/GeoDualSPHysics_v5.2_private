"""One fresh Release-r3 GPU source control only; no sanitizer/decode/retry/next job."""
import csv,json,re,shutil,subprocess,sys,time
from pathlib import Path
import psutil
import upl_material_release_native_r2_run as base
T=base.T;L=base.L;TAG='upl_material_release_native_r1_source_GPU_release'
def main():
    base.need(sys.argv[1:]==['--execution-authorized'],'Use --execution-authorized after root review');out=T/'outputs'/TAG;seedroot=T/'outputs'/(TAG+'_seed');paths={k:L/(TAG+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',log='.log').items()};base.need(not out.exists() and not seedroot.exists() and not any(p.exists() for p in paths.values()),'Existing or partial Release control protected')
    frozen=[];result=dict(stage=TAG+'.run',tag=TAG,mode='source',backend='GPU_release',passed=False,solver_invocations=0,native_decoder_invoked=False,memcheck_invoked=False,automatic_next_solver=False,SHA_scans=0,physical_acceptance=False)
    def bind(e):
        q=base.stat(e['path']);base.need(q==e,'Frozen consumed binding changed: '+e['path']);frozen.append(q);return q
    try:
        bp=L/'upl_material_release_Release_r3.build.json';b=base.read(bp);base.need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_and_package_stats_unchanged'],'Closed actual Release-r3 GPU build required');bind(base.stat(bp));program=bind(b['program']);capture=bind(b['source_capture']);archive=bind(base.read(capture['path'])['archive']);exe=Path(program['path']);base.need(exe.parent.name=='upl_material_release_Release_r3' and exe.name=='DualSPHysics5.2_GEO_win64.exe','Wrong physical program/configuration')
        oldpath=L/'upl_preload_handoff_source_GPU_r1.run.json';old=base.read(oldpath);oldnative=L/'upl_preload_handoff_source_GPU_r1_native_r1.check.json';prior=base.read(oldnative);base.need(old['passed'] and old['actual_exit']==old['actual_Win32_exit']==0 and prior['passed'] and prior['original_native_guards_passed'],'Closed old Release source required');bind(base.stat(oldpath));bind(base.stat(oldnative));original=[bind(e) for e in old['seed']];base.need(len(original)==3,'Historical exact XML/BI4/normal seed required')
        seedroot.mkdir();seed=seedroot/Path(original[0]['path']).stem
        for e,suffix in zip(original,('.xml','.bi4','_Normals.nbi4')):shutil.copy2(e['path'],str(seed)+suffix);base.need(Path(str(seed)+suffix).read_bytes()==Path(e['path']).read_bytes(),'Exact old source seed copy differs');bind(base.stat(str(seed)+suffix))
        runtime=[]
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            src=bind(base.stat(T/'outputs/upl_prestress_check_GPU_r1_runtime'/name));dst=exe.parent/name
            if not dst.exists():shutil.copy2(src['path'],dst)
            q=base.stat(dst);base.need((q['bytes'],q['mtime_ns'])==(src['bytes'],src['mtime_ns']),'Release runtime copy differs');bind(q);runtime.append(q)
        bind(base.stat(__file__));bind(base.stat(base.__file__));base.need(not any((p.info['name'] or '').lower().startswith('dualsphysics') for p in psutil.process_iter(['name'])),'Another solver is active; no process is stopped')
        argv=[str(exe),'-gpu:0','-stable','-mdbc_freeslip',str(seed),str(out),'-dirdataout','data','-svres','-nsteps:800'];oid=base.identity(psutil.Process());started=base.utc();wall=time.monotonic();errors=[];child={}
        with paths['log'].open('xb') as stream:
            p=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['solver_invocations']=1
            try:child=base.identity(psutil.Process(p.pid));base.need(Path(child['exe']).samefile(exe) and child['argv'][1:]==argv[1:] and child['parent_pid']==oid['pid'],'Actual owned direct GPU identity differs')
            except Exception as e:errors.append(str(e))
            base.save(paths['start'],dict(stage=TAG+'.start',owner=oid,tool=child,solver=child,target_argv=argv,program=program,consumed=frozen,direct_owner_no_scheduler=True));print(json.dumps(dict(tag=TAG,actual_solver=child)),flush=True);rc=p.wait();win=base.exitcode(int(p._handle))
        base.save(paths['call'],dict(stage=TAG+'.call',owner=oid,tool=child,solver=child,argv=argv,target_argv=argv,program=program,actual_Popen_wait_exit=rc,actual_tool_Win32_exit=win,actual_solver_Win32_exit=win,typed_returncode_captured_first=type(rc) is int,ownership_errors=errors,started_utc=started,ended_utc=base.utc(),elapsed_s=time.monotonic()-wall,log=base.stat(paths['log'])));result.update(actual_exit=win,actual_Win32_exit=win,actual_tool_exit=win,program=program,source_build=base.stat(bp),source_capture=capture,source_archive=archive,seed=[base.stat(str(seed)+s) for s in ('.xml','.bi4','_Normals.nbi4')],base_seed=original,runtime=runtime,solver=child,start_record=base.stat(paths['start']),actual_call=base.stat(paths['call']));base.need(rc==win==0 and child and not errors,'Actual direct Release GPU exit/ownership failed')
        text=(out/'Run.out').read_text(encoding='utf-8-sig');base.need('Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal Release completion/no-exclusion failed')
        with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
        base.need(len(rows)==1,'One actual Release summary required');r=rows[0];base.need(int(r['Steps'])==800 and r['Np']=='7060' and r['Nfixed']==r['Nbound']=='2060' and all(int(r[k])==0 for k in ['PartsOut','PartsOutRhop','PartsOutVel']),'Actual Release updates/registry/exclusions differ');parts=sorted((out/'data').glob('Part_*.bi4'));base.need(len(parts)==int(r['PartFiles']) and [p.name for p in parts]==['Part_%04d.bi4'%i for i in range(len(parts))],'Actual Release PART sequence differs');releases=[s for s in text.splitlines() if 'GravityPreload:' in s and 'phase=released' in s];base.need(len(releases)==1 and 'completed_step=380 retired=260;' in releases[0] and 'damping=OFF Shepard=OFF FreeSeepage=ON.' in releases[0],'Actual one-shot Release event differs');result.update(passed=True,actual_steps=800,new_updates_from_completed_counters=800,saved_frames=len(parts),summary=r,event_markers=releases,Run_out=base.stat(out/'Run.out'),Run_csv=base.stat(out/'Run.csv'),native_review_pending=True)
    except Exception as e:result.update(passed=False,first_failure=str(e))
    try:result['consumed_stats_unchanged']=bool(frozen) and all(base.stat(e['path'])==e for e in frozen)
    except Exception:result['consumed_stats_unchanged']=False
    if not result['consumed_stats_unchanged']:result['passed']=False;result.setdefault('first_failure','Consumed binding changed')
    result['consumed']=frozen;base.save(paths['run'],result);print(json.dumps(result),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
