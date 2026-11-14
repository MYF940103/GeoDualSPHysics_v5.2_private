"""Offline paired joint-Darcy manufactured-field review; no component, solver or reader calls."""
import argparse,csv,itertools,json,math,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
TAG='c08_h18_joint_darcy_review_r1';SOURCE='c08_h18_joint_darcy_probe_r1';T=Path(__file__).resolve().parents[1];RAW=T/'outputs'/SOURCE;GATE=T/'logs'/(SOURCE+'.check.json');CHECK=T/'logs'/(TAG+'.check.json');NOTE=T/'notes'/(TAG+'.md');OUT=T/'figures'
PARTS=(29,30);FIELDS=('H_hydro_affine','N_normal_quadratic','X_cross_cubic');ORACLES=('real_wall','analytic_ghost');REGIONS=('all','legal_flat_bed','interior_no_wall');TERMS=('compression','LP','Taylor_pressure','Da','FS_Ace_Lx','chain_pressure','chain_Ace')
BASE='part,time_s,tau_s,completed_step,field,oracle,native_id,x_m,z_m,native_FS,manufactured_FS,legal_flat_bed,interior_no_wall,near_manufactured_FS,wall_donors,analytic_p_Pa,stored_p_Pa,p_float_error_Pa,P0_original_Pa,J,n,V_m2,rho_kg_m3,k_m_s,theta_s_1'.split(',')
VECTORS=('analytic_as_m_s2','analytic_Ace_m_s2','stored_Ace_m_s2','Ace_float_error_m_s2','analytic_gradp_Pa_m','analytic_drive_Pa_m','discrete_drive_Pa_m','Lx_m_1','Gp_Pa_m','gradJ_m_1')
C=[f'C{i}{j}'for i in range(1,4)for j in range(1,4)]
HEAD=BASE+[p+'_'+a for p in VECTORS for a in 'xyz']+'LP_Pa_m2,Da_s_2,source_lap_Pa_m2,source_chain_Pa_m_s,literal_rate_Pa_s,float_rate_Pa_s,seven_terms_sum_Pa_s,numeric_residual_Pa_s,float_budget_Pa_s,double_budget_Pa_s,expanded_budget_Pa_s'.split(',')+[p+'_Pa_s'for p in TERMS]+C+'Cplane_det,Cplane_cond_inf,Cplane_cond_defined,fluid_donors,fixed_donors,actual_API_rate_bit_reconciled'.split(',')
WH='part,time_s,tau_s,completed_step,field,oracle,native_id,sorted_index,NpbOk,slip_mode,x_m,z_m,J,J_minus1,stored_p_Pa,analytic_p_Pa,p_error_Pa'.split(',')+[p+'_'+a for p in('analytic_Ace_m_s2','stored_Ace_m_s2','Ace_error_m_s2','raw_wall_normal_m')for a in 'xyz']+C
SH='part,time_s,tau_s,completed_step,field,oracle,rate_RMS_Pa_s,rate_absmax_Pa_s,legal_bed_count,legal_bed_RMS_Pa_s,legal_bed_absmax_Pa_s,interior_count,interior_RMS_Pa_s,FS_count,active_wall_J_minus1_absmax,dynamic_conductivity_gradient_speed_m_s'.split(',')
BH='part,time_s,completed_step,actual_natural_dt_s,force_bound_s,wave_bound_s,pore_bound_s,k_gradient_bound_s,necessary_bound_s,control_rows_cumulative,control_scalar_bits_cumulative'.split(',')
RH='restore_index,case,part,time_s,completed_step,baseline_force,forces_before,actual_API_rates_before'.split(',')
CH='case,part,file,time_s,tau_from_actual_release_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,native_IDs,phase'.split(',')
def need(x,s):
    if not x:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):
    a=stat(e['path']);need(a['bytes']==e['bytes']and a['mtime_ns']==e['mtime_ns'],'Bound file changed: '+str(e['path']));return a
