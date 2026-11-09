"""Interpret the sealed two-snapshot actual CPU gradients; no force, integration or theory acceptance."""
import argparse,csv,json,os,re
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_pair_gradient_review_r1';SOURCE='upl_c08_pair_gradient_cpu_r1'
CHECK=L/(TAG+'.check.json');FILES={k:T/'figures'/(TAG+'_'+k+s) for k,s in (('pairs','.csv'),('focus','.csv'),('closure','.png'),('stress','.png'))}
need,read,stat,bind=e.need,e.read,e.stat,e.bind
AXES=('xx','xy','xz','yx','yy','yz','zx','zy','zz');SIX=('xx','yy','zz','xy','yz','xz')


def table(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def write(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def tensor(row,prefix):
    a=np.zeros((3,3))
    for key,i,j in (('xx',0,0),('yy',1,1),('zz',2,2),('xy',0,1),('yz',1,2),('xz',0,2)):a[i,j]=a[j,i]=float(row[prefix+key+'_Pa' if prefix=='sigma_' else prefix+key+'_Pa_s'])
    return a


def focus_rows(raw,K,G):
    rows=[];matrices={}
    for q in raw:
        r={k:(v if k=='mode' else float(v)) for k,v in q.items()};identity,part=int(r['native_id']),int(r['part']);M=np.array([r['L_sum_'+s] for s in AXES]).reshape(3,3);D=(M+M.T)*.5;W=(M-M.T)*.5;S=tensor(q,'sigma_').astype('f4').astype('f8');A=tensor(q,'Rsigma_');elastic=K*np.trace(D)*np.eye(3)+2*G*(D-np.trace(D)*np.eye(3)/3);spin=W@S-S@W;shadow=elastic+spin;ev=np.linalg.eigvalsh(D[np.ix_([0,2],[0,2])]);matrices[(part,identity)]=(M,D,W,r)
        r.update(gradient_trace_s_1=float(np.trace(M)),theta_minus_gradient_trace_s_1=r['theta_s_1']-float(np.trace(M)),D_XZ_eigen_min_s_1=float(ev[0]),D_XZ_eigen_max_s_1=float(ev[-1]),D_Frobenius_s_1=float(np.linalg.norm(D)),W_Frobenius_s_1=float(np.linalg.norm(W)),actual_Rsigma_Frobenius_Pa_s=float(np.linalg.norm(A)),actual_Rsigma_trace_over_3K_s_1=float(np.trace(A)/(3*K)),actual_Rsigma_trace_minus_3Ktheta_Pa_s=float(np.trace(A)-3*K*r['theta_s_1']),double_shadow_elastic_Frobenius_Pa_s=float(np.linalg.norm(elastic)),double_shadow_spin_Frobenius_Pa_s=float(np.linalg.norm(spin)),double_shadow_spin_trace_Pa_s=float(np.trace(spin)),double_shadow_total_Frobenius_Pa_s=float(np.linalg.norm(shadow)),actual_minus_double_shadow_Frobenius_Pa_s=float(np.linalg.norm(A-shadow)))
        for k,i,j in (('xx',0,0),('yy',1,1),('zz',2,2),('xy',0,1),('yz',1,2),('xz',0,2)):r['double_shadow_spin_'+k+'_Pa_s']=float(spin[i,j]);r['double_shadow_elastic_'+k+'_Pa_s']=float(elastic[i,j])
        rows.append(r)
    return rows,matrices


def pair_rows(raw,matrices):
    rows=[]
    for q in raw:
        r={k:float(v) for k,v in q.items()};part,i,j=int(r['part']),int(r['id_i']),int(r['id_j']);Li,Di,Wi,fi=matrices[part,i];Lj,Dj,Wj,fj=matrices[part,j];D=(Di+Dj)*.5;W=(Wi+Wj)*.5;n=np.array([r['n'+c] for c in 'xyz']);dv=np.array([r['dv'+c+'_m_s'] for c in 'xyz']);area_rate=.5*(Li[0,0]+Li[2,2]+Lj[0,0]+Lj[2,2]);normal=float(n@D@n);spin_normal=float(n@W@n);v_t=dv-n*r['rdot_m_s'];da=np.array([fi['total_a_'+c+'_m_s2']-fj['total_a_'+c+'_m_s2'] for c in 'xyz']);radial_a=float(n@da);curvature=float(v_t@v_t/r['r_m']);res=r['directional_residual_over_r_s_1']
        r.update(r_over_dp=r['r_m']/.04,mean_gradient_area_trace_s_1=float(area_rate),normal_isotropic_XZ_rate_s_1=float(area_rate*.5),normal_deviatoric_XZ_rate_s_1=normal-area_rate*.5,normal_spin_rate_s_1=spin_normal,resolved_plus_residual_identity_difference_s_1=r['rdot_over_r_s_1']-normal-res,signed_residual_over_actual_closure_ratio=res/r['rdot_over_r_s_1'] if r['rdot_over_r_s_1']!=0 else None,relative_total_a_normal_m_s2=radial_a,tangential_curvature_m_s2=curvature,rddot_m_s2=radial_a+curvature,J_i=fi['J'],J_j=fj['J'],mean_J=.5*(fi['J']+fj['J']),theta_i_s_1=fi['theta_s_1'],theta_j_s_1=fj['theta_s_1'],saved_FS_i=int(fi['saved_FS']),saved_FS_j=int(fj['saved_FS']),actual_FS_i=int(fi['actual_FS']),actual_FS_j=int(fj['actual_FS']))
        rows.append(r)
    return rows


def plots(pairs,focus):
    labels=['%d/%d @%.2f'%(r['id_i'],r['id_j'],r['tau_s']) for r in pairs];x=np.arange(len(pairs));fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained')
    for k,(key,label) in enumerate((('rdot_over_r_s_1','actual rdot/r'),('n_sym_meanL_n_s_1','mean-gradient resolved'),('directional_residual_over_r_s_1','directional residual'))):axes[0].bar(x+(k-1)*.24,[r[key] for r in pairs],width=.24,label=label)
    for k,(key,label) in enumerate((('normal_isotropic_XZ_rate_s_1','XZ isotropic part'),('normal_deviatoric_XZ_rate_s_1','XZ deviatoric part'),('normal_spin_rate_s_1','normal spin (zero analytically)'))):axes[1].bar(x+(k-1)*.24,[r[key] for r in pairs],width=.24,label=label)
    for ax in axes:ax.set_xticks(x,labels,rotation=18);ax.set_ylabel('Signed directional rate [1/s]');ax.axhline(0,color='k',lw=.6);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    axes[0].set_title('Negative means closing; residual is not an error proof');axes[1].set_title('Resolved strain: 2D area/isotropic and shear parts');fig.suptitle('Two actual frozen CPU force snapshots; no trajectory or operator switch')
    with FILES['closure'].open('xb') as f:fig.savefig(f,format='png',dpi=170)
    plt.close(fig);labels=['%d @%.2f'%(r['native_id'],r['tau_s']) for r in focus];x=np.arange(len(focus));fig,axes=plt.subplots(1,3,figsize=(18,5),layout='constrained')
    for k,(key,label) in enumerate((('D_XZ_eigen_min_s_1','min strain'),('D_XZ_eigen_max_s_1','max strain'),('W_Frobenius_s_1','spin Frobenius'))):axes[0].bar(x+(k-1)*.24,[r[key] for r in focus],width=.24,label=label)
    for k,(key,label) in enumerate((('actual_Rsigma_Frobenius_Pa_s','actual full rate'),('double_shadow_elastic_Frobenius_Pa_s','elastic shadow'),('double_shadow_spin_Frobenius_Pa_s','spin shadow'))):axes[1].bar(x+(k-1)*.24,[r[key]/1e6 for r in focus],width=.24,label=label)
    for key,label,style in (('theta_s_1','actual theta','o-'),('gradient_trace_s_1','trace of grouped L','x--'),('actual_Rsigma_trace_over_3K_s_1','actual trace(rate)/(3K)','+:')):axes[2].plot(x,[r[key] for r in focus],style,label=label,ms=5)
    for ax in axes:ax.set_xticks(x,labels,rotation=50,ha='right');ax.axhline(0,color='k',lw=.6);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Rate [1/s]');axes[1].set_ylabel('Stress-rate norm [MPa/s]');axes[2].set_ylabel('Volume-rate comparison [1/s]');fig.suptitle('Actual grouped gradients and full stress rate; double tensor decomposition is a shadow')
    with FILES['stress'].open('xb') as f:fig.savefig(f,format='png',dpi=170)
    plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline extraction');need(not CHECK.exists() and not any(p.exists() for p in FILES.values()),'Existing complete/partial derived products protected');before=[];result=dict(stage=TAG,passed=False,analysis_completed=False,physical_acceptance=False,force_evaluations=0,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
    try:
        qp=L/(SOURCE+'.check.json');q=read(qp);need(q['passed'] and q['consumed_stats_unchanged'] and q['force_evaluations']==2 and q['actual_physical_steps']==0 and q['operator_variants']==0 and q['source_parts']==[13,14] and q['full_velocity_gradient_observed'] and q['gradient_observed_IDs']==[7011,7012,6230,6231] and q['baseline_alignment']['field_checks']==210224 and q['baseline_alignment']['mismatched_fields']==0,'Actual passed two-state output-only gradient component required');entries={Path(v['path']).name:bind(v) for v in q['files'] if Path(v['path']).name in ('gradient_pairs.csv','focus.csv','pairs.csv','calls.csv','Run.out')};need(len(entries)==5,'Closed small output files required')
        before=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(e.__file__),qp)]+[bind(q[k]) for k in ('component_build','component_completion','actual_call','source_run','source_native','source_prefix_proof')]+list(entries.values());done=read(q['component_completion']['path']);need(done['passed'] and done['physical_steps']==done['material_return_calls']==0 and done['gradient_pair_rows']==4 and done['focus_rows']==8,'Original completion scope differs')
        text=Path(entries['Run.out']['path']).read_text(encoding='utf-8-sig');moduli=[]
        for label in ('Bulk Modulus','Shear Modulus'):
            hits=re.findall(r'^\s*'+label+r':\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(hits)==1,'Unique actual logged modulus required');moduli.append(float(hits[0]))
        K,G=moduli;fraw=table(Path(entries['focus.csv']['path']));praw=table(Path(entries['gradient_pairs.csv']['path']));need(len(fraw)==8 and len(praw)==4,'Two-state focus/pair coverage differs');focus,matrices=focus_rows(fraw,K,G);pairs=pair_rows(praw,matrices);need({(int(r['part']),int(r['native_id'])) for r in focus}=={(p,i) for p in (13,14) for i in (7011,7012,6230,6231)},'Actual focus IDs differ');write(FILES['pairs'],pairs);write(FILES['focus'],focus);plots(pairs,focus);need(all(stat(v['path'])==v for v in before),'Closed inputs changed')
        result.update(passed=True,analysis_completed=True,source_component=stat(qp),source_parts=[13,14],pair_observations=pairs,actual_logged_K_Pa=K,actual_logged_G_Pa=G,moduli_from_sealed_Run_out=True,no_new_numerical_or_theory_acceptance_gate=True,residual_is_not_hourglass_or_error_proof=True,gradient_sum_is_double_sum_of_actual_float_groups=True,double_shadow_is_not_literal_float_replay=True,CPU_shared_baseline_fields_exactly_aligned=True,old_all5000_Rsigma_comparison_available=False,temporal_growth_or_cause_claimed=False,visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=before,consumed_stats_unchanged=bool(before) and all(stat(v['path'])==v for v in before),outputs=[stat(p) for p in FILES.values() if p.exists()])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(passed=result['passed'],check=str(CHECK),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
