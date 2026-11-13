"""Offline review of the explicit completed Wendland H1.8 psi0 source; no continuation."""
import argparse,csv,json,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_compare_r2 as old
import c08_h18_plastic_review_r1 as plastic

T,C,need,path,stat,read,table,bind=old.T,old.C,old.need,old.path,old.stat,old.read,old.table,old.bind
np=old.np;TAG='c08_h18_wend_review_r1';SOURCE='c08_h18_wend_psi0_pre_r2';COUNT=1001;NODES=7060;FIXED=2060
BUILD=T/'logs/c08_h18_wend_native_r1.build.json'

def same(a,b):return path(a).samefile(path(b))
def material_xml(csvpath,xml):
    rows=table(csvpath);p={q['key']:q['value'] for q in rows};keys=plastic.MATERIAL_KEYS|{'Kernel'}
    need(len(rows)==len(p)==15 and set(p)==keys and p['group']=='psi0' and p['fresh_trigger_active']=='0','Exact15-key Wendland/psi0 material CSV required')
    soil=xml.find('execution/special/soils');pairs=[(q.get('key'),q.get('value')) for q in xml.findall('execution/parameters/parameter')];pars=dict(pairs);need(soil is not None and len(pairs)==len(pars),'Actual unique parameter/soil XML required')
    for key in keys-{'group','fresh_trigger_active'}:
        node=soil.find(key);value=pars[key] if key in ('Kernel','DPCtes') else (node.get('value') if node is not None else '1.65' if key=='SoilTriggerFos' else None)
        need(value is not None and old.f32(p[key])==old.f32(value),'CSV disagrees with actual generated XML: '+key)
    for key,value in dict(Kernel=2,DPCtes=3,ModulusE=20e6,PRvs=.33,phi=25,phi_r=25,n_phi=0,coh=5000,coh_r=1000,n_coh=5,dlt=0,DilationDecay=0).items():need(old.f32(p[key])==old.f32(value),'Outside actual Wendland psi0 material: '+key)
    need(float(p['SoilTriggerFos'])>=1,'Original FOS domain differs')
    return pars

