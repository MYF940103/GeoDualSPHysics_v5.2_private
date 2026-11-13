"""Compare sealed Wendland AS reviews at exact common saved states; no solver or winner."""
import argparse,json,re,struct
from pathlib import Path
import c08_h18_wend_receiver_review_r1 as receiver

old=receiver.old
np,T,need,path,stat,read,table,bind=old.np,old.T,old.need,old.path,old.stat,old.read,old.table,old.bind
TAG='c08_h18_wend_options_review_r1'
HISTORY=('p_RMS_Pa','p_min_Pa','p_max_Pa','negative_p_soil','native_p_minus_fixedP0_RMS_Pa',
         'effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa',
         'NN_min_over_dp','NN_q05_over_dp','pairs_r_lt_0p7dp','max_kappa','min_J','max_J',
         'current_mixture_KE_J_per_m','velocity_RMS_m_s','max_speed_m_s','front_x_m',
         'runout_from_PRE_front_m','top_material_settlement_mm','mean_settlement_reference_mm',
         'material_displacement_RMS_mm','min_soil_x_m','min_soil_z_m','AS_coefficient','AS_exponent')

def seal(entry,consumed):
    entry=bind(entry)
    previous=next((q for q in consumed if path(q['path'])==path(entry['path'])),None)
    need(previous is None or previous==entry,'Contradictory sealed identities: '+entry['path'])
    if previous is None:consumed.append(entry)
    return entry

def required(prior,value):
    key=str(path(value));need(key in prior,'Prior review did not bind: '+key)
    return bind(prior[key])

