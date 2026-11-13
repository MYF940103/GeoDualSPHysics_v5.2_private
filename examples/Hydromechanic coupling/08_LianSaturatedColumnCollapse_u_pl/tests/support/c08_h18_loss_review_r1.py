"""Offline C08 loss forensics: qualified complete prefix and separate incomplete final save."""
import argparse,csv,json,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_compare_r2 as old
import c08_h18_plastic_review_r1 as plastic

T,C,need,path,stat,read,table,bind=old.T,old.C,old.need,old.path,old.stat,old.read,old.table,old.bind
np=old.np;TAG='c08_h18_loss_review_r1';SOURCE='c08_h18_plastic_psi0_pre_r1'
BUILD=T/'logs/c08_h18_loss_native_r1.build.json';NODES=7060;FIXED=2060;SOIL=5000;COUNT=533;LOST=3060

def same(a,b):return path(a).samefile(path(b))
def record_dtype(layout,nodes):
    need(len(layout)==22,'Exactly22 literal layout rows required');fields=[('time','<f8')]
    for q,(name,kind,width) in zip(layout,old.SCHEMA):
        need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,old.TYPES[kind].itemsize*width),'Original typed22 layout differs')
        fields.append((name,old.TYPES[kind],(nodes,width)))
    return np.dtype(fields)

def mapped_record(raw,layout,nodes,count):
    dtype=record_dtype(table(layout),nodes)
    with path(raw).open('rb') as f:need(struct.unpack('<III',f.read(12))==(nodes,22,count),'Actual raw header cannot be relabelled')
    need(path(raw).stat().st_size==12+count*dtype.itemsize,'Actual typed22 extent differs')
    return np.memmap(path(raw),dtype=dtype,offset=12,mode='r',shape=(count,))

