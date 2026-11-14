"""Offline actual OFF/ON CPU-rate comparison; no component, solver or old-analysis call."""
import argparse, csv, itertools, math, struct
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, NullFormatter, SymmetricalLogLocator, FuncFormatter, MaxNLocator
import c08_h18_joint_darcy_probe_r1_build as old
m,T,L=old.m,old.T,old.L
TAG='c08_h18_lstar_cpu_review_r1'; FIG=T/'figures'; CHECK=L/(TAG+'.check.json')
FIELDS=('H_hydro_affine','N_normal_quadratic','X_cross_cubic'); ORACLES=('real_wall','analytic_ghost')
COHORTS=('all','legal_flat_bed','interior_no_wall')
INTENTIONAL={'Lx_m_1_'+q for q in 'xyz'}|{'LP_Pa_m2','source_lap_Pa_m2','literal_rate_Pa_s','float_rate_Pa_s','seven_terms_sum_Pa_s','numeric_residual_Pa_s','float_budget_Pa_s','double_budget_Pa_s','expanded_budget_Pa_s','LP_Pa_s','Taylor_pressure_Pa_s','FS_Ace_Lx_Pa_s'}

def bits(x):return struct.pack('<d',float(x))
def equal(a,b):return bits(a)==bits(b)
def key(r):return(int(r['part']),r['field'],r['oracle'],int(r['native_id']))
def rms(x):return float(np.sqrt(np.mean(np.square(x))))if len(x)else None
def ratio(x,b):
    m.need(math.isfinite(x)and math.isfinite(b)and b>=0,'Nonfinite exported-arithmetic comparison');m.need(abs(x)<=b,'Offline prediction outside original propagated arithmetic budget');return abs(x)/b if b else 0.
def gamma(n):return n*np.finfo(float).eps/(1-n*np.finfo(float).eps)
def csvfile(path):return Path(path).open(encoding='utf-8-sig',newline='')
def same_file(a,b):
    with Path(a).open('rb')as x,Path(b).open('rb')as y:
        while True:
            u,v=x.read(65536),y.read(65536)
            if u!=v:return False
            if not u:return True
def artifact(g,leaf,before):
    q=[q for q in g['files']if Path(q['path']).name==leaf];m.need(len(q)==1,'One bound artifact required: '+leaf);before.append(m.bind(q[0]));return Path(q[0]['path'])
