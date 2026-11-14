"""Offline review of the passed10-state CPU onset component; no physical tools."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import pandas as pd
import c08_h18_wend_matrix_r1 as m

T,L=m.T,m.L;TAG='c08_h18_rv_onset_review_r1';SOURCE='c08_h18_rv_onset_force_r1'
NOTE=T/'notes'/(TAG+'.md');GATE=L/(SOURCE+'.check.json')
UNITS=L/(SOURCE+'.AS_units_resolution_r2.json');PARTS=(40,42,43,76,90);CASES=('original','rv')
CHANNELS=('compression','LP','Taylor_pressure','Da','FS_Ace_Lx','chain_pressure','chain_Ace')
ALL_TERMS=CHANNELS+('numeric_residual',)
EXAMPLES=(('rv',42,6964,7012),('rv',90,6918,6967))

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save_csv(df,path):
    with path.open('x',encoding='utf-8',newline='') as f:df.to_csv(f,index=False,float_format='%.17g')
def take(e,used):m.bind(e);used.append(e);return Path(e['path'])
def unique_entry(entries,path):
    found=[e for e in entries if Path(e['path']).resolve()==Path(path).resolve()]
    m.need(found and all(e==found[0] for e in found),'One passed unchanged binding required: '+str(path));return found[0]
def arithmetic_ratio(actual,terms,subtraction_scale=None):
    """Pure CSV sum roundoff, never a replacement for original component gates."""
    nu=32*.5*np.finfo(float).eps;gamma=nu/(1-nu)
    total=np.sum(terms,axis=1);error=np.abs(actual-total)
    scale=np.abs(actual)+np.sum(np.abs(terms),axis=1)
    if subtraction_scale is not None:scale=scale+subtraction_scale
    budget=gamma*scale+32*np.nextafter(0.,1.)
    m.need(np.all(error<=budget),'CSV channel/export sum exceeds declared forward arithmetic budget')
    return np.divide(error,budget,out=np.zeros_like(error),where=budget>0)
def aggregate_equal(value,reference):
    nu=(16*5000+64)*.5*np.finfo(float).eps;budget=nu/(1-nu)*(abs(value)+abs(reference))
    m.need(abs(value-reference)<=budget,'CSV aggregate differs from actual component metric')

def load(used):
    c=m.read(GATE);m.need(c['passed'] and c['consumed_stats_unchanged'] and c['physical_steps']==c['material_return_calls']==0,'Passed protected zero-advance CPU component required')
    used.extend([m.stat(GATE),m.stat(Path(__file__)),m.stat(NOTE),m.stat(Path(m.__file__))])
    b=m.read(take(c['build'],used));call=m.read(take(c['actual_call'],used));done=m.read(take(c['completion'],used))
    program=take(b['program'],used)
    m.need(b['passed'] and b['consumed_stats_unchanged'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None
           and Path(call['program']).resolve()==program.resolve(),'Actual passed build/program/owned call required')
    expected=dict(trajectory_count=2,actual_force_calls=10,actual_Darcy_calls=30,extra_Darcy_calls=20,actual_DtVariable_false_calls=20,
        zero_recompute_rate_bit_rows=50000,external_GPU_RHS_bit_rows=0,literal_rate_rows=150000,soil_rows=50000,pair_rows=80,focus_rows=160,manufactured_rows=30,clock_rows=10,physical_steps=0,material_return_calls=0,filter_calls=0)
    m.need(done['passed'] and done['parts']==list(PARTS) and all(done[k]==v for k,v in expected.items())
           and done['max_final_float_budget_ratio']<=1 and done['max_expanded_budget_ratio']<=1
           and done['actual_CPUcell_RV_graph'] and done['reverse_membership_required'] and not done['GPU_bittruth_claimed'],'Original counts/bit/literal/cell-graph gates must pass')
    u=m.read(UNITS);used.append(m.stat(UNITS))
    m.need(u['passed'] and u['supersedes_without_overwriting']==c['AS_units_erratum']
           and u['actual_AS_tensor_nn_Pa_header_is_correct'] and u['actual_AS_tensor_in_active_branch_units']=='Pa'
           and u['no_CSV_rename_or_rescale_required'] and u['raw_output_source_build_and_numeric_gates_unchanged'], 'The actual current-J rho=1 AS units resolution r2 is mandatory')
    take(u['supersedes_without_overwriting'],used);take(u['source_archive'],used)
    tables={};paths={}
    for name,count in (('pairs',80),('focus',160),('soil',50000),('metrics',10),('manufactured',30),('selected_clocks',10)):
        path=T/'outputs'/SOURCE/(name+'.csv');take(unique_entry(c['files'],path),used);paths[name]=path
        if name=='selected_clocks':continue
        df=pd.read_csv(path,float_precision='round_trip');m.need(len(df)==count and np.isfinite(df.select_dtypes(include=np.number).to_numpy(dtype=float)).all(),name+' complete finite coverage differs');tables[name]=df
    clocks=read_csv(paths['selected_clocks']);m.need(len(clocks)==10,'All10 actual selected clocks required')
    clockmap={}
    for case,folder in (('original','c08_h18_as03_n255_r1'),('rv','c08_h18_rv_window_GPU_r2')):
        path=T/'outputs'/folder/'native_r1/clocks.csv';take(unique_entry(c['consumed'],path),used);raw=read_csv(path)
        for part in PARTS:clockmap[(case,part)]=raw[part]
    m.need({(r['case'],int(r['part'])) for r in clocks}==set(clockmap),'Selected case/part clocks differ')
    for q in clocks:
        key=(q['case'],int(q['part']));m.need({k:v for k,v in q.items() if k!='case'}==clockmap[key] and float(q['dt_s'])==5e-6
            and float(q['signed_dterror_s'])<=1e-14 and int(q['native_IDs'])==6805,'Actual original signed clock row differs; no rewriting')
    for part in PARTS:m.need(clockmap[('original',part)]['time_s']==clockmap[('rv',part)]['time_s'],'Actual same-time state comparison required')
    selection=Path(call['arguments'][call['arguments'].index('--selection')+1]);take(unique_entry(c['consumed'],selection),used);selected=read_csv(selection)
    keys={(r['case'],int(r['part']),int(r['id_i']),int(r['id_j'])) for r in selected};pairs=tables['pairs'];focus=tables['focus']
    m.need(len(selected)==len(keys)==80 and set(zip(pairs['case'],pairs.part,pairs.ID_i,pairs.ID_j))==keys and not pairs.duplicated(['case','part','ID_i','ID_j']).any(),'All80 root-selected pair rows required')
    m.need(not focus.duplicated(['case','part','pair_i','pair_j','native_id']).any() and len(focus)==160,'All160 original pair endpoints required without deduplication')
    for key,g in focus.groupby(['case','part','pair_i','pair_j'],sort=False):m.need(key in keys and len(g)==2 and set(g.native_id)==set(key[2:]),'Pair/focus identity mapping differs')
    for df in tables.values():
        if 'time_s' not in df:continue
        for key,g in df.groupby(['case','part'],sort=False):
            q=clockmap[key];m.need((g.time_s==float(q['time_s'])).all() and (g.completed_step==int(q['completed_step'])).all() and (g.tau_s==float(q['tau_from_actual_release_s'])).all(),'Actual source time/step/tau differs')
    return tables,paths,clocks,clockmap,done,u

def gates(tables,clockmap):
    metrics=tables['metrics'];made=tables['manufactured'];m.need(set(zip(metrics['case'],metrics.part))==set(clockmap),'All10 metric states required')
    for index,q in enumerate(metrics.itertuples(),1):
        m.need(q.actual_force_calls_cumulative==index and q.actual_Darcy_calls_cumulative==3*index and q.zero_recompute_bit_rows_cumulative==5000*index,'Actual cumulative component counts differ')
        m.need(q.wall_active+q.wall_inactive==q.wall_NpbOk and q.wall_NpbOk+q.wall_ignored==1805,'Original effective wall partition differs')
        m.need(q.base_DtVariable==q.candidate_DtVariable==5e-6 and q.necessary_bound_s>=5e-6 and q.alpha_dt_dmax<=1,'Original necessary/isolated step guard failed')
    for df in (metrics,made):
        m.need((df.work<=df.work_budget).all() and (abs(df.work_plus_2form)<=df.work_budget).all() and (df.max_normal_budget_fraction<=1).all()
            and (df.net_force_norm<=df.net_force_budget).all() and (abs(df.torque_y)<=df.torque_budget).all()
            and (df.committed_work<=df.committed_work_budget).all() and (df.committed_net_force_norm<=df.committed_net_force_budget).all()
            and (abs(df.committed_torque_y)<=df.committed_torque_budget).all(),'Original exported raw/committed mechanical budget failed')
    for key,g in made.groupby(['case','part'],sort=False):m.need(key in clockmap and len(g)==3 and set(g.manufacture)=={0,1,2},'All30 genuine manufactured rows required')
    m.need((made.manufacture_max_residual<=made.manufacture_residual_budget).all() and (made.max_force<=made.manufacture_force_budget).all(),'Original manufactured null budgets failed')

def rhs(tables,clockmap):
    soil=tables['soil'];summaries=[];maxratio=0.
    for key,g in soil.groupby(['case','part'],sort=False):
        m.need(key in clockmap and len(g)==5000 and np.array_equal(np.sort(g.native_id.to_numpy()),np.arange(2060,7060)),'All5000 material IDs in every state required')
        zero=g.candidate_R_Pa_s.to_numpy()-g.base_R_Pa_s.to_numpy();m.need(np.array_equal(zero,g.delta_R_Pa_s.to_numpy()),'Actual full-rate difference differs')
        for term in ALL_TERMS:m.need(np.array_equal(g['candidate_'+term].to_numpy()-g['base_'+term].to_numpy(),g['delta_'+term].to_numpy()),'Actual channel difference differs: '+term)
        for phase,rate in (('base',g.base_R_Pa_s.to_numpy()),('candidate',g.candidate_R_Pa_s.to_numpy()),('delta',g.delta_R_Pa_s.to_numpy())):
            terms=g[[phase+'_'+v for v in ALL_TERMS]].to_numpy();subtraction=None
            if phase=='delta':
                subtraction=np.abs(g.base_R_Pa_s.to_numpy())+np.abs(g.candidate_R_Pa_s.to_numpy())
                subtraction+=np.sum(np.abs(g[['base_'+v for v in ALL_TERMS]].to_numpy()),axis=1)+np.sum(np.abs(g[['candidate_'+v for v in ALL_TERMS]].to_numpy()),axis=1)
            maxratio=max(maxratio,float(arithmetic_ratio(rate,terms,subtraction).max()))
        metric=tables['metrics'][(tables['metrics']['case']==key[0])&(tables['metrics'].part==key[1])].iloc[0]
        row=dict(case=key[0],part=int(key[1]),time_s=float(g.time_s.iloc[0]),tau_s=float(g.tau_s.iloc[0]),completed_step=int(g.completed_step.iloc[0]),soil_IDs=5000)
        for name,col in (('base_R','base_R_Pa_s'),('candidate_R','candidate_R_Pa_s'),('delta_R','delta_R_Pa_s')):
            a=g[col].to_numpy();value=math.sqrt(math.fsum(a*a)/5000);aggregate_equal(value,float(metric[name+'_RMS']));m.need(float(np.abs(a).max())==float(metric[name+'_absmax']),'Full rate maximum differs')
            row[name+'_RMS_Pa_s']=value;row[name+'_absmax_Pa_s']=float(np.abs(a).max())
        for term in ALL_TERMS:
            a=g['delta_'+term].to_numpy();row['delta_'+term+'_mean_Pa_s']=math.fsum(a)/5000;row['delta_'+term+'_RMS_Pa_s']=math.sqrt(math.fsum(a*a)/5000);row['delta_'+term+'_absmax_Pa_s']=float(np.abs(a).max())
        summaries.append(row)
    m.need(len(summaries)==10,'All10 full-soil RHS summaries required')
    focus=tables['focus'].copy();focus.insert(0,'focus_row_index',np.arange(len(focus)))
    columns=['case','part','native_id','delta_R_Pa_s']+[phase+'_'+v for phase in ('base','candidate','delta') for v in ALL_TERMS]
    joined=focus.merge(soil[columns],on=['case','part','native_id'],how='left',validate='many_to_one',sort=False)
    m.need(len(joined)==160 and np.isfinite(joined.select_dtypes(include=np.number).to_numpy(dtype=float)).all(),'All160 complete focus/channel joins required')
    lookup=soil.set_index(['case','part','native_id']);wanted=pd.MultiIndex.from_frame(focus[['case','part','native_id']]);source=lookup.loc[wanted]
    for name in ('base_R_Pa_s','candidate_R_Pa_s'):m.need(np.array_equal(focus[name].to_numpy(),source[name].to_numpy()),'Focus/full-soil actual rate mismatch')
    m.need(np.array_equal(joined.actual_AS_tensor_nn_Pa.to_numpy(),focus.actual_AS_tensor_nn_Pa.to_numpy()),'Actual AS Pa projection must not be renamed or rescaled')
    return joined,pd.DataFrame(summaries),maxratio

def plots(prefix,pairs,focus,metrics):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    from matplotlib.lines import Line2D
    colors={'original':'#2166AC','rv':'#D6604D'};markers=dict(zip(PARTS,('o','s','^','D','X')))
    fig,axes=plt.subplots(2,2,figsize=(13,10),layout='constrained')
    specs=(('direct_RV_relative_a_n_m_s2','allneighbor_committed_da_n_m_s2','Direct-pair ideal delta a_n [m/s2]','All-neighbor committed delta a_n [m/s2]'),
        ('rdot_m_s','dv_affine_n_m_s','Actual s = rdot [m/s]','Fitted affine normal velocity [m/s]'),
        ('rbar_n_m_s','direct_RV_relative_a_n_m_s2','Residual q_n [m/s]','Direct-pair ideal delta a_n [m/s2]'),
        ('base_rddot_m_s2','candidate_rddot_m_s2','Bare r double-dot [m/s2]','Bare + RV r double-dot [m/s2]'))
    for ax,(x,y,xlabel,ylabel) in zip(axes.flat,specs):
        for case in CASES:
            for part in PARTS:
                q=pairs[(pairs['case']==case)&(pairs.part==part)];ax.scatter(q[x],q[y],s=27,c=colors[case],marker=markers[part],alpha=.8)
        ax.axhline(0,c='.6',lw=.7);ax.axvline(0,c='.6',lw=.7);ax.set(xlabel=xlabel,ylabel=ylabel);ax.grid(alpha=.2)
        if x in ('rdot_m_s','base_rddot_m_s2'):
            lo=min(float(pairs[x].min()),float(pairs[y].min()));hi=max(float(pairs[x].max()),float(pairs[y].max()));ax.plot([lo,hi],[lo,hi],c='.5',ls=':',lw=.8)
    for case,part,i,j in EXAMPLES:
        q=pairs[(pairs['case']==case)&(pairs.part==part)&(pairs.ID_i==i)&(pairs.ID_j==j)];m.need(len(q)==1,'Root illustrative pair must be an actual unique selection')
        r=q.iloc[0];axes[1,1].annotate(f'P{part} {i}/{j}',(r.base_rddot_m_s2,r.candidate_rddot_m_s2),xytext=(7,8 if part==42 else -16),textcoords='offset points',fontsize=8)
    handles=[Line2D([0],[0],color=colors[c],marker='o',ls='',label='Saved '+c+' trajectory') for c in CASES]+[Line2D([0],[0],color='.3',marker=markers[p],ls='',label='P'+str(p)) for p in PARTS]
    fig.legend(handles=handles,loc='outside lower center',ncol=4,fontsize=9);fig.suptitle('All80 selected pairs: CPU frozen-state responses, not replayed stage histories\nA direct pair is not the all-neighbor increment; examples do not replace the full scope',fontsize=12)
    files=[Path(str(prefix)+'_mechanics.png')];fig.savefig(files[-1],dpi=180);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(15,13),layout='constrained')
    for case in CASES:
        q=focus[focus['case']==case];axes[0,0].scatter(q.base_R_Pa_s,q.candidate_R_Pa_s,s=16,c=colors[case],label=case,alpha=.7)
        seven=q[['delta_'+v for v in CHANNELS]].sum(axis=1);axes[1,0].scatter(seven,q.delta_R_Pa_s,s=16,c=colors[case],alpha=.7)
        axes[1,1].scatter(q.focus_row_index,q.delta_numeric_residual,s=13,c=colors[case],alpha=.8)
        axes[2,0].scatter(q.total_positive_eigen_sum_Pa,q.actual_AS_tensor_nn_Pa,s=17,c=colors[case],alpha=.7)
        z=metrics[metrics['case']==case];axes[2,1].plot(z['part'],z.base_R_RMS,color=colors[case],marker='o',label=case+' bare');axes[2,1].plot(z['part'],z.candidate_R_RMS,color=colors[case],marker='s',ls='--',label=case+' +RV')
    axes[0,0].set(xlabel='Bare full rate [Pa/s]',ylabel='Bare + RV full rate [Pa/s]',title='All160 actual focus rates');axes[0,0].legend()
    axes[1,0].set(xlabel='Sum of seven physical channel deltas [Pa/s]',ylabel='Actual full delta rate [Pa/s]',title='Independent numeric residual is not forced into the seven terms')
    for ax,x,y in ((axes[0,0],focus.base_R_Pa_s,focus.candidate_R_Pa_s),(axes[1,0],focus[['delta_'+v for v in CHANNELS]].sum(axis=1),focus.delta_R_Pa_s)):
        ax.set_xscale('symlog',linthresh=1.);ax.set_yscale('symlog',linthresh=1.);lo=min(float(x.min()),float(y.min()));hi=max(float(x.max()),float(y.max()));ax.plot([lo,hi],[lo,hi],c='.5',ls=':',lw=.8)
    values=focus[['delta_'+v for v in ALL_TERMS]].to_numpy().T;limit=float(np.abs(values).max());m.need(limit>0,'Actual RHS comparison requires a nonzero full-data range')
    im=axes[0,1].imshow(values,aspect='auto',interpolation='nearest',cmap='RdBu_r',norm=SymLogNorm(linthresh=1.,vmin=-limit,vmax=limit));axes[0,1].set(yticks=np.arange(8),yticklabels=ALL_TERMS,xlabel='Actual focus row index0..159',title='All7 channel deltas + independent numeric residual')
    fig.colorbar(im,ax=axes[0,1],label='Actual delta term [Pa/s]; full range, symlog1Pa/s')
    axes[1,1].set(xlabel='Actual focus row index',ylabel='Independent delta numeric residual [Pa/s]',title='Observed float/source-order remainder, not a physical source')
    axes[2,0].set(xlabel='Actual float total positive eigenvalue sum [Pa]',ylabel='actual_AS_tensor_nn_Pa [Pa]',title='Original actual AS tensor projection: rho argument=1, no rescaling')
    axes[2,1].set(xlabel='Actual selected part',ylabel='All5000-soil rate RMS [Pa/s]',title='All10 states, original/candidate full rates');axes[2,1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.15)
    fig.suptitle('Conditional full-Darcy response on two existing trajectories; no time integration or causal acceptance',fontsize=12)
    files.append(Path(str(prefix)+'_rhs_AS.png'));fig.savefig(files[-1],dpi=180);plt.close(fig);return files

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');m.need(p.parse_args().execution_authorized,'Author-only until root full-read/offline admission')
    prefix=T/'figures'/TAG;check=L/(TAG+'.check.json');m.need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')),'Prior complete/partial derived artifacts protected')
    used=[];files=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,physical_steps=0,solver_invocations=0,native_invocations=0,build_invocations=0,GPU_actions=0,SHA_scans=0)
    try:
        tables,paths,clocks,clockmap,done,units=load(used);gates(tables,clockmap);focus,summary,ratio=rhs(tables,clockmap)
        pairs=tables['pairs'].copy();pairs.insert(0,'pair_row_index',np.arange(len(pairs)));m.verify(used)
        for name,df in (('pairs',pairs),('focus_RHS',focus),('metrics',tables['metrics']),('manufactured',tables['manufactured']),('RHS_summary',summary)):
            out=Path(str(prefix)+'_'+name+'.csv');save_csv(df,out);files.append(out)
        out=Path(str(prefix)+'_selected_clocks.csv')
        with out.open('xb') as f:f.write(paths['selected_clocks'].read_bytes())
        files.append(out);files+=plots(prefix,pairs,focus,tables['metrics']);m.verify(used)
        examples=[]
        for case,part,i,j in EXAMPLES:
            pair=pairs[(pairs['case']==case)&(pairs.part==part)&(pairs.ID_i==i)&(pairs.ID_j==j)]
            points=focus[(focus['case']==case)&(focus.part==part)&(focus.pair_i==i)&(focus.pair_j==j)]
            examples.append(dict(pair=pair.to_dict(orient='records'),endpoints=points.to_dict(orient='records')))
        result.update(passed=True,analysis_complete=True,source_gate=m.stat(GATE),completion_counts=done,AS_units_resolution=m.stat(UNITS),actual_AS_tensor_nn_units='Pa',AS_tensor_rescaled_or_renamed=False,
            preserved_pair_rows=80,preserved_focus_rows=160,soil_rows_checked=50000,actual_states=10,manufactured_rows=30,clock_rows=10,
            CSV_channel_arithmetic_max_budget_ratio=ratio,original_literal_and_zero_bit_gates_inherited=True,GPU_bittruth_claimed=False,
            seven_physical_channels=list(CHANNELS),independent_numeric_residual_not_redefined=True,root_illustrative_pairs_not_full_scope=examples,
            sparse_component_values_not_actual_stage_history=True,causal_mechanism_automatically_accepted=False,automatic_next_job=False,visual_QA_pending=True,
            consumed=used,consumed_stats_unchanged=True,files=[m.stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),consumed=used,partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
