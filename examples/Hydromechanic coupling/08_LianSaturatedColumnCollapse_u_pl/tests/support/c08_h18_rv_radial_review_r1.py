"""One offline review of the passed ten-state radial CPU component; no tools.

Root-only command after a full source read:
  D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_radial_review_r1.py --execution-authorized
The radial certificate is independent of the old vector work+2form identity.
"""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import pandas as pd
import c08_h18_wend_matrix_r1 as m
import c08_h18_rv_onset_review_r1 as onset

T,L=m.T,m.L;TAG='c08_h18_rv_radial_review_r1';SOURCE='c08_h18_rv_radial_candidate_r1'
GATE=L/(SOURCE+'.check.json');OLD=L/'c08_h18_rv_onset_review_r1.check.json'
NOTE=T/'notes'/(TAG+'.md');PARTS=onset.PARTS;CASES=onset.CASES;TERMS=onset.ALL_TERMS
KEYS=['case','part','time_s','tau_s','completed_step','ID_i','ID_j']
FOCUS_KEYS=['case','part','time_s','tau_s','completed_step','pair_i','pair_j','native_id']
EXAMPLES=onset.EXAMPLES;DT=5e-6;N=5000;ALPHA=.1


def take(entry,used):m.bind(entry);used.append(entry);return Path(entry['path'])


def read_table(path,count):
    q=pd.read_csv(path,float_precision='round_trip')
    m.need(len(q)==count and np.isfinite(q.select_dtypes(include=np.number).to_numpy(dtype=float)).all(),path.name+' must retain every finite original row')
    return q


def gamma(count):
    x=float(count)*(.5*np.finfo(float).eps);m.need(math.isfinite(x) and 0<=x<1,'Invalid declared radial operation count');return x/(1-x)


def export_equal(actual,expected,scale=None):
    """CSV recomputation allowance only; original measured <= budget gates stay exact."""
    if scale is None:scale=abs(actual)+abs(expected)
    budget=8*np.finfo(float).eps*scale
    m.need(abs(actual-expected)<=budget,'CSV radial formula recomputation exceeds export arithmetic allowance')


def utilization(value,budget,absolute=True):
    m.need(math.isfinite(value) and math.isfinite(budget) and budget>=0,'Nonfinite/negative original radial budget')
    amount=abs(value) if absolute else max(value,0.)
    m.need(amount<=budget,'Original independent radial certificate rejected')
    return amount/budget if budget else 0.


