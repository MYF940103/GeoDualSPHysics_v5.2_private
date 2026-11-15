"""Two independently tagged 2-step CPU implementation runs, not a half test."""
import argparse
import os
from pathlib import Path
import psutil
import shutil
import c08_h18_wend_matrix_r1 as m

TAG='c08_h18_wall_c_retry_CPU_smoke_r1'
SCRIPT=Path(__file__).resolve()
T02=m.T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests'
SEED=T02/'outputs/upl_column_public_seed_r1/upl_column_public_smoke_r1'
READER_BUILD=T02/'logs/upl_column_public_reader_ReleaseCPU_r1.helper.json'
BEFORE=m.L/'c08_h18_wall_c_before_CPU_Debug_r2.build.json'
AFTER=m.L/'c08_h18_wall_c_retry_CPU_Debug_r1.build.json'
RUNTIME=m.L/'c08_h18_wall_c_retry_GPU_r1.build.json'
DEBUG_OMP=Path('D:/Program Files/VS2022/VC/Redist/MSVC/14.36.32532/debug_nonredist/x64/Microsoft.VC143.DebugOpenMP/vcomp140d.dll')
COMPARED=('original15.bin','physical.bin','clock.bin','common_j_theta.bin','soil_n.bin',
          'native_ids.csv','fixed_ids.csv','ledger.csv','fixed_samples.csv','history.csv',
          'last_poro.csv','columns.csv')


