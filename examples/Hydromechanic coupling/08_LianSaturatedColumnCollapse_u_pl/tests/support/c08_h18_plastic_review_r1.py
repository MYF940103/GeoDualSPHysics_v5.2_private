"""Offline schema2 source/receiver adapter; reuse frozen compare_r2 analysis and figures unchanged."""
import argparse,json,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_compare_r2 as old

T,C,need,path,stat,read,table,bind=old.T,old.C,old.need,old.path,old.stat,old.read,old.table,old.bind
np=old.np;TAG='c08_h18_plastic_review_r1';NATIVE_BUILD=T/'logs/c08_h18_plastic_native_r1.build.json'
GROUPS={'psi0':(5000.,0.,0.),'psi2p5':(5000.,2.5,.2),'psim5':(7500.,-5.,.2)}
MATERIAL_KEYS={'group','ModulusE','PRvs','DPCtes','phi','phi_r','n_phi','coh','coh_r','n_coh','dlt','DilationDecay','SoilTriggerFos','fresh_trigger_active'}

def same(a,b):return path(a).samefile(path(b))
def material_csv(spec,xml,source):
    rr=table(spec['material_csv']);p={q['key']:q['value'] for q in rr};keys=MATERIAL_KEYS if source else MATERIAL_KEYS|{'ArtificialStressCoef','ArtificialStressExp'}
    need(len(rr)==len(p)==len(keys) and set(p)==keys and p['group']==spec['group'] and p['fresh_trigger_active']=='0','Exact14/16 material CSV keys/group/fresh trigger required')
    soil=xml.find('execution/special/soils');params={q.get('key'):q.get('value') for q in xml.findall('execution/parameters/parameter')};need(soil is not None,'Actual generated soil parameters required')
    for key in keys-{'group','fresh_trigger_active'}:
        if key in ('DPCtes','ArtificialStressCoef','ArtificialStressExp'):value=params[key]
        else:
            node=soil.find(key);need(node is not None or key=='SoilTriggerFos','Actual XML material key missing: '+key);value=node.get('value') if node is not None else '1.65'
        need(old.f32(p[key])==old.f32(value),'CSV does not match actual generated XML: '+key)
    cp,psi,sf=GROUPS[spec['group']]
    for key,value in dict(ModulusE=20e6,PRvs=.33,DPCtes=3,phi=25,phi_r=25,n_phi=0,coh=cp,coh_r=1000,n_coh=5,dlt=psi,DilationDecay=sf).items():need(old.f32(p[key])==old.f32(value),'Outside closed same-material group: '+key)
    need(float(p['SoilTriggerFos'])>=1,'Original FOS domain differs')
    return p,params

