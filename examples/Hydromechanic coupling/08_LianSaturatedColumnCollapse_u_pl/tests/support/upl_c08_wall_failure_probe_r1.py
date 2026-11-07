"""One error-only C08 diagnostic rerun from the original elastic PRE; no queue/retry/full solve."""
import argparse,datetime,json,os,re,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as old
from upl_c08_resume_native_r1_run import check_input
from upl_c08_resume_r1 import summary
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_wall_failure_probe_r1'
OUT=T/'outputs'/TAG;RUNTIME=T/'outputs/upl_c08_wall_failure_probe_runtime_r1';CONFIG=T/'configs'/(TAG+'_Def.xml')
FAILED=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r3_GPU_out';SOURCE_XML=FAILED/'CaseLianSaturatedColumnCollapse_psi0_shared_r3.xml';PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
DEFAULT_BUILD=L/'upl_c08_wall_diag_Release_r1.build.json'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def last_part(text):
    for line in reversed(text.splitlines(keepends=True)):
        if re.match(r'^Part_\d+\s+[0-9.eE+-]+\s+\d+\s+',line) and line.endswith('\n'):return dict(raw_complete_line=line,last_saved_console_time_is_truncated_not_native=True)
    return None

def diagnostic(text):
    pattern=r'^DynamicPoreWall rejected: stage=(\d+) sorted_slot=(\d+) native_id=(\d+) step_start=([^ ]+) step=(\d+) B=\(([^,]+),([^,]+),([^)]+)\) normal=\(([^,]+),([^,]+),([^)]+)\)\.$'
    rows=[]
    for line in text.splitlines():
        m=re.match(pattern,line)
        if m:
            stage=int(m[1]);rows.append(dict(raw_line=line,stage=stage,stage_name={0:'state',1:'correction_matrix'}.get(stage,'unclassified_host_stage'),sorted_slot=int(m[2]),native_id=int(m[3]),step_start_text=m[4],step_start=float(m[4]),step=int(m[5]),B=[float(m[i]) for i in (6,7,8)],normal=[float(m[i]) for i in (9,10,11)],clock_meaning='Current new-run TimeStep/Nstep at this force stage; not an already completed post-step time or the old failure time.'))
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build-check',type=Path,default=DEFAULT_BUILD);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read and explicit single-probe execution required');record=L/(TAG+'.run.json');start=L/(TAG+'.start.json')
    need(not any(p.exists() for p in (OUT,RUNTIME,record,start,L/(TAG+'.gencase.call.json'),L/(TAG+'.solver.call.json'))),'Existing/partial diagnostic is protected')
    consumed=[];result=dict(stage=TAG,passed=False,observation_closed=False,physical_acceptance=False,old_failure_time_replaced=False,automatic_next_solver=False,solver_invocations=0,GenCase_invocations=0,native_decoder_invocations=0,source_PRE_recomputed=False,PART_restart_used=False,SHA_scans=0);solver_call=None
    try:
        bp=a.build_check.resolve();b=read(bp);need(bp.name=='upl_c08_wall_diag_Release_r1.build.json' and b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Passed new diagnostic GPU Release build required');program=Path(bind(b['program'])['path']);need(program.name=='DualSPHysics5.2_GEO_win64.exe','New diagnostic GPU Release target differs')
        previous=L/'upl_c08_formal_psi0_r1.run.json';r=read(previous);need(not r['passed'] and r['actual_exit']==r['actual_Win32_exit']==1 and r['consumed_stats_unchanged'],'Original failed run evidence differs');need(Path(r['source_pre_file']['path']).samefile(PRE) and CONFIG.read_bytes()==SOURCE_XML.read_bytes(),'Probe must use the exact parsed failed-run XML and original PRE')
        check_input(CONFIG,PRE);parameters={e.get('key'):e.get('value') for e in ET.parse(CONFIG).getroot().findall('execution/parameters/parameter')};need(float(parameters['TimeMax'])==13.,'Retain the actual TimeMax13 input; bound this probe only by global -nsteps')
        consumed=[stat(p) for p in (bp,previous,CONFIG,SOURCE_XML,PRE,PRE.parent/'Part_Head.ibi4',Path(__file__),Path(old.__file__),T/'support/upl_c08_resume_native_r1_run.py',T/'support/upl_c08_resume_r1.py',T/'notes'/(TAG+'.md'))]+[bind(b['program']),bind(b['source_capture']),bind(b['source_archive'])]
        capture=read(b['source_capture']['path'])
        if 'archive' in capture:consumed.append(bind(capture['archive']))
        for q in psutil.process_iter(['exe','cmdline']):need(not any(x.lower().startswith('-gpu') for x in(q.info['cmdline'] or [])[1:]),'Another GPU target is active; no process is stopped')
        RUNTIME.mkdir();runtime=[]
        for p in [program,*[C/'support/runtime_r3'/name for name in ('GenCase_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')]]:
            origin=stat(p);dest=RUNTIME/p.name;shutil.copy2(p,dest);copy=stat(dest);need((origin['bytes'],origin['mtime_ns'])==(copy['bytes'],copy['mtime_ns']),'Isolated runtime copy stat differs');runtime.append(dict(original=origin,copy=copy));consumed += [origin,copy]
        prefix=OUT/TAG;gargv=[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'];sargv=[str(RUNTIME/program.name),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:4048000']
        me=psutil.Process();save(start,dict(stage=TAG+'.start',utc=utc(),owner=dict(pid=me.pid,created_epoch=me.create_time()),record_kind='Real owner pre-call admission; actual child identity/creation/argv/native handles are captured by each immutable tool call.',GenCase_argv=gargv,solver_argv=sargv,source_build=stat(bp),consumed=consumed))
        result['GenCase_invocations']=1;gcall=invoke(TAG+'.gencase',gargv,C);seed=[stat(str(prefix)+x) for x in ('.xml','.bi4','_Normals.nbi4')];consumed += seed;check_input(Path(seed[0]['path']),PRE)
        result['solver_invocations']=1
        try:solver_call=invoke(TAG+'.solver',sargv,C)
        except RuntimeError:
            # The reused primitive seals real wait/Win32 exits before rejecting rc1.
            path=L/(TAG+'.solver.call.json');need(path.exists(),'No genuine sealed diagnostic target call; do not infer an exit');call=read(path);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==1 and call['ownership_failure'] is None,'Unexpected tool/ownership failure');solver_call=stat(path)
        call=read(solver_call['path']);rc=call['actual_Popen_wait_exit'];need(rc==call['actual_Win32_exit'] and rc in (0,1) and call['ownership_failure'] is None,'Actual target exit/ownership differs')
        need(Path(call['child']['exe']).samefile(RUNTIME/program.name) and call['child']['argv'][1:]==sargv[1:] and call['child']['parent_pid']==me.pid,'Actual diagnostic target identity/argv/parent differs')
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig');rows=diagnostic(text)
        if rc==0:
            sr=summary(OUT/'Run.csv');need('Finished execution (code=0).' in text and int(sr['Steps'])==4048000 and all(int(sr[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'A no-reproduction run must genuinely reach the bounded global endpoint');outcome='bounded_endpoint_reached_without_wall_diagnostic';need(not rows,'An error diagnostic accompanied rc0; inspect rather than calling it reproduced')
        else:
            need('Finished execution (code=1).' in text,'Original new-run failure log missing');outcome='wall_diagnostic_observed' if rows else 'different_failure_or_missing_diagnostic'
            need(len(rows)==1 and 'GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.' in text,'New rc1 did not capture exactly one original wall rejection diagnostic')
        need(all(stat(e['path'])==e for e in consumed),'Consumed source/input/program changed during probe')
        result.update(passed=True,observation_closed=True,outcome=outcome,actual_exit=rc,actual_Win32_exit=call['actual_Win32_exit'],runtime_completed=(rc==0),diagnostic_reproduced=bool(rows),diagnostics=rows,GenCase_call=gcall,solver_call=solver_call,program=stat(RUNTIME/program.name),source_build=stat(bp),source_pre_file=stat(PRE),input_xml=seed[0],runtime=runtime,seed=seed,global_completed_cap=4048000,maximum_new_updates=48000,last_console_report=last_part(text),Run_out=stat(OUT/'Run.out'),consumed=consumed,consumed_stats_unchanged=True)
    except Exception as e:
        result.update(first_failure=str(e),solver_call=solver_call,consumed=consumed)
        if (OUT/'Run.out').exists():result.update(last_console_report=last_part((OUT/'Run.out').read_text(encoding='utf-8-sig')))
    callpath=L/(TAG+'.solver.call.json')
    if callpath.exists():
        actual=read(callpath);result.update(actual_exit=actual['actual_Popen_wait_exit'],actual_Win32_exit=actual['actual_Win32_exit'],solver_call=stat(callpath))
    save(record,result);print(json.dumps(dict(passed=result['passed'],outcome=result.get('outcome'),actual_exit=result.get('actual_exit'),first_failure=result.get('first_failure'),physical_acceptance=False)),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