def modes(before):
    result={}; evidence={}
    for mode,expected in(('off',580000),('on',570000)):
        tag='c08_h18_lstar_cpu_'+mode+'_r1';path=L/(tag+'.check.json');g=m.read(path);before.append(m.stat(path))
        m.need(g['passed']and g['mode']==mode and g['consumed_stats_unchanged']and g['upstream_scalar_bits']==expected and g['actual_rate_float_bits']==30000 and g['physical_steps']==g['solver_invocations']==0 and not g['physical_acceptance'],'Passed actual mode check required')
        if mode=='off':m.need(g['OFF_old_physical_CSV_bit_files']==6 and g['OFF_old_physical_CSV_bit_bytes']==61874092,'Genuine original six-CSV OFF proof required')
        else:m.need(not g['old_rate_bit_equivalence_claimed']and m.bind(g['OFF_prerequisite'])==m.stat(L/'c08_h18_lstar_cpu_off_r1.check.json'),'ON prerequisite/old-R limitation differs')
        b=m.read(m.bind(g['build'])['path']);c=m.read(m.bind(g['completion'])['path']);call=m.read(m.bind(g['actual_call'])['path']);before += [g['build'],g['completion'],g['actual_call']]
        m.need(b['passed']and b['mode']==mode and b['receiver_C_bare_enabled']==(mode=='on')and b['consumed_stats_unchanged']and b['actual_link_objects']==87 and b['retained_original_objects']==85 and b['physical_objects_compiled']==1 and b['new_entry_objects']==1 and b['exact_reversible_private_w_block']and b['physical_source_from_full_schema2_archive']and b['changed_Darcy_terms']==['LP','Lx']and b['unchanged_Darcy_terms']==['Gp','Da','gradJ','chain','FS'],'Actual private source/object contract differs')
        for q in('program','source','private_physical_source','private_physical_object','source_capture','source_archive'):before.append(m.bind(b[q]))
        m.need(len(b['archived_headers'])==160 and len(b['calls'])==3,'Actual three-tool/160-header closure differs')
        for i,q in enumerate(b['calls']):
            tool=m.read(m.bind(q)['path']);before.append(q);m.need(tool['actual_Popen_wait_exit']==tool['actual_Win32_exit']==0 and tool['ownership_failure']is None,'Actual build tool exit differs')
            if i<2:m.need('/DC08_H18_LSTAR_ON='+str(int(mode=='on'))in tool['arguments'],'Actual private source/entry macro differs')
        m.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure']is None and call['arguments'][0]=='--check-'+mode and Path(call['program']).resolve()==Path(b['program']['path']).resolve()and Path(call['child']['exe']).resolve()==Path(call['program']).resolve()and call['child']['argv']==[call['program'],*call['arguments']],'Actual owned component call differs');before.append(m.bind(call['log']))
        m.need(c['passed']and c['receiver_C_bare_enabled']==(mode=='on')and c['external_CPU_rate_compared_to_old']==(mode=='off')and c['external_CPU_baseline_scalar_bits']==expected and c['restore_CellDivide_calls']==14 and c['sorting_only_states']==12 and c['actual_force_calls']==2 and c['total_mode_Darcy_API_calls']==8 and c['actual_rate_float_bit_rows']==30000 and c['analytic_generated_float_rows']==30000 and c['manufactured_rows']==60000 and c['wall_rows']==5700 and c['literal_theta_bits']==10000 and c['literal_Rsigma_component_bits']==60000 and c['physical_steps']==c['material_return_calls']==c['filter_calls']==0,'Actual closed-state coverage differs')
        m.need(c['max_original_float_budget_ratio']<=1 and c['max_original_expanded_budget_ratio']<=1 and not c['analytic_ghost_uses_actual_rate_API']and not c['analytic_ghost_changes_J_C_FS'],'Original actual/analytic arithmetic gates differ')
        files={leaf:artifact(g,leaf,before)for leaf in('manufactured.csv','summary.csv','walls.csv','baseline.csv','restore_route.csv','selected_clocks.csv')};result[mode]=files
        evidence[mode]=dict(check=m.stat(path),actual_call=g['actual_call'],build=g['build'],program=b['program'],stdout=call['log'],actual_child=call['child'],upstream_scalar_bits=expected,actual_manufactured_rate_bits=30000,old_R_bit_equivalence=mode=='off',kappa='preserved native/Restore/Unchanged and unchanged upstream source contract; no manufactured CSV kappa column')
    return result,evidence

