"""One reviewed two-state component invocation; no solver/reader/build/automatic follow-on."""
import os,sys
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
T,L=m.T,m.L
TAG='c08_tpi_state_r1'

def main():
    m.need(sys.argv[1:]==['--execution-authorized'],'One independent root component admission required')
    check=L/(TAG+'.check.json');out=T/'outputs'/TAG;call=None;before=[]
    m.need(not out.exists() and not check.exists() and not (L/(TAG+'.component.call.json')).exists(),'Existing complete/partial component protected')
    try:
        bp=L/(TAG+'.build.json');b=m.read(bp)
        m.need(b['passed'] and b['configuration']=='DebugCPU' and b['consumed_stats_unchanged'] and b['actual_link_objects']==87 and b['new_entry_objects']==1 and b['physical_objects_compiled']==0 and b['component_max_actual_force_calls']==4,'Original-object private component build required')
        exe=Path(m.bind(b['program'])['path'])
        for p in psutil.process_iter(['exe']):
            try:m.need(not p.info['exe'] or Path(p.info['exe']).resolve()!=exe.resolve(),'Exact component is already active')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        native=T/'outputs/c08_h18_as03n255_full3_r1/native_r1';seed=T/'outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1'
        before=[m.stat(q) for q in [Path(__file__),bp]]+[m.bind(b[q]) for q in ['program','source','note','source_build','source_capture','source_archive','source_RHS','source_full_run','source_native','source_review']]+[m.bind(q) for q in b['generated_includes']]+[m.bind(q) for q in b['runtime']]
        retained_run=m.read(b['source_full_run']['path'])
        targets=[native/q for q in ['typed22.bin','typed22_layout.csv','clocks.csv']]+[Path(str(seed)+q)for q in ['.xml','.bi4','_Normals.nbi4']]+[T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4',T/'outputs/c08_h18_as03_rhs_r1/soil_rhs.csv']
        for p in targets:
            matches=[q for q in b['consumed'] if Path(q['path']).resolve()==p.resolve()]
            if not matches:matches=[q for q in retained_run['seed'] if Path(q['path']).resolve()==p.resolve()]
            m.need(len(matches)==1,'Actual bound component input missing or repeated: '+str(p));before.append(m.bind(matches[0]))
        m.verify(before);env=os.environ.copy();env.pop('C08_TPI_X0',None);env['OMP_NUM_THREADS']='1'
        call=m.invoke(TAG+'.component',[str(exe),'--check','--native',str(native),'-cpu','-ompthreads:1','-stable','-svres','-mdbc_freeslip:1',str(seed),str(out)],T.parent,env)
        actual=m.read(call['path']);done=m.read(out/'completion.json')
        m.need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None and done['passed'] and done['parts']==[38,76] and done['baseline_native_bits_rows']==10000 and 2<=done['actual_force_calls']<=4 and done['physical_steps']==0 and done['material_return_calls']==0,'Actual bounded component exit/coverage failed')
        m.need(done['soil_rows']==5000*done['actual_force_calls'] and done['focus_rows']==4*done['actual_force_calls'] and done['pair_rows']==2*done['actual_force_calls'] and done['summary_rows']==done['actual_force_calls'],'Complete conditional-output row counts differ')
        m.verify(before)
        m.save(check,dict(stage=TAG,passed=True,actual_call=call,completion=m.stat(out/'completion.json'),summary=done,files=[m.stat(p) for p in sorted(out.iterdir()) if p.is_file()],consumed=before,consumed_stats_unchanged=True,component_invocations=1,physical_steps=0,solver_invocations=0,reader_invocations=0,GPU_actions=0,SHA_scans=0,baseline_bits_reference_is_retained_CPU_RHS_not_saved_GPU_force=True,scientific_review_pending=True,physical_acceptance=False,automatic_next_job=False))
    except Exception as error:
        if call is None and (L/(TAG+'.component.call.json')).exists():call=m.stat(L/(TAG+'.component.call.json'))
        if not check.exists():m.save(check,dict(stage=TAG,passed=False,first_failure=str(error),actual_call=call,consumed=before,partial_outputs_preserved=True,physical_steps=0,automatic_retry=False,physical_acceptance=False))
        raise

if __name__=='__main__':main()
