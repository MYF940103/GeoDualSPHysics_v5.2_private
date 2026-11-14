"""One DebugCPU two-update X0 implementation smoke after complete default-OFF equality."""
import csv,os,sys
from pathlib import Path
T=Path(__file__).resolve().parents[1];L=T/'logs';R=T.parents[3]
C8=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
sys.path.insert(0,str(C8/'support'))
import mdbc_partition_components_r3 as m
m.L=L

def main():
    m.need(sys.argv[1:]==['--execution-authorized'],'Independent root implementation-smoke admission required')
    tag='upl_tpi_x0_debug_smoke_r1';check=L/(tag+'.check.json');out=T/'outputs'/tag;call=None;before=[]
    m.need(not out.exists() and not check.exists() and not (L/(tag+'.call.json')).exists(),'Existing smoke protected')
    try:
        pairpath=L/'upl_tpi_x0_short_r2_off_pair.check.json';pair=m.read(pairpath)
        m.need(pair['passed'] and pair['all22_payload_bytes_equal'] and pair['all_signed_clock_bytes_equal'] and pair['samples']==151,'Complete defaultOFF implementation equality required')
        buildpath=C8/'logs/c08_tpi_x0_build_r2_DebugCPU.check.json';build=m.read(buildpath)
        m.need(build['passed'] and build['configuration']=='DebugCPU' and build['consumed_stats_unchanged'],'New private DebugCPU build required')
        seedpath=L/'upl_tpi_x0_short_r1_seed.run.json';seed=m.read(seedpath);m.need(seed['passed'],'Common actual GenCase required')
        program=m.bind(build['program']);prefix=T/'outputs/upl_tpi_x0_short_r1_seed/upl_tpi_x0_short_r1'
        before=[m.stat(q) for q in [Path(__file__),pairpath,buildpath,seedpath]]+[program]+[m.bind(q) for q in seed['generated_seed']]+[m.bind(q) for q in build['private_source']]
        for q in before:m.bind(q)
        env=os.environ.copy();env['C08_TPI_X0']='1';env['OMP_NUM_THREADS']='1';out.mkdir()
        call=m.invoke(tag,[program['path'],'-cpu','-mdbc_freeslip','-ompthreads:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:2'],T.parent,env)
        actual=m.read(call['path']);summary=m.read(out/'C02TpiX0.summary.json')
        with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
        m.need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual DebugCPU exit failed')
        m.need(len(rows)==1 and int(rows[0]['Steps'])==2 and int(rows[0]['PartFiles'])==2 and int(rows[0]['PartsOut'])==0,'Only two actual updates/two real saved frames admitted')
        m.need(summary['completed'] and all(summary[k]==2 for k in ['commits','pre_calls','corr_calls','J_corrector_captures','endpoint_calls','native_save_events']) and summary['actual_end_s']==1e-5 and summary['alpha']==.5 and summary['beta']==0,'Actual implementation lifecycle counters differ')
        for q in before:m.bind(q)
        m.save(check,dict(stage=tag,passed=True,actual_call=call,summary=summary,Run_csv=m.stat(out/'Run.csv'),Run_out=m.stat(out/'Run.out'),sidecar=m.stat(out/'C02TpiX0.csv'),consumed=before,consumed_stats_unchanged=True,actual_updates=2,declared_0p15_window_completed=False,independent_native_reader_invocations=0,solver_invocations=1,Debug_not_Release_bit_truth=True,physical_acceptance=False,automatic_next_job=False,SHA_scans=0))
    except Exception as error:
        if call is None and (L/(tag+'.call.json')).exists():call=m.stat(L/(tag+'.call.json'))
        if not check.exists():m.save(check,dict(stage=tag,passed=False,first_failure=str(error),actual_call=call,consumed=before,partial_outputs_preserved=True,physical_acceptance=False,automatic_retry=False))
        raise

if __name__=='__main__':main()
