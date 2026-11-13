"""Offline Wendland psi0 AS comparison; actual PRE+1 states, no automatic winner or continuation."""
import argparse,json,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_wend_review_r1 as source

old,plastic=source.old,source.plastic
T,C,need,path,stat,read,table,bind=old.T,old.C,old.need,old.path,old.stat,old.read,old.table,old.bind
np=old.np;TAG='c08_h18_wend_receiver_review_r1';BUILD=source.BUILD

def same(a,b):return path(a).samefile(path(b))
def profile_xml(spec,xml,source_csv):
    rows=table(spec['material_csv']);p={q['key']:q['value'] for q in rows};keys=plastic.MATERIAL_KEYS|{'Kernel','ArtificialStressCoef','ArtificialStressExp'};need(len(rows)==len(p)==17 and set(p)==keys and p['group']=='psi0' and p['fresh_trigger_active']=='0','Actual17-key psi0/Wendland receiver profile required')
    soil=xml.find('execution/special/soils');pairs=[(q.get('key'),q.get('value')) for q in xml.findall('execution/parameters/parameter')];pars=dict(pairs);need(soil is not None and len(pars)==len(pairs),'Actual unique receiver material/parameter XML required')
    for key in keys-{'group','fresh_trigger_active'}:
        node=soil.find(key);value=pars[key] if key in ('Kernel','DPCtes','ArtificialStressCoef','ArtificialStressExp') else (node.get('value') if node is not None else '1.65' if key=='SoilTriggerFos' else None);need(value is not None and old.f32(p[key])==old.f32(value),'Receiver17CSV does not match actual XML: '+key)
    original={q['key']:q['value'] for q in table(source_csv)}
    for key in plastic.MATERIAL_KEYS|{'Kernel'}:need(p[key]==original[key] if key in ('group','fresh_trigger_active') else old.f32(p[key])==old.f32(original[key]),'Receiver differs from its same-material source: '+key)
    a=spec['actualAS'];need(old.f32(p['Kernel'])==2 and old.f32(a['coefficient']) in tuple(old.f32(x) for x in (.3,.5,.7)) and old.f32(a['exponent']) in tuple(old.f32(x) for x in (3.825,3.,5.)) and old.f32(p['ArtificialStressCoef'])==old.f32(a['coefficient']) and old.f32(p['ArtificialStressExp'])==old.f32(a['exponent']),'Explicit actual AS coefficient/exponent differs')
    return pars

