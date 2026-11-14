"""One separately reviewed preprocessing or CPU short run; no automatic chain/reader."""
import argparse, csv, os, re, sys
from pathlib import Path

T=Path(__file__).resolve().parents[1];R=T.parents[3]
C08=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
sys.path.insert(0,str(C08/'support'))
import c08_h18_wend_matrix_r1 as m

TAG='upl_tpi_x0_short_r1';L=T/'logs';PREP=L/(TAG+'.prepare.json')
SEED=T/'outputs'/(TAG+'_seed');PREFIX=SEED/TAG
BASE=C08/'logs/c08_preload_schema2_ReleaseCPU_r1.build.json'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['off','on'])
    p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    m.need(a.execution_authorized,'One independent root admission required')
    tag='upl_tpi_x0_short_r2_'+a.phase;check=L/(tag+'.run.json');m.need(not check.exists(),'Existing run, including failure, protected')
    before=[];call=None;out=SEED if a.phase=='seed' else T/'outputs'/tag
    m.need(not out.exists(),'Existing complete/partial output protected')
    try:
        prep=m.read(PREP);base=m.read(BASE)
        m.need(prep['passed'] and prep['planned_samples']==151 and prep['planned_completed_steps']==30000 and prep['dt_s']==5e-6,'Closed prepared scalar plan required')
        m.need(base['passed'] and base['configuration']=='ReleaseCPU' and base['consumed_stats_unchanged'],'Frozen actual CPU original required')
        before=[m.stat(q) for q in [Path(__file__),T/'notes/upl_tpi_x0_short_r1.md',PREP,BASE]]
        before += [m.bind(prep[q]) for q in ['XML','clock_plan']]
        before += [m.bind(base[q]) for q in ['program','source_capture','source_archive','actual_call']]
        env=os.environ.copy();env.pop('C08_TPI_X0',None);env['OMP_NUM_THREADS']='1'
        if a.phase=='seed':
            program=Path(base['program']['path']).parent/'GenCase_win64.exe';before.append(m.stat(program))
            argv=[str(program),str(Path(prep['XML']['path']).with_suffix('')),str(PREFIX),'-save:all']
        else:
            seedpath=L/(TAG+'_seed.run.json');seed=m.read(seedpath)
            m.need(seed['passed'] and seed['GenCase_invocations']==1 and seed['solver_invocations']==0,'One successful common seed required')
            before.append(m.stat(seedpath));before += [m.bind(q) for q in seed['generated_seed']]
            program=Path(base['program']['path'])
            if a.phase in ('off','on'):
                buildpath=C08/'logs/c08_tpi_x0_build_r2_ReleaseCPU.check.json';build=m.read(buildpath)
                m.need(build['passed'] and build['original_objects_retained']==85 and build['private_objects']==2 and build['source_archive']==base['source_archive'],'Reviewed two-overlay CPU build required')
                before.append(m.stat(buildpath));before += [m.bind(q) for q in build['private_source']];program=Path(m.bind(build['program'])['path'])
                originalpath=L/('upl_tpi_x0_short_r2_original.native.check.json');original=m.read(originalpath)
                m.need(original['passed'],'Original complete native read required before private OFF')
                before.append(m.stat(originalpath))
            if a.phase=='on':
                pairpath=L/('upl_tpi_x0_short_r2_off_pair.check.json');pair=m.read(pairpath)
                m.need(pair['passed'] and pair['all22_payload_bytes_equal'] and pair['all_signed_clock_bytes_equal'] and pair['samples']==151,'Complete same-CPU defaultOFF equivalence required before ON')
                before.append(m.stat(pairpath));env['C08_TPI_X0']='1'
            before.append(m.stat(program));argv=[str(program),'-cpu','-mdbc_freeslip','-ompthreads:1',str(PREFIX),str(out),'-dirdataout','data','-svres']
        m.verify(before);out.mkdir()
        # Shared owned-call helper writes its immutable tool receipt in parent C08/logs.
        call=m.invoke(tag+'.tool',argv,T.parent,env)
        actual=m.read(call['path']);m.need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual owned tool exit failed')
        m.verify(before)
        if a.phase=='seed':
            generated=[m.stat(PREFIX.with_suffix('.xml')),m.stat(PREFIX.with_suffix('.bi4')),m.stat(SEED/(TAG+'_Normals.nbi4'))]
            m.save(check,dict(stage=tag,passed=True,actual_call=call,program=m.stat(program),generated_seed=generated,consumed=before,consumed_stats_unchanged=True,GenCase_invocations=1,solver_invocations=0,reader_invocations=0,SHA_scans=0,physical_acceptance=False))
        else:
            with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
            m.need(len(rows)==1,'Exactly one native Run.csv row required');row=rows[0]
            m.need(int(row['Steps'])==30000 and int(row['PartFiles'])==151 and int(row['PartsOut'])==0 and int(row['Nbound'])==40,'Original runtime step/frame/exclusion/fixed counts differ')
            text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=[q for q in text.splitlines(keepends=True) if re.match(r'^Part_\d+\s',q)]
            m.need('Finished execution (code=0)' in text and not re.search(r'\*\*\* Exception',text),'Native normal completion required')
            m.save(check,dict(stage=tag,passed=True,solver_completed=True,actual_call=call,program=m.stat(program),input_prefix=str(PREFIX),output=str(out),configuration_phase=a.phase,private_X0_requested=a.phase=='on',dt_s=5e-6,planned_samples=151,planned_steps=30000,Run_csv=m.stat(out/'Run.csv'),Run_out=m.stat(out/'Run.out'),summary=row,last_original_console_line=parts[-1] if parts else None,actual_exit=actual['actual_Popen_wait_exit'],actual_Win32_exit=actual['actual_Win32_exit'],consumed=before,consumed_stats_unchanged=True,solver_invocations=1,reader_invocations=0,VTK_invocations=0,SHA_scans=0,native_review_pending=True,physical_acceptance=False,automatic_next_job=False))
    except Exception as error:
        if not check.exists():
            if call is None and (m.L/(tag+'.tool.call.json')).exists():call=m.stat(m.L/(tag+'.tool.call.json'))
            text=(out/'Run.out').read_text(encoding='utf-8-sig',errors='replace') if (out/'Run.out').exists() else ''
            parts=[q for q in text.splitlines(keepends=True) if re.match(r'^Part_\d+\s',q)]
            m.save(check,dict(stage=tag,passed=False,first_failure=str(error),actual_call=call,output=str(out),last_original_console_line=parts[-1] if parts else None,consumed=before,partial_outputs_preserved=True,unsaved_failure_time_reconstructed=False,automatic_retry=False,physical_acceptance=False))
        raise

if __name__=='__main__':main()
