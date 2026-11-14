"""One closed completed CPU window read, never a solver or VTK invocation."""
import argparse, os, sys
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';R=T.parents[3]
C8=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
sys.path.insert(0,str(C8/'support'))
import mdbc_partition_components_r3 as m
m.L=L

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['original','off','on']);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    m.need(a.execution_authorized,'Independent read admission required')
    tag='upl_tpi_x0_short_r2_'+a.phase;runpath=L/(tag+'.run.json');check=L/(tag+'.native.check.json');call=None;before=[]
    run=m.read(runpath);out=Path(run['output'])/'native_r1'
    m.need(not out.exists() and not check.exists() and not (L/(tag+'.native.call.json')).exists(),'Existing complete/failed/partial native read protected')
    try:
        m.need(run['passed'] and run['solver_completed'] and run['planned_samples']==151 and run['planned_steps']==30000 and run['actual_exit']==run['actual_Win32_exit']==0 and run['consumed_stats_unchanged'],'Completed owned native solver required')
        buildpath=L/'upl_tpi_x0_short_r1_reader.build.json';build=m.read(buildpath);m.need(build['passed'] and build['configuration']=='DebugCPU' and build['reader_invocations']==0 and build['consumed_stats_unchanged'],'Successful new closed reader build required')
        program=Path(m.bind(build['program'])['path']);plan=T/'configs/upl_tpi_x0_short_r1.clock.csv';data=Path(run['output'])/'data'
        for proc in psutil.process_iter(['pid','exe']):
            try:m.need(not proc.info['exe'] or Path(proc.info['exe']).resolve()!=program.resolve(),'Existing active exact reader protected')
            except (psutil.AccessDenied,psutil.NoSuchProcess):pass
        frames=sorted(data.glob('Part_????.bi4'));m.need(len(frames)==151,'Exactly151 saved native frames required')
        before=[m.stat(q) for q in [Path(__file__),runpath,buildpath,plan,*frames]]
        before += [m.bind(run[q]) for q in ['program','actual_call','Run_out','Run_csv']]
        before += [m.bind(build[q]) for q in ['program','source','core','dependencies']]
        for q in run['consumed']:m.bind(q)
        for q in before:m.bind(q)
        call=m.invoke(tag+'.native',[str(program),'--read','CPU',str(data),str(plan),'x0_short15',str(out)],T.parent,os.environ.copy())
        actual=m.read(call['path']);done=m.read(out/'completion.json')
        m.need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None and done['passed'] and done['samples']==151 and done['total_native_count']==1040 and done['native_total_arrays']==22 and done['noninitial_signed_dterror_intervals']==150 and done['post_open_frames']==141 and done['post_open_drained_particle_checks']==1410,'Complete original native safety and clock coverage required')
        for q in before:m.bind(q)
        m.save(check,dict(stage=tag+'.native',passed=True,run=m.stat(runpath),build=m.stat(buildpath),actual_call=call,completion=m.stat(out/'completion.json'),summary=done,files=[m.stat(q) for q in sorted(out.iterdir()) if q.is_file()],consumed=before,consumed_stats_unchanged=True,reader_invocations=1,solver_invocations=0,VTK_invocations=0,SHA_scans=0,stress_and_phase_review_pending=True,physical_acceptance=False))
    except Exception as error:
        if call is None and (L/(tag+'.native.call.json')).exists():call=m.stat(L/(tag+'.native.call.json'))
        if not check.exists():m.save(check,dict(stage=tag+'.native',passed=False,first_failure=str(error),actual_call=call,consumed=before,partial_native_preserved=True,solver_invocations=0,automatic_retry=False,physical_acceptance=False))
        raise

if __name__=='__main__':main()