def read(p):
    with Path(p).open(encoding='utf-8-sig')as f:return json.load(f)
def same(a,b):return struct.pack('<d',float(a))==struct.pack('<d',float(b))
def rows(leaf,header,text=('field','oracle'),empty=()):
    with (RAW/leaf).open(encoding='utf-8-sig',newline='')as f:
        r=csv.DictReader(f);need(r.fieldnames==header,'Exact source CSV schema differs: '+leaf)
        for q in r:
            need(None not in q and None not in q.values(),'Malformed CSV row: '+leaf)
            for k,v in q.items():
                if k not in text and not(k in empty and v==''):need(math.isfinite(float(v)),'Nonfinite numeric field: '+leaf+'/'+k)
            yield q
def gkey(q):
    k=(int(q['part']),q['field'],q['oracle']);need(k[0]in PARTS and k[1]in FIELDS and k[2]in ORACLES,'Outside closed group');return k
def scalar_rms(values):
    s=0.;n=0
    for x in values:x=float(x);s+=x*x;n+=1
    return None if not n else math.sqrt(s/n)
def norm(a):return np.sqrt(np.sum(a*a,axis=1))
def stat3(v):return (None,None,None)if not len(v)else(float(np.mean(v)),scalar_rms(v),float(np.max(np.abs(v))))
def matrix(group,header):
    names=[n for n in header if n not in('field','oracle')];idx={n:i for i,n in enumerate(names)};data=np.array([[np.nan if q[n]==''else float(q[n])for n in names]for q in group],dtype='<f8');return data,idx
METRICS=['rate_mean_Pa_s','rate_RMS_Pa_s','rate_absmax_Pa_s','N_reference_rate_Pa_s','N_RMS_fraction','N_RMS_percent','pressure_group_RMS_Pa_s','acceleration_group_RMS_Pa_s','chain_group_RMS_Pa_s','net_to_sum_group_RMS','p_error_RMS_Pa','p_error_absmax_Pa','Ace_error_norm_RMS_m_s2','Ace_error_norm_absmax_m_s2','analytic_drive_norm_absmax_Pa_m','discrete_drive_norm_RMS_Pa_m','gradJ_norm_absmax_m_1','Cplane_condition_inf_absmax','Cplane_condition_undefined_count','Cplane_det_min','paired_delta_mean_Pa_s','paired_delta_RMS_Pa_s','paired_delta_absmax_Pa_s','paired_rate_Pearson','paired_same_nonzero_sign_fraction','paired_opposite_nonzero_sign_fraction','paired_both_zero_count','paired_one_zero_count']
for t in TERMS:METRICS += [t+'_mean_Pa_s',t+'_RMS_Pa_s','paired_delta_'+t+'_mean_Pa_s','paired_delta_'+t+'_RMS_Pa_s']
def blank(family,k,region,count,clock):
    d=dict(family=family,part=k[0],time_s=float(clock['time_s']),tau_s=float(clock['tau_from_actual_release_s']),completed_step=int(clock['completed_step']),field=k[1],oracle=k[2],region=region,count=int(count));d.update((m,None)for m in METRICS);return d
def addstats(d,prefix,v,unit):
    a,b,c=stat3(v);d[prefix+'_mean_'+unit]=a;d[prefix+'_RMS_'+unit]=b;d[prefix+'_absmax_'+unit]=c