def load(manifest,consumed):
    for key in ('tag','native_dir','native_call','material_csv','plan','run','input_xml'):need(key in manifest,'Explicit source manifest key missing: '+key)
    root=path(manifest['native_dir']);d=read(root/'completion.json');b=read(BUILD);call=read(manifest['native_call']);r=read(manifest['run'])
    need(d['stage']=='c08_h18_wend_native_r1.source' and d['passed'] and d['profile']=='full' and not d['partial'] and not d['uncertified'] and d['certified_PRE'] and not d['runtime_success_claimed'],'Explicit full Wendland native stage required')
    need(d['samples']==COUNT and d['completed_steps']==2000000 and d['native_IDs']==NODES and d['fixed_IDs']==FIXED and d['soil_IDs']==5000 and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212,'Original full source shape differs')
    need(d['ledger_checks']==d['rho_cache_bits_checks']==d['kappa_nondecreasing_checks']==COUNT*5000 and d['P0_bits_checks']==COUNT*NODES and d['fixed_marker_checks']==d['fixed_kappa_zero_checks']==COUNT*FIXED and d['initial_kappa_zero_checks']==NODES,'Original full-ID ledger/history/fixed coverage differs')
    need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_noninitial_signed_dterror_s']<=1e-14 and d['noninitial_signed_intervals']==1000,'Original full source numerical budgets differ')
    need(d['H']==old.f32(.072) and d['group']=='psi0' and d['geometry_profile']=='bedroles' and d['release_target_ID_begin']==1805 and d['release_target_ID_count']==255 and not d['keep_bed_overlap'] and d['expected_handoff_schema']==2,'Actual H/group/schema2/bed roles differ')
    need(d['source_material_CSV_keys']==15 and d['source_group_certificate_checked'] and d['same_material_plastic_PRE'] and d['source_yield_uses_actual_kappa'] and d['declared_Kernel_XML_CSV']==2 and d['kernel_name_declared']=='Wendland' and d['source_event_contract_kernel_checked'] and not d['non_event_kernel_identity_proven_by_reader'] and not d['full_material_contract_independently_reconstructed'],'Native actual kernel/material identity annotations differ')
    need(b['passed'] and b['consumed_stats_unchanged'] and not b['JSph_objects_linked'] and b['source_material_CSV_keys']==15 and b['declared_Kernel_XML_CSV']==2 and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and same(call['program'],bind(b['program'])['path']),'Actual qualified Wendland utility/exit differs')
    args=call['arguments'];need(len(args)==6 and args[:2]==['--source','full'] and same(args[2],path(manifest['input_xml']).parent/'data') and same(args[3],manifest['material_csv']) and same(args[4],manifest['plan']) and same(args[5],root),'Actual native DATA/15CSV/full-plan/output binding differs')
    need(r['stage']==SOURCE and r['solver_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==2000000 and r['saved_frames']==COUNT and r['kernel']==2 and r['kernel_name']=='Wendland','Actual completed source plan/kernel required, not exit0 alone')
    actual=read(bind(r['actual_call'])['path']);need(actual['actual_solver_Win32_exit']==actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and not actual['ownership_errors'] and same(actual['actual_solver']['exe'],bind(r['program'])['path']) and same(bind(r['input_xml'])['path'],manifest['input_xml']),'Actual solver ownership/program/input differs')
    pb=read(bind(r['source_build'])['path']);need(pb['passed'] and pb['configuration']=='Release' and pb['consumed_stats_unchanged'] and bind(pb['program'])==bind(r['program']) and pb['source_capture']==r['source_capture'] and pb['source_archive']==r['source_archive'],'Actual physical build/source closure differs')
    xml=ET.parse(path(manifest['input_xml'])).getroot();pars=material_xml(manifest['material_csv'],xml);hyd=xml.find('execution/special/hydromechanics');g=xml.find('execution/special/gravitypreload')
    need(hyd is not None and g is not None and old.f32(xml.find('execution/constants/h').get('value'))==d['H'] and float(pars['DtFixed'])==5e-6 and g.get('elastic_source')==g.get('keep_bed_overlap')=='false' and not g.get('statefile') and float(g.get('time'))==10,'Actual fresh source H/step/phase differs')
    need(float(pars.get('ArtificialStress','0'))==float(pars.get('NoPenetration','0'))==0 and float(pars['SoilDamping'])==1 and float(pars['SoilDampingCoef'])==.03,'Actual preload stabilization scope differs')
    run_dir=path(manifest['input_xml']).parent;runout=(run_dir/'Run.out').read_text(encoding='utf-8-sig')
    need('Kernel="Wendland"' in runout and 'Kernel="CubicSpline"' not in runout and 'GravityPreload: phase=released' not in runout and 'GravityPreload: state imported' not in runout and 'Simulation INTERRUPTED' not in runout and 'Finished execution (code=0).' in runout,'Actual Run.out kernel/completed pre-release path differs')
    with (run_dir/'Run.csv').open(encoding='utf-8-sig',newline='') as f:summary=list(csv.DictReader(f,delimiter=';'))
    need(len(summary)==1 and all(int(summary[0][k])==v for k,v in dict(Steps=2000000,PartFiles=COUNT,Np=NODES,Nbound=FIXED,Nfixed=FIXED,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items()),'Actual no-exclusion 2M/1001 summary differs')
    layout=table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Literal22 layout required')
    for q,(name,kind,width) in zip(layout,old.SCHEMA):need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,old.TYPES[kind].itemsize*width),'Original typed22 schema differs');fields.append((name,old.TYPES[kind],(NODES,width)))
    raw=root/'typed22.bin';dtype=np.dtype(fields)
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(NODES,22,COUNT),'Genuine source header differs')
    need(raw.stat().st_size==12+COUNT*dtype.itemsize,'Actual payload extent differs');clocks=table(root/'clocks.csv');plan=table(manifest['plan']);need(len(clocks)==len(plan)==COUNT and set(plan[0])=={'part','completed_step','saved_step','time_s','dt_s'},'Original complete1001 scalar plan required')
    for i,(q,p) in enumerate(zip(clocks,plan)):need(int(q['part'])==int(p['part'])==i and int(q['completed_step'])==int(p['completed_step']) and int(q['saved_step'])==int(p['saved_step']) and float(q['dt_s'])==float(p['dt_s'])==5e-6 and abs(float(q['time_s'])-float(p['time_s']))<=1e-14,'Actual scalar clocks/steps differ from the original complete plan')
    yields={int(q['part']):q for q in table(root/'summary.csv') if q['initial_material_group']=='all'};need(len(yields)==COUNT,'Actual-kappa yield coverage differs')
    consumed += [stat(q) for q in (BUILD,root/'completion.json',manifest['native_call'],manifest['run'],manifest['input_xml'],manifest['material_csv'],manifest['plan'],run_dir/'Run.out',run_dir/'Run.csv')]+[bind(b['program']),bind(b['source'])]+[bind(r[k]) for k in ('actual_call','program','source_build','source_capture','source_archive','input_xml')]+[stat(root/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv','summary.csv')]
    return dict(spec=dict(tag=manifest['tag'],source=SOURCE,group='psi0',actualAS=None,H=.072),root=root,done=d,source=True,geometry_profile='bedroles',count=COUNT,nodes=NODES,expected=np.arange(NODES,dtype=np.uint32),frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(COUNT,)),clocks=clocks,kw=old.f32(hyd.find('PoreWaterBulkModulus').get('value')),yield_rows=yields,runtime_observed=dict(passed=bool(r['passed']),solver_completed=True,actual_exit=0,actual_Win32_exit=0))

def geometry(bundle,history):
    rows=[]
    for part,x in enumerate(bundle['frames']):
        pos=x['Posd'][FIXED:];tree=old.cKDTree(pos[:,(0,2)]);distance,index=tree.query(pos[:,(0,2)],k=2,workers=1);nn=np.min(np.where(index!=np.arange(5000)[:,None],distance,np.inf),axis=1)/old.DP;pair=tree.query_pairs(.7*old.DP,output_type='ndarray');pairs=int(np.count_nonzero(np.linalg.norm(pos[pair[:,0]]-pos[pair[:,1]],axis=1)<.7*old.DP)) if len(pair) else 0
        row=dict(part=part,time_s=history[part]['time_s'],completed_step=history[part]['completed_step'],NN_min_over_dp=float(nn.min()),NN_q05_over_dp=float(np.quantile(nn,.05)),NN_median_over_dp=float(np.median(nn)),pairs_r_lt_0p7dp=pairs,soil_x_below0=int(np.count_nonzero(pos[:,0]<0)),soil_z_below0=int(np.count_nonzero(pos[:,2]<0)),min_soil_x_m=float(pos[:,0].min()),min_soil_z_m=float(pos[:,2].min()));rows.append(row)
    return rows

def tails(bundle,analysis):
    history=analysis['history'];end=history[-1]['time_s'];rows=[];states=[];last=bundle['frames'][-1];initial=bundle['frames'][0]['Posd'][FIXED:];top=initial[:,2]==initial[:,2].max();bottom=initial[:,2]==initial[:,2].min()
    keys=('p_mean_Pa','p_RMS_Pa','native_p_minus_fixedP0_RMS_Pa','effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa','velocity_RMS_m_s','max_speed_m_s','current_mixture_KE_J_per_m','current_pressure_storage_quadratic_J_per_m','mean_settlement_reference_mm','top_material_settlement_mm','bottom_material_settlement_mm','max_kappa','min_J','max_J','min_n','max_n','min_k_m_s','max_k_m_s')
    for duration in (.5,1.):
        at=next(i for i,q in enumerate(history) if q['time_s']>=end-duration);tail=history[at:];width=end-tail[0]['time_s'];need(width>0,'Actual tail interval must be nonzero');first=bundle['frames'][at]
        common=dict(requested_duration_s=duration,actual_start_s=tail[0]['time_s'],actual_end_s=end,actual_duration_s=width,start_part=at,end_part=1000,samples=len(tail))
        for key in keys:
            values=[q[key] for q in tail];rows.append(dict(**common,metric=key,first=values[0],last=values[-1],delta=values[-1]-values[0],minimum=min(values),maximum=max(values),endpoint_secant_per_s=(values[-1]-values[0])/width))
        du=last['Posd'][FIXED:]-first['Posd'][FIXED:];dp=last['PorePress'][FIXED:,0].astype(float)-first['PorePress'][FIXED:,0].astype(float);dsk=last['SigmaState_kk'][FIXED:]-first['SigmaState_kk'][FIXED:];dsi=last['SigmaState_ij'][FIXED:]-first['SigmaState_ij'][FIXED:];dtotal=dsk-dp[:,None];dv=last['Vel'][FIXED:].astype(float)-first['Vel'][FIXED:].astype(float)
        state=dict(**common,p_same_ID_RMS_change_Pa=float(np.sqrt(np.mean(dp*dp))),effective_stress_same_ID_Frob_RMS_change_Pa=float(np.sqrt(np.mean(np.sum(dsk*dsk,axis=1)+2*np.sum(dsi*dsi,axis=1)))),total_stress_same_ID_Frob_RMS_change_Pa=float(np.sqrt(np.mean(np.sum(dtotal*dtotal,axis=1)+2*np.sum(dsi*dsi,axis=1)))),velocity_vector_same_ID_RMS_change_m_s=float(np.sqrt(np.mean(np.sum(dv*dv,axis=1)))),same_ID_XYZ_movement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du,axis=1)))),same_ID_XYZ_movement_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),top_material_settlement_change_mm=float(-1000*du[top,2].mean()),bottom_material_settlement_change_mm=float(-1000*du[bottom,2].mean()))
        for field,name in (('Kplastic','kappa'),('PoroVolumeRatio','J'),('PoroPorosity','n'),('PoroHydraulicConductivity','k_m_s')):
            delta=last[field][FIXED:,0].astype(float)-first[field][FIXED:,0].astype(float);state[name+'_same_ID_change_RMS']=float(np.sqrt(np.mean(delta*delta)));state[name+'_same_ID_change_maxabs']=float(np.abs(delta).max())
        states.append(state)
    return rows,states

