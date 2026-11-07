"""Independent smoke/off/short reviews of sealed explicit6805/6800 native outputs; no follow-on."""
import argparse,csv,json,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_plane_window_review_r1 as w
from upl_c08_fsmask_r1 import SCHEMA,TYPES

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_bedkeep_short_review_r1';BED=(1800,1852,1904,1956,2008)
# tag, actual backend, keep, actual active N, actual frames, completed global end.
CASES={'CPU':('upl_c08_bedkeep_smoke_CPU_r1','CPU',True,6805,1,4000040),
       'GPU':('upl_c08_bedkeep_smoke_GPU_r1','GPU',True,6805,1,4000040),
       'OFF':('upl_c08_bedkeep_off_GPU_r1','GPU',False,6800,3,4012000),
       'SHORT':('upl_c08_bedkeep_short_GPU_r1','GPU',True,6805,3,4012000),
       'OLD':('upl_c08_asplane_short_GPU_r1','GPU',False,6800,3,4012000)}
PHASES={'smoke':('CPU','GPU'),'off':('OLD','OFF'),'short':('OLD','SHORT')};need,read,stat=w.need,w.read,w.stat

def bind(e):need(stat(Path(e['path']))==e,'Closed file identity changed: '+e['path']);return e
def table(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def csvout(prefix,leaf,rows):
    need(rows,'Empty derived '+leaf+' table');p=Path(str(prefix)+'_'+leaf+'.csv')
    with p.open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
    return p

def load_case(label,before):
    tag,backend,keep,n,frames,end=CASES[label];folder=T/'outputs'/tag/'native';cp=L/(tag+'.native.json');c=read(cp);before.append(stat(cp))
    need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'] and c['expected_AS'],'Passed bound native receipt required: '+label)
    if label!='OLD':need(c['keep_bed_overlap']==keep and c['expected_active_native_IDs']==n,'Explicit native6805/6800 policy differs')
    run=read(Path(bind(c['source_run'])['path']));before.append(c['source_run']);need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['actual_steps']==end and run['saved_frames']==frames and run['target_backend']==backend and run['ArtificialStress'] and run['consumed_stats_unchanged'],'Actual completed backend/window differs')
    if label!='OLD':need(run['keep_bed_overlap']==keep and run['expected_active_native_IDs']==n and run['expected_retired_wall_IDs']==(255 if keep else 260) and run['expected_kept_bed_IDs']==(list(BED) if keep else []),'Actual explicit release plan differs')
    call=read(Path(bind(run['actual_call'])['path']));before.append(run['actual_call']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['actual_solver_Win32_exit']==0 and not call['ownership_errors'],'Actual solver/tool exits differ')
    if label=='GPU':need(run['memcheck_zero_errors_and_leaks'],'GPU Debug real memcheck closure required')
    for key in ('program','source_build','source_pre_file','input_xml'):before.append(bind(run[key]))
    build=read(Path(run['source_build']['path']));need(build['passed'] and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and (build['program']['bytes'],build['program']['mtime_ns'])==(run['program']['bytes'],run['program']['mtime_ns']),'Executed program/build binding differs')
    need(Path(bind(c['completion'])['path']).samefile(folder/'completion.json'),'Completion path differs');before.append(c['completion']);rc=read(Path(bind(c['actual_call'])['path']));before.append(c['actual_call']);need(rc['actual_Popen_wait_exit']==rc['actual_Win32_exit']==0 and rc['ownership_failure'] is None,'Actual unique reader exit differs')
    for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv'):before.append(bind(next(e for e in c['outputs'] if Path(e['path']).samefile(folder/leaf))))
    mp=folder/('bedkeep_metadata.json' if keep else 'AS_metadata.json');need(Path(bind(c['AS_metadata'])['path']).samefile(mp),'Typed policy adapter binding differs');before.append(c['AS_metadata']);m=read(mp);d=read(folder/'completion.json');fixed=1805 if keep else 1800
    expected=dict(samples=frames,completed_steps=end,typed_arrays=22,typed_bytes_per_particle=212,original_ID_domain=7060,actual_native_IDs_per_frame=n,soil_IDs=5000,ledger_checks=5000*frames,fixed_marker_checks=fixed*frames,P0_bits_checks=n*frames,rho_cache_bits_checks=5000*frames,kappa_nondecreasing_from_PRE_checks=5000*frames,nonempty_signed_intervals=frames,plane_gap_checks=10000*frames)
    need(d['passed'] and all(d[k]==v for k,v in expected.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['completed_runtime_Run_csv_checked'],'Original native guards/policy/normal completion differ')
    need(d['geometry_tolerance_m']==w.TOL and d['min_soil_x_m']>=-w.TOL and d['min_soil_z_m']>=-w.TOL,'Original fixed-plane geometry guard differs')
    need(m['passed'] and m['expected_AS'] and m['samples']==m['metadata_header_scans']==m['AS_active_true_headers']==frames and m['completed_steps']==end and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==float(np.float32(2.55)),'Original all-header AS coverage differs')
    if keep:
        need(d['stage']=='upl_c08_bedkeep_native_r1' and d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and not d['actual_retired_IDs_contiguous'] and d['kept_bed_IDs']==list(BED) and d['kept_bed_count']==5 and d['actual_fixed_IDs']==1805 and d['kept_bed_source_geometry_checks']==5 and 'retired_ID_count' not in d,'Explicit noncontiguous retirement differs')
        need(m['stage']=='upl_c08_bedkeep_native_r1.metadata' and m['keep_bed_overlap'] and m['original_target_count']==260 and m['actual_retired_count']==255 and m['kept_bed_IDs']==list(BED) and m['kept_bed_count']==5 and m['keep_policy_headers']==frames and m['AS_policy']=='ReleaseOnly' and not m['core_original_numerical_budgets_changed'],'Original KeepBedOverlap typed metadata differs')
    else:need(d['stage']=='upl_c08_plane_native_r1' and d['retired_ID_begin']==1800 and d['retired_ID_count']==260 and m['stage']=='upl_c08_as_plane_native_r2' and m['AS_policy_when_enabled']=='ReleaseOnly' and not m['core_numerical_guards_modified'],'OFF/reference must retain the original6800 adapter')
    layout=table(folder/'typed22_layout.csv');need(len(layout)==22,'Exactly22 original fields required');fields=[('time','<f8')]
    for row,(name,kind,width) in zip(layout,SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Original22 schema differs');fields.append((name,TYPES[kind],(n,width)))
    dtype=np.dtype(fields);need(dtype.itemsize==8+n*212,'Actual typed stride differs')
    with (folder/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(n,22,frames),'Actual6805/6800 header differs; no adaptation or rewrite')
    need((folder/'typed22.bin').stat().st_size==12+frames*dtype.itemsize,'Actual payload length differs');a=np.memmap(folder/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(frames,));clock=table(folder/'clocks.csv');history=table(folder/'history.csv');need(len(clock)==len(history)==frames,'Actual clock/history coverage differs')
    fixedids=np.sort(np.r_[np.arange(1800),BED]).astype('uint32') if keep else np.arange(1800,dtype='uint32');ids=np.r_[fixedids,np.arange(2060,7060,dtype='uint32')];need(len(ids)==n,'Explicit expected ID cardinality differs');cadence=40 if frames==1 else 4000
    for part,x in enumerate(a):need(np.array_equal(x['Idp'][:,0],ids) and float(clock[part]['time_s'])==x['time'] and int(clock[part]['completed_step'])==4000000+(part+1)*cadence and int(clock[part]['completed_step'])==int(clock[part]['saved_step'])+1 and int(clock[part]['native_IDs'])==n and clock[part]['dterror_interval_empty']=='0' and np.isfinite(float(clock[part]['signed_dterror_s'])) and float(clock[part]['signed_dterror_s'])<=1e-14,'Original material IDs/actual clocks/signed intervals differ')
    return dict(a=a,d=d,clock=clock,history=history,folder=folder,keep=keep,label=label)

def compare(left,right,title):
    need(len(left['a'])==len(right['a']) and left['d']['source_actual_time_s']==right['d']['source_actual_time_s'],'Actual windows/PRE clocks differ');rows=[]
    for part,(x,y) in enumerate(zip(left['a'],right['a'])):
        need(int(left['clock'][part]['completed_step'])==int(right['clock'][part]['completed_step']) and abs(float(x['time'])-float(y['time']))<=1e-14,'Only actual same-step/time comparisons are admitted')
        sx=x['Idp'][:,0]>=2060;sy=y['Idp'][:,0]>=2060;need(np.array_equal(x['Idp'][sx],y['Idp'][sy]) and int(sx.sum())==int(sy.sum())==5000,'All original soil material IDs must match')
        dp=y['PorePress'][sy].astype(float)-x['PorePress'][sx].astype(float);du=(y['Posd'][sy]-x['Posd'][sx])*1000;xd,xo=w.total(x);yd,yo=w.total(y);dd=yd[sy]-xd[sx];do=yo[sy]-xo[sx]
        q=dict(comparison=title,part=part,completed_step=int(left['clock'][part]['completed_step']),left_time_s=float(x['time']),right_time_s=float(y['time']),pressure_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),pressure_max_abs_difference_Pa=float(np.abs(dp).max()),material_XYZ_max_difference_mm=float(np.abs(du).max()),total_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(dd*dd,axis=1)+2*np.sum(do*do,axis=1)))))
        for key,field in (('velocity','Vel'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity')):q[key+'_max_abs_difference']=float(np.abs(y[field][sy].astype(float)-x[field][sx].astype(float)).max())
        rows.append(q)
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('phase',choices=tuple(PHASES));ap.add_argument('--execution-authorized',action='store_true');arg=ap.parse_args();need(arg.execution_authorized,'Root full-read and explicit single-phase execution required');prefix=T/'figures'/(TAG+'_'+arg.phase);need(not list(prefix.parent.glob(prefix.name+'*')),'Existing completed/partial phase protected; no repeat')
    before=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md')),stat(Path(w.__file__)),stat(T/'support/upl_c08_fsmask_r1.py')];cases={k:load_case(k,before) for k in PHASES[arg.phase]};left,right=cases.values();matched=compare(left,right,arg.phase);exact=[]
    if arg.phase=='smoke':need(matched[0]['pressure_RMS_difference_Pa']<=5 and matched[0]['material_XYZ_max_difference_mm']<=.005,'Original DebugCPU/GPU pressure/material budgets failed')
    if arg.phase=='off':
        for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
            same=(left['folder']/leaf).read_bytes()==(right['folder']/leaf).read_bytes();exact.append(dict(scope='entire_original_file',part='',field=leaf,byte_exact=same));need(same,'Keepfalse/default exact control differs: '+leaf)
        for part,(x,y) in enumerate(zip(left['a'],right['a'])):
            for name in ('time',*[q[0] for q in SCHEMA]):same=x[name].tobytes()==y[name].tobytes();exact.append(dict(scope='actual_record_field',part=part,field=name,byte_exact=same));need(same,'Original record field bytes differ')
    history=[]
    for label,v in cases.items():
        for part,x in enumerate(v['a']):
            soil=x['Idp'][:,0]>=2060;p=x['PorePress'][soil,0].astype(float);vel=x['Vel'][soil].astype(float);sd,so=w.total(x)
            history.append(dict(case=label,part=part,time_s=float(x['time']),tau_s=float(x['time'])-v['d']['source_actual_time_s'],completed_step=int(v['clock'][part]['completed_step']),native_N=len(x['Idp']),kept_bed_count=5 if v['keep'] else 0,p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(sd[soil]*sd[soil],axis=1)+2*np.sum(so[soil]*so[soil],axis=1)))),speed_RMS_m_s=float(np.sqrt(np.mean(np.sum(vel*vel,axis=1)))),speed_max_m_s=float(np.sqrt(np.sum(vel*vel,axis=1)).max()),mean_material_settlement_double_PRE_mm=-1000*float(v['history'][part]['mean_dz_from_PRE_m']),min_soil_z_m=float(x['Posd'][soil,2].min()),max_kappa=float(x['Kplastic'][soil,0].max()),J_min=float(x['PoroVolumeRatio'][soil,0].min()),J_max=float(x['PoroVolumeRatio'][soil,0].max()),signed_dterror_s=float(v['clock'][part]['signed_dterror_s'])))
    files=[csvout(prefix,'history',history),csvout(prefix,'matched',matched)]
    if exact:files.append(csvout(prefix,'byte_exact',exact))
    fig,axs=plt.subplots(2,3,figsize=(13,7),layout='constrained');specs=(('p_RMS_Pa','Absolute pressure RMS [kPa]',.001),('total_stress_Frobenius_RMS_Pa','Total stress RMS [kPa]',.001),('mean_material_settlement_double_PRE_mm','Mean material settlement [mm]',1),('speed_max_m_s','Maximum speed [m/s]',1),('min_soil_z_m','Minimum soil z [mm]',1000),('max_kappa','Maximum plastic history',1))
    for ax,(key,title,scale) in zip(axs.flat,specs):
        for label in cases:
            rr=[r for r in history if r['case']==label];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],marker='o',ms=4,label=label)
        ax.set(title=title,xlabel='Actual time since PRE [s]');ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle('KeepBedOverlap '+arg.phase+': bounded implementation checks; no theory/half/full-collapse claim');png=Path(str(prefix)+'.png');fig.savefig(png,dpi=160);plt.close(fig);files.append(png)
    need(all(stat(Path(e['path']))==e for e in before),'Consumed sealed phase inputs changed')
    result=dict(stage=TAG,phase=arg.phase,passed=True,explicit_scope='6805 kept5 or original6800 only; all5000 soil IDs',case_tags={k:CASES[k][0] for k in cases},actual_common_step_time_pairs=len(matched),CPU_GPU_budget_applied=(arg.phase=='smoke'),CPU_GPU_pressure_budget_Pa=5 if arg.phase=='smoke' else None,CPU_GPU_material_budget_mm=.005 if arg.phase=='smoke' else None,keepfalse_full22_layout_and_clock_file_byte_exact=(arg.phase=='off'),signed_dterror_compared_in_exact_clock_file=(arg.phase=='off'),keeptrue_vs_old_is_descriptive=(arg.phase=='short'),physical_acceptance=False,reaction_J_Darcy_closed=False,no_automatic_next_phase=True,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,matched=matched,consumed=before,files=[stat(p) for p in files])
    with Path(str(prefix)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('BEDKEEP_PHASE_REVIEW_COMPLETED',arg.phase,str(prefix)+'.check.json',flush=True)

if __name__=='__main__':main()
