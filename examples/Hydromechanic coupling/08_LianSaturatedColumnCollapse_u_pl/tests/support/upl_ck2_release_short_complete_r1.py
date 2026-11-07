"""Finish failed analysis metadata offline; retain original source, PNG/CSVs and solvers."""
import ast,json
from pathlib import Path
T=Path(__file__).resolve().parents[1];L=T/'logs';source=T/'support/upl_ck2_release_short_review_r1.py'
# Load only the reviewed definitions, never the old top-level artifact-producing code.
tree=ast.parse(source.read_text(encoding='utf-8'));nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='check' for t in node.targets):break
    nodes.append(node)
scope={'__file__':str(source)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),scope)
load,read,stat,table,need,np,frob,save=[scope[k] for k in ('load','read','stat','table','need','np','frob','save')]
cpu,_,cr=load('CPU');gpu,_,gr=load('GPU');cc=read(L/'upl_ck2_release_short_CPU_r1_native_r1.check.json');gc=read(L/'upl_ck2_release_short_GPU_r1_native_r1.check.json')
prefix=T/'figures/upl_ck2_release_short_r1';pairs=table(Path(str(prefix)+'_pairs.csv'));history=table(Path(str(prefix)+'_history.csv'));need(len(pairs)==len(cpu)==len(gpu) and len(history)==2*len(pairs),'Existing full analysis coverage differs')
for a,b,row in zip(cpu,gpu,pairs):
    x,y=a['row'],b['row'];need(x['completed_step']==y['completed_step']==int(row['completed_step']) and x['phase']==y['phase']==int(row['phase']) and x['actual_time_s']==float(row['actual_time_s']),'Actual-step/phase/time alignment differs');dp=b['p']-a['p'];du=b['u']-a['u']
    expected=dict(pressure_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZ_max_mm=float(np.linalg.norm(du,axis=1).max()),time_difference_s=abs(x['actual_time_s']-y['actual_time_s']),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(b['total']-a['total'])**2))),J_max_difference=float(np.abs(b['j']-a['j']).max()),k_max_difference_m_s=float(np.abs(b['k']-a['k']).max()))
    need(all(float(row[k])==v for k,v in expected.items()),'Existing pair CSV differs from independently recomputed actual arrays')
pressure=max(float(r['pressure_RMS_Pa']) for r in pairs);disp=max(float(r['material_XYZ_max_mm']) for r in pairs);dt=max(float(r['time_difference_s']) for r in pairs);passed=pressure<=5 and disp<=.005 and dt<=1e-14
check=L/'upl_ck2_release_short_r1.check.json';need(not check.exists(),'Existing final check protected')
result=dict(stage='upl_ck2_release_short_r1.review',passed=passed,backend_checks={b:stat(L/('upl_ck2_release_short_'+b+'_r1_native_r1.check.json')) for b in ('CPU','GPU')},run_checks={b:stat(L/('upl_ck2_release_short_'+b+'_r1.run.json')) for b in ('CPU','GPU')},source_builds=dict(CPU=cr['source_build'],GPU=gr['source_build']),programs=dict(CPU=cr['program'],GPU=gr['program']),memcheck_zero_errors_and_leaks=gr['memcheck_zero_errors_and_leaks'],actual_matched_pairs=len(pairs),phase_frame_counts=cc['actual_completion']['phase_saved_frames'],pressure_RMS_max_Pa=pressure,material_XYZ_max_mm=disp,time_error_max_s=dt,total_stress_Frobenius_RMS_max_Pa=max(float(r['total_stress_Frobenius_RMS_Pa']) for r in pairs),kappa_max_by_backend={b:max(r['row']['kappa_max'] for r in group) for b,group in (('CPU',cpu),('GPU',gpu))},outputs=[stat(Path(str(prefix)+s)) for s in ('.png','_history.csv','_pairs.csv')],physical_acceptance=False,full13s_or_paper_validation=False,no_half_or_old_control_rerun=True,metadata_only_repair='Original comparison PNG/CSVs retained; all pair metrics recomputed from original phase22 exports and equal CSV values exactly.',original_failure=stat(L/'upl_ck2_release_short_review_r1.analysis_failure.json'),original_analysis_source=stat(source),solver_or_decoder_reruns=0,SHA_scans=0)
save(check,result);print(json.dumps(result,indent=2));need(passed,'Original comparison bounds failed; preserve evidence')