def figures(summary,paths):
    lookup={(q['family'],q['part'],q['field'],q['oracle'],q['region']):q for q in summary};colors=('#2368a0','#d17b21');labels=('Real wall API','Analytic p/Ace ghost oracle')
    fig,ax=plt.subplots(2,3,figsize=(13,7.4),sharey=True)
    maxima=[q['rate_RMS_Pa_s']for q in summary if q['family']=='soil'and q['count']]
    for r,p in enumerate(PARTS):
        for c,f in enumerate(FIELDS):
            a=ax[r,c]
            for o,oracle in enumerate(ORACLES):
                for j,region in enumerate(REGIONS):
                    q=lookup['soil',p,f,oracle,region];x=j+(o-.5)*.26
                    if q['count']:a.bar(x,q['rate_RMS_Pa_s'],.24,color=colors[o],alpha=.87);a.plot(x,q['rate_RMS_Pa_s'],'o',color=colors[o],ms=3)
                    else:a.text(x,0,'∅',ha='center',va='bottom',color=colors[o])
            a.set_title(f'P{p}: '+('H hydro calibration','N normal quadratic','X cross cubic')[c]);a.set_xticks(range(3),('All¹','Legal bed','Interior'));a.set_yscale('symlog',linthresh=1.);a.set_ylim(0,max(maxima)*1.35);a.grid(axis='y',alpha=.23)
            if c==0:a.set_ylabel('Spatial zero-drive residual RMS [Pa/s]')
    fig.suptitle('Joint Darcy: same-ID residuals on two frozen geometries',y=.99);fig.legend([plt.Rectangle((0,0),1,1,color=z)for z in colors],labels,loc='upper center',bbox_to_anchor=(.5,.952),ncol=2,frameon=False);fig.text(.5,.018,'¹ Whole-domain side/FS fields are not a globally compatible IBVP. Symlog linear range: 1 Pa/s. No physical acceptance.',ha='center',fontsize=9);fig.subplots_adjust(top=.855,bottom=.10,wspace=.13,hspace=.30)
    with paths[0].open('xb')as h:fig.savefig(h,format='png',dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(2,3,figsize=(13,7.4),sharey=True);cats=('LP','Taylor','Da','FS-A','k-chain','Net');channel=('LP','Taylor_pressure','Da','FS_Ace_Lx');extent=0.
    for r,p in enumerate(PARTS):
        for c,f in enumerate(FIELDS):
            a=ax[r,c]
            for o,oracle in enumerate(ORACLES):
                q=lookup['soil',p,f,oracle,'legal_flat_bed']
                if not q['count']:a.text(.5,.5,'Empty legal-bed cohort',transform=a.transAxes,ha='center');continue
                y=[q[t+'_mean_Pa_s']for t in channel]+[q['chain_pressure_mean_Pa_s']+q['chain_Ace_mean_Pa_s'],q['rate_mean_Pa_s']];extent=max(extent,max(abs(v)for v in y));a.bar(np.arange(6)+(o-.5)*.28,y,.26,color=colors[o],alpha=.87)
            a.set_title(f'P{p}: '+('H','N','X')[c]+' legal flat bed');a.set_xticks(range(6),cats,fontsize=8);a.axhline(0,color='.35',lw=.7);a.set_yscale('symlog',linthresh=1.);a.grid(axis='y',alpha=.22)
            if c==0:a.set_ylabel('Signed mean source contribution [Pa/s]')
    for a in ax.flat:a.set_ylim(-extent*1.35,extent*1.35)
    fig.suptitle('Pressure / acceleration / k-chain cancellation in the legal bed cohort',y=.99);fig.legend([plt.Rectangle((0,0),1,1,color=z)for z in colors],labels,loc='upper center',bbox_to_anchor=(.5,.952),ncol=2,frameon=False);fig.text(.5,.018,'Signed spatial means can cancel; channel RMS and matched vector differences remain in the CSV. No operator is changed.',ha='center',fontsize=9);fig.subplots_adjust(top=.855,bottom=.10,wspace=.13,hspace=.30)
    with paths[1].open('xb')as h:fig.savefig(h,format='png',dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(2,2,figsize=(11,7.2),sharex=True,sharey='row');pcolors={29:'#2368a0',30:'#7e4794'}
    for col,region in enumerate(('all_active','geometric_flat_bed')):
        for p in PARTS:
            for oracle,ls,marker in zip(ORACLES,('-','--'),('o','s')):
                q=[lookup['wall',p,f,oracle,region]for f in FIELDS]
                for r,metric in enumerate(('p_error_RMS_Pa','Ace_error_norm_RMS_m_s2')):
                    y=[z[metric]if z['count']else np.nan for z in q];ax[r,col].plot(range(3),y,color=pcolors[p],ls=ls,marker=marker,ms=5,label=f'P{p} '+('real','analytic')[oracle=='analytic_ghost']);ax[r,col].grid(alpha=.23);ax[r,col].set_yscale('symlog',linthresh=1e-6 if r else 1e-3)
        ax[0,col].set_title(('All active walls¹','Geometric flat-bed walls')[col]);ax[1,col].set_xticks(range(3),('H','N','X'))
    ax[0,0].set_ylabel('Wall pressure error RMS [Pa]');ax[1,0].set_ylabel('Wall Ace error norm RMS [m/s²]');fig.suptitle('Actual ghost extension versus declared analytic values',y=.99);h,l=ax[0,0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',bbox_to_anchor=(.5,.952),ncol=4,frameon=False,fontsize=9);fig.text(.5,.018,'¹ Side/corner polynomial conditions are not all physically compatible. Analytic curves retain float storage errors; zero is not deleted.',ha='center',fontsize=8.7);fig.subplots_adjust(top=.855,bottom=.10,hspace=.18,wspace=.15)
    with paths[2].open('xb')as h:fig.savefig(h,format='png',dpi=180)
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');need(ap.parse_args().execution_authorized,'Independent root offline-review admission required');csvout=OUT/(TAG+'_summary.csv');png=[OUT/(TAG+'_'+s+'.png')for s in('residuals','cancellation','wall_errors')];need(not CHECK.exists()and all(not p.exists()for p in[csvout,*png]),'Protect earlier review/partials');consumed=[]
    try:
        gate=read(GATE);need(gate['passed']and gate['consumed_stats_unchanged']and gate['component']and gate['physical_steps']==gate['material_return_calls']==gate['filter_calls']==0,'Genuine passed zero-step component required');consumed=[stat(GATE),stat(__file__),stat(NOTE)]
        for k in('completion','actual_call','build'):consumed.append(bind(gate[k]))
        done=read(gate['completion']['path']);call=read(gate['actual_call']['path']);build=read(gate['build']['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure']is None and build['passed']and build['consumed_stats_unchanged'],'Real original call/build exits required')
        counts={'restore_CellDivide_calls':14,'sorting_only_states':12,'actual_force_calls':2,'baseline_DtVariable_false_calls':2,'baseline_included_actual_Darcy_calls':2,'manufactured_actual_Darcy_calls':6,'total_original_Darcy_API_calls':8,'actual_field_literal_reconciliations':6,'analytic_oracle_groups':6,'literal_assemblies_groups':12,'actual_rate_float_bit_rows':30000,'analytic_generated_float_rows':30000,'external_CPU_baseline_rows':10000,'external_CPU_baseline_scalar_bits':580000,'literal_theta_bits':10000,'literal_Rsigma_component_bits':60000,'manufactured_rows':60000,'summary_rows':12,'physical_steps':0,'material_return_calls':0,'filter_calls':0,'RV_commits':0}
        need(done['stage']==SOURCE and done['passed']and all(done[k]==v for k,v in counts.items())and done['max_original_float_budget_ratio']<=1 and done['max_original_expanded_budget_ratio']<=1,'Original completion coverage/budgets differ');need(not done['analytic_ghost_uses_actual_rate_API']and not done['analytic_ghost_changes_J_C_FS'],'Oracle scope differs')
        for leaf in('manufactured.csv','summary.csv','walls.csv','baseline.csv','restore_route.csv','selected_clocks.csv','completion.json'):
            p=(RAW/leaf).resolve();matches=[e for e in gate['files']if Path(e['path']).resolve()==p];need(matches and all(e==matches[0]for e in matches),'Original source file seal required: '+leaf);consumed.append(bind(matches[0]))
        clocks={}
        for q in rows('selected_clocks.csv',CH,('case','file')):
            p=int(q['part']);need(p in PARTS and p not in clocks and q['case']=='original','Two original actual clocks required');need(int(q['completed_step'])==2000001+2000*p and int(q['saved_step'])==int(q['completed_step'])-1 and same(q['dt_s'],5e-6)and float(q['signed_dterror_s'])<=1e-14 and int(q['dterror_interval_empty'])==0 and int(q['native_IDs'])==6805 and int(q['phase'])==1,'Actual signed clock differs');clocks[p]=q
        need(set(clocks)==set(PARTS),'Original selected clocks incomplete')
        def clockmatch(q):
            p=int(q['part']);need(p in clocks and same(q['time_s'],clocks[p]['time_s'])and int(q['completed_step'])==int(clocks[p]['completed_step']),'Actual CSV clock join differs')
            if 'tau_s'in q:need(same(q['tau_s'],clocks[p]['tau_from_actual_release_s']),'Actual tau differs')
        baseline=list(rows('baseline.csv',BH,()))
        need(len(baseline)==2,'Two actual baseline rows required')
        for j,q in enumerate(baseline):clockmatch(q);need(int(q['part'])==PARTS[j]and same(q['actual_natural_dt_s'],5e-6)and min(float(q[k])for k in('force_bound_s','wave_bound_s','pore_bound_s'))>=5e-6 and int(q['control_rows_cumulative'])==(j+1)*5000 and int(q['control_scalar_bits_cumulative'])==(j+1)*290000,'Original bare bounds/control counters differ')
        route=list(rows('restore_route.csv',RH,('case',)));need(len(route)==14,'Original14 route required');nf=nr=0
        for j,q in enumerate(route):
            case=('original','radial')[j//7];p=28+j%7;flag=case=='original'and p in PARTS;need(q['case']==case and int(q['part'])==p and int(q['restore_index'])==j+1 and int(q['baseline_force'])==int(flag)and int(q['forces_before'])==nf and int(q['actual_API_rates_before'])==nr,'Original dry/force route differs');nf+=flag;nr+=4*flag
        need(nf==2 and nr==8,'Production API accounting differs')
        src={}
        for q in rows('summary.csv',SH,empty=('legal_bed_RMS_Pa_s','legal_bed_absmax_Pa_s','interior_RMS_Pa_s')):clockmatch(q);k=gkey(q);need(k not in src,'Duplicate source summary');src[k]=q
        need(len(src)==12,'All12 source summaries required');soilsummary=[];wallsummary=[];real=None;total=actual=generated=0;source_RMS_bit_checks=0;all_ids=set(range(2060,7060));saved={};emptycond=0
        numeric=[n for n in HEAD if n not in('field','oracle')];ix={n:i for i,n in enumerate(numeric)}
        def val(a,n):return a[:,ix[n]]
        def vec(a,n):return a[:,[ix[n+'_'+z]for z in'xyz']]
        keys=list(itertools.product(PARTS,FIELDS,ORACLES));seen=[]
        for k,it in itertools.groupby(rows('manufactured.csv',HEAD,empty=('Cplane_cond_inf',)),gkey):
            q=list(it);need(k==keys[len(seen)]and len(q)==5000,'Closed manufactured group order/5000 rows differs');seen.append(k);[clockmatch(z)for z in q];a,_=matrix(q,HEAD);need(set(val(a,'native_id').astype(int))==all_ids,'Exact5000 material IDs required');need(np.all(val(a,'actual_API_rate_bit_reconciled')==(k[2]=='real_wall')),'Actual versus generated flag differs');need(np.all(val(a,'J')==1)and np.all(val(a,'theta_s_1')==0),'Declared manufactured soil J/theta differs')
            cond=val(a,'Cplane_cond_defined')==1;need(np.all(np.isfinite(val(a,'Cplane_cond_inf')[cond]))and np.all(np.isnan(val(a,'Cplane_cond_inf')[~cond]))and np.all(val(a,'Cplane_det')[~cond]==0),'Condition descriptor undefined/singular schema differs');emptycond+=int(np.sum(~cond));terms=a[:,[ix[t+'_Pa_s']for t in TERMS]];rates=val(a,'float_rate_Pa_s')
            for j,z in enumerate(a):
                zsum=0.
                for v in terms[j]:zsum+=float(v)
                need(same(zsum,z[ix['seven_terms_sum_Pa_s']])and same(float(rates[j])-zsum,z[ix['numeric_residual_Pa_s']]),'Original ordered seven-term arithmetic differs');lit=float(z[ix['literal_rate_Pa_s']]);need(struct.pack('<f',float(rates[j]))==struct.pack('<f',lit),'Actual/generated float conversion differs');need(abs(float(rates[j])-lit)<=z[ix['float_budget_Pa_s']]and abs(float(rates[j])-zsum)<=z[ix['expanded_budget_Pa_s']],'Original row arithmetic budget differs')
            masks={'all':np.ones(5000,dtype=bool),'legal_flat_bed':val(a,'legal_flat_bed')==1,'interior_no_wall':val(a,'interior_no_wall')==1};s=src[k]
            for region,cf,rf,mf in(('all',None,'rate_RMS_Pa_s','rate_absmax_Pa_s'),('legal_flat_bed','legal_bed_count','legal_bed_RMS_Pa_s','legal_bed_absmax_Pa_s'),('interior_no_wall','interior_count','interior_RMS_Pa_s',None)):
                m=masks[region];n=int(np.sum(m));need(cf is None or int(s[cf])==n,'Source cohort count differs');rr=scalar_rms(rates[m]);need((s[rf]==''if rr is None else same(rr,s[rf])),'Source original-order RMS differs');source_RMS_bit_checks+=rr is not None
                if mf:need((s[mf]==''if not n else same(np.max(np.abs(rates[m])),s[mf])),'Source cohort max differs')
            need(int(s['FS_count'])==int(np.sum(np.isin(val(a,'manufactured_FS'),(2,3)))),'Source FS count differs');a=a[np.argsort(val(a,'native_id'))];masks={'all':np.ones(5000,dtype=bool),'legal_flat_bed':val(a,'legal_flat_bed')==1,'interior_no_wall':val(a,'interior_no_wall')==1};start=len(soilsummary)
            for region,m in masks.items():
                v=a[m];d=blank('soil',k,region,len(v),clocks[k[0]])
                if len(v):
                    rr=val(v,'float_rate_Pa_s');addstats(d,'rate',rr,'Pa_s');ch=v[:,[ix[t+'_Pa_s']for t in TERMS]]
                    for j,t in enumerate(TERMS):d[t+'_mean_Pa_s']=float(np.mean(ch[:,j]));d[t+'_RMS_Pa_s']=scalar_rms(ch[:,j])
                    pg=ch[:,1]+ch[:,2];ag=ch[:,3]+ch[:,4];cg=ch[:,5]+ch[:,6];pr=scalar_rms(pg);ar=scalar_rms(ag);cr=scalar_rms(cg);d['pressure_group_RMS_Pa_s']=pr;d['acceleration_group_RMS_Pa_s']=ar;d['chain_group_RMS_Pa_s']=cr;d['net_to_sum_group_RMS']=None if pr+ar+cr==0 else d['rate_RMS_Pa_s']/(pr+ar+cr)
                    d['p_error_RMS_Pa']=scalar_rms(val(v,'p_float_error_Pa'));d['p_error_absmax_Pa']=float(np.max(np.abs(val(v,'p_float_error_Pa'))));ae=norm(vec(v,'Ace_float_error_m_s2'));d['Ace_error_norm_RMS_m_s2']=scalar_rms(ae);d['Ace_error_norm_absmax_m_s2']=float(np.max(ae));d['analytic_drive_norm_absmax_Pa_m']=float(np.max(norm(vec(v,'analytic_drive_Pa_m'))));d['discrete_drive_norm_RMS_Pa_m']=scalar_rms(norm(vec(v,'discrete_drive_Pa_m')));d['gradJ_norm_absmax_m_1']=float(np.max(norm(vec(v,'gradJ_m_1'))));defined=val(v,'Cplane_cond_defined')==1;d['Cplane_condition_inf_absmax']=None if not np.any(defined)else float(np.max(val(v,'Cplane_cond_inf')[defined]));d['Cplane_condition_undefined_count']=int(np.sum(~defined));d['Cplane_det_min']=float(np.min(val(v,'Cplane_det')))
                    if k[1].startswith('N_'):
                        need(np.all(val(v,'n')==val(v,'n')[0])and np.all(val(v,'k_m_s')==val(v,'k_m_s')[0]),'N reference must use actual constant n/k');scale=1e9/float(val(v,'n')[0])*float(val(v,'k_m_s')[0])/(1000*9.80665)*1000;d['N_reference_rate_Pa_s']=scale;d['N_RMS_fraction']=d['rate_RMS_Pa_s']/scale;d['N_RMS_percent']=100*d['N_RMS_fraction']
                soilsummary.append(d)
            common=['native_id','x_m','z_m','native_FS','manufactured_FS','legal_flat_bed','interior_no_wall','near_manufactured_FS','wall_donors','analytic_p_Pa','stored_p_Pa','p_float_error_Pa','P0_original_Pa','J','n','V_m2','rho_kg_m3','k_m_s','theta_s_1']+[p+'_'+z for p in('analytic_as_m_s2','analytic_Ace_m_s2','stored_Ace_m_s2','Ace_float_error_m_s2','analytic_gradp_Pa_m','analytic_drive_Pa_m','Lx_m_1','gradJ_m_1')for z in'xyz']+C+['Cplane_det','Cplane_cond_defined','fluid_donors','fixed_donors']
            if k[2]=='real_wall':real=(k,a,start);actual+=5000
            else:
                rk,b,bs=real;need(rk[:2]==k[:2]and np.array_equal(a[:,[ix[x]for x in common]].view('<u8'),b[:,[ix[x]for x in common]].view('<u8')),'Same-ID J/C/FS/cohort/soil-field pairing differs')
                for j,region in enumerate(REGIONS):
                    m=masks[region];d=soilsummary[bs+j]
                    if not np.any(m):continue
                    x=val(b[m],'float_rate_Pa_s');y=val(a[m],'float_rate_Pa_s');addstats(d,'paired_delta',x-y,'Pa_s');xc=x-np.mean(x);yc=y-np.mean(y);den=math.sqrt(float(np.dot(xc,xc))*float(np.dot(yc,yc)));d['paired_rate_Pearson']=None if den==0 else float(np.dot(xc,yc))/den;both=(x!=0)&(y!=0);n=int(np.sum(both));d['paired_same_nonzero_sign_fraction']=None if not n else float(np.mean(np.sign(x[both])==np.sign(y[both])));d['paired_opposite_nonzero_sign_fraction']=None if not n else float(np.mean(np.sign(x[both])!=np.sign(y[both])));d['paired_both_zero_count']=int(np.sum((x==0)&(y==0)));d['paired_one_zero_count']=int(np.sum((x==0)^(y==0)))
                    for t in TERMS:dv=val(b[m],t+'_Pa_s')-val(a[m],t+'_Pa_s');d['paired_delta_'+t+'_mean_Pa_s']=float(np.mean(dv));d['paired_delta_'+t+'_RMS_Pa_s']=scalar_rms(dv)
                generated+=5000;real=None
            total+=5000
        need(seen==keys and total==60000 and actual==generated==30000 and real is None,'Full actual/analytic coverage differs')
        wallcount=0;seen=[];wreal=None
        for k,it in itertools.groupby(rows('walls.csv',WH),gkey):
            q=list(it);need(k==keys[len(seen)]and q,'Closed wall group order differs');seen.append(k);[clockmatch(z)for z in q];a,wi=matrix(q,WH);vv=lambda n:a[:,wi[n]];ids=vv('native_id').astype(int);need(len(set(ids))==len(ids)and np.all((ids>=0)&(ids<1805))and np.all(vv('sorted_index')<vv('NpbOk')),'Active wall identities differ');need(same(np.max(np.abs(vv('J_minus1'))),src[k]['active_wall_J_minus1_absmax']),'Actual wall J residual differs');a=a[np.argsort(ids)];vv=lambda n:a[:,wi[n]]
            bed=(vv('x_m')>=.5)&(vv('x_m')<=3.5)&(vv('raw_wall_normal_m_x')==0)&(vv('raw_wall_normal_m_y')==0)&(vv('raw_wall_normal_m_z')>0)&(vv('slip_mode')==2)
            for region,m in(('all_active',np.ones(len(a),bool)),('geometric_flat_bed',bed)):
                d=blank('wall',k,region,int(np.sum(m)),clocks[k[0]])
                if np.any(m):pe=vv('p_error_Pa')[m];ae=norm(a[m][:,[wi['Ace_error_m_s2_'+z]for z in'xyz']]);d['p_error_RMS_Pa']=scalar_rms(pe);d['p_error_absmax_Pa']=float(np.max(np.abs(pe)));d['Ace_error_norm_RMS_m_s2']=scalar_rms(ae);d['Ace_error_norm_absmax_m_s2']=float(np.max(ae))
                wallsummary.append(d)
            common=['native_id','sorted_index','NpbOk','slip_mode','x_m','z_m','J','J_minus1','analytic_p_Pa']+[p+'_'+z for p in('analytic_Ace_m_s2','raw_wall_normal_m')for z in'xyz']+C
            if k[2]=='real_wall':wreal=(k,a)
            else:
                rk,b=wreal;need(rk[:2]==k[:2]and a.shape==b.shape and np.array_equal(a[:,[wi[x]for x in common]].view('<u8'),b[:,[wi[x]for x in common]].view('<u8')),'Same-wall J/C/normal/identity pairing differs');wreal=None
            wallcount+=len(a)
        need(seen==keys and wallcount==done['wall_rows']and wreal is None,'All active wall groups incomplete');summary=soilsummary+wallsummary;need(len(summary)==60,'36soil+24wall compact summaries required');OUT.mkdir(exist_ok=True)
        with csvout.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
        figures(summary,png);[bind(e)for e in consumed]
        check=dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,source_component=stat(GATE),actual_rows=total,actual_proof_rows=actual,analytic_generated_rows=generated,active_wall_rows=wallcount,groups=12,soil_region_rows=36,wall_region_rows=24,original_order_RMS_bit_checks=source_RMS_bit_checks,undefined_condition_rows=emptycond,normal_quadratic_reference='(Kw/n)*(k/gamma_ref)*B, B1000Pa/m2; actual n/k, Kw1GPa, gamma_ref1000*9.80665',rate_units='Pa/s spatial truncation, no integrated pressure error',all_domain_is_legal_IBVP=False,matched_delta_direction='real minus analytic, same material ID/C/J/FS; correlation/sign retained',same_RMS_is_ghost_irrelevance=False,wall_cohort_is_receiver_cohort=False,continuous_drive_declared_zero=True,physical_threshold_added=False,solver_invocations=0,reader_invocations=0,native_invocations=0,component_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(p)for p in[csvout,*png]])
        with CHECK.open('x',encoding='utf-8')as f:json.dump(check,f,indent=2,allow_nan=False);f.write('\n')
    except Exception as e:
        if not CHECK.exists():
            with CHECK.open('x',encoding='utf-8')as f:json.dump(dict(stage=TAG,passed=False,first_failure=str(e),partial_outputs_preserved=True,physical_acceptance=False,solver_invocations=0,component_invocations=0,reader_invocations=0,consumed=consumed),f,indent=2);f.write('\n')
        raise
if __name__=='__main__':main()