def load_option(option,consumed):
    for key in ('tag','kind','review_check','history_csv','native_dir'):
        need(key in option,'Explicit option key missing: '+key)
    tag=option['tag'];kind=option['kind'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag) and kind in ('completed','partial'),'Safe tag and explicit completed/partial kind required')
    seal(stat(option['review_check']),consumed);q=read(option['review_check'])
    need(q.get('analysis_complete') is True and q.get('consumed_stats_unchanged') is True and q.get('consumed') and q.get('files'),'Require a completed, stat-sealed prior offline analysis')
    for entry in q['consumed']+q['files']:seal(entry,consumed)
    prior={str(path(v['path'])):v for v in q['consumed']}
    outputs={str(path(v['path'])):v for v in q['files']}
    hp=path(option['history_csv']);need(str(hp) in outputs,'History must be an output bound by its prior review')
    bind(outputs[str(hp)]);manifest=read(required(prior,q['consumed'][0]['path'])['path'])
    need('source' in manifest,'Prior review manifest must explicitly identify its same-material source')
    specs=([manifest['case']] if 'case' in manifest else manifest.get('cases',[]))
    matches=[s for s in specs if s['tag']==tag];need(len(matches)==1,'Exactly one matching case in the prior review manifest required')
    spec=matches[0];root=path(option['native_dir']);need(root==path(spec['native_dir']),'Requested native directory differs from the reviewed case')
    for name in ('completion.json','bedkeep_metadata.json','typed22.bin','typed22_layout.csv','clocks.csv'):required(prior,root/name)
    for key in ('run','input_xml','material_csv','plan','native_call'):required(prior,spec[key])
    source=manifest['source'];required(prior,source['run']);required(prior,source['material_csv'])
    run=read(spec['run']);source_run=read(source['run']);d=read(root/'completion.json');meta=read(root/'bedkeep_metadata.json');count=int(d['samples'])
    need(d['stage'].startswith('c08_h18_wend_') and d['stage'].endswith('.receiver'),'Only reviewed Wendland receiver exports are supported')
    need(d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['actual_native_IDs_per_frame']==6805 and d['soil_IDs']==5000 and d['actual_fixed_IDs']==1805,'Original receiver schema and ID domain required')
    summaries=q.get('receiver_summaries',[q.get('receiver_summary')]);matches=[s for s in summaries if s is not None and s['tag']==tag]
    need(len(matches)==1,'Prior analysis must expose exactly one matching receiver summary');summary=matches[0];runtime=summary['runtime_observed']
    if kind=='completed':
        need(q['stage']=='c08_h18_wend_receiver_review_r1' and d['stage']=='c08_h18_wend_native_r1.receiver' and d['passed'] and count==91 and d['completed_steps']==2180000,'Completed option must retain genuine full91 native qualification')
        need(run['solver_completed'] and run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and runtime['solver_completed'] and runtime['actual_exit']==runtime['actual_Win32_exit']==0 and meta['passed'],'Completed option requires the reviewed real solver completion and exits')
        status='completed_native91'
    else:
        need('partial_review' in q['stage'] and q.get('saved_prefix_native_qualified') is True and q.get('receiver_complete') is False and q.get('whole_run_passed') is False,'Partial option requires an explicitly qualified saved-prefix analysis')
        need('partial' in d['stage'] and d.get('diagnostic_complete') is True and d.get('saved_prefix_native_passed') is True and d.get('partial') is True and d.get('passed') is False and d.get('whole_run_native_passed') is False and d.get('full_run_completed') is False and d.get('certified_receiver') is False,'Partial native diagnostic must remain failed overall and uncertified')
        need(0<count<=91 and d['original_target_samples']==91 and d['original_target_completed_step']==2180000 and q['actual_saved_records']==count and d.get('actual_terminal_solver_step_proven') is False and d.get('unsaved_state_reconstructed') is False,'Partial export must preserve actual count and the original uncompleted target')
        need(not run['solver_completed'] and not run['passed'] and run['actual_exit']==run['actual_Win32_exit']!=0 and not runtime['solver_completed'] and runtime['actual_exit']==runtime['actual_Win32_exit']==run['actual_exit'] and meta.get('saved_metadata_passed') is True and meta.get('partial') is True and meta.get('passed') is False,'Partial option cannot be relabelled a successful solver or full native result')
        status='qualified_partial_saved_prefix'
    a=spec['actualAS'];need(old.f32(a['coefficient']) in tuple(old.f32(v) for v in (.3,.5,.7)) and old.f32(a['exponent'])==old.f32(3.825),'Only the explicitly prepared epsilon .3/.5/.7 at exponent3.825 is supported')
    need(meta['samples']==count and meta['AS_policy']=='ReleaseOnly' and meta['AS_coefficient_float_reference']==old.f32(a['coefficient']) and meta['AS_exponent_float_reference']==old.f32(a['exponent']),'Sealed native AS metadata differs from the reviewed option')
    profile={r['key']:r['value'] for r in table(spec['material_csv'])}
    for key in ('program','source_build','source_capture','source_archive','source_pre_file'):
        need(required(prior,run[key]['path'])==run[key],'Run closure differs from the sealed review: '+key)
    need(run['source_pre_file']==source_run['source_pre_file'],'Reviewed option and source must refer to the same actual PRE')
    context={key:run[key] for key in ('program','source_build','source_capture','source_archive','source_pre_file')}
    context.update(source_run=required(prior,source['run']),source_material=required(prior,source['material_csv']),plan=required(prior,spec['plan']),source_time_s=float(d['source_actual_time_s']),profile_without_AS={k:(v if k in ('group','fresh_trigger_active') else old.f32(v)) for k,v in profile.items() if k not in ('ArtificialStressCoef','ArtificialStressExp')})
    layout=table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Literal original typed22 layout required')
    for row,(name,kind_name,width) in zip(layout,old.SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind_name,width,old.TYPES[kind_name].itemsize*width),'Literal typed22 schema differs')
        fields.append((name,old.TYPES[kind_name],(6805,width)))
    raw=root/'typed22.bin';dtype=np.dtype(fields)
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,count),'Native header count or schema differs; no rewriting allowed')
    need(raw.stat().st_size==12+count*dtype.itemsize,'Sealed native payload extent differs')
    clocks=table(root/'clocks.csv');history=table(hp);need(len(clocks)==len(history)==count,'History must cover every actual native save')
    rows={};parts={}
    for part,(clock,row) in enumerate(zip(clocks,history)):
        key=(int(clock['completed_step']),float(clock['time_s']))
        need(key not in rows and key[0] not in [k[0] for k in rows] and int(clock['part'])==int(row['part'])==part and row['tag']==tag and int(row['completed_step'])==key[0] and float(row['time_s'])==key[1],'Unique exact native/history step and time binding required')
        need(float(clock['dt_s'])==5e-6 and float(row['tau_s'])==key[1]-context['source_time_s'],'Keep the actual scalar saved time and PRE-relative tau')
        parsed=dict(tag=tag,part=part,completed_step=key[0],time_s=key[1],tau_s=float(row['tau_s']))
        for field in HISTORY:
            parsed[field]=float(row[field]);need(np.isfinite(parsed[field]),'Nonfinite sealed history value: '+field)
        need(parsed['AS_coefficient']==old.f32(a['coefficient']) and parsed['AS_exponent']==old.f32(a['exponent']),'History AS option differs')
        rows[key]=parsed;parts[key]=part
    keys=list(rows);need(all(b[0]>a0[0] and b[1]>a0[1] for a0,b in zip(keys,keys[1:])),'Actual saved steps and times must increase')
    need(summary['actual_samples']==count and summary['actual_first_time_s']==keys[0][1] and summary['actual_end_time_s']==keys[-1][1] and summary['maximum_actual_tau_s']==rows[keys[-1]]['tau_s'],'Prior receiver summary endpoint differs from its actual history')
    if kind=='partial':need(d['last_saved_completed_step']==keys[-1][0] and d['last_saved_part']==count-1,'Partial last saved state differs')
    expected=np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)))
    bundle=dict(root=root,done=d,count=count,nodes=6805,expected=expected,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,)),clocks=clocks)
    return dict(tag=tag,kind=option['kind'],status=status,actualAS=a,review_stage=q['stage'],native_stage=d['stage'],review_check=str(path(option['review_check'])),history=rows,parts=parts,bundle=bundle,context=context,runtime=runtime)