def cubic_comparison(history,consumed):
    cp=T/'logs/c08_h18_loss_review_r1.check.json';d=read(cp);need(d['analysis_complete'] and not d['whole_run_passed'] and not d['certified_PRE'] and d['strict_prefix_samples']==533 and d['all_actual_saved_frames_accounted_for'],'Retained failed Cubic review must remain failed')
    csvpath=T/'figures/c08_h18_loss_review_r1_prefix_history.csv';entry=next(q for q in d['files'] if same(q['path'],csvpath));bind(entry);consumed += [stat(cp),entry]
    control=table(csvpath);lookup={(q['completed_step'],q['time_s']):q for q in history};matched=[];pairs=[];keys=('p_RMS_Pa','p_min_Pa','p_max_Pa','velocity_RMS_m_s','max_speed_m_s','current_mixture_KE_J_per_m','max_kappa','min_J','max_J','mean_settlement_reference_mm','top_material_settlement_mm','bottom_material_settlement_mm')
    for q in control:
        key=(int(q['completed_step']),float(q['time_s']))
        if key not in lookup:continue
        w=lookup[key];row=dict(completed_step=key[0],time_s=key[1],Wendland_part=w['part'],Cubic_part=int(q['part']))
        for name in keys:row[name+'_Wendland']=w[name];row[name+'_Cubic']=float(q[name]);row[name+'_Wendland_minus_Cubic']=w[name]-float(q[name])
        matched.append(row);pairs.append((w,q))
    return matched,dict(retained_source='c08_h18_plastic_psi0_pre_r1',retained_complete_prefix_samples=533,actual_exact_time_step_pairs=len(matched),unmatched_complete_prefix_samples=len(control)-len(matched),forced_final_Cubic_time_s=d['incomplete_final_metadata']['time_s'],forced_final_Cubic_not_interpolated_or_mixed=True,comparison_is_descriptive_not_theory_or_half_error=True),pairs

