"""Offline adoption of the one completed CPU smoke; never invokes a solver, reader, build or queue."""
import argparse,csv,json,re,struct
from pathlib import Path
import upl_c08_asplane_run_r1 as original
from upl_c08_asplane_summary_r1 import summary

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_asplane_smoke_CPU_r1';OUT=T/'outputs'/TAG
CHECK=L/(TAG+'.adopted_run.json');RUN=L/(TAG+'.run.json');CALL=L/(TAG+'.call.json');START=L/(TAG+'.start.json')
need,read,stat=original.need,original.read,original.stat

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline adoption');need(not CHECK.exists(),'Existing adoption preserved')
    before=[];result=dict(stage=TAG+'.adopted_run',passed=False,adoption_only=True,solver_invocations=0,decoder_invocations=0,build_invocations=0,queue_invocations=0,physical_acceptance=False,native_review_pending=True,SHA_scans=0)
    try:
        run,call,start=read(RUN),read(CALL),read(START);before=[stat(p) for p in (RUN,CALL,START,Path(__file__),T/'support/upl_c08_asplane_summary_r1.py',T/'notes/upl_c08_asplane_summary_r1.md')]
        need(not run['passed'] and run['actual_exit']==run['actual_Win32_exit']==run['actual_tool_exit']==0 and run['ownership_errors']==[],'Original runtime failed or ownership not closed')
        need(run['first_failure'].startswith("invalid literal for int() with base 10: '2.55)") and run['solver_invocations']==1 and run['reader_invocations']==run['postprocessor_invocations']==run['PartVTK_invocations']==0,'Only this summary parser failure is adoptable')
        need(stat(CALL)==run['actual_call'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['actual_solver_Win32_exit']==0 and call['ownership_errors']==[],'Actual typed exits/call binding differ')
        admission=Path(call['admission']['path']);need(stat(admission)==call['admission']==start['admission'],'Actual admission changed');ad=read(admission);before.append(stat(admission))
        identity=call['actual_solver'];need(identity==call['actual_outer']==start['actual_solver']==start['actual_outer'] and identity['argv']==call['arguments']==ad['argv']==ad['solver_argv'] and identity['parent_pid']==ad['owner']['pid']==start['owner']['pid'],'Original process creation/argv/parent evidence differs')
        need(Path(identity['exe']).samefile(ad['program']['path']) and ad['target_backend']=='CPU' and ad['policy']==original.POLICY and ad['ArtificialStress'] and ad['AS_phase_policy']=='ReleaseOnly' and ad['AS_coef']==.2 and ad['AS_exp']==2.55,'Original program/backend/AS/NoPen scope differs')
        need(ad['planned_new_updates']==40 and ad['planned_global_end']==4000040 and ad['expected_saved_frames']==1,'Original one40-update smoke plan differs')
        for entry in run['consumed']+ad['consumed']+[ad['program'],ad['source_build'],ad['source_pre_file'],ad['planned_steps'],run['GenCase_call']]:need(stat(entry['path'])==entry,'Original consumed stat changed: '+entry['path']);before.append(entry)
        gen=read(run['GenCase_call']['path']);need(gen['actual_Popen_wait_exit']==gen['actual_Win32_exit']==0 and gen['ownership_failure'] is None,'Original GenCase did not pass')
        plan=Path(ad['planned_steps']['path']);need(plan.samefile(OUT/'planned_steps.csv'),'Original plan binding differs')
        with plan.open(encoding='utf-8',newline='') as f:planned=list(csv.DictReader(f))
        need(planned==[dict(part='0',completed_step='4000040')],'Original frozen saved-step plan differs')
        xml=OUT/(TAG+'.xml');original.check_input(xml,'10.0001','0.0001',True,True);need(Path(ad['source_pre_file']['path']).samefile(original.PRE),'Original source PRE differs')
        row=summary(OUT/'Run.csv');text=(OUT/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((OUT/'data').glob('Part_*.bi4'))
        need(int(row['Steps'])==4000040 and int(row['PartFiles'])==1 and int(row['Np'])==7060 and int(row['Nbound'])==int(row['Nfixed'])==2060 and all(int(row[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual strict summary registry/step/count/no-exclusion failed')
        need(row['RunName']==TAG and row['Hardware']=='CPU' and [p.name for p in parts]==['Part_0000.bi4'],'Actual run/backend/native sequence differs')
        need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+original.POLICY in text,'Actual normal finish/AS/NoPen log differs')
        for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',2.55)):
            matches=re.findall(r'^\s*'+key+r'=\s*([0-9.eE+-]+)\s*$',text,re.M)
            need(len(matches)==1 and struct.pack('<f',float(matches[0]))==struct.pack('<f',value),'Actual equals-sign AS coefficient/exponent log differs')
        need(text.count('GravityPreload: phase=released ')==1 and 'retired=260; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Original unique260 release/phase differs')
        imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==4000000,'Actual loader source clock/import missing')
        before += [stat(p) for p in (xml,OUT/'Run.csv',OUT/'Run.out',*parts)]
        need(all(stat(e['path'])==e for e in before),'Closed inputs changed during offline adoption')
        raw=(OUT/'Run.csv').read_text(encoding='utf-8-sig').splitlines();header_columns=len(raw[0].split(';'));raw_columns=len(raw[1].split(';'))
        result.update(passed=True,actual_exit=0,actual_Win32_exit=0,ArtificialStress=True,policy=original.POLICY,original_run=stat(RUN),original_run_passed=False,original_run_first_failure=run['first_failure'],original_solver_invocations=1,original_actual_exit=0,original_actual_Win32_exit=0,original_call=stat(CALL),original_start=stat(START),original_admission=stat(admission),actual_solver=identity,
                      actual_steps=4000040,saved_frames=1,summary=row,header_columns=header_columns,raw_delimited_columns=raw_columns,reconstructed_columns=len(row),only_Configuration_AS_semicolon_rejoined=True,original_numeric_column_strings_preserved=True,AS_log_separator_observed='=',
                      actual_source_time_from_loader=float(imported[0][0]),program=ad['program'],source_build=ad['source_build'],source_pre_file=ad['source_pre_file'],input_xml=stat(xml),Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(p) for p in parts],consumed_stats_unchanged=True,original_run_or_CSV_rewritten=False,source_inputs_or_program_modified=False,all_original_post_run_gates_rechecked=True,AS_active_typed_metadata_pending=True)
    except Exception as error:result.update(first_failure=str(error))
    result['consumed']=before
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(passed=result['passed'],receipt=str(CHECK),first_failure=result.get('first_failure'),solver_invocations=0,decoder_invocations=0)));need(result['passed'],result.get('first_failure','Offline adoption failed'))

if __name__=='__main__':main()