def load_receiver(spec,src,src_spec,consumed):
    for key in ('tag','native_dir','native_call','material_csv','plan','run','input_xml','actualAS'):need(key in spec,'Explicit receiver case key missing: '+key)
    need(re.fullmatch(r'[A-Za-z0-9_]+',spec['tag']),'Safe case tag required');root=path(spec['native_dir']);d=read(root/'completion.json');m=read(root/'bedkeep_metadata.json');b=read(BUILD);call=read(spec['native_call']);r=read(spec['run']);sr=read(src_spec['run']);count=int(d['samples']);end=2180000 if count==91 else 2600000
    need(d['stage']=='c08_h18_wend_native_r1.receiver' and d['passed'] and count in (91,301) and d['completed_steps']==end and d['new_updates']==end-2000000 and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212,'Only actual91-window/301-formal Wendland receivers supported')
    need(d['actual_native_IDs_per_frame']==6805 and d['soil_IDs']==5000 and d['actual_fixed_IDs']==1805 and d['ledger_checks']==d['rho_cache_bits_checks']==d['kappa_nondecreasing_from_PRE_checks']==count*5000 and d['P0_bits_checks']==count*6805 and d['fixed_marker_checks']==count*1805 and d['plane_gap_checks']==count*10000 and d['FS23_pressure_checks']>=count,'Original all-ID ledger/cache/P0/kappa/load/contact/FS coverage differs')
    need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['nonempty_signed_intervals']==count and d['saved_steps_checked_against_launch_plan'] and d['completed_runtime_Run_csv_checked'],'Original clock/signed/native safety budgets differ')
    need(d['H']==old.f32(.072) and d['fixed_dt_s']==5e-6 and d['group']=='psi0' and d['geometry_profile']=='bedroles' and d['release_target_ID_begin']==1805 and d['release_target_ID_count']==d['actual_retired_count']==255 and d['actual_retired_IDs_contiguous'] and d['retained_fixed_ID_begin']==0 and d['retained_fixed_ID_count']==1805 and not d['keep_bed_overlap'],'Actual geometry/ID retirement differs')
    need(d['source_handoff_schema']==d['source_material_law_version']==d['target_material_law_version']==2 and not d['source_elastic'] and d['same_material_plastic_PRE'] and d['source_PREs_read']==1 and d['source_PRE_part']==1000 and d['source_completed_step']==2000000 and d['source_actual_time_s']==src['done']['actual_end_s'] and d['source_PRE_contract_kernel_checked'] and d['declared_Kernel_XML_CSV']==2 and d['kernel_name_declared']=='Wendland' and not d['receiver_kernel_independently_proven_by_arrays'] and not d['full_material_contract_independently_reconstructed'] and d['target_full_material_contract_enforced_by_solver'],'Actual same-material/schema2/Wendland PRE identity differs')
    need(d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['receiver_part0_is_real_post_not_t0_or_PRE'],'Original fixed-plane/pre-step limitations differ')
    need(b['passed'] and b['consumed_stats_unchanged'] and b['receiver_material_CSV_keys']==17 and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and same(call['program'],bind(b['program'])['path']),'Actual Wendland native program/exit differs')
    args=call['arguments'];need(len(args)==8 and args[:3]==['--receiver','window' if count==91 else 'formal','psi0'] and same(args[3],path(spec['input_xml']).parent/'data') and same(args[4],bind(sr['source_pre_file'])['path']) and same(args[5],spec['plan']) and same(args[6],spec['material_csv']) and same(args[7],root),'Actual receiver DATA/PRE/plan/profile/output call binding differs')
    need(r['solver_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==end and r['saved_frames']==count and bind(r['source_pre_file'])==bind(sr['source_pre_file']) and same(bind(r['input_xml'])['path'],spec['input_xml']),'Actual completed receiver or PRE binding differs')
    actual=read(bind(r['actual_call'])['path']);need(actual['actual_solver_Win32_exit']==actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and not actual['ownership_errors'] and same(actual['actual_solver']['exe'],bind(r['program'])['path']),'Actual receiver ownership/program/exits differ');pb=read(bind(r['source_build'])['path']);need(pb['passed'] and pb['configuration']=='Release' and pb['consumed_stats_unchanged'] and bind(pb['program'])==bind(r['program']) and pb['source_capture']==r['source_capture'] and pb['source_archive']==r['source_archive'],'Actual receiver physical build/source closure differs')
    xml=ET.parse(path(spec['input_xml'])).getroot();pars=profile_xml(spec,xml,src_spec['material_csv']);g=xml.find('execution/special/gravitypreload');need(g is not None and same(g.get('statefile'),args[4]) and g.get('keep_bed_overlap')=='false' and float(pars['DtFixed'])==5e-6 and int(pars['NoPenetration'])==int(pars['ArtificialStress'])==1 and old.f32(xml.find('execution/constants/h').get('value'))==d['H'],'Actual receiver PRE/step/AS/contact/XML differs')
    runout=(path(spec['input_xml']).parent/'Run.out').read_text(encoding='utf-8-sig');need('Kernel="Wendland"' in runout and runout.count('GravityPreload: phase=released ')==1 and runout.count('GravityPreload: state imported file=')==1 and 'Simulation INTERRUPTED' not in runout and 'Finished execution (code=0).' in runout,'Actual receiver Run.out kernel/import/release completion differs')
    a=spec['actualAS'];need(m['stage']=='c08_h18_wend_native_r1.metadata' and m['passed'] and m['samples']==count and m['group']=='psi0' and m['receiver_material_CSV_keys']==17 and m['expected_source_material_CSV_keys']==15 and m['declared_Kernel_XML_CSV']==2 and m['source_PRE_contract_kernel_checked'] and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==old.f32(a['coefficient']) and m['AS_exponent_float_reference']==old.f32(a['exponent']) and m['AS_active_true_headers']==count and m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==count and not m['keep_bed_overlap'],'Actual17CSV/AS ReleaseOnly/CompletedOnly metadata differs')
    expected=np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)));layout=table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Literal22 receiver layout required')
    for q,(name,kind,width) in zip(layout,old.SCHEMA):need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,old.TYPES[kind].itemsize*width),'Original receiver typed22 schema differs');fields.append((name,old.TYPES[kind],(6805,width)))
    raw=root/'typed22.bin';dtype=np.dtype(fields)
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,count),'Genuine6805 receiver header differs')
    need(raw.stat().st_size==12+count*dtype.itemsize,'Actual receiver payload extent differs');clocks=table(root/'clocks.csv');plan=table(spec['plan']);need(len(clocks)==len(plan)==count and set(plan[0])=={'part','completed_step','saved_step','time_s','dt_s'},'Original complete receiver plan required')
    for i,(q,p) in enumerate(zip(clocks,plan)):need(int(q['part'])==int(p['part'])==i and int(q['completed_step'])==int(p['completed_step']) and int(q['saved_step'])==int(p['saved_step']) and float(q['dt_s'])==float(p['dt_s'])==5e-6 and abs(float(q['time_s'])-float(p['time_s']))<=1e-14,'Actual complete receiver clocks differ')
    need(int(clocks[0]['completed_step'])==2000001 and float(clocks[0]['time_s'])>src['done']['actual_end_s'],'First save must be the genuine PRE+1 update, never PRE/t0')
    consumed += [stat(q) for q in (root/'completion.json',root/'bedkeep_metadata.json',spec['native_call'],spec['run'],spec['input_xml'],spec['material_csv'],spec['plan'],path(spec['input_xml']).parent/'Run.out')]+[bind(r[k]) for k in ('actual_call','program','source_build','source_capture','source_archive','input_xml','source_pre_file')]+[stat(root/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv')]
    return dict(spec=dict(tag=spec['tag'],source=src['spec']['source'],group='psi0',actualAS=a,H=.072),root=root,done=d,source=False,geometry_profile='bedroles',count=count,nodes=6805,expected=expected,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,)),clocks=clocks,kw=src['kw'],yield_rows={},runtime_observed=dict(passed=bool(r['passed']),solver_completed=True,actual_exit=0,actual_Win32_exit=0))