def load_bundle(spec,consumed):
    for key in ('tag','native_dir','source','group','actualAS','H','input_xml','material_csv','native_call','run','plan'):need(key in spec,'Missing explicit schema2 review case key: '+key)
    need(spec['group'] in GROUPS and re.fullmatch(r'[A-Za-z0-9_]+',spec['tag']),'Closed group/safe case tag required');root=path(spec['native_dir']);d=read(root/'completion.json');source=d['stage']=='c08_h18_plastic_native_r1.source';need(source or d['stage']=='c08_h18_plastic_native_r1.receiver','Only the new schema2 native stages are supported')
    count=int(d['samples']);nodes=7060 if source else 6805;fixed=2060 if source else 1805
    need(d['passed'] and d['group']==spec['group'] and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and float(d['H'])==old.f32(spec['H'])==old.f32(.072),'Original native group/H/22/clock/ledger budgets differ')
    need(count>0 and (count<=1001 if source else count in (91,301)) and d['soil_IDs']==5000 and d['native_IDs' if source else 'actual_native_IDs_per_frame']==nodes and d['ledger_checks']==d['rho_cache_bits_checks']==count*5000 and d['P0_bits_checks']==count*nodes and d['fixed_marker_checks']==count*fixed,'Original all-ID native coverage differs')
    need(d['geometry_profile']=='bedroles' and d['release_target_ID_begin']==1805 and d['release_target_ID_count']==255 and not d['keep_bed_overlap'] and all(k not in d for k in ('kept_bed_IDs','kept_bed_count','kept_bed_source_geometry_checks','GravityPreloadReleasePolicy')),'Old Keep5 or different bed-role registry is not supported')
    nb=read(NATIVE_BUILD);need(nb['passed'] and nb['PRE_schema']==2 and nb['consumed_stats_unchanged'] and not nb['JSph_objects_linked'],'Passed actual schema2 native build required');call=read(spec['native_call']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and same(call['program'],bind(nb['program'])['path']),'Actual new utility exits/program differ')
    args=call['arguments'];need(len(args)==(6 if source else 8) and same(args[-1],root) and same(args[2 if source else 3],root.parent/'data') and same(args[3 if source else 6],spec['material_csv']) and same(args[4 if source else 5],spec['plan']),'Actual native call DATA/CSV/plan/output binding differs')
    r=read(spec['run']);need(r['actual_exit'] in (0,1) and r['actual_Win32_exit']==r['actual_exit'],'Terminal real runtime exits required');actual=read(bind(r['actual_call'])['path']);need(actual['actual_solver_Win32_exit']==r['actual_exit'] and actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==r['actual_exit'] and not actual['ownership_errors'],'Original owned runtime exit/identity errors differ')
    need(same(bind(r['input_xml'])['path'],spec['input_xml']) and same(actual['actual_solver']['exe'],bind(r['program'])['path']),'Actual source/receiver input/program differs');pb=read(bind(r['source_build'])['path']);built=bind(pb['program']);need(pb['passed'] and pb['configuration']=='Release' and pb['consumed_stats_unchanged'] and (built['bytes'],built['mtime_ns'])==(r['program']['bytes'],r['program']['mtime_ns']) and pb['source_capture']==r['source_capture'] and pb['source_archive']==r['source_archive'],'Actual schema2 physical program/source closure differs')
    consumed += [stat(q) for q in (NATIVE_BUILD,root/'completion.json',spec['native_call'],spec['run'],spec['input_xml'],spec['material_csv'],spec['plan'])]+[bind(nb['program']),bind(nb['source'])]+[bind(r[k]) for k in ('actual_call','program','source_build','source_capture','source_archive','input_xml')]
    xml=ET.parse(path(spec['input_xml'])).getroot();p,pars=material_csv(spec,xml,source);hyd=xml.find('execution/special/hydromechanics');g=xml.find('execution/special/gravitypreload');need(hyd is not None and g is not None and old.f32(xml.find('execution/constants/h').get('value'))==float(d['H']) and float(pars['DtFixed'])==5e-6 and g.get('keep_bed_overlap')=='false','Actual generated H/dt/keep policy differs');kw=old.f32(hyd.find('PoreWaterBulkModulus').get('value'));need(kw>0,'Actual water bulk modulus required')
    if source:
        full=not d['partial'];need(args[:2]==['--source','full' if full else 'partial'] and spec['actualAS'] is None and spec['source']==r['stage'] and g.get('elastic_source')=='false' and not g.get('statefile') and float(pars.get('ArtificialStress','0'))==float(pars.get('NoPenetration','0'))==0,'Actual source phase/AS/material/source identity differs')
        need(d['expected_handoff_schema']==2 and d['source_material_CSV_keys']==14 and d['same_material_plastic_PRE'] and d['source_yield_uses_actual_kappa'] and not d['full_material_contract_independently_reconstructed'] and d['kappa_nondecreasing_checks']==count*5000 and d['fixed_kappa_zero_checks']==count*2060 and d['initial_kappa_zero_checks']==7060 and d['max_noninitial_signed_dterror_s']<=1e-14 and d['noninitial_signed_intervals']==count-1,'Original source nonnegative/history/fixed/initial kappa/signed guards differ')
        need(d['source_group_certificate_checked']==full and d['certified_PRE']==full and d['uncertified']!=full and not d['runtime_success_claimed'],'Native partial/full certificate annotations differ')
        if full:need(count==1001 and d['completed_steps']==2000000 and r['solver_completed'] and r['actual_exit']==0 and r['actual_steps']==2000000 and r['saved_frames']==1001,'Incomplete/failed source cannot be relabelled full')
    else:
        need(args[:3]==['--receiver','window' if count==91 else 'formal',spec['group']] and r['passed'] and r['solver_completed'] and r['actual_exit']==0 and r['actual_steps']==d['completed_steps'] and r['saved_frames']==count and same(bind(r['source_pre_file'])['path'],args[4]) and same(g.get('statefile'),args[4]),'Completed receiver and actual source PRE bindings required')
        need(d['source_handoff_schema']==2 and d['source_material_law_version']==d['target_material_law_version']==2 and not d['source_elastic'] and d['same_material_plastic_PRE'] and not d['full_material_contract_independently_reconstructed'] and d['target_full_material_contract_enforced_by_solver'] and d['source_PREs_read']==1 and d['actual_retired_count']==255 and d['actual_retired_IDs_contiguous'] and d['retained_fixed_ID_begin']==0 and d['retained_fixed_ID_count']==1805 and d['completed_runtime_Run_csv_checked'] and d['kappa_nondecreasing_from_PRE_checks']==count*5000 and d['plane_gap_checks']==count*10000 and d['max_signed_dterror_s']<=1e-14 and d['nonempty_signed_intervals']==count,'Original receiver schema2/IDs/clock/FS/kappa/plane guards differ')
        m=read(root/'bedkeep_metadata.json');a=spec['actualAS'];need(a is not None and m['passed'] and m['stage']=='c08_h18_plastic_native_r1.metadata' and m['group']==spec['group'] and m['samples']==count and m['expected_source_handoff_schema']==2 and m['receiver_material_CSV_keys']==16 and m['same_material_plastic_PRE'] and m['geometry_profile']=='bedroles' and not m['keep_bed_overlap'] and m['AS_coefficient_float_reference']==old.f32(a['coefficient'])==old.f32(p['ArtificialStressCoef']) and m['AS_exponent_float_reference']==old.f32(a['exponent'])==old.f32(p['ArtificialStressExp']) and m['AS_active_true_headers']==count and m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==count,'Actual same-material AS/CompletedOnly metadata differs');consumed += [stat(root/'bedkeep_metadata.json'),bind(r['source_pre_file'])]
    expected=np.arange(7060,dtype=np.uint32) if source else np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)));layout=table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Exactly22 layout rows required')
    for q,(name,kind,width) in zip(layout,old.SCHEMA):need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,old.TYPES[kind].itemsize*width),'Original typed22 layout differs');fields.append((name,old.TYPES[kind],(nodes,width)))
    raw=root/'typed22.bin';dtype=np.dtype(fields)
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(nodes,22,count),'Genuine actual native header differs')
    need(raw.stat().st_size==12+count*dtype.itemsize,'Actual payload extent differs');clocks=table(root/'clocks.csv');plan=table(spec['plan']);need(len(clocks)==count and len(plan)==(1001 if source else count) and set(plan[0])=={'part','completed_step','saved_step','time_s','dt_s'},'Original complete five-column plan/actual clock coverage required')
    for i,(q,w) in enumerate(zip(clocks,plan)):
        need(int(q['part'])==int(w['part'])==i and int(q['completed_step'])==int(w['completed_step']) and int(q['saved_step'])==int(w['saved_step']) and float(q['dt_s'])==float(w['dt_s'])==5e-6 and abs(float(q['time_s'])-float(w['time_s']))<=1e-14,'Actual clocks do not match original plan prefix')
    if not source:need(int(clocks[0]['completed_step'])==2000001 and d['completed_steps']==(2180000 if count==91 else 2600000),'Actual first-post+1/full receiver schedule differs')
    consumed += [stat(root/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv')]
    for extra in spec.get('evidence',[]):consumed.append(bind(extra) if isinstance(extra,dict) else stat(extra))
    yields={}
    if source:consumed.append(stat(root/'summary.csv'));yields={int(q['part']):q for q in table(root/'summary.csv') if q['initial_material_group']=='all'};need(len(yields)==count,'Actual-kappa source yield observations missing')
    return dict(spec=spec,root=root,done=d,source=source,geometry_profile='bedroles',count=count,nodes=nodes,expected=expected,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,)),clocks=clocks,kw=kw,yield_rows=yields,runtime_observed=dict(passed=bool(r['passed']),solver_completed=bool(r['solver_completed']),actual_exit=r['actual_exit'],actual_Win32_exit=r['actual_Win32_exit']))