def scalar_difference(row,name,values,ids):
    at=int(np.argmax(np.abs(values)))
    row.update({name+'_mean':float(values.mean()),name+'_RMS':float(np.sqrt(np.mean(values*values))),name+'_maxabs':float(abs(values[at])),name+'_signed_at_maxabs':float(values[at]),name+'_maxabs_ID':int(ids[at])})

def material_difference(reference,option,key,ref_frame,frame,detail):
    soil=ref_frame['Idp'][:,0]>=2060;ids=ref_frame['Idp'][soil,0]
    need(np.array_equal(ids,np.arange(2060,7060)) and np.array_equal(frame['Idp'][soil,0],ids),'All5000 original material IDs must match')
    need(np.array_equal(ref_frame['PorePress0'][soil].view('<u4'),frame['PorePress0'][soil].view('<u4')),'Matched original material P0 must remain identical')
    pref=ref_frame['PorePress'][soil,0].astype(float);poption=frame['PorePress'][soil,0].astype(float);dp=poption-pref
    dx=frame['Posd'][soil]-ref_frame['Posd'][soil]
    dk=frame['SigmaState_kk'][soil]-ref_frame['SigmaState_kk'][soil];di=frame['SigmaState_ij'][soil]-ref_frame['SigmaState_ij'][soil];dt=dk-dp[:,None]
    jref=ref_frame['PoroVolumeRatio'][soil,0];joption=frame['PoroVolumeRatio'][soil,0];nref=ref_frame['PoroPorosity'][soil,0];noption=frame['PoroPorosity'][soil,0];dJ=joption-jref;dn=noption-nref
    row=dict(reference_tag=reference['tag'],tag=option['tag'],option_status=option['status'],completed_step=key[0],time_s=key[1],tau_s=key[1]-reference['context']['source_time_s'],reference_part=reference['parts'][key],part=option['parts'][key],matched_material_IDs=5000)
    scalar_difference(row,'pressure_difference_Pa',dp,ids);scalar_difference(row,'J_difference',dJ,ids);scalar_difference(row,'n_difference',dn,ids)
    norm=np.linalg.norm(dx,axis=1);at=int(norm.argmax())
    row.update(XYZ_difference_RMS_mm=float(1000*np.sqrt(np.mean(norm*norm))),XYZ_difference_max_mm=float(1000*norm[at]),XYZ_difference_max_ID=int(ids[at]))
    for k,axis in enumerate(('x','y','z')):scalar_difference(row,axis+'_difference_mm',1000*dx[:,k],ids)
    for name,diag in (('effective_stress',dk),('total_stress',dt)):
        frob=np.sqrt(np.sum(diag*diag,axis=1)+2*np.sum(di*di,axis=1));at=int(frob.argmax())
        row.update({name+'_difference_Frobenius_RMS_Pa':float(np.sqrt(np.mean(frob*frob))),name+'_difference_Frobenius_max_Pa':float(frob[at]),name+'_difference_Frobenius_max_ID':int(ids[at])})
    details=[]
    if detail:
        for i,identity in enumerate(ids):
            r=dict(reference_tag=reference['tag'],tag=option['tag'],option_status=option['status'],completed_step=key[0],time_s=key[1],tau_s=row['tau_s'],native_id=int(identity),reference_p_Pa=float(pref[i]),option_p_Pa=float(poption[i]),pressure_difference_Pa=float(dp[i]))
            for k,axis in enumerate(('x','y','z')):r[axis+'_difference_mm']=float(1000*dx[i,k])
            for k,component in enumerate(('xx','yy','zz')):r['effective_stress_'+component+'_difference_Pa']=float(dk[i,k]);r['total_stress_'+component+'_difference_Pa']=float(dt[i,k])
            for k,component in enumerate(('xy','yz','xz')):r['effective_and_total_stress_'+component+'_difference_Pa']=float(di[i,k])
            r.update(reference_J=float(jref[i]),option_J=float(joption[i]),J_difference=float(dJ[i]),reference_n=float(nref[i]),option_n=float(noption[i]),n_difference=float(dn[i]));details.append(r)
    return row,details