def extra_plots(history,geometry_rows,pairs,prefix):
    files=[];fig,axes=old.plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for key,ax,title in [('NN_min_over_dp',axes[0],'Minimum nearest distance / dp'),('pairs_r_lt_0p7dp',axes[1],'Pairs at r < .7dp'),('soil_z_below0',axes[2],'Saved soil points below z=0')]:ax.plot([q['time_s'] for q in geometry_rows],[q[key] for q in geometry_rows]);ax.set(title=title,xlabel='Actual source time [s]');ax.grid(alpha=.2)
    fig.suptitle('Wendland source spatial observations; no contact or equilibrium acceptance');dest=Path(str(prefix)+'_geometry.png');fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest)
    if pairs:
        fig,axes=old.plt.subplots(2,3,figsize=(13,8),layout='constrained');charts=(('p_RMS_Pa','Absolute p RMS [kPa]',.001),('max_speed_m_s','Maximum speed [m/s]',1.),('current_mixture_KE_J_per_m','Mixture KE [J/m]',1.),('max_kappa','Maximum kappa',1.),('min_J','Minimum J',1.),('mean_settlement_reference_mm','Mean material settlement [mm]',1.))
        for ax,(key,title,scale) in zip(axes.flat,charts):
            for side,label in ((0,'Wendland completed source'),(1,'Cubic failed source, complete prefix only')):ax.plot([float(p[side]['time_s']) for p in pairs],[float(p[side][key])*scale for p in pairs],label=label)
            ax.set(title=title,xlabel='Exact shared source time [s]');ax.grid(alpha=.2);ax.legend(fontsize=6)
        fig.suptitle('Descriptive different-kernel comparison at actual matching step/time only; no fitted or missing final state');dest=Path(str(prefix)+'_versus_Cubic.png');fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest)
    return files