def first_step(bundle,reference):
    x=old.read22(bundle,0);soil=x['Idp'][:,0]>=2060;pos=x['Posd'][soil];du=pos-reference['pos'][2060:];pre=bundle['_source']['frames'][-1];dp=x['PorePress'][soil,0].astype(float)-pre['PorePress'][2060:,0].astype(float);ds=x['SigmaState_kk'][soil]-pre['SigmaState_kk'][2060:];dt=x['SigmaState_ij'][soil]-pre['SigmaState_ij'][2060:]
    dv=x['Vel'][soil].astype(float)-pre['Vel'][2060:].astype(float);row=dict(tag=bundle['spec']['tag'],actual_first_time_s=float(x['time']),source_actual_time_s=reference['time'],actual_tau_s=float(x['time'])-reference['time'],first_completed_step=int(bundle['clocks'][0]['completed_step']),first_is_PRE_plus_one_not_PRE=True,XYZ_change_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du,axis=1)))),XYZ_change_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),p_change_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),effective_stress_change_Frob_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(dt*dt,axis=1)))),velocity_vector_change_RMS_m_s=float(np.sqrt(np.mean(np.sum(dv*dv,axis=1)))),not_a_bit_equality_or_physical_equivalence_test=True)
    for field,name in (('Kplastic','kappa'),('PoroVolumeRatio','J'),('PoroPorosity','n'),('PoroHydraulicConductivity','k_m_s')):
        delta=x[field][soil,0].astype(float)-pre[field][2060:,0].astype(float);row[name+'_change_maxabs']=float(np.abs(delta).max())
    return row