def consume(files):
    records={};groups=defaultdict(list);counts=Counter();common_bits=0;columns=None
    with csvfile(files['off']['selected_clocks.csv'])as f:clocks={int(q['part']):q for q in csv.DictReader(f)}
    m.need(set(clocks)=={29,30}and all(q['case']=='original'and int(q['native_IDs'])==6805 and int(q['saved_step'])+1==int(q['completed_step'])and float(q['dt_s'])==.000005 and float(q['signed_dterror_s'])<=1e-14 and q['dterror_interval_empty']=='0'for q in clocks.values()),'Original two signed clocks differ')
    with csvfile(files['off']['manufactured.csv'])as f,csvfile(files['on']['manufactured.csv'])as g:
        a,b=csv.DictReader(f),csv.DictReader(g);m.need(a.fieldnames==b.fieldnames and INTENTIONAL<=set(a.fieldnames),'Original manufactured CSV schema differs');columns=[q for q in a.fieldnames if q not in INTENTIONAL]
        for x,y in itertools.zip_longest(a,b):
            m.need(x is not None and y is not None,'Actual mode row counts differ');k=key(x);m.need(k==key(y)and k not in records and k[0]in(29,30)and k[1]in FIELDS and k[2]in ORACLES and 2060<=k[3]<7060,'Actual fixed-ID/group row join differs')
            clock=clocks[k[0]];m.need(equal(y['time_s'],clock['time_s'])and equal(y['tau_s'],clock['tau_from_actual_release_s'])and int(y['completed_step'])==int(clock['completed_step']),'Actual row/native clock differs')
            for q in columns:
                if q in('field','oracle'):m.need(x[q]==y[q],'Unchanged label differs: '+q)
                elif x[q]==''or y[q]=='':m.need(x[q]==y[q],'Unchanged undefined marker differs: '+q)
                else:m.need(equal(x[q],y[q]),'Unchanged exported scalar bits differ: '+str(k)+' '+q);common_bits+=1
            for row in(x,y):
                m.need(all(math.isfinite(float(row[q]))for q in row if q not in('field','oracle')and row[q]!=''),'Nonfinite retained row')
                m.need(int(row['actual_API_rate_bit_reconciled'])==(k[2]=='real_wall'),'Actual API/oracle label differs')
                m.need(abs(float(row['numeric_residual_Pa_s']))<=float(row['expanded_budget_Pa_s']),'Original expanded source budget failed')
                if k[2]=='real_wall':m.need(struct.pack('<f',float(row['literal_rate_Pa_s']))==struct.pack('<f',float(row['float_rate_Pa_s'])),'Actual float-commit bits differ')
            o,n=float(x['float_rate_Pa_s']),float(y['float_rate_Pa_s']);r=dict(part=k[0],field=k[1],oracle=k[2],id=k[3],time=float(y['time_s']),step=int(y['completed_step']),old=o,new=n,oldliteral=float(x['literal_rate_Pa_s']),literal=float(y['literal_rate_Pa_s']),oldbudget=float(x['double_budget_Pa_s']),newbudget=float(y['double_budget_Pa_s']),floatbudget=float(y['float_budget_Pa_s']),bed=int(y['legal_flat_bed']),interior=int(y['interior_no_wall']),shadow=None,comparison_budget=None,nref=1e9/float(y['n'])*float(y['k_m_s'])/(1000.*9.80665)*1000.)
            records[k]=r;counts[k[:3]]+=1
            for cohort in COHORTS:
                if cohort=='all'or r['bed'if cohort=='legal_flat_bed'else'interior']:groups[(*k[:3],cohort)].append(r)
    m.need(len(records)==60000 and len(counts)==12 and all(q==5000 for q in counts.values()),'All60000 original fixed-ID rows required')
    return records,groups,columns,common_bits