def focus_plots(history,prefix):
    """Readable six-panel actual-source summaries; no fitted curve or new analysis."""
    files=[];end=history[-1]['time_s'];charts=(('Pressure RMS [kPa]',(('p_RMS_Pa','absolute p',.001),('native_p_minus_fixedP0_RMS_Pa','native p-fixed P0',.001))),('Speed [m/s]',(('velocity_RMS_m_s','RMS',1.),('max_speed_m_s','maximum',1.))),('Stress Frobenius RMS [kPa]',(('effective_stress_Frobenius_RMS_Pa','effective',.001),('total_stress_Frobenius_RMS_Pa','total',.001))),('Current mixture kinetic energy [J/m]',(('current_mixture_KE_J_per_m','KE',1.),)),('Material settlement [mm]',(('mean_settlement_reference_mm','all mean',1.),('top_material_settlement_mm','initial top layer',1.),('bottom_material_settlement_mm','initial bottom layer',1.))))
    for name,duration in (('full',None),('last1s',1.),('last0p5s',.5)):
        rr=[q for q in history if duration is None or q['time_s']>=end-duration];fig,axes=old.plt.subplots(2,3,figsize=(13,8),layout='constrained');x=[q['time_s'] for q in rr]
        for ax,(title,series) in zip(axes.flat,charts):
            for key,label,scale in series:ax.plot(x,[q[key]*scale for q in rr],label=label,lw=1.25)
            ax.set(title=title,xlabel='Actual source time t [s]');ax.grid(alpha=.25);ax.legend(fontsize=8)
        ax=axes.flat[5]
        for key,label,offset in (('max_kappa','maximum kappa',0.),('min_J','minimum J minus1',1.),('max_J','maximum J minus1',1.)):ax.plot(x,[q[key]-offset for q in rr],label=label,lw=1.25)
        ax.set(title='History and volume changes [dimensionless]',xlabel='Actual source time t [s]');ax.grid(alpha=.25);ax.legend(fontsize=8)
        fig.suptitle('Wendland psi0 preload, actual '+format(rr[0]['time_s'],'.6f')+' to '+format(rr[-1]['time_s'],'.6f')+'s\nSaved native histories; completion/certificate are not equilibrium acceptance');dest=Path(str(prefix)+'_focus_'+name+'.png');fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest)
    return files

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root full-read before unique offline analysis');m=read(a.manifest);tag=m['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag),'Safe new derived tag required');prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'_*')),'Existing complete/partial analysis protected');consumed=[stat(a.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(old.__file__),stat(plastic.__file__)];result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,source_equilibrium_accepted=False,consumed=consumed)
    try:
        bundle=load(m,consumed);analysis=old.analyze_case(bundle);spatial=geometry(bundle,analysis['history']);tail_rows,tail_states=tails(bundle,analysis);matched=[];comparison=None;pairs=[]
        if m.get('compare_failed_Cubic',True):matched,comparison,pairs=cubic_comparison(analysis['history'],consumed)
        files=[]
        for key in ('history','extrema','layers','tracks'):dest=Path(str(prefix)+'_'+key+'.csv');old.write_csv(dest,analysis[key]);files.append(dest)
        for name,rows in [('geometry',spatial),('tail_metrics',tail_rows),('tail_same_material_changes',tail_states)]+([('versus_Cubic',matched)] if matched else []):dest=Path(str(prefix)+'_'+name+'.csv');old.write_csv(dest,rows);files.append(dest)
        files+=plastic.source_plots([analysis],prefix);files+=extra_plots(analysis['history'],spatial,pairs,prefix);files+=focus_plots(analysis['history'],prefix);need(all(stat(q['path'])==q for q in consumed),'Sealed source/native evidence changed')
        result.update(analysis_complete=True,actual_samples=COUNT,source_summary=analysis['summary'],tail_same_material_changes=tail_states,spatial_summary=dict(final=spatial[-1],minimum_NN_over_dp=min(q['NN_min_over_dp'] for q in spatial),maximum_pairs_r_lt_0p7dp=max(q['pairs_r_lt_0p7dp'] for q in spatial),first_saved_below_bed=next((q for q in spatial if q['soil_z_below0']>0),None),first_saved_near_pair=next((q for q in spatial if q['pairs_r_lt_0p7dp']>0),None)),Cubic_comparison=comparison,source_native_qualified=True,source_native_certificate_not_equilibrium=True,new_receiver_continuity_not_tested=True,full_material_contract_independently_reconstructed=False,native_p_minus_P0_not_paper_defined_excess=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