def add_total_settlement(analysis,reference):
    du=reference['pos'][2060:]-reference['initial_pos'][2060:];z=reference['initial_pos'][2060:,2];offsets=dict(mean_settlement_reference_mm=float(-1000*du[:,2].mean()),top_material_settlement_mm=float(-1000*du[z==z.max(),2].mean()),bottom_material_settlement_mm=float(-1000*du[z==z.min(),2].mean()));front=float(reference['pos'][2060:,0].max())
    for q in analysis['history']:
        for key,value in offsets.items():q[key+'_including_preload']=q[key]+value
        q['runout_from_PRE_front_m']=q['front_x_m']-front
    return dict(source_preload_settlement_mm=offsets,existing_settlement_fields_reference='Actual PRE positions; collapse-only changes',including_preload_fields_reference='Source initial positions, with original fixed material layers',native_excess_reference='Immutable original material P0, not pressure at release')

def selection_summary(analysis):
    h=analysis['history'];last=h[-1];return dict(tag=analysis['summary']['tag'],coefficient=last['AS_coefficient'],exponent=last['AS_exponent'],actual_tau_end_s=last['tau_s'],max_pairs_r_lt_0p7dp=max(q['pairs_r_lt_0p7dp'] for q in h),final_pairs_r_lt_0p7dp=last['pairs_r_lt_0p7dp'],minimum_NN_over_dp=min(q['NN_min_over_dp'] for q in h),minimum_pressure_Pa=min(q['p_min_Pa'] for q in h),maximum_pressure_RMS_Pa=max(q['p_RMS_Pa'] for q in h),maximum_excess_RMS_Pa=max(q['native_p_minus_fixedP0_RMS_Pa'] for q in h),maximum_total_stress_RMS_Pa=max(q['total_stress_Frobenius_RMS_Pa'] for q in h),minimum_J=min(q['min_J'] for q in h),maximum_J=max(q['max_J'] for q in h),maximum_kappa=max(q['max_kappa'] for q in h),final_runout_from_PRE_m=last['runout_from_PRE_front_m'],final_KE_J_per_m=last['current_mixture_KE_J_per_m'],final_velocity_RMS_m_s=last['velocity_RMS_m_s'],final_top_material_settlement_mm=last['top_material_settlement_mm'])

def comparison(analyses,reference_tag):
    base=next(a for a in analyses if a['summary']['tag']==reference_tag);lookup={(q['completed_step'],q['time_s']):q for q in base['history']};rows=[];keys=('p_RMS_Pa','p_min_Pa','p_max_Pa','native_p_minus_fixedP0_RMS_Pa','current_mixture_KE_J_per_m','velocity_RMS_m_s','max_kappa','min_J','max_J','runout_from_PRE_front_m','top_material_settlement_mm','pairs_r_lt_0p7dp','NN_q05_over_dp')
    for a in analyses:
        if a is base:continue
        for q in a['history']:
            key=(q['completed_step'],q['time_s'])
            if key not in lookup:continue
            b=lookup[key];row=dict(reference_tag=reference_tag,tag=q['tag'],completed_step=key[0],time_s=key[1],tau_s=q['tau_s'])
            for name in keys:row[name+'_minus_reference']=q[name]-b[name]
            rows.append(row)
    return rows