def load(manifest,consumed):
    for key in ('tag','native_dir','native_call','material_csv','plan','run','input_xml','excluded_csv'):need(key in manifest,'Explicit loss-review manifest key missing: '+key)
    root=path(manifest['native_dir']);prefix=root/'prefix';whole=read(root/'completion.json');d=read(prefix/'completion.json');final=read(root/'final_part533.json')
    need(whole['diagnostic_complete'] and whole['strict_prefix_native_passed'] and not whole['whole_run_native_passed'] and not whole['source_complete'] and not whole['certified_PRE'],'Incomplete whole-run status must remain failed')
    need(d['stage']=='c08_h18_loss_native_r1.strict_prefix' and d['passed'] and not d['whole_run_native_passed'] and not d['certified_PRE'] and d['partial'] and d['uncertified'],'Explicit qualified partial-prefix stage required')
    need(d['samples']==COUNT and d['native_IDs']==NODES and d['soil_IDs']==SOIL and d['fixed_IDs']==FIXED and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212,'Exact prefix shape differs')
    need(d['ledger_checks']==d['rho_cache_bits_checks']==d['kappa_nondecreasing_checks']==COUNT*SOIL and d['P0_bits_checks']==COUNT*NODES and d['fixed_marker_checks']==d['fixed_kappa_zero_checks']==COUNT*FIXED and d['initial_kappa_zero_checks']==NODES,'Original prefix ledger/history/fixed coverage differs')
    need(d['max_scalar_clock_error_s']<=1e-14 and d['max_noninitial_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['noninitial_signed_intervals']==COUNT-1,'Original prefix numerical budgets differ')
    need(d['H']==old.f32(.072) and d['group']=='psi0' and d['geometry_profile']=='bedroles' and d['release_target_ID_begin']==1805 and d['release_target_ID_count']==255 and not d['keep_bed_overlap'],'Actual source H/group/bed roles differ')
    b=read(BUILD);call=read(manifest['native_call']);need(b['passed'] and b['consumed_stats_unchanged'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and same(call['program'],bind(b['program'])['path']),'Actual new forensic reader build/exit differs')
    args=call['arguments'];need(len(args)==5 and args[0]=='--read' and same(args[1],path(manifest['input_xml']).parent/'data') and same(args[2],manifest['material_csv']) and same(args[3],manifest['plan']) and same(args[4],root),'Actual forensic DATA/material/full-plan/output binding differs')
    r=read(manifest['run']);need(r['stage']==SOURCE and not r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0,'Original interrupted source cannot be relabelled complete')
    actual=read(bind(r['actual_call'])['path']);need(actual['actual_solver_Win32_exit']==actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and not actual['ownership_errors'] and same(actual['actual_solver']['exe'],bind(r['program'])['path']),'Actual source handles/exits differ')
    need(same(bind(r['input_xml'])['path'],manifest['input_xml']),'Actual generated source XML differs');pb=read(bind(r['source_build'])['path']);need(pb['passed'] and pb['configuration']=='Release' and pb['consumed_stats_unchanged'] and bind(pb['program'])==bind(r['program']) and pb['source_capture']==r['source_capture'] and pb['source_archive']==r['source_archive'],'Frozen physical source/program closure differs')
    xml=ET.parse(path(manifest['input_xml'])).getroot();spec=dict(group='psi0',material_csv=manifest['material_csv']);_,pars=plastic.material_csv(spec,xml,True);g=xml.find('execution/special/gravitypreload');hyd=xml.find('execution/special/hydromechanics')
    need(g.get('elastic_source')==g.get('keep_bed_overlap')=='false' and not g.get('statefile') and float(pars['DtFixed'])==5e-6 and float(pars.get('ArtificialStress','0'))==float(pars.get('NoPenetration','0'))==0,'Actual plastic source/ASoff/NoPenoff scope differs')
    run_dir=path(r['input_xml']['path']).parent;run_rows=table_semicolon(run_dir/'Run.csv');need(len(run_rows)==1,'Actual run summary required');v=run_rows[0]
    need(all(int(v[k])==val for k,val in dict(Steps=1064544,PartFiles=534,PartsOut=1,PartsOutRhop=0,PartsOutVel=0).items()),'Original interruption counters differ')
    text=(run_dir/'Run.out').read_text(encoding='utf-8-sig');need('Particles OUT limit reached' in text and 'Simulation INTERRUPTED' in text,'Original first-cause interruption record missing')
    plan=table(manifest['plan']);clocks=table(prefix/'clocks.csv');need(len(plan)==1001 and len(clocks)==COUNT and set(plan[0])=={'part','completed_step','saved_step','time_s','dt_s'},'Keep the untouched full1001 plan and actual533 prefix clocks')
    for i,(q,p) in enumerate(zip(clocks,plan)):
        need(int(q['part'])==int(p['part'])==i and int(q['completed_step'])==int(p['completed_step']) and int(q['saved_step'])==int(p['saved_step']) and float(q['dt_s'])==float(p['dt_s'])==5e-6 and abs(float(q['time_s'])-float(p['time_s']))<=1e-14,'Actual qualified prefix clocks differ from the complete plan')
    need(final['part']==533 and final['completed_step']==1064544 and final['saved_step']==1064543 and final['native_ID_domain']==NODES and final['present_IDs']==7059 and final['missing_ids']==[LOST] and final['dt_s']==5e-6 and final['signed_dterror_s']<=1e-14,'Actual incomplete forced-final identity differs')
    frames=mapped_record(prefix/'typed22.bin',prefix/'typed22_layout.csv',NODES,COUNT);tail=mapped_record(root/'final_part533_typed22.bin',root/'final_part533_layout.csv',7059,1)[0]
    need(float(tail['time'])==final['time_s'] and final['time_s']>float(clocks[-1]['time_s']),'Genuine forced-final clock differs')
    scalar=float(clocks[-1]['time_s'])
    for unused in range(int(clocks[-1]['completed_step']),final['completed_step']):scalar+=5e-6
    need(abs(scalar-final['time_s'])<=1e-14,'Final scalar +=dt clock differs; nominal n*dt is not substituted')
    ids=tail['Idp'][:,0];need(np.unique(ids).size==7059 and np.array_equal(np.setdiff1d(np.arange(NODES,dtype=np.uint32),ids),[LOST]) and all(np.isfinite(tail[name]).all() for name,_,_ in old.SCHEMA),'Actual final original-order ID domain/finite fields differ')
    excluded=table(root/'excluded.csv');aux=table(manifest['excluded_csv']);need(len(excluded)==len(aux)==1 and int(excluded[0]['native_id'])==int(aux[0]['Idp'])==LOST and int(excluded[0]['motive'])==int(aux[0]['Motive'])==1,'Both genuine excluded records must identify3060/position')
    need(int(excluded[0]['part'])==533 and float(excluded[0]['time_s'])==final['time_s'],'Actual excluded-part clock differs')
    consumed += [stat(q) for q in (BUILD,root/'completion.json',prefix/'completion.json',root/'final_part533.json',manifest['native_call'],manifest['run'],manifest['input_xml'],manifest['material_csv'],manifest['plan'],manifest['excluded_csv'],run_dir/'Run.csv',run_dir/'Run.out',root/'excluded.csv')]+[bind(b['program']),bind(b['source'])]+[bind(r[k]) for k in ('actual_call','program','source_build','source_capture','source_archive','input_xml')]
    consumed += [stat(prefix/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv','summary.csv')]+[stat(root/q) for q in ('final_part533_typed22.bin','final_part533_layout.csv')]
    yields={int(q['part']):q for q in table(prefix/'summary.csv') if q['initial_material_group']=='all'};need(len(yields)==COUNT,'Actual-kappa prefix yield coverage differs')
    bundle=dict(spec=dict(tag=manifest['tag']+'_strict_prefix',source=SOURCE,group='psi0',actualAS=None,H=.072),root=prefix,done=d,source=True,geometry_profile='bedroles',count=COUNT,nodes=NODES,expected=np.arange(NODES,dtype=np.uint32),frames=frames,clocks=clocks,kw=old.f32(hyd.find('PoreWaterBulkModulus').get('value')),yield_rows=yields,runtime_observed=dict(passed=False,solver_completed=False,actual_exit=0,actual_Win32_exit=0))
    return bundle,tail,final,excluded[0],whole

def retained_control(bundle,consumed):
    """Descriptive old strict-source comparison; preserve both original header counts."""
    root=T/'outputs/c08_h18_bedroles_pre_r1/native_partial_r1';cp=T/'logs/c08_h18_bedroles_pre_r1.native_partial_r1.call.json';rp=T/'logs/c08_h18_bedroles_pre_r1.run.json';d=read(root/'completion.json');call=read(cp);run=read(rp)
    need(d['passed'] and d['samples']==208 and d['typed_arrays']==22 and d['native_IDs']==NODES and d['partial'] and not d['certified_PRE'] and d['max_scalar_clock_error_s']<=1e-14 and d['max_noninitial_signed_dterror_s']<=1e-14,'Retained strict source original native qualification differs')
    need(not run['passed'] and run['actual_exit']==run['actual_Win32_exit']==1 and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and same(call['arguments'][-1],root),'Retained actual source failure/reader completion differs')
    consumed += [stat(q) for q in (root/'completion.json',root/'typed22.bin',root/'typed22_layout.csv',root/'clocks.csv',cp,rp)]+[bind(run['actual_call']),bind(run['program']),bind(run['input_xml'])]
    raw=root/'typed22.bin';other=mapped_record(raw,root/'typed22_layout.csv',NODES,208);need(other.dtype==bundle['frames'].dtype,'Retained original literal22 dtype differs')
    oldclock=(root/'clocks.csv').read_bytes().splitlines(keepends=True);newclock=(bundle['root']/'clocks.csv').read_bytes().splitlines(keepends=True);need(len(oldclock)==209 and len(newclock)==COUNT+1,'Actual raw clock row coverage differs')
    records=[];first_difference=None
    with raw.open('rb') as oldraw,(bundle['root']/'typed22.bin').open('rb') as newraw:
        old_header=oldraw.read(12);new_header=newraw.read(12);need(struct.unpack('<III',old_header)==(NODES,22,208) and struct.unpack('<III',new_header)==(NODES,22,COUNT),'Native header counts must remain208/533')
        for part in range(208):
            left=oldraw.read(other.dtype.itemsize);right=newraw.read(other.dtype.itemsize);equal=left==right;clock_equal=oldclock[part+1]==newclock[part+1]
            row=dict(part=part,old_time_s=float(other[part]['time']),new_time_s=float(bundle['frames'][part]['time']),all22_and_time_bytes_equal=equal,signed_clock_row_bytes_equal=clock_equal)
            if first_difference is None and not(equal and clock_equal):
                first_difference=dict(part=part,record_payload_equal=equal,signed_clock_row_equal=clock_equal,fields=[])
                for name in other.dtype.names:
                    if other[part][name].tobytes()!=bundle['frames'][part][name].tobytes():
                        q=dict(field=name)
                        if name!='time':
                            mismatch=np.any(other[part][name].view('u1').reshape(NODES,-1)!=bundle['frames'][part][name].view('u1').reshape(NODES,-1),axis=1);q['first_native_ID']=int(np.flatnonzero(mismatch)[0]);q['different_native_IDs']=int(mismatch.sum())
                        first_difference['fields'].append(q)
            records.append(row)
    return records,dict(retained_source='c08_h18_bedroles_pre_r1',retained_count=208,new_prefix_count=COUNT,actual_shared_records=208,original_headers_preserved=True,raw_clock_header_equal=oldclock[0]==newclock[0],all208_record_payloads_equal=all(q['all22_and_time_bytes_equal'] for q in records),all208_signed_clock_rows_equal=all(q['signed_clock_row_bytes_equal'] for q in records),first_difference=first_difference,comparison_is_descriptive_not_physical_gate=True,no_new_solver_or_half=True)

def table_semicolon(p):
    with path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter=';'))

def particle_row(x,at,part,time,identity,initial,present=True):
    if not present:return dict(part=part,time_s=time,native_id=identity,present=False,x_m=None,z_m=None,dx_m=None,dz_m=None,p_Pa=None,native_p_minus_fixedP0_Pa=None,vx_m_s=None,vz_m_s=None,speed_m_s=None,kappa=None,J=None,n=None,rho_kg_m3=None,k_m_s=None,sigma_eff_xx_Pa=None,sigma_eff_zz_Pa=None,sigma_eff_xz_Pa=None,sigma_total_zz_Pa=None,FSType=None)
    p=float(x['PorePress'][at,0]);sk=x['SigmaState_kk'][at];pos=x['Posd'][at];vel=x['Vel'][at]
    return dict(part=part,time_s=time,native_id=identity,present=True,x_m=float(pos[0]),z_m=float(pos[2]),dx_m=float(pos[0]-initial[0]),dz_m=float(pos[2]-initial[2]),p_Pa=p,native_p_minus_fixedP0_Pa=float(x['ExcessPorePress'][at,0]),vx_m_s=float(vel[0]),vz_m_s=float(vel[2]),speed_m_s=float(np.linalg.norm(vel)),kappa=float(x['Kplastic'][at,0]),J=float(x['PoroVolumeRatio'][at,0]),n=float(x['PoroPorosity'][at,0]),rho_kg_m3=float(x['PoroMixtureDensity'][at,0]),k_m_s=float(x['PoroHydraulicConductivity'][at,0]),sigma_eff_xx_Pa=float(sk[0]),sigma_eff_zz_Pa=float(sk[2]),sigma_eff_xz_Pa=float(x['SigmaState_ij'][at,2]),sigma_total_zz_Pa=float(sk[2]-p),FSType=int(x['FSType'][at,0]))

def loss_history(bundle,tail,meta):
    initial=np.array(bundle['frames'][0]['Posd']);soil_initial=initial[FIXED:];dist=np.linalg.norm(soil_initial[:,(0,2)]-initial[LOST,(0,2)],axis=1);near=np.argsort(dist,kind='stable')[:9]+FIXED;need(LOST in near,'Lost original material point missing from initial neighbour set');tracks=[];geometry=[];first_below={};first=bundle['frames'][0]
    # analyze_case already validated every original22 field once; this second pass
    # computes the newly requested spatial/track diagnostics without another scan.
    states=[(p,bundle['frames'][p],float(bundle['clocks'][p]['time_s']),True) for p in range(COUNT)]
    states.append((533,tail,meta['time_s'],False))
    for part,x,time,complete in states:
        ids=x['Idp'][:,0];index={int(v):i for i,v in enumerate(ids)};soil=ids>=FIXED;pos=x['Posd'][soil];sid=ids[soil];tree=old.cKDTree(pos[:,(0,2)]);distance,unused=tree.query(pos[:,(0,2)],k=2,workers=1);nn=distance[:,1]/old.DP;pairs=tree.query_pairs(.7*old.DP,output_type='ndarray');pairs_count=int(np.count_nonzero(np.linalg.norm(pos[pairs[:,0]]-pos[pairs[:,1]],axis=1)<.7*old.DP)) if len(pairs) else 0
        below=sid[pos[:,2]<0];geometry.append(dict(part=part,time_s=time,complete_original_material_set=complete,present_soil=int(soil.sum()),missing_soil=0 if complete else 1,min_z_m=float(pos[:,2].min()),min_x_m=float(pos[:,0].min()),soil_below_bed=int(below.size),NN_min_over_dp=float(nn.min()),NN_q05_over_dp=float(np.quantile(nn,.05)),NN_median_over_dp=float(np.median(nn)),pairs_r_lt_0p7dp=pairs_count))
        for identity in below:
            if int(identity) not in first_below:first_below[int(identity)]=dict(part=part,time_s=time,z_m=float(pos[np.flatnonzero(sid==identity)[0],2]))
        for identity in near:tracks.append(particle_row(x,index.get(int(identity)),part,time,int(identity),initial[identity],int(identity) in index))
        if not complete:
            ordered=ids.astype(int);need(np.array_equal(x['PorePress0'][:,0].view('<u4'),first['PorePress0'][ordered,0].view('<u4')) and np.array_equal(x['ExcessPorePress'][:,0],np.float32(x['PorePress'][:,0]-x['PorePress0'][:,0])),'Incomplete final fixed-P0/excess is not modified')
            need(np.all(x['Kplastic'][:,0]>=bundle['frames'][COUNT-1]['Kplastic'][ordered,0]),'Incomplete final present-ID kappa decreases')
    return tracks,geometry,dict(initial_neighbour_IDs=[int(q) for q in near],initial_neighbour_selection='Lost3060 plus eight smallest initial Euclidean x/z material distances; ties use originalID order',first_saved_below_bed_by_ID={str(k):v for k,v in first_below.items()},lost_point_first_saved_below_bed=first_below.get(LOST),first_saved_near_pair=next((q for q in geometry if q['pairs_r_lt_0p7dp']>0),None),saved_observations_not_first_unsaved_crossings=True)

def final_population(tail,bundle,meta):
    ids=tail['Idp'][:,0];mask=ids>=FIXED;present=ids[mask].astype(int);pos=tail['Posd'][mask];v=tail['Vel'][mask].astype(float);p=tail['PorePress'][mask,0].astype(float);sk=tail['SigmaState_kk'][mask];si=tail['SigmaState_ij'][mask];speed=np.linalg.norm(v,axis=1);initial=bundle['frames'][0]['Posd'][present];du=pos-initial;rho=tail['PoroMixtureDensity'][mask,0];volume=tail['PoroCurrentVolume'][mask,0];por=tail['PoroPorosity'][mask,0];J=tail['PoroVolumeRatio'][mask,0];kap=tail['Kplastic'][mask,0];ex=tail['ExcessPorePress'][mask,0].astype(float);need(len(present)==4999,'Incomplete final has exactly4999 present original soil IDs')
    total=sk-p[:,None];row=dict(part=533,time_s=meta['time_s'],present_soil=4999,original_soil=5000,missing_soil=1,missing_native_id=LOST,p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),native_p_minus_fixedP0_RMS_Pa=float(np.sqrt(np.mean(ex*ex))),velocity_RMS_m_s=float(np.sqrt(np.mean(speed*speed))),max_speed_m_s=float(speed.max()),effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(sk*sk,axis=1)+2*np.sum(si*si,axis=1)))),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(total*total,axis=1)+2*np.sum(si*si,axis=1)))),current_mixture_KE_J_per_m=float(.5*np.sum(rho*volume*speed*speed)),current_pressure_storage_quadratic_J_per_m=float(.5*np.sum(por*volume/bundle['kw']*p*p)),max_kappa=float(kap.max()),min_J=float(J.min()),max_J=float(J.max()),min_soil_z_m=float(pos[:,2].min()),mean_settlement_reference_mm=float(-1000*du[:,2].mean()),negative_p_soil=int(np.count_nonzero(p<0)))
    layers=[]
    for z in np.unique(bundle['frames'][0]['Posd'][FIXED:,2]):
        at=initial[:,2]==z;layers.append(dict(part=533,time_s=meta['time_s'],initial_z_m=float(z),present_IDs=int(at.sum()),original_layer_IDs=100,missing_IDs=100-int(at.sum()),p_mean_Pa=float(p[at].mean()),effective_zz_mean_Pa=float(sk[at,2].mean()),total_zz_mean_Pa=float(total[at,2].mean()),velocity_RMS_m_s=float(np.sqrt(np.mean(speed[at]**2))),mean_settlement_reference_mm=float(-1000*du[at,2].mean()),mean_J=float(J[at].mean()),max_kappa=float(kap[at].max())))
    return row,layers