def window_metrics(option,keys,scope):
    history=[option['history'][key] for key in keys]
    row=dict(scope=scope,option_status=option['status'],kind=option['kind'],actual_saved_records=len(history),first_completed_step=keys[0][0],last_completed_step=keys[-1][0],actual_first_time_s=keys[0][1],actual_end_time_s=keys[-1][1],actual_tau_start_s=history[0]['tau_s'],actual_duration_s=keys[-1][1]-keys[0][1],solver_completed=bool(option['runtime']['solver_completed']),solver_exit=option['runtime']['actual_exit'])
    row.update(receiver.selection_summary(dict(history=history,summary=dict(tag=option['tag']))))
    return row

def plots(options,common,material,prefix):
    labels={o['tag']:'epsilon='+format(float(o['actualAS']['coefficient']),'.1f').lstrip('0') for o in options}
    fig,axes=old.plt.subplots(3,3,figsize=(14,11),layout='constrained')
    charts=(('p_RMS_Pa','Absolute pressure RMS [kPa]',.001),('p_min_Pa','Minimum absolute pressure [kPa]',.001),('NN_q05_over_dp','5% nearest distance / dp',1.),('pairs_r_lt_0p7dp','Pairs at r < .7dp (descriptive)',1.),('max_kappa','Maximum kappa',1.),('max_J','Maximum J',1.),('runout_from_PRE_front_m','Front advance from PRE [m]',1.),('current_mixture_KE_J_per_m','Current mixture KE [J/m]',1.),('velocity_RMS_m_s','Velocity RMS [m/s]',1.))
    for ax,(field,title,scale) in zip(axes.flat,charts):
        for option in options:
            rows=[option['history'][key] for key in common];label=labels[option['tag']]
            ax.plot([r['tau_s'] for r in rows],[scale*r[field] for r in rows],label=label)
        ax.set(title=title,xlabel='Actual shared saved tau [s]');ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=7)
    fig.suptitle('Wendland AS options: exact shared step/time intersection only\nPressure, spacing and motion are descriptive; no automatic physical acceptance or winner')
    history_path=Path(str(prefix)+'_common_history.png');fig.savefig(history_path,dpi=170);old.plt.close(fig)
    fig,axes=old.plt.subplots(2,3,figsize=(14,8),layout='constrained')
    charts=(('pressure_difference_Pa_RMS','Material pressure difference RMS [kPa]',.001),('XYZ_difference_RMS_mm','Material XYZ difference RMS [mm]',1.),('effective_stress_difference_Frobenius_RMS_Pa','Effective stress difference RMS [kPa]',.001),('total_stress_difference_Frobenius_RMS_Pa','Total stress difference RMS [kPa]',.001),('J_difference_RMS','Material J difference RMS',1.),('n_difference_RMS','Material porosity difference RMS',1.))
    for ax,(field,title,scale) in zip(axes.flat,charts):
        for tag in dict.fromkeys(r['tag'] for r in material):
            rows=[r for r in material if r['tag']==tag];ax.plot([r['tau_s'] for r in rows],[scale*r[field] for r in rows],label=labels[tag]+' minus '+labels[rows[0]['reference_tag']])
        ax.set(title=title,xlabel='Actual shared saved tau [s]');ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=6)
    fig.suptitle('Same original5000 material IDs at exact shared saves\nChanged AS coefficients: descriptive trajectory differences, without half-step bounds')
    material_path=Path(str(prefix)+'_material_differences.png');fig.savefig(material_path,dpi=170);old.plt.close(fig)
    return [history_path,material_path]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root must fully read this adapter before one unique offline invocation')
    manifest=read(args.manifest);tag=manifest['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag),'Safe fresh derived tag required')
    prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'*')),'Retained complete or partial derived output is protected')
    consumed=[stat(args.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(receiver.__file__),stat(old.__file__)]
    result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,winner_selected=False,causation_proven=False,consumed=consumed)
    try:
        need(2<=len(manifest['options'])<=3,'Provide two or three already qualified AS option reviews')
        options=[load_option(option,consumed) for option in manifest['options']]
        need(len({o['tag'] for o in options})==len(options) and len({old.f32(o['actualAS']['coefficient']) for o in options})==len(options),'Option tags and AS coefficients must be distinct')
        reference=next((o for o in options if o['tag']==manifest['reference_tag']),None);need(reference is not None,'Explicit reference_tag must identify a supplied option')
        need(all(o['context']==reference['context'] for o in options),'Only the same source/PRE/material/program/plan context may be compared')
        common=sorted(set.intersection(*(set(o['history']) for o in options)),key=lambda key:(key[1],key[0]));need(common,'No exact common completed_step/time_s pairs; no interpolation or tolerance matching is allowed')
        detail_steps=manifest.get('material_detail_completed_steps',sorted({common[0][0],common[-1][0]}))
        need(isinstance(detail_steps,list) and len(set(detail_steps))==len(detail_steps) and all(isinstance(v,int) and v in {key[0] for key in common} for v in detail_steps),'Material detail steps must be distinct actual common completed steps')
        history=[];differences=[];material=[];details=[];window=[];own=[]
        for option in options:
            window.append(window_metrics(option,common,'common_exact_step_time_intersection'))
            own.append(window_metrics(option,list(option['history']),'own_actual_saved_window_not_a_cross_endpoint_ranking'))
            for key in common:
                history.append(dict(option_status=option['status'],**option['history'][key]))
                if option is reference:continue
                row=dict(reference_tag=reference['tag'],tag=option['tag'],option_status=option['status'],completed_step=key[0],time_s=key[1],tau_s=option['history'][key]['tau_s'])
                row.update({field+'_minus_reference':option['history'][key][field]-reference['history'][key][field] for field in HISTORY if field not in ('AS_coefficient','AS_exponent')});differences.append(row)
        for key in common:
            ref_frame=old.read22(reference['bundle'],reference['parts'][key])
            for option in options:
                if option is reference:continue
                frame=old.read22(option['bundle'],option['parts'][key]);row,selected=material_difference(reference,option,key,ref_frame,frame,key[0] in detail_steps);material.append(row);details.extend(selected)
        files=[]
        for suffix,rows in (('common_history',history),('history_differences',differences),('material_differences',material),('common_window_metrics',window),('own_window_metrics',own),('material_fields',details)):
            if rows:dest=Path(str(prefix)+'_'+suffix+'.csv');old.write_csv(dest,rows);files.append(dest)
        files+=plots(options,common,material,prefix)
        need(all(stat(entry['path'])==entry for entry in consumed),'A sealed input, prior review output or helper changed during this offline comparison')
        scope=[dict(tag=o['tag'],kind=o['kind'],status=o['status'],actualAS=o['actualAS'],review_stage=o['review_stage'],native_stage=o['native_stage'],review_check=o['review_check'],actual_saved_records=o['bundle']['count'],actual_first_time_s=next(iter(o['history']))[1],actual_end_time_s=list(o['history'])[-1][1],unmatched_own_saved_records=len(o['history'])-len(common),runtime_observed=o['runtime']) for o in options]
        result.update(analysis_complete=True,reference_tag=reference['tag'],option_scopes=scope,source_actual_time_s=reference['context']['source_time_s'],source_context=reference['context'],common_saved_records=len(common),common_first_completed_step=common[0][0],common_last_completed_step=common[-1][0],common_first_time_s=common[0][1],common_last_time_s=common[-1][1],common_tau_start_s=common[0][1]-reference['context']['source_time_s'],common_tau_end_s=common[-1][1]-reference['context']['source_time_s'],material_detail_completed_steps=detail_steps,matched_original_material_IDs_per_frame=5000,exact_step_and_time_intersection=True,interpolation=False,metadata_rewritten=False,partial_diagnostics_not_full_native=True,own_windows_not_ranked_against_different_endpoints=True,parameter_differences_not_half_step_errors=True,half_step_acceptance_bounds_applied=False,NN_threshold_is_descriptive_not_tensile_causation=True,negative_pressure_alone_not_total_stress_tension=True,whole_run_physics_or_paper_accuracy_proven=False,no_automatic_next_job=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(p) for p in files])
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