def prediction(records,before):
    path=L/'c08_h18_joint_eta_shadow_r1.check.json';g=m.read(path);before.append(m.stat(path));m.need(g['passed']and g['analysis_complete']and g['consumed_stats_unchanged']and g['soil_rows_consumed']==60000 and g['per_ID_variant_rows']==240000 and g['actual_groups']==12,'Sealed four-weight offline algebra required');body=artifact(g,'per_ID_weights.csv',before);variants=Counter();selected=0;literalRatio=floatRatio=0.;error2=0.;absolute=0.
    with csvfile(body)as f:
        for row in csv.DictReader(f):
            variants[row['variant']]+=1
            if row['variant']!='receiver_C_bare':continue
            k=key(row);m.need(k in records,'Prediction unknown fixed ID/group');r=records[k];m.need(r['shadow']is None and equal(row['time_s'],r['time'])and int(row['completed_step'])==r['step']and equal(row['original_literal_rate_Pa_s'],r['oldliteral'])and int(row['legal_flat_bed'])==r['bed']and int(row['interior_no_wall'])==r['interior'],'Prediction actual-clock/anchor/cohort join differs')
            pred=float(row['shadow_rate_Pa_s']);delta=float(row['variant_minus_original_Pa_s']);db=float(row['delta_rate_arithmetic_budget_Pa_s']);m.need(math.isfinite(pred)and math.isfinite(db)and db>=0,'Invalid sealed prediction/budget')
            # Existing neighbor/kernel enclosure + both source expression roundoffs;
            # final exported host addition only. This is not a physical tolerance.
            budget=db+r['oldbudget']+r['newbudget']+gamma(16)*(abs(pred)+abs(r['literal'])+abs(r['oldliteral'])+abs(delta));err=r['literal']-pred
            literalRatio=max(literalRatio,ratio(err,budget));floatRatio=max(floatRatio,ratio(r['new']-pred,budget+r['floatbudget']));r['shadow']=pred;r['comparison_budget']=budget;error2+=err*err;absolute=max(absolute,abs(err));selected+=1
    m.need(selected==60000 and variants==Counter({v:60000 for v in('pair_C_eta','pair_C_bare','receiver_C_eta','receiver_C_bare')}),'All240000 stored predictions/60000 receiver-C rows required')
    return dict(source=m.stat(path),body=m.stat(body),rows=selected,literal_max_budget_ratio=literalRatio,float_max_budget_ratio=floatRatio,literal_difference_RMS_Pa_s=math.sqrt(error2/selected),literal_difference_absmax_Pa_s=absolute,actual_rate_is_shadow=False)

def metrics(groups):
    out=[]
    for k in sorted(groups):
        rr=groups[k];o=np.array([r['old']for r in rr]);n=np.array([r['new']for r in rr]);s=np.array([r['shadow']for r in rr]);ro,rn=rms(o),rms(n)
        out.append(dict(part=k[0],field=k[1],oracle=k[2],cohort=k[3],count=len(rr),time_s=rr[0]['time'],completed_step=rr[0]['step'],rate_origin='actual_API_float'if k[2]=='real_wall'else'analytic_generated_float',old_rate_RMS_Pa_s=ro,new_rate_RMS_Pa_s=rn,new_minus_old_RMS_Pa_s=rms(n-o),old_absmax_Pa_s=float(np.max(np.abs(o))),new_absmax_Pa_s=float(np.max(np.abs(n))),RMS_reduction_percent=100*(1-rn/ro)if ro else None,old_mean_Pa_s=float(np.mean(o)),new_mean_Pa_s=float(np.mean(n)),N_reference_RMS_Pa_s=rms([r['nref']for r in rr])if k[1]==FIELDS[1]else None,new_RMS_over_N_reference=rn/rms([r['nref']for r in rr])if k[1]==FIELDS[1]else None,offline_shadow_literal_RMS_Pa_s=rms(s),new_float_minus_shadow_RMS_Pa_s=rms(n-s),comparison_budget_absmax_Pa_s=max(r['comparison_budget']for r in rr)))
    m.need(len(out)==36,'Exactly12groups times3nonempty cohorts required');return out

