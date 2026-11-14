"""One offline saved-state pair/localization pass; no force, solver or reader calls."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import c08_h18_rv_window_review_r1 as window

T,L=window.T,window.L;need,read,stat,bind=window.need,window.read,window.stat,window.bind
TAG='c08_h18_rv_localization_review_r1';NOTE=T/'notes'/(TAG+'.md')
GATE=L/'c08_h18_rv_window_review_r1.check.json'
DP=.04;N=5000;CASES=('original','rv');LABELS=dict(zip(CASES,window.CASES));CUTS=(.7,.5)

def csvread(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvwrite(p,rows):
    need(rows,'Expected nonempty current-case scientific table')
    with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def consume(e,used):bind(e);used.append(e);return Path(e['path'])
def recorded(path,entries):
    found=[e for e in entries if Path(e['path']).resolve()==Path(path).resolve()]
    need(found and all(e==found[0] for e in found),'Passed gate has no unique unchanged binding: '+str(path));return found[0]
def inputs(used):
    g=read(GATE);need(g['passed'] and g['analysis_complete'] and g['consumed_stats_unchanged'] and g['actual_matched_native_states']==91 and g['actual_soil_IDs']==N and g['typed_arrays']==22,'Passed complete native/scientific window gate required')
    used.extend([stat(GATE),stat(Path(__file__)),stat(NOTE),stat(Path(window.__file__)),stat(Path(window.typed.__file__)),stat(Path(window.core.__file__))])
    histpath=consume(recorded(T/'figures/c08_h18_rv_window_review_r1_history.csv',g['files']),used)
    cohortpath=consume(recorded(T/'figures/c08_h18_rv_window_review_r1_source_cohorts.csv',g['files']),used)
    history={(r['case'],int(r['part'])):r for r in csvread(histpath)};rows=csvread(cohortpath)
    ids=np.array([int(r['native_id']) for r in rows],dtype=np.uint32);need(np.array_equal(ids,np.arange(2060,7060,dtype=np.uint32)) and len(history)==182,'All actual material/reference/history rows required')
    ref={key:np.array([[float(r[key+'_'+axis+'_m']) for axis in 'xyz'] for r in rows]) for key in ('initial','PRE')};ref['PRE_time_s']=g['actual_source_time_s']
    bundles={};h=None
    for case,key in (('original','reference_native'),('rv','native_receipt')):
        n=read(consume(g[key],used));need(n['passed'] and n['consumed_stats_unchanged'] and n['reader_invocations']==1,'Passed existing unique native receipt required')
        doneentry=consume(n['native_completion'],used);done=read(doneentry);need(done['passed'] and done['samples']==91 and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805,'Original complete native profile required')
        root=doneentry.parent
        for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):consume(recorded(root/leaf,g['consumed']),used)
        bundles[case]=window.typed.typed(root,6805,91,used)
        if h is None:h=float(done['H'])
        need(h==float(done['H']) and done['source_actual_time_s']==g['actual_source_time_s'],'Actual common H/PRE clock differs')
    return g,bundles,history,ids,ref,h

def geometry(pos):
    tree=cKDTree(pos);_,j=tree.query(pos,k=2,workers=1)
    d=np.linalg.norm(pos[j]-pos[:,None,:],axis=-1);nn=np.min(np.where(j!=np.arange(N)[:,None],d,np.inf),axis=1)
    pairs=tree.query_pairs(.7*DP,output_type='ndarray');r=np.linalg.norm(pos[pairs[:,0]]-pos[pairs[:,1]],axis=-1) if len(pairs) else np.empty(0)
    sets={cut:{tuple(map(int,p)) for p in pairs[r<cut*DP]} for cut in (.7,.5,.3)}
    return tree,nn,sets

def ls(s,i,h):
    """Conditional soil-only saved-velocity LS; not the original SPH/RV gradient."""
    if i in s['ls']:return s['ls'][i]
    p=s['pos'];j=np.asarray(s['tree'].query_ball_point(p[i],2*h),dtype=int);j=j[j!=i]
    delta=p[j]-p[i];r=np.linalg.norm(delta,axis=1);keep=r<2*h;j,delta,r=j[keep],delta[keep],r[keep]
    out=dict(valid=False,neighbors=len(j),coincident=int(np.count_nonzero(r==0)),condition=None,compression_s_1=None,shear_s_1=None)
    if len(j)>=2:
        q=r/h;w=s['f']['PoroCurrentVolume'][1805+j,0]*(1-.5*q)**4*(1+2*q)
        if len(w) and w.max()>0:
            w=w/w.max();u=delta[:,(0,2)]/h;dv=s['f']['Vel'][1805+j][:,(0,2)].astype(float)-s['f']['Vel'][1805+i,(0,2)].astype(float)
            A=(u.T*w)@u;B=(dv.T*w)@u;scale=float(np.abs(A).max());eig=np.linalg.eigvalsh(A)
            if eig[0]>0:
                condition=float(eig[-1]/eig[0]);out['condition']=condition if math.isfinite(condition) else None
            if scale>0:
                a,b,c=A[0,0]/scale,A[0,1]/scale,A[1,1]/scale
                if a*c-b*b>128*np.finfo(float).eps*(a*c+b*b):
                    grad=np.linalg.solve(A,B.T).T/h;D=.5*(grad+grad.T)
                    if np.isfinite(grad).all():out.update(valid=True,compression_s_1=float(-np.trace(D)),shear_s_1=float(np.sqrt((D[0,0]-D[1,1])**2+4*D[0,1]**2)))
    s['ls'][i]=out;return out

def sigma(s,i):
    kk=s['f']['SigmaState_kk'][1805+i];xy,yz,xz=s['f']['SigmaState_ij'][1805+i]
    eff=np.array(((kk[0],xy,xz),(xy,kk[1],yz),(xz,yz,kk[2])),dtype=float)
    p=float(s['f']['PorePress'][1805+i,0]);return eff,eff-p*np.eye(3)

def pair_fields(s,pair,prevpos,prevtime,ids,h,with_ls=False):
    i,j=pair;d=s['pos'][j]-s['pos'][i];r=float(np.linalg.norm(d));dv=s['f']['Vel'][1805+j].astype(float)-s['f']['Vel'][1805+i].astype(float)
    e=d/r if r>0 else None;rdot=None if e is None else float(e@dv)
    prior=float(np.linalg.norm(prevpos[j]-prevpos[i]));elapsed=s['time']-prevtime;need(elapsed>0,'Actual saved interval must be positive')
    row=dict(case=s['case'],part=s['part'],completed_step=s['step'],actual_time_s=s['time'],tau_s=s['tau'],id_i=int(ids[i]),id_j=int(ids[j]),
        r_over_dp=r/DP,previous_r_over_dp=prior/DP,previous_actual_time_s=prevtime,
        sampled_distance_rate_m_s=(r-prior)/elapsed,relative_radial_velocity_m_s=rdot,
        relative_tangential_speed_m_s=None if e is None else float(np.linalg.norm(dv-rdot*e)),direction_defined=e is not None)
    matrices=[]
    for endpoint,index in (('i',i),('j',j)):
        eff,total=sigma(s,index);matrices.append((eff,total))
        for axis,c in zip('xyz',s['pos'][index]):row[axis+'_'+endpoint+'_m']=float(c)
        for name,field in (('p','PorePress'),('native_p_minus_fixedP0','ExcessPorePress'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity')):row[name+'_'+endpoint]=float(s['f'][field][1805+index,0])
        row['FSType_'+endpoint]=int(s['f']['FSType'][1805+index,0])
        row['effective_max_principal_'+endpoint+'_Pa']=float(np.linalg.eigvalsh(eff)[-1]);row['total_max_principal_'+endpoint+'_Pa']=float(np.linalg.eigvalsh(total)[-1])
        row['effective_normal_'+endpoint+'_Pa']=None if e is None else float(e@eff@e)
        row['total_normal_'+endpoint+'_Pa']=None if e is None else float(e@total@e)
    row['total_max_principal_positive_endpoints']=sum(row['total_max_principal_'+k+'_Pa']>0 for k in ('i','j'))
    row['total_normal_positive_endpoints']=None if e is None else sum(row['total_normal_'+k+'_Pa']>0 for k in ('i','j'))
    row['effective_normal_mean_Pa']=None if e is None else .5*(row['effective_normal_i_Pa']+row['effective_normal_j_Pa'])
    row['total_normal_mean_Pa']=None if e is None else .5*(row['total_normal_i_Pa']+row['total_normal_j_Pa'])
    mean=.5*(matrices[0][1]+matrices[1][1]);row['total_tangential_traction_norm_Pa']=None if e is None else float(np.linalg.norm(mean@e-row['total_normal_mean_Pa']*e))
    if with_ls:
        for endpoint,index in (('i',i),('j',j)):
            for key,value in ls(s,index,h).items():row['LS_'+endpoint+'_'+key]=value
    return row

def catalog_new(case,pair,ids,ref):
    i,j=pair;q=dict(case=case,id_i=int(ids[i]),id_j=int(ids[j]),PRE_time_s=ref['PRE_time_s'],first_part=None,first_time_s=None,first_tau_s=None,
        first_below_0p5_part=None,first_below_0p5_time_s=None,min_r_part=None,min_r_time_s=None,min_r_tau_s=None,min_r_over_dp=None,
        last_part=None,close_0p7_observations=0,close_0p5_observations=0,late_0p5_observations=0,
        r_initial_over_dp=float(np.linalg.norm(ref['initial'][j]-ref['initial'][i])/DP),r_PRE_over_dp=float(np.linalg.norm(ref['PRE'][j]-ref['PRE'][i])/DP),
        longest_0p7_saved_run=0,longest_0p5_saved_run=0,longest_0p7_saved_span_s=0.,longest_0p5_saved_span_s=0.)
    for endpoint,index in (('i',i),('j',j)):
        for stage in ('initial','PRE'):
            for axis,value in zip('xyz',ref[stage][index]):q[stage+'_'+axis+'_'+endpoint+'_m']=float(value)
    q['_last5']=-2;q['_run7']=q['_run5']=0;q['_start7']=q['_start5']=0.;return q

def scan(bundles,history,ids,ref,h,source_time):
    states={c:[] for c in CASES};catalog={};events=[];globalrows=[]
    _,_,presets=geometry(ref['PRE'])
    for case in CASES:
        previous=presets;prevpos=ref['PRE'];prevtime=source_time
        for part in range(91):
            bundle=bundles[case];f=window.core.read22(bundle,part);clock=bundle['clocks'][part]
            need(np.array_equal(f['Idp'][1805:,0],ids),'All fixed original material IDs required')
            if case=='rv':need(window.bits(clock['time_s'])==window.bits(bundles['original']['clocks'][part]['time_s']) and int(clock['completed_step'])==int(bundles['original']['clocks'][part]['completed_step']),'Every actual matched time/step required')
            pos=np.array(f['Posd'][1805:]);tree,nn,sets=geometry(pos)
            s=dict(case=case,part=part,time=float(f['time']),tau=float(f['time'])-source_time,step=int(clock['completed_step']),f=f,pos=pos,tree=tree,ls={});states[case].append(s)
            old=history[(LABELS[case],part)]
            need(float(nn.min()/DP)==float(old['NN_min_over_dp']) and all(len(sets[cut])==int(old['unique_pairs_lt_'+label+'dp']) for cut,label in ((.7,'0p7'),(.5,'0p5'),(.3,'0p3'))),'One-pass geometry differs from passed complete-window history')
            row=dict(case=case,part=part,completed_step=s['step'],actual_time_s=s['time'],tau_s=s['tau'],signed_dterror_s=float(clock['signed_dterror_s']),NN_min_over_dp=float(nn.min()/DP))
            for cut,label in ((.7,'0p7'),(.5,'0p5')):
                row['pairs_'+label]=len(sets[cut]);row['new_'+label]=len(sets[cut]-previous[cut]);row['retained_'+label]=len(sets[cut]&previous[cut]);row['exited_'+label]=len(previous[cut]-sets[cut])
            for group in ('close0p7','close0p5'):
                for count in (0,1,2):row[group+'_total_maxprincipal_positive_endpoints'+str(count)]=0
            row['close0p5_approaching']=row['close0p5_approaching_no_positive_normal_traction']=row['undefined_pair_directions']=0
            for pair in sorted(sets[.7]):
                attrs=pair_fields(s,pair,prevpos,prevtime,ids,h);key=(case,*pair)
                if key not in catalog:catalog[key]=catalog_new(case,pair,ids,ref)
                q=catalog[key];oldpart=q['last_part']
                if q['first_part'] is None:q.update(first_part=part,first_time_s=s['time'],first_tau_s=s['tau'])
                q['last_part']=part
                if oldpart!=part-1:q['_start7']=s['time']
                q['_run7']=q['_run7']+1 if oldpart==part-1 else 1;q['longest_0p7_saved_run']=max(q['longest_0p7_saved_run'],q['_run7']);q['longest_0p7_saved_span_s']=max(q['longest_0p7_saved_span_s'],s['time']-q['_start7']);q['close_0p7_observations']+=1
                if q['min_r_over_dp'] is None or attrs['r_over_dp']<q['min_r_over_dp']:q.update(min_r_over_dp=attrs['r_over_dp'],min_r_part=part,min_r_time_s=s['time'],min_r_tau_s=s['tau'])
                positive=attrs['total_max_principal_positive_endpoints'];row['close0p7_total_maxprincipal_positive_endpoints'+str(positive)]+=1
                if not attrs['direction_defined']:row['undefined_pair_directions']+=1
                if pair in sets[.5]:
                    if q['first_below_0p5_part'] is None:q.update(first_below_0p5_part=part,first_below_0p5_time_s=s['time'])
                    if q['_last5']!=part-1:q['_start5']=s['time']
                    q['close_0p5_observations']+=1;q['_run5']=q['_run5']+1 if q['_last5']==part-1 else 1;q['_last5']=part;q['longest_0p5_saved_run']=max(q['longest_0p5_saved_run'],q['_run5']);q['longest_0p5_saved_span_s']=max(q['longest_0p5_saved_span_s'],s['time']-q['_start5']);q['late_0p5_observations']+=int(part>=60)
                    row['close0p5_total_maxprincipal_positive_endpoints'+str(positive)]+=1
                    if attrs['relative_radial_velocity_m_s'] is not None and attrs['relative_radial_velocity_m_s']<0:
                        row['close0p5_approaching']+=1;row['close0p5_approaching_no_positive_normal_traction']+=int(attrs['total_normal_positive_endpoints']==0)
                births=[cut for cut in CUTS if pair in sets[cut] and pair not in previous[cut]]
                if births:
                    detailed=pair_fields(s,pair,prevpos,prevtime,ids,h,True)
                    for cut in births:events.append(dict(cutoff_over_dp=cut,observed_entry_bracket_not_exact_crossing=True,**detailed))
            globalrows.append(row);previous=sets;prevpos=pos;prevtime=s['time']
    cats=[]
    for (case,i,j),q in catalog.items():
        final=states[case][-1]['pos'];q['final_r_over_dp']=float(np.linalg.norm(final[j]-final[i])/DP)
        q['preexisting_at_PRE_0p7']=q['r_PRE_over_dp']<.7
        cats.append({k:v for k,v in q.items() if not k.startswith('_')})
    return states,globalrows,events,cats

def representatives(states,events,catalog,ids,ref,h,source_time):
    selected=[]
    for case in CASES:
        for cut,rule in ((.5,'first_new0p5_P40to43'),(.7,'first_new0p7_P40to43')):
            choices=[r for r in events if r['case']==case and r['cutoff_over_dp']==cut and 40<=r['part']<=43]
            if choices:
                q=min(choices,key=lambda r:(r['part'],r['r_over_dp'],r['id_i'],r['id_j']));selected.append((case,rule,q['id_i'],q['id_j'],q['part']))
        cats=[r for r in catalog if r['case']==case]
        if cats:
            q=min(cats,key=lambda r:(r['final_r_over_dp'],r['id_i'],r['id_j']));selected.append((case,'closest_final_pair',q['id_i'],q['id_j'],90))
            late=[r for r in cats if r['late_0p5_observations']>0]
            if late:
                q=min(late,key=lambda r:(-r['late_0p5_observations'],-r['longest_0p5_saved_run'],r['min_r_over_dp'],r['id_i'],r['id_j']));selected.append((case,'most_observed_late0p5_pair',q['id_i'],q['id_j'],q['min_r_part']))
    selection=[]
    for case,rule,i,j,part in selected:
        s=states[case][part];selection.append(dict(source_case=case,selection_rule=rule,id_i=i,id_j=j,selection_part=part,selection_time_s=s['time'],selection_tau_s=s['tau']))
    rows=[];idrow={int(v):i for i,v in enumerate(ids)}
    for i,j in sorted({(r['id_i'],r['id_j']) for r in selection}):
        for case in CASES:
            prev=ref['PRE'];time=source_time
            for s in states[case]:rows.append(pair_fields(s,(idrow[i],idrow[j]),prev,time,ids,h,True));prev=s['pos'];time=s['time']
    return selection,rows

def plots(prefix,states,globalrows,events):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors=dict(original='#2166AC',rv='#D6604D');styles=('-','--',':')
    charts=(('Unique pairs <.7 / .5 dp',('pairs_0p7','pairs_0p5')),('New observed entries <.7 / .5 dp',('new_0p7','new_0p5')),
        ('Close .7 pairs: positive total principal at0/1/2 ends',tuple('close0p7_total_maxprincipal_positive_endpoints'+str(i) for i in (0,1,2))),
        ('Close .5 pairs: positive total principal at0/1/2 ends',tuple('close0p5_total_maxprincipal_positive_endpoints'+str(i) for i in (0,1,2))),
        ('Approaching .5 pairs / no positive directional traction',('close0p5_approaching','close0p5_approaching_no_positive_normal_traction')),('Minimum nonself NN / dp',('NN_min_over_dp',)))
    fig,axes=plt.subplots(3,2,figsize=(14,11),layout='constrained')
    for ax,(title,keys) in zip(axes.flat,charts):
        for case in CASES:
            rows=[q for q in globalrows if q['case']==case]
            for k,key in enumerate(keys):ax.plot([q['tau_s'] for q in rows],[q[key] for q in rows],color=colors[case],ls=styles[k])
        for p in (40,43,60):ax.axvline(states['rv'][p]['tau'],color='.65',lw=.7,ls=':')
        ax.set(title=title,xlabel='Actual time since PRE [s]');ax.grid(alpha=.2)
    handles=[Line2D([0],[0],color=colors[c],label=c) for c in CASES]+[Line2D([0],[0],color='.25',ls=s,label=label+' metric in title') for s,label in zip(styles,('1st','2nd','3rd'))]
    fig.legend(handles=handles,loc='outside lower center',ncol=5,fontsize=9);fig.suptitle('All5000 material IDs at91 actual saves: observations do not establish a force/cause',fontsize=12)
    files=[Path(str(prefix)+'_history.png')];fig.savefig(files[-1],dpi=175);plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(17,8),layout='constrained')
    allpos=np.concatenate([states[c][p]['pos'] for c in CASES for p in (40,41,42,43)]);lo=allpos.min(axis=0);hi=allpos.max(axis=0)
    lookup={int(v):i for i,v in enumerate(states['rv'][0]['f']['Idp'][1805:,0])}
    for row,case in enumerate(CASES):
        for col,part in enumerate((40,41,42,43)):
            s=states[case][part];ax=axes[row,col];ax.scatter(s['pos'][:,0],s['pos'][:,2],s=4,c='.72',edgecolors='none',rasterized=True)
            group=[q for q in events if q['case']==case and q['part']==part];pairs={}
            for q in group:pairs.setdefault((q['id_i'],q['id_j']),q)
            deep={(q['id_i'],q['id_j']) for q in group if q['cutoff_over_dp']==.5}
            for pair,q in pairs.items():
                a,b=(lookup[v] for v in pair);v=q['total_normal_mean_Pa'];color='.25' if v is None or v==0 else ('#D73027' if v>0 else '#2166AC')
                ax.plot(s['pos'][[a,b],0],s['pos'][[a,b],2],color=color,lw=2 if pair in deep else 1.)
            ax.set(xlim=(lo[0]-.04,hi[0]+.04),ylim=(lo[2]-.04,hi[2]+.04),xlabel='Actual x [m]',ylabel='Actual z [m]');ax.set_aspect('equal')
            ax.set_title(case+f" P{part}, tau={s['tau']:.9f}s\nnew pair IDs={len(pairs)}, new <.5={len(deep)}",fontsize=9)
    handles=[Line2D([0],[0],color=c,label=t) for c,t in (('#D73027','mean total normal traction >0'),('#2166AC','mean total normal traction <0'),('.25','zero/undefined direction'))]+[Line2D([0],[0],color='.25',lw=2,label='new <.5 entry')]
    fig.legend(handles=handles,loc='outside lower center',ncol=4,fontsize=9);fig.suptitle('P40–43 observed new .7/.5 pair entries; all5000 points retained; stress sign is not pair force',fontsize=12)
    files.append(Path(str(prefix)+'_onset.png'));fig.savefig(files[-1],dpi=175);plt.close(fig);return files

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until independent root full-read/offline admission')
    prefix=T/'figures'/TAG;check=L/(TAG+'.check.json');need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')),'Prior complete/partial analysis protected')
    used=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,native_invocations=0,GPU_actions=0,build_invocations=0,SHA_scans=0)
    try:
        gate,bundles,history,ids,ref,h=inputs(used);states,globalrows,events,catalog=scan(bundles,history,ids,ref,h,gate['actual_source_time_s'])
        selection,tracks=representatives(states,events,catalog,ids,ref,h,gate['actual_source_time_s']);onset=[q for q in events if 40<=q['part']<=43]
        need(all(stat(q['path'])==q for q in used),'Passed native/reference binding changed during offline analysis')
        files=[];bindings={}
        for name,rows in (('global',globalrows),('events',events),('catalog',catalog),('representative_selection',selection),('pair_history',tracks),('onset_events',onset)):
            out=Path(str(prefix)+'_'+name+'.csv');csvwrite(out,rows);files.append(out);bindings[name]=stat(out)
        files+=plots(prefix,states,globalrows,events);need(all(stat(q['path'])==q for q in used),'Input changed while plotting')
        result.update(passed=True,analysis_complete=True,window_gate=stat(GATE),case_labels=LABELS,catalog=bindings['catalog'],selection=bindings['representative_selection'],events=bindings['events'],pair_history=bindings['pair_history'],onset_events=bindings['onset_events'],
            rows={k:len(v) for k,v in (('global',globalrows),('events',events),('catalog',catalog),('selection',selection),('pair_history',tracks),('onset_events',onset))},native_frames_read=182,all5000_NN_scanned_each_frame=True,
            tensor_offdiag_order=['xy','yz','xz'],principal_positive_threshold_Pa=0.,LS_is_conditional_soil_only_saved_kinematics=True,exact_RV_force_or_acceleration_inferred=False,
            exact_crossing_time_interpolated=False,paper_excess_equivalence_claimed=False,causal_mechanism_concluded=False,automatic_next_solver=False,visual_QA_pending=True,consumed=used,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),consumed=used,partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
