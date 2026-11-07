"""Independent CPU material branches and expected source rejection; no decode or next run."""
import csv,importlib.util,json,re,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
T=Path(__file__).resolve().parents[1];L=T/'logs';BASE=T/'support/upl_preload_handoff_test_r1.py'
spec=importlib.util.spec_from_file_location('preload_owner_definitions',BASE);B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
need,read,stat,save,utc,identity=B.need,B.read,B.stat,B.save,B.utc,B.identity
CASES={'reject':('.1','.1','0','0'),'psi2p5':('5000','1000','2.5','.2'),'psim5':('7500','1000','-5','.2')}
def main():
    need(len(sys.argv)==3 and sys.argv[1] in CASES and sys.argv[2]=='CPU','Use reject|psi2p5|psim5 CPU')
    mode=sys.argv[1];reject=mode=='reject';tag='upl_preload_handoff_'+mode+'_CPU_r1';out=T/'outputs'/tag;seedroot=T/'outputs'/(tag+'_seed')
    paths={k:L/(tag+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',log='.log').items()}
    need(not out.exists() and not seedroot.exists() and not any(p.exists() for p in paths.values()),'Existing output/seed/partial receipt protected')
    frozen=[];result=dict(stage=tag+'.run',tag=tag,mode=mode,backend='CPU',passed=False,actual_exit=None,actual_Win32_exit=None,native_review_pending=True,expected_rejection=reject,native_decoder_invoked=False,automatic_next_solver=False,BAT_executed=False,SHA_scans=0,physical_acceptance=False)
    def bind(e):
        s=stat(e['path']);need((s['bytes'],s['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed file changed: '+e['path']);frozen.append(s);return s
    def load(p):bind(stat(p));return read(p)
    try:
        admission=L/'upl_preload_handoff_branches_r1.admission.json';a=load(admission);need(a['passed'] is True and tag in a['allowed_jobs'],'Separate root branch admission required')
        for e in a['inputs']:bind(e)
        build=L/'upl_preload_handoff_ReleaseCPU_r2.build.json';b=load(build);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_stats_unchanged'],'Closed current ReleaseCPU_r2 required')
        program=bind(b['program']);capture=bind(b['source_capture']);archive=bind(read(capture['path'])['archive']);exe=Path(program['path'])
        source='upl_preload_handoff_source_CPU_r1';r=load(L/(source+'.run.json'));n=load(L/(source+'_native_r1.check.json'))
        need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==800 and r['consumed_stats_unchanged'] and Path(r['program']['path']).samefile(exe),'Closed current CPU source required')
        need(bind(r['program'])==program and bind(r['source_build'])==stat(build),'Source/current program-build binding differs')
        need(n['passed'] and n['original_native_guards_passed'] and n['qualified_elastic_PRE_verified'] and n['consumed_stats_unchanged'],'Actual qualified CPU PRE required')
        need(bind(n['source_run'])==stat(L/(source+'.run.json')),'Source native ownership differs')
        call=read(bind(n['reader_call'])['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Source reader actual exits differ')
        done=read(bind(n['native_completion'])['path']);pre=Path(bind(n['certified_pre_file'])['path'])
        need(done['qualified_PRE_read_by_current_helper'] and done['source_PRE_completed_step']==380 and pre.name==done['certified_pre_filename'] and pre.samefile(T/'outputs'/source/'data'/('Part_%04d.bi4'%done['genuine_pre_event_part'])),'Source PRE identity differs')
        original=T/'outputs/upl_ck2_release_short_r1_seed/CaseLianSaturatedColumnCollapse_ck2_release_short_r1';originals=[bind(stat(str(original)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        text=Path(originals[0]['path']).read_bytes().decode('utf-8');expected=ET.fromstring(text);g=expected.find('.//gravitypreload');params={q.get('key'):q.get('value') for q in expected.findall('.//parameter')}
        need(g is not None and g.get('time')=='0.00095' and g.get('release_mkbound')=='2' and 'statefile' not in g.attrib and 'elastic_source' not in g.attrib,'Original event differs')
        need(expected.find('.//soils/phi').get('value')=='25' and all(float(params[k])==v for k,v in (('DtIni',2.5e-6),('DtFixed',2.5e-6),('TimeMax',.002),('TimeOut',.0001),('PartsOutMax',0))),'Original legal friction/controls differ')
        cp,cr,psi,sf=CASES[mode];values={'coh':cp,'coh_r':cr,'n_coh':'5','dlt':psi,'DilationDecay':sf}
        for key,value in values.items():
            comment='Expected rejection fixture: low constant cohesion' if reject and key in ('coh','coh_r') else 'Shared elastic PRE branch: '+mode+'; '+key
            node=expected.find('.//soils/'+key);need(node is not None,'Missing material node '+key);node.set('value',value);node.set('comment',comment)
            def replacement(m):
                e=ET.fromstring(m[0]);e.set('value',value);e.set('comment',comment);return ET.tostring(e,encoding='unicode')
            text,count=re.subn(r'<'+key+r'\b[^>]*/>',replacement,text);need(count==1,'Repeated/missing material node '+key)
        attribute='elastic_source' if reject else 'statefile';value='true' if reject else str(pre);g.set(attribute,value)
        def event(m):
            e=ET.fromstring(m[0]);e.set(attribute,value);return ET.tostring(e,encoding='unicode')
        text,count=re.subn(r'<gravitypreload\b[^>]*/>',event,text);need(count==1 and ET.tostring(ET.fromstring(text))==ET.tostring(expected),'Only declared material/event changes allowed')
        seedroot.mkdir();seed=seedroot/original.name;Path(str(seed)+'.xml').write_bytes(text.encode('utf-8'))
        for suffix,e in zip(('.bi4','_Normals.nbi4'),originals[1:]):shutil.copy2(e['path'],str(seed)+suffix)
        seedfiles=[bind(stat(str(seed)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        closed={Path(e['path']).resolve():e for e in r['consumed']}
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):bind(closed[(exe.parent/name).resolve()])
        bind(stat(BASE));bind(stat(__file__));bind(stat(T/'notes/upl_preload_handoff_branches_r1.json'))
        need(not any((q.info['name'] or '').lower().startswith('dualsphysics') for q in B.psutil.process_iter(['name'])),'Another solver is active; do not duplicate')
        argv=[str(exe),'-cpu','-ompthreads:8','-stable','-mdbc_freeslip',str(seed),str(out),'-dirdataout','data','-svres','-nsteps:800'];owner=identity(B.psutil.Process());started=utc();wall=time.monotonic();errors=[];child=None
        result.update(program=program,source_build=stat(build),source_capture=capture,source_archive=archive,seed=seedfiles,base_seed=originals,admission=stat(admission),source_run=stat(L/(source+'.run.json')),source_native=stat(L/(source+'_native_r1.check.json')),source_pre_file=None if reject else stat(pre),source_pre_time_s=None if reject else done['genuine_pre_event_time_s'],material_values=values,initial_completed_step=0 if reject else 380)
        with paths['log'].open('xb') as f:
            p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                child=identity(B.psutil.Process(p.pid));need(Path(child['exe']).samefile(exe) and child['argv'][1:]==argv[1:] and child['parent_pid']==owner['pid'],'Actual CPU ownership differs')
                save(paths['start'],dict(stage=tag+'.start',owner=owner,tool=child,solver=child,program=program,target_argv=argv,working_directory=str(T.parent),consumed=frozen,direct_owner_no_scheduler=True,BAT_executed=False))
            except Exception as e:errors.append(str(e))
            print(json.dumps(dict(tag=tag,actual_solver=child,actual_PID=p.pid)),flush=True);rc=p.wait();win=None
            try:win=B.exitcode(int(p._handle))
            except Exception as e:errors.append(str(e))
        save(paths['call'],dict(stage=tag+'.call',owner=owner,tool=child,solver=child,program=program,argv=argv,target_argv=argv,working_directory=str(T.parent),actual_Popen_wait_exit=rc,actual_tool_Win32_exit=win,actual_solver_Win32_exit=win,typed_returncode_captured_first=type(rc) is int,ownership_errors=errors,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,log=stat(paths['log']),BAT_executed=False))
        result.update(actual_exit=win,actual_Win32_exit=win,actual_tool_exit=win,solver=child,start_record=stat(paths['start']) if paths['start'].exists() else None,actual_call=stat(paths['call']),elapsed_s=time.monotonic()-wall);need(child is not None and rc==win and not errors,'Actual CPU ownership/typed exits differ')
        text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'));need(parts and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(len(parts))] and all(q.stat().st_size>0 for q in parts),'Actual saved native membership differs')
        markers=[s for s in text.splitlines() if 'GravityPreload:' in s];released=[s for s in markers if 'phase=released' in s];imports=[s for s in markers if 'state imported file=' in s]
        if reject:
            failure=re.search(r'ConsistentDev material return failed in (predictor|corrector); status mask=(\d+)\.',text)
            need(rc!=0 and failure is not None and int(failure[2])==4 and not released and not imports,'Expected source Radial rejection was not observed; preserve actual first cause')
            result.update(passed=True,expected_rejection_observed=True,rejected_stage=failure[1],actual_status_mask=4,actual_failure_text=failure[0],qualified_PRE_absence_pending_native=True,native_first_and_last_saved_clock_pending=True,last_console_reported_PART_line=next((s for s in reversed(text.splitlines()) if re.match(r'^PART_\d+',s)),None))
        else:
            need(rc==0 and 'Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal branch completion/no-exclusion failed')
            with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
            need(len(rows)==1,'One actual Run summary required');row=rows[0];need(int(row['Steps'])==800 and int(row['PartFiles'])==len(parts) and row['Np']=='7060' and row['Nbound']==row['Nfixed']=='2060' and all(int(row[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual branch summary differs')
            need(len(imports)==len(released)==1 and 'completed_step=380 retired=260;' in released[0] and 'damping=OFF Shepard=OFF FreeSeepage=ON.' in released[0],'Actual import/release differs')
            for line in (imports[0],released[0]):
                m=re.search(r'actual=([^ ]+) completed_step=(\d+)',line);need(m is not None and float(m[1])==done['genuine_pre_event_time_s'] and int(m[2])==380,'Actual imported/release scalar clock differs')
            result.update(passed=True,actual_steps=800,new_updates_from_completed_counters=420,summary=row,Run_csv=stat(out/'Run.csv'))
        result.update(saved_frames=len(parts),event_markers=markers,Run_out=stat(out/'Run.out'),native_file_names=[q.name for q in parts])
    except Exception as e:result.update(passed=False,first_failure=str(e))
    finally:
        try:result['consumed_stats_unchanged']=bool(frozen) and all(stat(e['path'])==e for e in frozen)
        except Exception:result['consumed_stats_unchanged']=False
        if not result['consumed_stats_unchanged']:result['passed']=False;result.setdefault('first_failure','Consumed stat changed')
        result['consumed']=frozen;save(paths['run'],result)
    print(json.dumps(dict(tag=tag,passed=result['passed'],actual_exit=result['actual_exit'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
