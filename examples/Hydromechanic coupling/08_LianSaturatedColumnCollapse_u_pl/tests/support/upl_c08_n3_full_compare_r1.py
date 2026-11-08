"""Two sealed CompletedOnly full3s datasets: one typed pass each, descriptive spatial/material comparison."""
import argparse,json,struct
from pathlib import Path
import upl_c08_clustering_r1 as cluster
from matplotlib.colors import SymLogNorm
np,c,plt=cluster.np,cluster.c,cluster.plt
T=c.T;TAG='upl_c08_n3_full_compare_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
SPECS=(('n2p55','r5',2.55,'upl_c08_bedkeep_formal_native_r1'),('n3','r6',3.,'upl_c08_n3_formal_native_r1'));SNAPS=((.3,29),(.6,59),(1.2,119),(2.,199),(3.,299))

def load(spec):
    label,version,exponent,stage=spec;rp=T/'logs'/('upl_c08_formal_psi0_'+version+'_r1.run.json');r=c.read(rp);out=Path(r['output']);pp=out/('postprocess_'+version+'.json');post=c.read(pp)
    c.need(r['passed'] and r['solver_completed'] and r['postprocess_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==5200000 and r['saved_frames']==300 and r['consumed_stats_unchanged'],'Sealed normal full3s owner required')
    c.need(post['passed'] and post['native_completed'] and post['global_steps']==5200000 and post['saved_frames']==300 and post['actual_native_IDs']==6805 and post['AS_policy']=='ReleaseOnly' and post['AS_coefficient']==.2 and post['AS_exponent']==exponent and not post['raw_BI4_rewritten'],'Original postprocess/native scope differs')
    native=Path(c.bind(post['native_completion'])['path']).parent;d=c.read(native/'completion.json');m=c.read(c.bind(post['bedkeep_metadata'])['path']);call=c.read(c.bind(post['native_call'])['path'])
    counts=dict(samples=300,completed_steps=5200000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=1500000,fixed_marker_checks=541500,P0_bits_checks=2041500,rho_cache_bits_checks=1500000,kappa_nondecreasing_from_PRE_checks=1500000,nonempty_signed_intervals=300,plane_gap_checks=3000000)
    c.need(d['passed'] and d['stage']==stage and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['saved_steps_checked_against_formal_profile'] and d['source_completed_step']==4000000 and d['kept_bed_IDs']==[1800,1852,1904,1956,2008] and d['actual_retired_count']==255,'Original300 native/ledger/clock/keep coverage differs')
    c.need(d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and not d['reaction_J_Darcy_closed'] and not d['same_operator_PRE_contract_claimed'],'Original fixed-plane split scope differs')
    c.need(m['passed'] and m['stage']==stage+'.metadata' and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==300 and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==float(np.float32(exponent)),'Actual AS coefficient/exponent headers differ')
    if version=='r6':c.need(m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==300 and post['free_seepage_ponding_policy']=='CompletedOnly' and post['ponding_policy_keys_absent_headers']==300,'New formal adapter must prove CompletedOnly headers, not the rejected half policy')
    c.need(call['passed'] and call['actual_exit']==call['actual_Win32_exit']==0,'Actual original native tool exit required');before=[c.stat(rp),c.stat(pp),c.bind(r['actual_call']),c.bind(post['native_call']),c.bind(post['native_completion']),c.bind(post['bedkeep_metadata'])]+[c.bind(r[k]) for k in ('program','source_build','source_pre_file','input_xml')]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):before.append(c.bind(next(e for e in call['outputs'] if Path(e['path']).samefile(native/leaf))))
    layout=c.table(native/'typed22_layout.csv');fields=[('time','<f8')];c.need(len(layout)==22,'Literal22 layout required')
    for q,(name,kind,width) in zip(layout,c.SCHEMA):c.need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,c.TYPES[kind].itemsize*width),'Typed22 field changed');fields.append((name,c.TYPES[kind],(6805,width)))
    dtype=np.dtype(fields);c.need(dtype.itemsize==8+6805*212 and (native/'typed22.bin').stat().st_size==12+300*dtype.itemsize,'Literal300-record payload extent differs');clocks=c.table(native/'clocks.csv');history=c.table(native/'history.csv');c.need(len(clocks)==len(history)==300,'True300 clocks/history required')
    xml=c.ET.parse(r['input_xml']['path']).getroot();nodes=[q for q in xml.findall('execution/parameters/parameter') if q.get('key')=='ArtificialStressExp'];c.need(len(nodes)==1 and float(nodes[0].get('value'))==exponent,'Actual input exponent differs');nodes[0].set('value','2.55')
    return dict(label=label,epsilon=.2,exponent=exponent,run=r,done=d,native=native,dtype=dtype,layout=layout,clocks=clocks,history=history,before=before,physics=tuple(c.physics(xml.find('execution/'+key)) for key in ('special','parameters')))