def idle(program):
    for p in psutil.process_iter(['exe']):
        try:m.need(not p.info['exe'] or Path(p.info['exe']).resolve()!=program.resolve(),'Exact program already active')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    m.need(a.execution_authorized,'Explicit root read and admission required')
    adpath=m.L/(TAG+'.admission.json');ad=m.read(adpath)
    m.need(ad['authorized'] and ad['script']==m.stat(SCRIPT) and ad['before_build']==m.stat(BEFORE)
           and ad['after_build']==m.stat(AFTER) and ad['reader_build']==m.stat(READER_BUILD)
           and ad['root_thread_id']==os.environ.get('CODEX_THREAD_ID')=='01a07683-bc64-7463-8db7-9ee6243967d8',
           'Exact current root comparison admission required')
    result=m.L/(TAG+'.check.json');m.need(not result.exists(),'Existing comparison protected')
    for label in ('before','after'):
        m.need(not (m.T/'outputs'/(TAG+'_'+label)).exists() and not (m.L/(TAG+'_'+label+'.solver.call.json')).exists()
               and not (m.L/(TAG+'_'+label+'.native.call.json')).exists(),'Existing run/read/partial protected')
    consumed=[m.stat(q) for q in (SCRIPT,adpath,BEFORE,AFTER,READER_BUILD,RUNTIME,DEBUG_OMP)]
    consumed += [m.stat(Path(str(SEED)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4')]
    before,after=m.read(BEFORE),m.read(AFTER);helper=m.read(READER_BUILD);runtime=m.read(RUNTIME)
    m.need(before['passed'] and before['actual_link_objects']==87 and before['retained_objects_count']==86
           and before['source_and_original_objects_stat_unchanged'] and after['passed']
           and before['source_candidate']==after['source_candidate'],'Both isolated same-source Debug builds required')
    header=m.read(m.bind(before['header_closure'])['path']);m.need(header['passed'] and not header['missing'] and not header['extra'],'Actual unique header sets must match')
    for ref in before['calls']+[after['call']]:
        c=m.read(m.bind(ref)['path']);m.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0,'Actual build tool exits required')
    reader=Path(helper['program']['path']);m.need(helper['passed'] and reader.stat().st_size==helper['program']['bytes'],'Retained public22 reader path/size required; historical SHA not rescanned')
    consumed.append(m.stat(reader))
    refs=[q for q in runtime['runtime'] if Path(q['path']).suffix.lower()=='.dll' or Path(q['path']).name=='DsphConfig.xml']+[m.stat(DEBUG_OMP)]
    programs=[];jobs=[]
    for label,b in [('before',before),('after',after)]:
        program=Path(m.bind(b['program'])['path']);consumed.append(m.stat(program));programs.append(program)
        for ref in refs:
            source=Path(m.bind(ref)['path']);target=program.parent/source.name;consumed.append(m.stat(source))
            m.need(not target.exists(),'Existing private CPU runtime leaf protected');shutil.copy2(source,target)
            m.need(target.read_bytes()==source.read_bytes(),'Runtime copy differs');consumed.append(m.stat(target))
    rec=dict(stage=TAG,passed=False,physical_acceptance=False,SHA_scans=0,half_tests=0,
             source_before_host_compiler_identity_not_fully_proven=True,solver_invocations=0,reader_invocations=0,jobs=jobs)
    try:
        for label,program in zip(('before','after'),programs):
            idle(program);tag=TAG+'_'+label;out=m.T/'outputs'/tag
            argv=[str(program),'-cpu','-ompthreads:1','-stable','-mdbc_freeslip',str(SEED),str(out),'-dirdataout','data','-svres','-nsteps:2']
            m.verify(consumed);m.save(m.L/(tag+'.start.json'),dict(stage=tag,program=m.stat(program),argv=argv,script=m.stat(SCRIPT),root_admission=m.stat(adpath),NoPen=False,steps=2,samples=3))
            rec['solver_invocations']+=1;call=m.invoke(tag+'.solver',argv,m.T.parents[3]/'src')
            text=(out/'Run.out').read_text(encoding='utf-8-sig');m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text,'Own normal CPU solver completion required')
            parts=sorted((out/'data').glob('Part_*.bi4'));m.need([q.name for q in parts]==['Part_0000.bi4','Part_0001.bi4','Part_0002.bi4'],'Three actual PARTs required')
            m.save(m.L/(tag+'.solver_completed.json'),dict(solver_completed=True,actual_call=call,PARTs=[m.stat(q) for q in parts],physical_acceptance=False))
            consumed.extend(m.stat(q) for q in parts)
            idle(reader);native=out/'native_r1';rec['reader_invocations']+=1
            readcall=m.invoke(tag+'.native',[str(reader),'--read','CPU',str(out/'data'),'3','0.0000025',str(native)],m.C)
            d=m.read(native/'completion.json')
            m.need(d['passed'] and d['samples']==3 and d['native_total_arrays']==22 and d['total_native_count']==1040
                   and d['soil_ledger_checks']==3000 and d['fixed_public_zero_marker_checks']==120
                   and d['planned_completed_steps']==2 and d['actual_end_s']==.000005
                   and d['noninitial_signed_dterror_intervals']==2 and d['max_noninitial_signed_dterror_s']<=1e-14
                   and d['post_open_frames']==0 and d['no_exclusions'] and d['all_exported_physical_fields_finite']
                   and d['max_ledger_relative_error']<=5e-13,'Original public22 native safety and coverage required')
            jobs.append(dict(label=label,program=m.stat(program),output=str(out),solver_call=call,reader_call=readcall,native_completion=m.stat(native/'completion.json')))
        equal=[]
        for leaf in COMPARED:
            p,q=[Path(j['output'])/'native_r1'/leaf for j in jobs];m.need(p.read_bytes()==q.read_bytes(),'Before/after byte mismatch: '+leaf);equal.append(dict(name=leaf,before=m.stat(p),after=m.stat(q)))
        m.verify(consumed);rec.update(passed=True,all22_coverage_comparison=True,five_binary_exports_equal=True,
            actual_PosDiv_V_rho_k_CSV_equal=True,all_initial_and_noninitial_signed_clock_bytes_equal=True,
            material_and_fixed_IDs_equal=True,compared=equal,nonempty_drainage_acceptance=False,force_stage_acceptance=False,
            new_failed_C_branch_exercised_by_CPU_smoke=False,consumed_stats_unchanged=True)
    except Exception as error:
        rec['first_failure']=str(error)
        raise
    finally:
        rec['consumed']=consumed;m.save(result,rec)


if __name__=='__main__':main()