def metrics_plot(analyses,prefix):
    fig,axes=old.plt.subplots(2,3,figsize=(13,8),layout='constrained');charts=(('runout_from_PRE_front_m','Front advance from PRE [m]',1.),('NN_q05_over_dp','5% nearest distance / dp',1.),('pairs_r_lt_0p7dp','Pairs at r < .7dp',1.),('current_mixture_KE_J_per_m','Current mixture KE [J/m]',1.),('p_min_Pa','Minimum absolute p [kPa]',.001),('p_RMS_Pa','Absolute p RMS [kPa]',.001))
    for ax,(key,title,scale) in zip(axes.flat,charts):
        for a in analyses:ax.plot([q['tau_s'] for q in a['history']],[q[key]*scale for q in a['history']],label=a['summary']['tag'])
        ax.set(title=title,xlabel='Actual time since PRE release [s]');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('Wendland AS options: judge clumping, pressure and motion together\nDifferent AS coefficients are not half-step errors; low motion alone is not a winner');dest=Path(str(prefix)+'_selection.png');fig.savefig(dest,dpi=170);old.plt.close(fig);return dest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Root full-read before one offline review');m=read(args.manifest);tag=m['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag),'Safe fresh derived tag required');prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'_*')),'Existing complete/partial review protected');consumed=[stat(args.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(source.__file__),stat(old.__file__),stat(plastic.__file__)];result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,winner_selected=False,consumed=consumed)
    try:
        need(m['cases'],'At least one actual completed receiver required');src=source.load(m['source'],consumed);reference=old.reference_from(src);bundles=[load_receiver(q,src,m['source'],consumed) for q in m['cases']];need(len({b['spec']['tag'] for b in bundles})==len(bundles),'Receiver case tags must be unique');analyses=[];first=[];definitions=[]
        for bundle in bundles:
            bundle['_source']=src;a=old.analyze_case(bundle,reference,m.get('snapshots_tau_s',[.3,.6,.9]));definitions.append(dict(tag=bundle['spec']['tag'],**add_total_settlement(a,reference)));first.append(first_step(bundle,reference));analyses.append(a)
        reference_tag=m.get('reference_tag',analyses[0]['summary']['tag']);need(reference_tag in {a['summary']['tag'] for a in analyses},'Explicit option reference tag missing');matched=comparison(analyses,reference_tag);selection=[selection_summary(a) for a in analyses];files=[]
        for key in ('history','extrema','layers','tracks'):dest=Path(str(prefix)+'_'+key+'.csv');old.write_csv(dest,[q for a in analyses for q in a[key]]);files.append(dest)
        for name,rows in [('first_real_step',first),('selection_metrics',selection)]+([('option_differences',matched)] if matched else []):dest=Path(str(prefix)+'_'+name+'.csv');old.write_csv(dest,rows);files.append(dest)
        fields=[]
        for a in analyses:
            for part,s in a['snapshots'].items():
                for i,x in enumerate(s['pos']):fields.append(dict(tag=a['summary']['tag'],part=part,time_s=s['time_s'],tau_s=s['tau_s'],native_id=2060+i,x_m=float(x[0]),z_m=float(x[2]),p_Pa=float(s['p'][i]),native_p_minus_fixedP0_Pa=float(s['excess'][i]),kappa=float(s['kappa'][i]),J=float(s['J'][i])))
        if fields:dest=Path(str(prefix)+'_fields.csv');old.write_csv(dest,fields);files.append(dest)
        files+=old.plot_results(analyses,prefix);files.append(metrics_plot(analyses,prefix));need(all(stat(q['path'])==q for q in consumed),'Sealed source/receiver evidence changed');result.update(analysis_complete=True,source_reference=m['source'],source_actual_time_s=reference['time'],receiver_summaries=[a['summary'] for a in analyses],first_real_step_changes=first,reference_definitions=definitions,selection_metrics=selection,option_reference_tag=reference_tag,exact_matching_option_rows=len(matched),different_options_not_half_or_theory_errors=True,full_material_contract_independently_reconstructed=False,actual_target_contract_enforced_by_solver=True,reaction_J_Darcy_closed=False,normal_exit_not_physical_acceptance=True,no_automatic_winner_or_next_job=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