def extrema_update(results,frame,context,part,tau,step,m):
    soil=frame['Idp'][:,0]>=2060;ids=frame['Idp'][soil,0];pos=frame['Posd'][soil];vel=frame['Vel'][soil].astype(float);p=frame['PorePress'][soil,0].astype(float);kk=frame['SigmaState_kk'][soil];ij=frame['SigmaState_ij'][soil];fields=[('p',p,'Pa'),('excess_fixed_P0',frame['ExcessPorePress'][soil,0].astype(float),'Pa'),('kappa',m['kappa'],'1'),('J',frame['PoroVolumeRatio'][soil,0],'1'),('n',frame['PoroPorosity'][soil,0],'1'),('rho',frame['PoroMixtureDensity'][soil,0],'kg/m3'),('conductivity',frame['PoroHydraulicConductivity'][soil,0],'m/s'),('theta_last_stage',frame['PoroThetaLastStage'][soil,0],'1/s'),('speed',np.linalg.norm(vel,axis=1),'m/s'),('NN_over_dp',m['nn'],'1'),('NN_minus_dp',(m['nn']-1)*cluster.DP*1000,'mm')]
    fields += [('v'+key,vel[:,i],'m/s') for i,key in enumerate(('x','y','z'))]
    for i,key in enumerate(('xx','yy','zz','xy','yz','xz')):
        v=kk[:,i] if i<3 else ij[:,i-3];fields.extend((('effective_'+key,v,'Pa'),('total_'+key,v-p if i<3 else v,'Pa')))
    for field,values,unit in fields:
        for kind,index in (('min',int(np.argmin(values))),('max',int(np.argmax(values)))):
            key=(context['label'],field,kind);value=float(values[index]);old=results.get(key)
            if old is None or (value<old['value'] if kind=='min' else value>old['value']):results[key]=dict(group=context['label'],AS_exponent=context['exponent'],field=field,extreme=kind,unit=unit,value=value,part=part,time_s=float(frame['time']),tau_s=tau,completed_step=step,native_id=int(ids[index]),x_m=float(pos[index,0]),y_m=float(pos[index,1]),z_m=float(pos[index,2]),p_Pa=float(p[index]),kappa=float(m['kappa'][index]),J=float(frame['PoroVolumeRatio'][soil,0][index]),FSType=int(frame['FSType'][soil,0][index]),nearest_soil_id=int(ids[m['near'][index]]),rNN_over_dp=float(m['nn'][index]),nearest_fixed_B_distance_m=float(m['walldist'][index]),effective_trace_Pa=float(kk[index].sum()),total_trace_Pa=float(kk[index].sum()-3*p[index]),theta_last_stage_s_inv=float(frame['PoroThetaLastStage'][soil,0][index]))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();c.need(args.execution_authorized,'Root full-read before one offline comparison required');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial comparison protected')
    contexts=[load(q) for q in SPECS];old,new=contexts;c.need(old['layout']==new['layout'] and old['run']['source_pre_file']==new['run']['source_pre_file'] and old['run']['source_build']==new['run']['source_build'] and old['done']['source_actual_time_s']==new['done']['source_actual_time_s'] and old['physics']==new['physics'],'Same original PRE/build/physics except declared AS exponent required; runtime-copy paths may differ')
    before=[c.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(cluster.__file__),Path(c.__file__))]+old['before']+new['before'];body=[];cohorts=[];extrema={};pictures={};spacing={q['label']:[] for q in contexts};seen_times={};seen_steps={}
    for context in contexts:
        label=context['label'];print('READING',label,'300 records',flush=True)
        with (context['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,300),'Original full300 header required; never rewritten')
            for part in range(300):
                raw=f.read(context['dtype'].itemsize);c.need(len(raw)==context['dtype'].itemsize,'Incomplete original full record');state=np.frombuffer(raw,dtype=context['dtype'],count=1)[0];time,tau,step=c.inspect(state,context,part);seen_times.setdefault(label,[]).append(time);seen_steps.setdefault(label,[]).append(step)
                if label==new['label']:c.need(time==seen_times[old['label']][part] and step==seen_steps[old['label']][part],'Actual full300 clocks/steps differ; no interpolation')
                m=cluster.measures(state);q=c.quantities(state,context,part,tau,step);q.update(AS_exponent=context['exponent'],mean_kappa=float(np.mean(m['kappa'])),mean_n=float(np.mean(m['n'])),mean_conductivity_m_s=float(np.mean(state['PoroHydraulicConductivity'][state['Idp'][:,0]>=2060,0])));body.append(q)
                rows=cluster.summarize(m,dict(group=label,epsilon=.2,AS_exponent=context['exponent'],part=part,time_s=time,tau_s=tau,completed_step=step));cohorts.extend(rows);spacing[label].append(m['nn'].copy());extrema_update(extrema,state,context,part,tau,step,m)
                if part in [p for _,p in SNAPS]:
                    soil=state['Idp'][:,0]>=2060;pictures[(label,part)]=dict(label=label,time=time,tau=tau,step=step,ids=state['Idp'][soil,0].copy(),FS=state['FSType'][soil,0].copy(),x=m['x'].copy(),fixed=m['fixed'].copy(),p=m['p'].copy(),kappa=m['kappa'].copy(),nn=m['nn'].copy())
                if (part+1)%50==0:print('RECORDS',label,part+1,flush=True)
            c.need(f.read(1)==b'','Extra data beyond genuine300 records')
    c.need(len(body)==600 and len(cohorts)==3600 and all(len(v)==300 for v in spacing.values()),'Full symmetric material coverage differs');files=[]
    allc={(q['group'],int(q['part'])):q for q in cohorts if q['cohort']=='all_soil'};differences=[]
    for part in range(300):
        a,b=body[part],body[300+part];d=dict(part=part,time_s=a['time_s'],tau_s=a['tau_s'],completed_step=a['completed_step'])
        for key in a:
            if key not in ('group','epsilon','AS_exponent','part','time_s','tau_s','completed_step','soil_IDs'):d[key+'_n3_minus_n2p55']=float(b[key])-float(a[key])
        for key in ('rNN_over_dp_min','rNN_over_dp_q05','rNN_over_dp_median','rNN_over_dp_max','pair_both_in_cohort_lt_0p5dp','pair_both_in_cohort_lt_0p7dp'):d[key+'_n3_minus_n2p55']=allc[(new['label'],part)][key]-allc[(old['label'],part)][key]
        differences.append(d)
    for leaf,rows in (('body',body),('cohorts',cohorts),('differences',differences),('extrema',list(extrema.values()))):p=Path(str(PREFIX)+'_'+leaf+'.csv');c.write(p,rows);files.append(p)
    arrays={k:np.concatenate(v) for k,v in spacing.items()};lo=min(float(a.min()) for a in arrays.values());hi=max(float(a.max()) for a in arrays.values());edges=np.linspace(lo,hi,61);histrows=[]
    for label,a in arrays.items():
        counts,_=np.histogram(a,bins=edges);c.need(int(counts.sum())==1500000,'All300x5000 spacings must enter the common histogram')
        for kind,scale,offset,unit in (('NN_over_dp',1.,0.,'1'),('NN_minus_dp',cluster.DP*1000,-cluster.DP*1000,'mm')):
            for i,count in enumerate(counts):histrows.append(dict(group=label,quantity=kind,unit=unit,bin=i,left=float(edges[i]*scale+offset),right=float(edges[i+1]*scale+offset),count=int(count),total_saved_soil_time_observations=1500000))
    p=Path(str(PREFIX)+'_spacing_hist.csv');c.write(p,histrows);files.append(p);plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(2,4,figsize=(17,9),layout='constrained')
    for context,color in zip(contexts,('C0','C1')):
        label=context['label'];rr=[r for r in body if r['group']==label];cc=[allc[(label,i)] for i in range(300)];t=[r['tau_s'] for r in rr];ax=axes.ravel()
        for key,style in (('p_min_Pa','--'),('p_max_Pa',':'),('p_RMS_Pa','-')):ax[0].plot(t,[r[key]*.001 for r in rr],style,c=color,label=label+' '+key.split('_')[1])
        for axis,key,scale in ((1,'mean_settlement_from_PRE_mm',1.),(2,'front_particle_center_x_m',1.),(4,'total_stress_Frobenius_RMS_Pa',.001),(5,'max_kappa',1.)):ax[axis].plot(t,[r[key]*scale for r in rr],c=color,label=label)
        ax[2].plot(t,[r['max_particle_center_z_m'] for r in rr],'--',c=color,label=label+' height')
        for key,style in (('velocity_RMS_m_s','-'),('max_speed_m_s','--')):ax[3].plot(t,[r[key] for r in rr],style,c=color,label=label+(' RMS' if style=='-' else ' max'))
        for key,style in (('pair_both_in_cohort_lt_0p5dp','-'),('pair_both_in_cohort_lt_0p7dp','--')):ax[6].plot(t,[r[key] for r in cc],style,c=color,label=label+(' <.5dp' if style=='-' else ' <.7dp'))
        for key,style in (('rNN_over_dp_min','-'),('rNN_over_dp_q05','--')):ax[7].plot(t,[r[key] for r in cc],style,c=color,label=label+(' min' if style=='-' else ' q05'))
    axes[0,0].set_yscale('symlog',linthresh=1.)
    for ax,(title,unit) in zip(axes.ravel(),(('Saved pressure, not substage extrema','p [kPa]'),('All5000 material mean from true PRE','Settlement [mm]'),('Particle-center front/maximum height','Position [m]'),('All5000 velocity','Speed [m/s]'),('Total stress Frobenius RMS','Stress [kPa]'),('Maximum dev plastic history','kappa'),('Unique close pairs; descriptive','Count'),('Nearest-other spacing; descriptive','rNN / dp'))):ax.set(title=title,xlabel='Actual tau from PRE [s]',ylabel=unit);ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Full3s: AS epsilon.2, exponent2.55 versus3; CompletedOnly held fixed; no physical/accuracy acceptance');p=Path(str(PREFIX)+'_history.png');fig.savefig(p);plt.close(fig);files.append(p)
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for label,color in zip((q['label'] for q in contexts),('C0','C1')):
        counts,_=np.histogram(arrays[label],bins=edges)
        for ax,scale,offset in ((axes[0],1.,0.),(axes[1],cluster.DP*1000,-cluster.DP*1000)):ax.stairs(counts,edges*scale+offset,label=label,color=color)
    for ax,title,unit in zip(axes,('Nearest-other spacing: all300 states','Same data minus nominal dp, not crack aperture'),('rNN / dp','rNN - dp [mm]')):ax.set(title=title,xlabel=unit,ylabel='Saved soil-time observations');ax.set_yscale('log');ax.grid(alpha=.25);ax.legend()
    p=Path(str(PREFIX)+'_spacing.png');fig.savefig(p);plt.close(fig);files.append(p);points=[]
    ranges={'p':(min(q['value'] for q in extrema.values() if q['field']=='p' and q['extreme']=='min')*.001,max(q['value'] for q in extrema.values() if q['field']=='p' and q['extreme']=='max')*.001),'kappa':(0.,max(q['value'] for q in extrema.values() if q['field']=='kappa' and q['extreme']=='max')),'nn':(lo,hi)}
    for requested,part in SNAPS:
        qs=[pictures[(q['label'],part)] for q in contexts];c.need(qs[0]['time']==qs[1]['time'] and qs[0]['step']==4000000+round(requested/.0000025) and abs(qs[0]['tau']-requested)<1e-8,'Requested saved material time is not an exact common step');xy=np.concatenate([q['x'] for q in qs]);limits=(float(xy[:,0].min()-2*cluster.DP),float(xy[:,0].max()+2*cluster.DP),float(xy[:,1].min()-2*cluster.DP),float(xy[:,1].max()+2*cluster.DP));fig,axes=plt.subplots(3,2,figsize=(12,13),sharex=True,sharey=True,layout='constrained')
        for row,key in enumerate(('p','kappa','nn')):
            vmin,vmax=ranges[key];norm=SymLogNorm(linthresh=1.,vmin=vmin,vmax=vmax,base=10,clip=False) if key=='p' else cluster.Normalize(vmin,vmax,clip=False)
            for col,q in enumerate(qs):
                ax=axes[row,col];ax.scatter(q['fixed'][:,0],q['fixed'][:,1],s=3,c='.7',marker='s',linewidths=0);values=q[key]*(.001 if key=='p' else 1.)
                for mask,marker in ((~np.isin(q['FS'],(2,3)),'o'),(np.isin(q['FS'],(2,3)),'^')):ax.scatter(q['x'][mask,0],q['x'][mask,1],c=values[mask],norm=norm,cmap='coolwarm' if key=='p' else 'viridis',s=6,marker=marker,linewidths=0)
                ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title=q['label']+' actual tau=%.12g s'%q['tau']);ax.set_aspect('equal',adjustable='box')
            fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='coolwarm' if key=='p' else 'viridis'),ax=axes[row,:].tolist(),label={'p':'Raw p [kPa], signed symlog','kappa':'Kplastic kappa','nn':'rNN / dp'}[key],shrink=.8)
        fig.suptitle('Complete5000 soil at requested tau%g; actual clocks shown; common full300 raw ranges\nTriangles FS2/3, grey actual fixed markers; no inferred crack width or physical fix'%requested);p=Path(str(PREFIX)+'_tau_'+str(requested).replace('.','p')+'.png');fig.savefig(p);plt.close(fig);files.append(p)
        for q in qs:
            for i in range(5000):points.append(dict(group=q['label'],requested_tau_s=requested,time_s=q['time'],tau_s=q['tau'],completed_step=q['step'],native_id=int(q['ids'][i]),x_m=float(q['x'][i,0]),z_m=float(q['x'][i,1]),p_Pa=float(q['p'][i]),kappa=float(q['kappa'][i]),rNN_over_dp=float(q['nn'][i]),FSType=int(q['FS'][i])))
    p=Path(str(PREFIX)+'_spatial.csv');c.write(p,points);files.append(p);c.need(all(c.stat(e['path'])==e for e in before),'Closed input changed during offline comparison')
    result=dict(stage=TAG,passed=True,analysis_completed=True,groups=[q['label'] for q in contexts],actual_common_frames=300,soil_IDs_per_frame=5000,original_typed_headers=[6805,22,300],typed_payload_sequential_passes_per_group=1,extra_record_seeks=0,all300_clustering_cohorts_per_group=6,cached_statistics_inferred=False,spacing_observations_per_group=1500000,spatial_soil_rows=len(points),spatial_requested_tau_s=[q[0] for q in SNAPS],full_saved_record_extrema=True,extrema_tie_policy='earliest actual part then lowest native ID',pressure_is_absolute_not_paper_excess=True,spacing_minus_dp_is_not_crack_width=True,CompletedOnly_both=True,new_adapter_ponding_keys_absent_headers=300,AS_epsilon=.2,AS_exponents=[2.55,3.],NoPenReactionClosed=False,no_cross_option_5Pa_half_or_accuracy_gate=True,normal_exit_not_physical_acceptance=True,physical_acceptance=False,other_psi_admitted=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(p) for p in files])
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('N3_FULL_COMPARISON_READY',CHECK,flush=True)
if __name__=='__main__':main()