def source_plots(results,prefix):
    # Local display adapter only. Analysis/CSV values remain the original units.
    from matplotlib.ticker import MaxNLocator,ScalarFormatter
    charts=(('Absolute p min/max/RMS [kPa]',('p_min_Pa','p_max_Pa','p_RMS_Pa'),.001),('Native p-fixed P0 min/max/RMS [kPa]',('native_p_minus_fixedP0_min_Pa','native_p_minus_fixedP0_max_Pa','native_p_minus_fixedP0_RMS_Pa'),.001),('Effective/total stress RMS [kPa]',('effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa'),.001),('Speed RMS/max [m/s]',('velocity_RMS_m_s','max_speed_m_s'),1.),('KE/pressure quadratics [J/m]',('current_mixture_KE_J_per_m','current_pressure_storage_quadratic_J_per_m'),1.),('Maximum kappa',('max_kappa',),1.),('J min/max',('min_J','max_J'),1.),('Porosity min/max',('min_n','max_n'),1.),('Conductivity min/max [m/s]',('min_k_m_s','max_k_m_s'),1.),('Mean/top/bottom material settlement [mm]',('mean_settlement_reference_mm','top_material_settlement_mm','bottom_material_settlement_mm'),1.),('Front x / height [m]',('front_x_m','max_height_m'),1.),('Saved f max (actual kappa) [kPa]',('saved_f_max_Pa',),.001),('Saved negative p count',('negative_p_soil',),1.),('Minimum x/z [m]',('min_soil_x_m','min_soil_z_m'),1.),('Saved positive/negative FS23 [count]',('saved_FS23_positive','saved_FS23_negative'),1.));files=[]
    for tail in (False,True):
        fig,axes=old.plt.subplots(5,3,figsize=(15,16),layout='constrained')
        for ax,(title,keys,scale) in zip(axes.flat,charts):
            for ci,a in enumerate(results):
                rr=[q for q in a['history'] if not tail or q['time_s']>=a['summary']['late_interval']['actual_first_time_s']]
                for ki,key in enumerate(keys):ax.plot([q['time_s'] for q in rr],[q[key]*scale for q in rr],color='C'+str(ci%10),ls=('-','--',':')[ki],label=a['summary']['tag'] if ki==0 else None)
            ax.set(title=title,xlabel='Actual source time t [s]');ax.grid(alpha=.2);ax.xaxis.set_major_locator(MaxNLocator(5));ax.ticklabel_format(axis='x',style='plain',useOffset=False);ax.legend(fontsize=7)
            if title.startswith(('Absolute p','Native p-fixed')):ax.set_yscale('symlog',linthresh=1.)
        fig.suptitle('Source actual saves; '+('last up-to1s interval, no equilibrium gate' if tail else 'no release occurred')+'\nSolid/dashed/dotted follow each panel metric order');dest=Path(str(prefix)+('_tail.png' if tail else '_history.png'));fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest)
    fig,axes=old.plt.subplots(2,3,figsize=(14,9),layout='constrained');fields=(('p_mean_Pa','Mean absolute p [kPa]',.001),('effective_zz_mean_Pa','Mean effective sigma_zz [kPa]',.001),('total_zz_mean_Pa','Mean total sigma_zz [kPa]',.001),('velocity_RMS_m_s','Speed RMS [m/s]',1.),('mean_J','Mean J',1.),('mean_settlement_reference_mm','Mean material settlement [mm]',1.))
    for ci,a in enumerate(results):
        start=a['summary']['late_interval']['actual_first_time_s'];times=sorted({q['time_s'] for q in a['layers'] if q['time_s']>=start});chosen=sorted({times[0],times[len(times)//2],times[-1]})
        for ti,time in enumerate(chosen):
            rr=[q for q in a['layers'] if q['time_s']==time]
            for ax,(key,label,scale) in zip(axes.flat,fields):ax.plot([q[key]*scale for q in rr],[q['initial_z_m'] for q in rr],color='C'+str(ci%10),ls=('-','--',':')[ti],label=a['summary']['tag']+f' t={time:.6f}s');ax.set(xlabel=label,ylabel='Fixed material initial z [m]');ax.grid(alpha=.2)
    for ax in axes.flat:
        ax.xaxis.set_major_locator(MaxNLocator(4));fmt=ScalarFormatter(useOffset=False);fmt.set_powerlimits((-3,4));ax.xaxis.set_major_formatter(fmt);ax.legend(fontsize=6)
    fig.suptitle('Source:50 original100-ID layers; actual first/middle/last saves in the tail interval\nStress/pressure displayed in kPa; CSV remains Pa');dest=Path(str(prefix)+'_layers.png');fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest);return files

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root must read before one offline review');manifest=read(a.manifest);tag=manifest['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag),'Safe exclusive derived tag required');prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'_*')),'Existing complete/partial analysis protected');consumed=[stat(a.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(old.__file__),stat(T/'notes/c08_h18_compare_r2.md')];result=dict(stage=TAG,passed=False,physical_acceptance=False,consumed=consumed)
    try:
        need(manifest['schema']==2 and manifest['mode'] in ('source','receiver') and manifest['cases'],'Explicit schema2 source/receiver review required');bundles=[load_bundle(q,consumed) for q in manifest['cases']];need(len({q['spec']['tag'] for q in bundles})==len(bundles) and all(q['source']==(manifest['mode']=='source') for q in bundles),'Unique tags and one review mode required');references={}
        if manifest['mode']=='receiver':
            for spec in manifest['source_references']:
                b=load_bundle(spec,consumed);need(b['source'] and spec['source'] not in references,'Unique full source reference per actual source required');references[spec['source']]=(b,old.reference_from(b))
            for b in bundles:
                need(b['spec']['source'] in references,'Missing same-material full source reference');s,_=references[b['spec']['source']];r=read(b['spec']['run']);sr=read(s['spec']['run']);need(s['spec']['group']==b['spec']['group'] and bind(r['source_pre_file'])==bind(sr['source_pre_file']),'Receiver references a different group or actual PRE')
        analyses=[old.analyze_case(b,None if b['source'] else references[b['spec']['source']][1],manifest.get('snapshots_tau_s')) for b in bundles];files=[]
        for key in ('history','extrema','layers','tracks'):
            dest=Path(str(prefix)+'_'+key+'.csv');old.write_csv(dest,[q for x in analyses for q in x[key]]);files.append(dest)
        tail=[]
        for x in analyses:
            late=x['summary']['late_interval']
            for key,q in late['metrics'].items():tail.append(dict(tag=x['summary']['tag'],group=x['bundle']['spec']['group'],metric=key,requested_duration_s=late['requested_duration_s'],actual_duration_s=late['actual_duration_s'],actual_first_time_s=late['actual_first_time_s'],actual_last_time_s=late['actual_last_time_s'],samples=late['samples'],**q))
        dest=Path(str(prefix)+'_tail_changes.csv');old.write_csv(dest,tail);files.append(dest)
        if manifest['mode']=='receiver':
            snapshot=[]
            for x in analyses:
                for part,s in x['snapshots'].items():
                    for i,pos in enumerate(s['pos']):snapshot.append(dict(tag=x['summary']['tag'],group=x['bundle']['spec']['group'],part=part,time_s=s['time_s'],tau_s=s['tau_s'],native_id=2060+i,x_m=float(pos[0]),z_m=float(pos[2]),p_Pa=float(s['p'][i]),native_p_minus_fixedP0_Pa=float(s['excess'][i]),kappa=float(s['kappa'][i]),J=float(s['J'][i])))
            dest=Path(str(prefix)+'_fields.csv');old.write_csv(dest,snapshot);files.append(dest)
        files+=(source_plots(analyses,prefix) if manifest['mode']=='source' else old.plot_results(analyses,prefix));need(all(stat(q['path'])==q for q in consumed),'Consumed sealed input changed');result.update(passed=True,mode=manifest['mode'],original_headers={q['spec']['tag']:[q['nodes'],22,q['count']] for q in bundles},actual_samples={q['spec']['tag']:q['count'] for q in bundles},summaries=[q['summary'] for q in analyses],schema2_actual_material_binding_checked=True,source_yield_uses_saved_kappa=True,full_material_contract_independently_reconstructed=False,target_full_contract_enforced_by_receiving_solver=True,source_equilibrium_gate_added=False,source_equilibrium_accepted=False,native_excess_is_fixed_P0_difference_not_paper_equivalence=True,winner_selected=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