def plots(rows,records):
    paths=[];fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained');labels=['P29 real','P29 analytic','P30 real','P30 analytic']
    for i,cohort in enumerate(COHORTS):
        for j,field in enumerate(FIELDS):
            ax=axes[i,j];rr=[next(r for r in rows if(r['part'],r['field'],r['oracle'],r['cohort'])==(p,field,o,cohort))for p in(29,30)for o in ORACLES]
            for col,label,color in(('old_rate_RMS_Pa_s','Original pair-C / Eta²','#b35c00'),('new_rate_RMS_Pa_s','Private receiver-C / bare','#1764aa')):ax.plot(range(4),[r[col]for r in rr],'o-',label=label,color=color)
            values=[r[q]for r in rr for q in('old_rate_RMS_Pa_s','new_rate_RMS_Pa_s')]
            if j and min(values)>0 and max(values)/min(values)>=5:ax.set_yscale('log');ax.yaxis.set_major_locator(LogLocator(base=10,subs=(1,2,5),numticks=12));ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:format(x,'.3g')));ax.yaxis.set_minor_formatter(NullFormatter())
            else:ax.set_ylim(bottom=0);ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
            ax.set_xticks(range(4),labels,rotation=18);ax.set_title(field[0]+' | '+cohort);ax.set_ylabel('RMS rate [Pa/s]');ax.grid(True,alpha=.25)
    axes[0,0].legend(fontsize=9);fig.suptitle('Actual CPU spatial-rate implementation comparison; no trajectory or physical acceptance\nReal = API float; analytic = generated oracle float; H/N/X continuous joint drive is zero')
    path=FIG/(TAG+'_rates.png');fig.savefig(path,dpi=165);plt.close(fig);paths.append(path)
    fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    for i,oracle in enumerate(ORACLES):
        for j,field in enumerate(FIELDS):
            ax=axes[i,j];rr=[r for r in records.values()if r['field']==field and r['oracle']==oracle];x=np.array([r['old']for r in rr]);y=np.array([r['new']for r in rr]);ax.scatter(x,y,s=2,alpha=.25,rasterized=True);lim=[float(min(x.min(),y.min())),float(max(x.max(),y.max()))];ax.plot(lim,lim,'--',color='.3',lw=.8)
            if j:
                for axis in('x','y'):getattr(ax,'set_'+axis+'scale')('symlog',linthresh=1);loc=SymmetricalLogLocator(base=10,linthresh=1);loc.set_params(numticks=9);getattr(ax,axis+'axis').set_major_locator(loc)
            ax.set_title(field[0]+' | '+oracle+' | all10000 signed rows');ax.set_xlabel('Original rate [Pa/s]');ax.set_ylabel('Private rate [Pa/s]');ax.grid(True,alpha=.25)
    fig.suptitle('Every fixed material ID at both actual clocks; signed ranges retained, no interpolation or clipping')
    path=FIG/(TAG+'_signed.png');fig.savefig(path,dpi=165);plt.close(fig);paths.append(path);return paths

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');m.need(p.parse_args().execution_authorized,'Independent offline root admission required');outputs=[FIG/(TAG+s)for s in('_metrics.csv','_rates.png','_signed.png')];m.need(not CHECK.exists()and all(not q.exists()for q in outputs),'Existing review/partial figures protected');before=[m.stat(Path(__file__)),m.stat(T/'notes'/(TAG+'.md'))]
    try:
        files,evidence=modes(before);byteproof={q:same_file(files['off'][q],files['on'][q])for q in('walls.csv','restore_route.csv','selected_clocks.csv')};m.need(all(byteproof.values()),'Unchanged actual wall/restore/clock bytes differ');records,groups,columns,scalarbits=consume(files);shadow=prediction(records,before);rows=metrics(groups);m.verify(before)
        with outputs[0].open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        figures=plots(rows,records);m.verify(before);m.save(CHECK,dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,actual_rows=60000,actual_rate_rows=30000,analytic_generated_rows=30000,matched_groups=12,metrics_rows=36,unchanged_exported_columns=columns,unchanged_exported_scalar_bits=scalarbits,OFF_ON_unchanged_file_bytes=byteproof,modes=evidence,prediction=shadow,material_kappa='inherited native/upstream contract only, not an invented manufactured column',continuous_reference='declared H/N/X gradp+rho_w Ace=0; whole-side/FS geometry not a complete IBVP',source_operator_choice='receiver-C/bare Eq23 isotropic2D trace consistency, not fine rank certified by broad FP enclosure',prior_pair_bare_H12_failure_preserved=True,new_API_calls=0,new_solver_invocations=0,new_native_invocations=0,old_analysis_reexecuted=False,SHA_scans=0,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[m.stat(q)for q in(outputs[0],*figures)]))
    except Exception as e:
        if not CHECK.exists():m.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),consumed=before,partial_outputs_preserved=True,new_API_calls=0,new_solver_invocations=0,new_native_invocations=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()