def forensic_plot(tracks,geometry,excluded,prefix):
    fig,axes=old.plt.subplots(3,3,figsize=(14,11),layout='constrained');panels=(('z_m','Material z [m]',1.),('speed_m_s','Speed [m/s]',1.),('p_Pa','Absolute p [kPa]',.001),('native_p_minus_fixedP0_Pa','Native p-fixed P0 [kPa]',.001),('kappa','Kappa',1.),('J','J',1.),('sigma_total_zz_Pa','Total sigma_zz [kPa]',.001))
    for ax,(key,title,scale) in zip(axes.flat,panels):
        for i,identity in enumerate(sorted({q['native_id'] for q in tracks})):
            rr=[q for q in tracks if q['native_id']==identity and q['present']];ax.plot([q['time_s'] for q in rr],[q[key]*scale for q in rr],label=str(identity),lw=1.6 if identity==LOST else .7,alpha=1. if identity==LOST else .55)
        ax.set(title=title,xlabel='Actual source time [s]');ax.grid(alpha=.2)
    axes.flat[0].axhline(0,color='k',ls='--',lw=.7);axes.flat[0].plot(float(excluded['time_s']),float(excluded['z_m']),'rx',label='3060 excluded record')
    for key,ax,title in [('NN_min_over_dp',axes.flat[7],'Minimum nearest distance / dp'),('pairs_r_lt_0p7dp',axes.flat[8],'Pairs at r < .7 dp')]:ax.plot([q['time_s'] for q in geometry],[q[key] for q in geometry]);ax.set(title=title,xlabel='Actual source time [s]');ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=6,ncol=2);fig.suptitle('Failed source: lost3060 and its eight initial material neighbours\nFinal7059 state is separate, missing3060 is not padded or interpolated; no repair/acceptance claim');dest=Path(str(prefix)+'_loss_tracks.png');fig.savefig(dest,dpi=170);old.plt.close(fig);return dest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root full-read before unique offline analysis');m=read(a.manifest);tag=m['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag),'Safe fresh tag required');prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'_*')),'Existing full/partial analysis protected');consumed=[stat(a.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(old.__file__),stat(plastic.__file__)];result=dict(stage=TAG,analysis_complete=False,whole_run_passed=False,certified_PRE=False,physical_acceptance=False,source_equilibrium_accepted=False,consumed=consumed)
    try:
        bundle,tail,meta,excluded,whole=load(m,consumed);analysis=old.analyze_case(bundle);control_rows,control=retained_control(bundle,consumed);tracks,geometry,events=loss_history(bundle,tail,meta);final_summary,final_layers=final_population(tail,bundle,meta);files=[]
        for key in ('history','extrema','layers','tracks'):
            dest=Path(str(prefix)+'_prefix_'+key+'.csv');old.write_csv(dest,analysis[key]);files.append(dest)
        for name,rows in [('loss_tracks',tracks),('geometry',geometry),('excluded',[excluded]),('retained_control',control_rows),('final_summary',[final_summary]),('final_layers',final_layers)]:dest=Path(str(prefix)+'_'+name+'.csv');old.write_csv(dest,rows);files.append(dest)
        final_rows=[particle_row(tail,i,533,meta['time_s'],int(identity),bundle['frames'][0]['Posd'][identity]) for i,identity in enumerate(tail['Idp'][:,0])];dest=Path(str(prefix)+'_final_present.csv');old.write_csv(dest,final_rows);files.append(dest)
        files+=plastic.source_plots([analysis],Path(str(prefix)+'_prefix'));files.append(forensic_plot(tracks,geometry,excluded,prefix));need(all(stat(q['path'])==q for q in consumed),'Sealed source/native inputs changed')
        result.update(analysis_complete=True,strict_prefix_samples=COUNT,strict_prefix_IDs=NODES,actual_saved_total=534,incomplete_final_present_IDs=7059,incomplete_final_missing_IDs=[LOST],strict_prefix_summary=analysis['summary'],incomplete_final_metadata=meta,incomplete_final_present_population_summary=final_summary,retained_strict_control=control,events=events,excluded_record=excluded,all_actual_saved_frames_accounted_for=True,final_not_added_to_constant_material_means=True,native_excess_is_fixed_P0_difference_not_paper_equivalence=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
