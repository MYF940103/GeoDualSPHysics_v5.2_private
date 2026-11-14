"""One offline six-state CPU momentum/virtual-power review; never run a component or reader."""
import argparse,csv,json,math,struct
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
TAG='c08_h18_bed_power_review_r1';SOURCE='c08_h18_bed_power_probe_r1'
T=Path(__file__).resolve().parents[1];RAW=T/'outputs'/SOURCE;GATE=T/'logs'/(SOURCE+'.check.json')
OUT=T/'figures';CHECK=T/'logs'/(TAG+'.check.json');NOTE=T/'notes'/(TAG+'.md')
CASES=('original','radial');PARTS=(29,30,31);PASSES=('fluid','bound');FOCUS=(6961,6962,7011,7012)
TERMS=('combined_force_power','effective_force_power','pressure_force_power','split_force_power_residual','effective_raw_virtual_power','effective_G1_virtual_power','pressure_raw_virtual_power','pressure_G1_virtual_power','pressure_theta_virtual_power')
# First stat observation after the already passed component, not exit-time or historical seals.
FIRST_OBSERVED_UTC='2026-11-14T21:50:12.319Z'
FIRST_OBSERVED={
  "soil.csv": {
    "bytes": 32538634,
    "mtime_ns": 1794692715914468600
  },
  "focus.csv": {
    "bytes": 34344,
    "mtime_ns": 1794692715914468600
  },
  "walls.csv": {
    "bytes": 1447860,
    "mtime_ns": 1794692715914468600
  },
  "power.csv": {
    "bytes": 5460,
    "mtime_ns": 1794692715914468600
  },
  "metrics.csv": {
    "bytes": 1645,
    "mtime_ns": 1794692715914468600
  },
  "restore_route.csv": {
    "bytes": 858,
    "mtime_ns": 1794692716096045200
  },
  "selected_clocks.csv": {
    "bytes": 955,
    "mtime_ns": 1794692715914468600
  }
}
def need(ok,message):
    if not ok:raise RuntimeError(message)
def stat(path):
    p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):
    a=stat(e['path']);need(a['bytes']==e['bytes']and a['mtime_ns']==e['mtime_ns'],'Consumed file changed: '+str(e['path']));return a
def read(path):
    with Path(path).open(encoding='utf-8-sig')as f:return json.load(f)
def same(a,b):return struct.pack('<d',float(a))==struct.pack('<d',float(b))
def rows(leaf,width,text=('case',)):
    with (RAW/leaf).open(encoding='utf-8-sig',newline='')as f:
        r=csv.DictReader(f);need(len(r.fieldnames)==width,'CSV schema differs: '+leaf)
        for q in r:
            need(None not in q and None not in q.values(),'Malformed row: '+leaf)
            for k,v in q.items():
                if k not in text:need(math.isfinite(float(v)),'Nonfinite saved field: '+leaf+'/'+k)
            yield q
def key(q):
    a=(q['case'],int(q['part']));need(a[0]in CASES and a[1]in PARTS,'Outside closed six states');return a