def load(used):
    c=m.read(GATE);old=m.read(OLD)
    m.need(c['passed'] and c['consumed_stats_unchanged'] and c['physical_steps']==c['material_return_calls']==0
           and old['passed'] and old['consumed_stats_unchanged'] and old['analysis_complete'],'Both previously passed protected component/review bindings are required')
    used.extend([m.stat(GATE),m.stat(OLD),m.stat(Path(__file__)),m.stat(NOTE),m.stat(Path(m.__file__)),m.stat(Path(onset.__file__))])
    # Stat inventories only. No SHA, BI4 scan, decoding or old 50000-row reread.
    m.verify(c['consumed']);m.verify(old['consumed']);used.extend(c['consumed'])
    b=m.read(take(c['build'],used));call=m.read(take(c['actual_call'],used));done=m.read(take(c['completion'],used))
    program=take(b['program'],used);take(b['source'],used);take(b['note'],used)
    child=call['child'];m.need(b['passed'] and b['consumed_stats_unchanged'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0
        and call['ownership_failure'] is None and Path(call['program']).resolve()==program.resolve()
        and Path(child['exe']).resolve()==program.resolve() and child['parent_pid']==call['owner']['pid']
        and child['argv']==[str(program)]+call['arguments'] and child['creation_filetime_100ns']>0,'Actual passed source/program/owned component call differs')
    expected=dict(trajectory_count=2,source_samples_each=91,actual_force_calls=10,actual_Darcy_calls=20,extra_Darcy_calls=10,
        actual_DtVariable_false_calls=20,bare_CPU_control_bit_rows=50000,external_GPU_RHS_bit_rows=0,literal_rate_rows=100000,
        soil_rows=50000,pair_rows=80,focus_rows=160,manufactured_rows=50,limiter_scalar_fixture_rows=8,clock_rows=10,
        physical_steps=0,material_return_calls=0,filter_calls=0)
    m.need(done['stage']==SOURCE and done['passed'] and done['parts']==list(PARTS) and all(done[k]==v for k,v in expected.items())
        and done['operator']=='compression_only_radial_residual_limiter' and done['alpha']==ALPHA
        and done['actual_CPUcell_RV_graph'] and done['reverse_membership_required'] and done['frozen_Euler_only']
        and not done['old_vector_form_identity_claimed'] and not done['GPU_bittruth_claimed'] and not done['physical_acceptance'], 'Original radial component coverage/scope differs')
    for name in ('max_final_float_budget_ratio','max_expanded_budget_ratio'):
        m.need(math.isfinite(done[name]) and 0<=done[name]<=1,'Original literal/final-float budget failed')
    u=m.read(take(old['AS_units_resolution'],used))
    m.need(u['passed'] and u['actual_AS_tensor_nn_Pa_header_is_correct'] and u['actual_AS_tensor_in_active_branch_units']=='Pa'
        and u['no_CSV_rename_or_rescale_required'] and u['raw_output_source_build_and_numeric_gates_unchanged'], 'Correct current-J rho=1 AS Pa resolution r2 required')
    take(u['supersedes_without_overwriting'],used);take(u['source_archive'],used)
    tables={};paths={}
    for name,count in (('pairs',80),('focus',160),('soil',50000),('metrics',10),('manufactured',50),('limiter_fixtures',8),('selected_clocks',10)):
        path=T/'outputs'/SOURCE/(name+'.csv');take(onset.unique_entry(c['files'],path),used);paths[name]=path
        if name!='selected_clocks':tables[name]=read_table(path,count)
    prior={};prior_paths={}
    for name,count in (('pairs',80),('focus_RHS',160),('metrics',10),('RHS_summary',10),('selected_clocks',10)):
        path=T/'figures'/('c08_h18_rv_onset_review_r1_'+name+'.csv');take(onset.unique_entry(old['files'],path),used);prior_paths[name]=path
        if name!='selected_clocks':prior[name]=read_table(path,count)
    m.need(paths['selected_clocks'].read_bytes()==prior_paths['selected_clocks'].read_bytes(),'All10 original selected clock records must remain byte-identical')
    clocks=onset.read_csv(paths['selected_clocks']);clockmap={}
    for q in clocks:
        key=(q['case'],int(q['part']));m.need(key not in clockmap and key[0] in CASES and key[1] in PARTS,'Duplicate/unknown selected clock')
        m.need(float(q['dt_s'])==DT and float(q['signed_dterror_s'])<=1e-14 and int(q['native_IDs'])==6805
            and int(q['saved_step'])+1==int(q['completed_step']) and int(q['dterror_interval_empty'])==0,'Original actual scalar/signed clock gate failed')
        clockmap[key]=q
    m.need(set(clockmap)=={(c,p) for c in CASES for p in PARTS},'All10 actual source clocks required')
    for part in PARTS:m.need(clockmap[('original',part)]['time_s']==clockmap[('rv',part)]['time_s'],'Actual state times differ; no interpolation is allowed')
    for df in list(tables.values())+list(prior.values()):
        if 'time_s' not in df:continue
        for key,g in df.groupby(['case','part'],sort=False):
            q=clockmap[key];m.need((g.time_s==float(q['time_s'])).all() and (g.completed_step==int(q['completed_step'])).all()
                and (g.tau_s==float(q['tau_from_actual_release_s'])).all(),'An actual source step/time/tau was changed')
    selection=Path(call['arguments'][call['arguments'].index('--selection')+1]);take(onset.unique_entry(c['consumed'],selection),used)
    selected=onset.read_csv(selection);wanted={(q['case'],int(q['part']),int(q['id_i']),int(q['id_j'])) for q in selected}
    pairs=tables['pairs'];focus=tables['focus'];m.need(len(selected)==len(wanted)==80,'All80 root-unique selections required')
    for frame in (pairs,prior['pairs']):m.need(not frame.duplicated(['case','part','ID_i','ID_j']).any()
        and set(zip(frame['case'],frame.part,frame.ID_i,frame.ID_j))==wanted,'All80 actual same-ID pairs must be preserved')
    m.need(not focus.duplicated(['case','part','pair_i','pair_j','native_id']).any(),'Focus endpoints must not be deduplicated')
    for key,g in focus.groupby(['case','part','pair_i','pair_j'],sort=False):
        m.need(key in wanted and len(g)==2 and set(g.native_id)==set(key[2:]),'All160 root-selected pair endpoints required')
    return tables,prior,paths,clockmap,done


def radial_certificate(row):
    E=int(row.edges);degree=int(row.max_degree)
    m.need(row.edges==E and E>0 and row.max_degree==degree and degree>0 and 0<=row.active_edges<=E
        and 0<=row.closing_positive_residual_edges<=E,'Actual graph/count gate failed')
    for name,value in (('net_gamma',gamma(degree+N)),('power_gamma',gamma(19*E+6*N)),('torque_gamma',gamma(13*E+4*N))):
        export_equal(float(row[name]),value)
    export_equal(row.lambda_upper_s_1,2*row.degree_upper_s_1)
    export_equal(row.dt_lambda_half,DT*row.degree_upper_s_1)
    m.need(row.degree_upper_s_1>0 and row.max_condition>0 and row.dissipation_D_W_m>=0,'Original weighted-degree/LS/dissipation gate failed')
    # Recompute only observable export algebra. Full graph budget formation stays
    # justified by the bound source/component, not by these sparse summary rows.
    export_equal(row.power_error_W_m,abs(row.node_power_W_m+row.dissipation_D_W_m),
        abs(row.node_power_W_m)+abs(row.dissipation_D_W_m)+abs(row.power_error_W_m))
    export_equal(row.torque_reduce_error_N,abs(row.node_torque_N-row.pair_torque_N),
        abs(row.node_torque_N)+abs(row.pair_torque_N)+abs(row.torque_reduce_error_N))
    export_equal(row.torque_budget_N,row.central_budget_N+row.torque_reduce_budget_N)
    ratios={
        'power_error':utilization(row.power_error_W_m,row.power_budget_W_m),
        'positive_power':utilization(row.node_power_W_m,row.power_budget_W_m,False),
        'net':utilization(row.net_norm_N_m,row.net_budget_N_m),
        'central_torque':utilization(row.pair_torque_N,row.central_budget_N),
        'torque_reduction':utilization(row.torque_reduce_error_N,row.torque_reduce_budget_N),
        'total_torque':utilization(row.node_torque_N,row.torque_budget_N),
        'normalization':utilization(row.normalization_max_ratio,1.),
        'LS_backward':utilization(row.LS_backward_max_ratio,1.),
        'dt_lambda_half':utilization(row.dt_lambda_half,1.),
        'frozen_Euler_positive':utilization(row.frozen_Euler_deltaE_J_m,row.frozen_Euler_budget_J_m,False),
        'float_commit':utilization(row.float_commit_budget_ratio,1.),
        'committed_positive_power':utilization(row.committed_power_W_m,row.committed_power_budget_W_m,False),
        'committed_net':utilization(row.committed_net_norm_N_m,row.committed_net_budget_N_m),
        'committed_torque':utilization(row.committed_torque_N,row.committed_torque_budget_N),
        'committed_Euler_positive':utilization(row.committed_Euler_deltaE_J_m,row.committed_Euler_budget_J_m,False)}
    m.need(row.normalization_max_ratio>=0 and row.LS_backward_max_ratio>=0 and row.dt_lambda_half>=0
        and row.float_commit_budget_ratio>=0 and row.max_float_commit_error_N_m>=0,'Original nonnegative certificate measurements differ')
    return ratios


def gates(tables,clockmap):
    metrics=tables['metrics'];made=tables['manufactured'];rows=[]
    m.need(set(zip(metrics['case'],metrics.part))==set(clockmap) and not metrics.duplicated(['case','part']).any(),'All10 unique metric states required')
    for index,q in enumerate(metrics.itertuples(),1):
        m.need(q.actual_force_calls_cumulative==index and q.actual_Darcy_calls_cumulative==2*index
            and q.bare_CPU_control_bit_rows_cumulative==N*index,'Actual10/20/50000 cumulative calls differ')
        m.need(q.wall_active+q.wall_inactive==q.wall_NpbOk and q.wall_NpbOk+q.wall_ignored==1805,'Original effective wall partition differs')
        m.need(q.base_DtVariable==q.candidate_DtVariable==DT and q.necessary_bound_s>=DT
            and q.force_bound_s>=DT and q.wave_bound_s>=DT and q.pore_bound_s>=DT and q.k_gradient_bound_s>=DT,'Original5us necessary limits failed')
        export_equal(q.necessary_bound_s,min(q.force_bound_s,q.wave_bound_s,q.pore_bound_s))
    for kind,df in (('actual',metrics),('manufactured',made)):
        for _,q in df.iterrows():
            r=dict(scope=kind,case=q['case'],part=int(q.part),manufacture=int(q.manufacture) if kind=='manufactured' else -1)
            r.update(radial_certificate(q))
            if kind=='manufactured':
                m.need(q.affine_LS_forward_budget_s_1>=0,'Original affine LS forward budget is invalid')
                r['affine_q']=utilization(q.max_q_m_s,q.affine_q_budget_m_s)
                r['affine_force']=utilization(q.max_force_N_m,q.affine_force_budget_N_m)
                # The synthetic evaluation does not commit into float Ace.
                for name in ('max_added_accel_m_s2','max_float_commit_error_N_m','float_commit_budget_ratio','committed_power_W_m','committed_power_budget_W_m',
                    'committed_net_norm_N_m','committed_net_budget_N_m','committed_torque_N','committed_torque_budget_N','committed_Euler_deltaE_J_m','committed_Euler_budget_J_m'):
                    m.need(q[name]==0,'A manufactured row must not be relabelled as an actual float commit')
            else:r.update(affine_q=0.,affine_force=0.)
            rows.append(r)
    for key,g in made.groupby(['case','part'],sort=False):m.need(key in clockmap and len(g)==5 and set(g.manufacture)==set(range(5)),'All50 actual manufactured modes0..4 required')
    m.need(len(rows)==60,'All10 actual +50 manufactured certificates required')
    fixture=tables['limiter_fixtures'];expected=((-1.,-2.,1.),(-1.,2.,0.),(1.,-2.,0.),(1.,2.,0.),(-1e-12,-1.,1e-12),(-1.,-1e-12,1e-12),(0.,-1.,0.),(-1.,0.,0.))
    for index,q in enumerate(fixture.itertuples()):
        s,z,a=expected[index];m.need(q.fixture==index and q.s_m_s==s and q.q_m_s==z and q.expected_a_m_s==a,'Closed eight-fixture profile changed')
        computed=min(-s,-z) if s<0 and z<0 else 0.
        m.need(q.a_m_s==computed==a and q.a_m_s>=0 and q.a_m_s<=max(-s,0) and (q.a_m_s!=0 or not np.signbit(q.a_m_s)),'Original sign/cap/zero limiter fixture failed')
        export_equal(q.pair_power_unit_beta_alpha,q.a_m_s*s);m.need(q.pair_power_unit_beta_alpha<=0,'Fixture pair power became positive')
    pair=tables['pairs']
    for q in pair.itertuples():
        a=min(-q.radial_s_m_s,-q.radial_q_m_s) if q.radial_s_m_s<0 and q.radial_q_m_s<0 else 0.
        m.need(q.direct_neighbor in (0,1) and q.direct_active==int(bool(q.direct_neighbor) and a>0) and q.limiter_a_m_s==a
            and q.radial_s_m_s==q.rdot_m_s and q.direct_RV_Fi_n_N_m>=0 and q.direct_RV_relative_a_n_m_s2>=0,'Original actual selected radial sign/limiter gate failed')
        if not q.direct_active:m.need(q.direct_RV_Fi_n_N_m==q.direct_RV_relative_a_n_m_s2==0,'Inactive direct pair force must remain zero')
    return pd.DataFrame(rows)


def compare(tables,prior,focus,summary):
    new=tables['pairs'];old=prior['pairs']
    pairs=old.drop(columns=['pair_row_index']).merge(new,on=KEYS,how='outer',suffixes=('_vector','_radial'),validate='one_to_one',indicator=True,sort=False)
    m.need(len(pairs)==80 and (pairs['_merge']=='both').all(),'All80 old/new actual ID/time pairs must match');pairs=pairs.drop(columns='_merge');pairs.insert(0,'pair_row_index',np.arange(80))
    for field in ('distance_m','distance_over_dp','rdot_m_s','curvature_m_s2','direct_neighbor','base_relative_a_n_m_s2','base_rddot_m_s2'):
        m.need(np.array_equal(pairs[field+'_vector'].to_numpy(),pairs[field+'_radial'].to_numpy()),'Frozen geometry/bare response differs from the passed old component: '+field)
    pairs['approaching']=pairs.rdot_m_s_radial<0
    for label in ('vector','radial'):
        pairs[label+'_allneighbor_inward']=pairs['allneighbor_committed_da_n_m_s2_'+label]<0
        pairs[label+'_approaching_and_inward']=pairs.approaching & pairs[label+'_allneighbor_inward']
    oldfocus=prior['focus_RHS'];wanted=pd.MultiIndex.from_frame(focus[FOCUS_KEYS]);lookup=oldfocus.set_index(FOCUS_KEYS)
    m.need(len(lookup)==160 and not lookup.index.duplicated().any() and set(wanted)==set(lookup.index),'All160 old/new actual endpoint identities must match')
    oldfocus=lookup.loc[wanted].reset_index();m.need(len(oldfocus)==160,'No repeated pair endpoints may be dropped')
    for name in ('p_Pa','P0_Pa','J','kappa','saved_FS','fresh_FS','total_nn_Pa','effective_nn_Pa','actual_AS_tensor_nn_Pa','base_R_Pa_s','base_Acex','base_Acez'):
        m.need(np.array_equal(focus[name].to_numpy(),oldfocus[name].to_numpy()),'Unchanged saved state/bare force/actual AS Pa projection differs: '+name)
    for name in ('candidate_R_Pa_s','delta_R_Pa_s')+tuple(f'delta_{q}' for q in TERMS):focus['vector_'+name]=oldfocus[name].to_numpy()
    metrics=tables['metrics'].copy();oldmetric=prior['metrics'].set_index(['case','part']);oldsum=prior['RHS_summary'].set_index(['case','part'])
    for frame in (metrics,summary):
        for label in ('base_R','candidate_R','delta_R'):
            source=[float(oldmetric.loc[(q['case'],q.part),label+'_RMS']) for _,q in frame.iterrows()]
            frame['vector_'+label+'_RMS_Pa_s']=source
    for term in TERMS:
        summary['vector_delta_'+term+'_RMS_Pa_s']=[float(oldsum.loc[(q['case'],q.part),'delta_'+term+'_RMS_Pa_s']) for _,q in summary.iterrows()]
    for _,q in metrics.iterrows():
        r=oldmetric.loc[(q['case'],q.part)];m.need(q.base_R_RMS==r.base_R_RMS and q.base_R_absmax==r.base_R_absmax,'Unchanged all-soil bare rate norms differ')
    counts=[]
    for case in CASES:
        q=pairs[pairs['case']==case];closing=q[q.approaching]
        counts.append(dict(case=case,pairs=len(q),approaching=len(closing),vector_inward=int(closing.vector_allneighbor_inward.sum()),
            radial_inward=int(closing.radial_allneighbor_inward.sum()),direct_radial_active=int(q.direct_active.sum())))
    return pairs,focus,metrics,summary,counts


def sparse_symlog(ax,which,linthresh):
    from matplotlib.ticker import SymmetricalLogLocator
    bounds=ax.get_xlim() if which=='x' else ax.get_ylim();lo,hi=sorted(bounds)
    for count in range(11,1,-1):
        locator=SymmetricalLogLocator(base=10,linthresh=linthresh);locator.set_params(numticks=count)
        if sum(lo<=x<=hi for x in locator.tick_values(lo,hi))<=11:break
    if which=='x':ax.xaxis.set_major_locator(locator);ax.set_xlim(bounds)
    else:ax.yaxis.set_major_locator(locator);ax.set_ylim(bounds)


def plots(prefix,pairs,focus,metrics,summary,cert):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    from matplotlib.lines import Line2D
    colors={'original':'#2166AC','rv':'#D6604D'};markers=dict(zip(PARTS,('o','s','^','D','X')))
    fig,axes=plt.subplots(2,2,figsize=(14,11),layout='constrained')
    specs=(('allneighbor_committed_da_n_m_s2_vector','allneighbor_committed_da_n_m_s2_radial','Old vector all-neighbor delta a_n [m/s2]','New radial all-neighbor delta a_n [m/s2]'),
        ('candidate_rddot_m_s2_vector','candidate_rddot_m_s2_radial','Bare + old vector r double-dot [m/s2]','Bare + new radial r double-dot [m/s2]'),
        ('radial_s_m_s','radial_q_m_s','Actual s = relative normal velocity [m/s]','Actual q = radial residual [m/s]'),
        ('direct_RV_relative_a_n_m_s2_radial','allneighbor_committed_da_n_m_s2_radial','New direct-pair delta a_n [m/s2]','New all-neighbor delta a_n [m/s2]'))
    for ax,(x,y,xlabel,ylabel) in zip(axes.flat,specs):
        for case in CASES:
            for part in PARTS:
                q=pairs[(pairs['case']==case)&(pairs.part==part)]
                if x=='radial_s_m_s':
                    for active in (0,1):
                        a=q[q.direct_active==active];ax.scatter(a[x],a[y],s=35,marker=markers[part],facecolors=colors[case] if active else 'none',edgecolors=colors[case],alpha=.85)
                else:ax.scatter(q[x],q[y],s=32,c=colors[case],marker=markers[part],alpha=.85)
        ax.axhline(0,c='.65',lw=.7);ax.axvline(0,c='.65',lw=.7);ax.set(xlabel=xlabel,ylabel=ylabel);ax.grid(alpha=.2)
        if x!='radial_s_m_s':
            lo=min(float(pairs[x].min()),float(pairs[y].min()));hi=max(float(pairs[x].max()),float(pairs[y].max()));ax.plot([lo,hi],[lo,hi],c='.5',ls=':',lw=.8)
        threshold=.01 if x=='radial_s_m_s' else .1
        ax.set_xscale('symlog',linthresh=threshold);ax.set_yscale('symlog',linthresh=threshold);sparse_symlog(ax,'x',threshold);sparse_symlog(ax,'y',threshold)
    for case,part,i,j in EXAMPLES:
        q=pairs[(pairs['case']==case)&(pairs.part==part)&(pairs.ID_i==i)&(pairs.ID_j==j)];m.need(len(q)==1,'Illustrations must remain within the complete selected scope');r=q.iloc[0]
        for ax,(x,y,_,_) in zip(axes.flat,specs):
            if x=='radial_s_m_s':continue
            ax.annotate(f'P{part} {i}/{j}',(r[x],r[y]),xytext=(6,9 if part==42 else -16),textcoords='offset points',fontsize=8)
    handles=[Line2D([0],[0],color=colors[c],marker='o',ls='',label='Saved '+c+' trajectory') for c in CASES]
    handles += [Line2D([0],[0],color='.3',marker=markers[p],ls='',label='P'+str(p)) for p in PARTS]
    handles += [Line2D([0],[0],color='.3',marker='o',ls='',markerfacecolor='none',label='s/q panel: inactive direct pair')]
    fig.legend(handles=handles,loc='outside lower center',ncol=4,fontsize=9)
    fig.suptitle('All80 fixed-state pairs: compression-only radial candidate versus old vector response\nDirect outward force does not guarantee all-neighbor outward response; no trajectory was integrated',fontsize=12)
    files=[Path(str(prefix)+'_mechanics.png')];fig.savefig(files[-1],dpi=180);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(16,14),layout='constrained');indices=np.arange(10)
    labels=[f'{q["case"]} P{int(q.part)}' for _,q in metrics.iterrows()]
    axes[0,0].plot(indices,metrics.base_R_RMS,marker='o',label='Bare original full rate')
    axes[0,0].plot(indices,metrics.vector_candidate_R_RMS_Pa_s,marker='s',label='Bare + old vector')
    axes[0,0].plot(indices,metrics.candidate_R_RMS,marker='^',label='Bare + new radial')
    axes[0,0].set(xticks=indices,xticklabels=labels,ylabel='All5000-soil full rate RMS [Pa/s]',title='All10 real states, one original + one complete Darcy response');axes[0,0].tick_params(axis='x',rotation=40);axes[0,0].legend(fontsize=8)
    values=summary[['delta_'+q+'_RMS_Pa_s' for q in TERMS]].to_numpy().T;limit=float(values.max());m.need(limit>0,'A nonzero complete RHS scale is required')
    im=axes[0,1].imshow(values,aspect='auto',interpolation='nearest',cmap='viridis',norm=SymLogNorm(linthresh=1.,vmin=0,vmax=limit))
    axes[0,1].set(yticks=np.arange(8),yticklabels=TERMS,xticks=indices,xticklabels=labels,title='New radial delta RHS: all8 independent term RMS norms');axes[0,1].tick_params(axis='x',rotation=40);fig.colorbar(im,ax=axes[0,1],label='Pa/s; full nonnegative RMS range, symlog1')
    for case in CASES:
        q=focus[focus['case']==case]
        axes[1,0].scatter(q.vector_delta_R_Pa_s,q.delta_R_Pa_s,s=18,c=colors[case],alpha=.75,label=case)
        axes[2,0].scatter(q.vector_delta_numeric_residual,q.delta_numeric_residual,s=18,c=colors[case],alpha=.75)
    for ax,x,y in ((axes[1,0],focus.vector_delta_R_Pa_s,focus.delta_R_Pa_s),(axes[2,0],focus.vector_delta_numeric_residual,focus.delta_numeric_residual)):
        lo=min(float(x.min()),float(y.min()));hi=max(float(x.max()),float(y.max()));ax.plot([lo,hi],[lo,hi],c='.5',ls=':',lw=.8)
        ax.set_xscale('symlog',linthresh=1.);ax.set_yscale('symlog',linthresh=1.);sparse_symlog(ax,'x',1.);sparse_symlog(ax,'y',1.)
    axes[1,0].set(xlabel='Old vector actual full delta rate [Pa/s]',ylabel='New radial actual full delta rate [Pa/s]',title='All160 original pair endpoints, repeated IDs retained');axes[1,0].legend()
    axes[2,0].set(xlabel='Old vector delta numeric residual [Pa/s]',ylabel='New radial delta numeric residual [Pa/s]',title='Independent float/source-order remainder, not a physical source')
    ratio_names=['power_error','net','central_torque','torque_reduction','total_torque','normalization','LS_backward','dt_lambda_half','frozen_Euler_positive','float_commit','committed_positive_power','committed_net','committed_torque','committed_Euler_positive']
    actual=cert[cert.scope=='actual'];ratio_values=actual[ratio_names].to_numpy().T
    im=axes[1,1].imshow(ratio_values,aspect='auto',interpolation='nearest',vmin=0,vmax=1,cmap='magma')
    axes[1,1].set(yticks=np.arange(len(ratio_names)),yticklabels=ratio_names,xticks=indices,xticklabels=labels,title='Original independent radial budget utilization, all10 states');axes[1,1].tick_params(axis='x',rotation=40);fig.colorbar(im,ax=axes[1,1],label='Measured / original budget; exact guard <=1')
    made=cert[cert.scope=='manufactured'];x=np.arange(50);axes[2,1].scatter(x,made.affine_q,s=16,label='Measured max q / affine q budget');axes[2,1].scatter(x,made.affine_force,s=16,marker='x',label='Measured max force / affine force budget')
    axes[2,1].axhline(1,c='.4',ls=':',lw=.8);axes[2,1].set(xlabel='Actual manufacture row0..49: modes0..4 in each state',ylabel='Original forward-budget utilization',title='All50 genuine null tests; no synthetic commit or old form identity');axes[2,1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.15)
    fig.suptitle('CPU frozen-state radial RHS and arithmetic certificates; AS tensor projection remains Pa\nSigned source clocks retained; no GPU bit truth, coupled-energy theorem or physical repair acceptance',fontsize=12)
    files.append(Path(str(prefix)+'_RHS_certificates.png'));fig.savefig(files[-1],dpi=180);plt.close(fig);return files


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true')
    m.need(parser.parse_args().execution_authorized,'Author-only until root independently reads and admits this offline analysis')
    prefix=T/'figures'/TAG;check=L/(TAG+'.check.json');m.need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')),'Existing full/partial derived artifacts are protected')
    used=[];files=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,physical_steps=0,solver_invocations=0,native_invocations=0,
        component_invocations=0,build_invocations=0,GPU_actions=0,SHA_scans=0,automatic_next_job=False)
    try:
        tables,prior,paths,clockmap,done=load(used);cert=gates(tables,clockmap)
        # Only this new50000-row soil table is read; reuse pure CSV RHS algebra,
        # never onset.load/gates or its legacy vector certificate.
        focus,summary,ratio=onset.rhs(tables,clockmap)
        pairs,focus,metrics,summary,counts=compare(tables,prior,focus,summary);m.verify(used)
        for name,frame in (('pairs',pairs),('focus_RHS',focus),('metrics',metrics),('RHS_summary',summary),('certificates',cert),('limiter_fixtures',tables['limiter_fixtures'])):
            path=Path(str(prefix)+'_'+name+'.csv');onset.save_csv(frame,path);files.append(path)
        out=Path(str(prefix)+'_selected_clocks.csv')
        with out.open('xb') as f:f.write(paths['selected_clocks'].read_bytes())
        files.append(out);files+=plots(prefix,pairs,focus,metrics,summary,cert);m.verify(used)
        examples=[]
        for case,part,i,j in EXAMPLES:
            p=pairs[(pairs['case']==case)&(pairs.part==part)&(pairs.ID_i==i)&(pairs.ID_j==j)]
            f=focus[(focus['case']==case)&(focus.part==part)&(focus.pair_i==i)&(focus.pair_j==j)]
            examples.append(dict(pair=p.to_dict(orient='records'),endpoints=f.to_dict(orient='records')))
        result.update(passed=True,analysis_complete=True,source_gate=m.stat(GATE),old_vector_review=m.stat(OLD),completion_counts=done,
            preserved_pair_rows=80,preserved_focus_rows=160,new_soil_rows_checked=50000,old_soil_reread=False,actual_states=10,
            manufactured_rows=50,limiter_fixture_rows=8,clock_rows=10,selected_clocks_byte_identical=True,
            independent_radial_certificates=60,old_vector_form_identity_used=False,
            CSV_channel_arithmetic_max_budget_ratio=ratio,seven_physical_channels=list(onset.CHANNELS),independent_numeric_residual_not_redefined=True,
            actual_AS_tensor_nn_units='Pa',AS_tensor_rescaled_or_renamed=False,approaching_response_counts=counts,
            illustrative_pairs_not_full_scope=examples,raw_signed_dterror_retained=True,source_formed_budgets_not_reconstructed_from_all_neighbors=True,
            frozen_Euler_only=True,sparse_component_values_not_actual_stage_history=True,GPU_bittruth_claimed=False,
            causal_mechanism_automatically_accepted=False,visual_QA_pending=True,consumed=used,consumed_stats_unchanged=True,files=[m.stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),consumed=used,partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