def csvwrite(path,data):
    need(bool(data),'Empty derived table')
    with path.open('x',encoding='utf-8',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def savecheck(q):
    with CHECK.open('x',encoding='utf-8')as f:json.dump(q,f,indent=2,allow_nan=False);f.write('\n')
def plot(comp,path):
    fig,axes=plt.subplots(2,2,figsize=(13,8.6),sharex=True)
    colors={'original':'#2368a0','radial':'#c96920'}
    for col,group in enumerate(PASSES):
        for case in CASES:
            d=[q for q in comp if q['case']==case and q['pass']==group];x=[q['tau_s']for q in d]
            for field,style,marker in (('P_comb_W_m','-','o'),('W_raw_W_m',':','s'),('W_corrected_W_m','--','^')):
                axes[0,col].plot(x,[q[field]for q in d],color=colors[case],ls=style,marker=marker,ms=5,lw=1.4)
            for field,style,marker in (('raw_gap_W_m',':','s'),('corrected_gap_W_m','--','^')):
                axes[1,col].plot(x,[q[field]for q in d],color=colors[case],ls=style,marker=marker,ms=5,lw=1.4)
        axes[0,col].set_title(('(a) Fluid-neighbor pass','(b) Wall-neighbor pass')[col]);axes[1,col].set_title(('(c) Fluid: P − W','(d) Wall: P − W')[col]);axes[0,col].set_ylabel('Signed power [W/m]');axes[1,col].set_ylabel('Signed gap [W/m], symlog');axes[1,col].set_yscale('symlog',linthresh=.01);axes[1,col].axhline(0,color='.5',lw=.6);axes[1,col].set_xlabel('Actual time since release [s]')
    for ax in axes.flat:ax.grid(True,alpha=.23);ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    casehandles=[Line2D([],[],color=colors[c],lw=2,label=('Original AS03','Radial RV')[i])for i,c in enumerate(CASES)]
    quantity=[Line2D([],[],color='.2',ls=s,marker=m,lw=1.4,label=l)for s,m,l in (('-','o','P: pure combined literal'),(':','s','W raw (lower: P − W raw)'),('--','^','W corrected (lower: P − W corrected)'))]
    fig.suptitle('C08 saved-state CPU force / virtual power',y=.99,fontsize=15);fig.legend(handles=casehandles,loc='upper center',bbox_to_anchor=(.5,.957),ncol=2,frameon=False);fig.legend(handles=quantity,loc='upper center',bbox_to_anchor=(.5,.916),ncol=3,frameon=False,fontsize=9)
    fig.text(.5,.018,'Six saved states only. Wall accounting is conditional, not closed wall work or GPU energy. No physical acceptance.',ha='center',fontsize=9)
    fig.subplots_adjust(top=.81,bottom=.11,hspace=.29,wspace=.25)
    with path.open('xb')as f:fig.savefig(f,format='png',dpi=180)
    plt.close(fig)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');need(ap.parse_args().execution_authorized,'Independent root offline-review admission required')
    products=[OUT/(TAG+'_comparison.csv'),OUT/(TAG+'_focus.csv'),OUT/(TAG+'.png')];need(not CHECK.exists()and all(not p.exists()for p in products),'Protect previous review/partials');consumed=[]
    try:
        gate=read(GATE);need(gate['passed']and gate['consumed_stats_unchanged']and gate['component']and gate['physical_steps']==gate['material_return_calls']==gate['filter_calls']==0,'Passed zero-step component required');consumed=[stat(GATE),stat(__file__),stat(NOTE)]
        done=read(bind(gate['completion'])['path']);call=read(bind(gate['actual_call'])['path']);build=read(bind(gate['build'])['path']);consumed += [bind(gate[k])for k in('completion','actual_call','build')]
        need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure']is None and build['passed']and build['consumed_stats_unchanged'],'Genuine passed call/build required')
        expected={'actual_restore_CellDivide_calls':14,'sorting_only_predecessor_states':8,'actual_force_calls':6,'actual_Darcy_calls':6,'actual_DtVariable_false_calls':6,'external_CPU_control_rows':30000,'external_CPU_control_scalar_bits':1740000,'literal_theta_bit_rows':30000,'literal_Rsigma_component_bit_checks':180000,'soil_rows':30000,'focus_rows':24,'power_rows':12,'active_wall_rows':2855,'physical_steps':0,'material_return_calls':0,'filter_calls':0,'RV_commits':0}
        need(done['passed']and done['stage']==SOURCE and all(done[k]==v for k,v in expected.items()),'Actual component coverage differs')
        for leaf,e in FIRST_OBSERVED.items():consumed.append(bind(dict(path=str(RAW/leaf),**e)))
        clocks={}
        for q in rows('selected_clocks.csv',12,('case','file')):
            k=key(q);need(k not in clocks,'Duplicate saved clock');need(int(q['completed_step'])==2000001+2000*k[1]and int(q['saved_step'])==int(q['completed_step'])-1 and same(q['dt_s'],5e-6)and float(q['signed_dterror_s'])<=1e-14 and int(q['dterror_interval_empty'])==0 and int(q['native_IDs'])==6805 and int(q['phase'])==1,'Original signed clock differs');clocks[k]=q
        need(len(clocks)==6,'Six original complete signed clocks required')
        def clockmatch(q):
            k=key(q);c=clocks[k];need(same(q['time_s'],c['time_s'])and int(q['completed_step'])==int(c['completed_step']),'CSV actual clock join differs');return k
        metrics={}
        for q in rows('metrics.csv',18):
            k=clockmatch(q);need(k not in metrics,'Duplicate metric state');need(int(q['active_walls'])+int(q['inactive_walls'])==int(q['NpbOk'])and int(q['NpbOk'])+int(q['ignored_walls'])==1805,'Wall role coverage differs');metrics[k]=q
        need(len(metrics)==6,'Six metric states required');nforce=0;route_count=0
        for q in rows('restore_route.csv',9):
            i=route_count;k=(CASES[i//7],28+i%7);need(q['case']==k[0]and int(q['part'])==k[1]and int(q['restore_index'])==i+1,'Fourteen-state route order differs');selected=int(q['selected_force']);need(selected==int(k[1]in PARTS)and int(q['original_force_calls_before_state'])==int(q['Darcy_calls_before_state'])==nforce,'Eight dry-state route or counts differ');nforce+=selected;route_count+=1
        need(route_count==14 and nforce==6,'Fourteen restore/six-force route required')
        aggregate={(c,p,g):[[0.]*9,[0.]*9]for c in CASES for p in PARTS for g in PASSES};ids={k:set()for k in clocks};selected={};soil_count=0
        for q in rows('soil.csv',89):
            k=clockmatch(q);i=int(q['native_id']);need(2060<=i<7060 and i not in ids[k],'Soil role/duplicate differs');ids[k].add(i);soil_count+=1
            for g in PASSES:
                a=aggregate[(*k,g)]
                for j,t in enumerate(TERMS):v=float(q[g+'_'+t+'_W_m']);a[0][j]+=v;a[1][j]+=abs(v)
            if i in FOCUS:selected[(*k,i)]=q
        need(soil_count==30000 and all(len(v)==5000 for v in ids.values())and len(selected)==24,'All original material rows/focus required')
        wall_ids={k:set()for k in clocks};wall_count=0
        for q in rows('walls.csv',44):
            k=clockmatch(q);i=int(q['native_id']);need(0<=i<1805 and i not in wall_ids[k]and int(q['mode'])==1 and int(q['sorted_index'])<int(q['NpbOk'])==int(metrics[k]['NpbOk']),'Active fresh wall identity differs');wall_ids[k].add(i);wall_count+=1
        need(wall_count==2855 and all(len(v)==int(metrics[k]['active_walls'])for k,v in wall_ids.items()),'All active wall rows required')
        focus=[]
        for q in rows('focus.csv',89):
            k=clockmatch(q);i=int(q['native_id']);need(i in FOCUS and q==selected.pop((*k,i),None),'Focus differs from same original soil row');d={f:q[f]for f in('case','part','time_s','tau_s','completed_step','native_id','x_m','z_m','p_Pa','P0_Pa','J','kappa','saved_FS','fresh_FS','CPU_theta_s_1','CPU_R_Pa_s')}
            for g in PASSES:
                for t in TERMS:d[g+'_'+t+'_W_m']=float(q[g+'_'+t+'_W_m'])
                P=float(q[g+'_combined_force_power_W_m']);W0=float(q[g+'_effective_raw_virtual_power_W_m'])+float(q[g+'_pressure_raw_virtual_power_W_m']);W1=float(q[g+'_effective_G1_virtual_power_W_m'])+float(q[g+'_pressure_theta_virtual_power_W_m']);d[g+'_raw_gap_W_m']=P-W0;d[g+'_corrected_gap_W_m']=P-W1
            focus.append(d)
        need(len(focus)==24 and not selected,'Exactly24 fixed material focus rows required');comparison=[];seen=set();sumchecks=0
        for q in rows('power.csv',23,('case','pass')):
            k=clockmatch(q);g=q['pass'];a=aggregate.get((*k,g));need(a is not None and (*k,g)not in seen,'Unknown/duplicate pass power row');seen.add((*k,g));d={f:q[f]for f in('case','part','time_s','completed_step','pass')};d['tau_s']=float(clocks[k]['tau_from_actual_release_s'])
            for j,t in enumerate(TERMS):
                for v,kind in ((a[0][j],'signed'),(a[1][j],'sumabs')):
                    col=t+'_'+kind+'_W_m';need(same(v,q[col]),'Original-order power sum differs: '+str((*k,g))+'/'+col);d[col]=v;sumchecks+=1
            P=a[0][0];W0=a[0][4]+a[0][6];W1=a[0][5]+a[0][8];scale=a[1][1]+a[1][2];d.update(P_comb_W_m=P,W_raw_W_m=W0,W_corrected_W_m=W1,raw_gap_W_m=P-W0,corrected_gap_W_m=P-W1,forceabs_scale_W_m=scale,raw_gap_percent=None if scale==0 else 100*(P-W0)/scale,corrected_gap_percent=None if scale==0 else 100*(P-W1)/scale,split_power_versus_subtracted_power_roundoff_W_m=a[0][3]-(P-a[0][1]-a[0][2]));comparison.append(d)
        need(len(comparison)==12 and sumchecks==216,'All12 pass-state/nine signed+absolute sums required');OUT.mkdir(exist_ok=True);csvwrite(products[0],comparison);csvwrite(products[1],focus);plot(comparison,products[2]);[bind(e)for e in consumed]
        savecheck(dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,source_component=stat(GATE),actual_soil_rows=soil_count,actual_focus_rows=len(focus),actual_active_wall_rows=wall_count,actual_pass_state_rows=12,original_order_sum_bit_checks=sumchecks,restore_route_rows=route_count,actual_signed_clock_rows=6,source_component_counters=expected,stat_binding_scope='First post-pass author observation of CSV stats; no claim of exit-time CSV seals',first_CSV_observed_UTC=FIRST_OBSERVED_UTC,scale_definition='sumabs(P_eff_node)+sumabs(P_p_node); differs from earlier G1-gradient-work normalization',power_definitions={'P':'pure combined source-literal float accumulator, not mixed total Ace','W_raw':'Weff_raw+Wp_raw','W_corrected':'Weff_G1+Wp_theta','gap':'P-W'},split_residual_is_retained=True,wall_account_is_closed=False,GPU_stage_force_truth=False,physical_gate_added=False,solver_invocations=0,native_invocations=0,component_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(p)for p in products]))
    except Exception as e:
        if not CHECK.exists():savecheck(dict(stage=TAG,passed=False,first_failure=str(e),partial_outputs_preserved=True,physical_acceptance=False,solver_invocations=0,native_invocations=0,component_invocations=0,consumed=consumed))
        raise
if __name__=='__main__':main()
