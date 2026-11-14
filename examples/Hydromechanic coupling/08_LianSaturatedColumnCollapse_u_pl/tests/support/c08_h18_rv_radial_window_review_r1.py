"""Offline radial window91 comparison only; no solver/reader/VTK/build or next job."""
import argparse,csv,json,math,struct
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import c08_h18_storage_review_r2 as typed
import c08_h18_rv_radial_gpu_run_r1 as radial
core=typed.core
T,L=typed.T,typed.L
need,read,stat,bind,entry,owned,same=typed.need,typed.read,typed.stat,typed.bind,typed.entry,typed.owned,typed.same
TAG='c08_h18_rv_radial_window_review_r1';NOTE=T/'notes'/(TAG+'.md')
RUN=L/'c08_h18_rv_radial_window_GPU_r1.run.json'
NATIVE=L/'c08_h18_rv_radial_window_GPU_r1.native_r1.check.json'
OLD_GATE=L/'c08_h18_rv_window_review_r1.check.json'
BASE,END,COUNT,N,DP=2000000,2180000,91,5000,.04
SELECTED=(38,76,90)
CASES=('Retained original AS03','Vector RV alpha0.1','Radial RV alpha0.1')
THRESHOLDS=((.7,'0p7'),(.5,'0p5'),(.3,'0p3'))
def bits(v):return struct.pack('<d',float(v))
def write_csv(path,rows):
    need(rows,'No empty scientific table')
    with path.open('x',encoding='utf-8',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def file_entry(gate,leaf):
    q=[e for e in gate['files']if Path(e['path']).name==leaf];need(len(q)==1,'One sealed reference file required: '+leaf);return bind(q[0])
def receiver_done(done):
    need(done['passed'] and done['stage'] == 'c08_h18_wend_native_r1.receiver'
         and done['samples'] == COUNT and done['completed_steps'] == END
         and done['typed_arrays'] == 22 and done['typed_bytes_per_particle'] == 212,
         'Original complete window91 typed22 native qualification required')
    coverage = dict(actual_native_IDs_per_frame=6805, actual_fixed_IDs=1805, soil_IDs=N,
        ledger_checks=COUNT*N, fixed_marker_checks=COUNT*1805, P0_bits_checks=COUNT*6805,
        rho_cache_bits_checks=COUNT*N, kappa_nondecreasing_from_PRE_checks=COUNT*N,
        plane_gap_checks=COUNT*10000, nonempty_signed_intervals=COUNT)
    need(all(done[k] == v for k, v in coverage.items()), 'Original full IDs/ledger/marker/history/clock coverage differs')
    need(done['max_scalar_clock_error_s'] <= 1e-14 and done['max_ledger_relative_error'] <= 5e-13
         and done['max_signed_dterror_s'] <= 1e-14 and done['FS23_pressure_checks'] > 0,
         'Original signed/clock/ledger/active-FS numerical gate failed')
    need(done['geometry_profile'] == 'bedroles' and not done['keep_bed_overlap']
         and done['release_target_ID_begin'] == 1805 and done['release_target_ID_count'] == 255
         and done['actual_retired_count'] == 255 and done['actual_retired_IDs_contiguous']
         and done['retained_fixed_ID_begin'] == 0 and done['retained_fixed_ID_count'] == 1805
         and done['DynamicNoPenetrationPolicy'] == 'FixedPlaneStageProjectionReleaseOnly'
         and done['DynamicNoPenetrationActive'] is True and done['DynamicNoPenetrationReactionClosed'] is False
         and done['geometry_tolerance_m'] == 4e-8 and done['min_soil_x_m'] >= -4e-8 and done['min_soil_z_m'] >= -4e-8,
         'Original bed-role/plane/reaction scope differs')
    need(done['source_handoff_schema'] == done['source_material_law_version'] == done['target_material_law_version'] == 2
         and done['same_material_plastic_PRE'] and not done['source_elastic'] and done['source_PREs_read'] == 1,
         'Actual unchanged same-material schema2 PRE/history contract required')



def load_inputs(consumed):
    run,native,gate=read(RUN),read(NATIVE),read(OLD_GATE)
    need(run['passed'] and run['solver_completed'] and run['profile']=='window' and run['actual_steps']==END and run['saved_frames']==COUNT
         and run['consumed_stats_unchanged'] and run['actual_exit']==run['actual_Win32_exit']==run['actual_tool_exit']==0
         and run['RV_requested'] is True and run['environment_override']=={'C08_RV_RADIAL_H18':'1'}
         and run['policy_schema']==3 and run['RV_operator']=='compression_only_radial_residual_limiter','Completed new radial owned window required')
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1 and entry(native,'source_run')==stat(RUN),'One passed actual radial native receipt required')
    consumed.extend(bind(q)for q in native['files'])
    need(gate['passed'] and gate['analysis_complete'] and gate['consumed_stats_unchanged'] and not gate['physical_acceptance'],'Sealed vector/original scientific reference required')
    runs=[read(entry(gate,'reference_run')['path']),read(entry(gate,'source_run')['path']),run]
    natives=[read(entry(gate,'reference_native')['path']),read(entry(gate,'native_receipt')['path']),native]
    bundles=[];doneall=[];timing=[]
    for label,r,q in zip(CASES,runs,natives):
        need(r['passed'] and r['solver_completed'] and r['actual_steps']==END and r['saved_frames']==COUNT and q['passed'] and q['consumed_stats_unchanged'] and q['reader_invocations']==1,'All three genuinely complete91-frame trajectories required')
        d=entry(q,'native_completion');done=read(d['path']);receiver_done(done);doneall.append(done)
        for k in ('source_pre_file','source_native','planned_steps'):need(r[k]==run[k],'Actual common PRE/clock contract differs: '+k)
        nroot=Path(d['path']).parent
        if label!=CASES[2]:
            for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
                expected=[e for e in gate['consumed']if same(e['path'],nroot/leaf)]
                need(expected and all(e==expected[0]for e in expected),'One unchanged original sealed reference stat required: '+str(nroot/leaf))
                consumed.append(bind(expected[0]))
        bundles.append(typed.typed(nroot,6805,COUNT,consumed));consumed.append(d)
        loop=float(r['summary']['TSimul']);total=float(r['summary']['TTotal']);need(math.isfinite(loop)and loop>0 and math.isfinite(total)and total>0,'Actual positive observed timing required')
        timing.append(dict(case=label,new_receiver_updates=180000,TSimul_loop_s=loop,TTotal_program_s=total,Hardware=r['summary']['Hardware'],new_updates_per_TSimul_s=180000/loop,controlled_benchmark=False))
    for label,b in zip(CASES,bundles):
        need((b['root']/'typed22_layout.csv').read_bytes()==(bundles[0]['root']/'typed22_layout.csv').read_bytes(),'Actual compared layouts differ')
        for part,clock in enumerate(b['clocks']):
            step=END if part==90 else BASE+1+2000*part;reference=bundles[0]['clocks'][part]
            need(int(clock['part'])==part and int(clock['completed_step'])==step and int(clock['saved_step'])==step-1
                 and bits(clock['time_s'])==bits(reference['time_s'])==bits(b['frames'][part]['time'])
                 and float(clock['dt_s'])==5e-6 and float(clock['signed_dterror_s'])<=1e-14
                 and clock['dterror_interval_empty']=='0' and int(clock['native_IDs'])==6805,'All91 actual same-time/Step/signed records required; no interpolation')
            need(np.array_equal(b['frames'][part]['Idp'][:,0],b['expected']),'All6805 original IDs required')
    for key in ('program','source_build','source_capture','source_archive','input_xml','native_profile','planned_steps'):
        consumed.append(entry(run,key))
    build=read(entry(run,'source_build')['path']);need(build['passed'] and build['consumed_stats_unchanged'] and build['policy_schema']==3
         and build['retained_original_objects']==112 and build['private_objects']==2 and build['actual_link_objects']==114
         and build['program']==run['program'] and build['source_capture']==run['source_capture'] and build['private_sources']==run['private_sources'],'Actual bound radial implementation build required')
    consumed.extend(bind(e)for e in run['private_sources'].values())
    nc=entry(native,'actual_call');owned(read(nc['path']));rc=entry(run,'actual_call');owned(read(rc['path']))
    consumed.extend([stat(RUN),stat(NATIVE),stat(OLD_GATE),nc,rc,entry(gate,'source_run'),entry(gate,'native_receipt'),entry(gate,'reference_run'),entry(gate,'reference_native'),entry(run,'source_native')])
    source=read(entry(run,'source_native')['path']);need(source['passed']and source['certified_PRE']and source['completed_steps']==BASE and bits(source['actual_end_s'])==bits(gate['actual_source_time_s']),'Actual original source reference differs')
    cohort=file_entry(gate,'c08_h18_rv_window_review_r1_source_cohorts.csv');rows=typed.table(cohort['path']);need(len(rows)==N,'All5000 sealed source cohorts required')
    ids=np.array([int(q['native_id'])for q in rows],dtype=np.uint32);need(np.array_equal(ids,np.arange(2060,7060,dtype=np.uint32)),'Actual original source ID order differs')
    initial=np.array([[float(q['initial_'+a+'_m'])for a in 'xyz']for q in rows]);pre=np.array([[float(q['PRE_'+a+'_m'])for a in 'xyz']for q in rows]);layer=np.array([int(q['initial_layer'])for q in rows]);top=np.array([q['fixed_initial_top_ID']=='True'for q in rows]);bottom=np.array([q['fixed_initial_bottom_ID']=='True'for q in rows])
    need(np.all(np.bincount(layer)==100) and set(layer)==set(range(50)) and top.sum()==bottom.sum()==100 and np.array_equal(top,layer==49) and np.array_equal(bottom,layer==0),'Sealed fixed initial material layers/cohorts differ')
    p0=np.array(bundles[0]['frames'][0]['PorePress0'][:,0],dtype='<f4');soilp0=np.array([float(q['fixed_P0_Pa'])for q in rows],dtype='<f4')
    need(np.array_equal(p0[-N:].view('<u4'),soilp0.view('<u4')),'Sealed source soilP0 bits differ')
    ref=dict(ids=ids,initial=initial,pos=pre,p0all=p0,pre_kappa=np.array([float(q['inherited_PRE_kappa'])for q in rows]),time=float(source['actual_end_s']),layer=layer,top=top,bottom=bottom)
    consumed.append(cohort)
    prep_entry=entry(run,'preparation');prep=read(prep_entry['path']);need(prep['passed']and prep['consumed_stats_unchanged'],'Actual radial preparation required')
    # Pure new87/57/6 checker only; no old66/vector-gate import or call.
    telemetry=radial.telemetry(Path(run['output']),radial.JOBS['window'],prep)
    for key in ('rv_policy','rv_sidecar','rv_manufactured','rv_fixtures'):
        need(telemetry[key]==entry(run,key),'Actual new radial sidecar binding differs: '+key);consumed.append(entry(run,key))
    consumed.append(prep_entry)
    return run,bundles,ref,source,timing,telemetry

def nearest(pos):
    tree = cKDTree(pos)
    _, indices = tree.query(pos, k=2, workers=1)
    lengths = np.linalg.norm(pos[indices]-pos[:, None, :], axis=-1)
    raw_nn = np.min(np.where(indices != np.arange(N)[:, None], lengths, np.inf), axis=1)
    nn = raw_nn/DP
    need(np.isfinite(nn).all() and np.all(nn >= 0), 'Every original soil node needs a finite nonself nearest neighbor')
    pairs = tree.query_pairs(.7*DP, output_type='ndarray')
    distances = np.linalg.norm(pos[pairs[:, 0]]-pos[pairs[:, 1]], axis=-1) if len(pairs) else np.empty(0)
    counts = {}
    for cutoff, label in THRESHOLDS:
        close = distances < cutoff*DP; selected = pairs[close]
        nodes = int(np.count_nonzero(raw_nn < cutoff*DP))
        unique_nodes = len(np.unique(selected)) if len(selected) else 0
        need(nodes == unique_nodes, 'Independent NN-node and unique-close-pair endpoints differ')
        counts['NN_nodes_lt_'+label+'dp'] = nodes
        counts['unique_pairs_lt_'+label+'dp'] = int(np.count_nonzero(close))
    return nn, counts


def physical_frame(frame, clock, label, ref, last_kappa):
    soil = frame['Idp'][:, 0] >= 2060; ids = frame['Idp'][soil, 0]
    need(np.array_equal(ids, ref['ids']) and np.count_nonzero(soil) == N
         and np.array_equal(frame['PorePress0'][:, 0].view('<u4'), ref['p0all'].view('<u4')),
         'All actual original soil IDs/fixed P0 bits required')
    expected_excess = np.asarray(frame['PorePress'][:, 0]-frame['PorePress0'][:, 0], dtype='<f4')
    need(np.array_equal(frame['ExcessPorePress'][:, 0].view('<u4'), expected_excess.view('<u4')), 'Original native float(p-fixedP0) definition differs')
    pos = np.array(frame['Posd'][soil]); v = frame['Vel'][soil].astype(float)
    p = frame['PorePress'][soil, 0].astype(float); p0 = frame['PorePress0'][soil, 0].astype(float)
    excess = frame['ExcessPorePress'][soil, 0].astype(float); kap = frame['Kplastic'][soil, 0].astype(float)
    need(np.all(kap >= ref['pre_kappa']) and (last_kappa is None or np.all(kap >= last_kappa)), 'Original material kappa history decreased')
    J = np.array(frame['PoroVolumeRatio'][soil, 0]); n = np.array(frame['PoroPorosity'][soil, 0])
    k = np.array(frame['PoroHydraulicConductivity'][soil, 0]); rho = np.array(frame['PoroMixtureDensity'][soil, 0])
    kk = np.array(frame['SigmaState_kk'][soil]); ij = np.array(frame['SigmaState_ij'][soil]); total = kk-p[:, None]
    effective_norm = np.sqrt(np.sum(kk*kk, axis=1)+2*np.sum(ij*ij, axis=1))
    total_norm = np.sqrt(np.sum(total*total, axis=1)+2*np.sum(ij*ij, axis=1))
    speed = np.linalg.norm(v, axis=1); du = pos-ref['pos']; settlement = -1000*du[:, 2]
    ft = frame['FSType'][soil, 0]; fs = (ft == 2)|(ft == 3)
    nn, counts = nearest(pos)
    row = dict(case=label, part=int(clock['part']), completed_step=int(clock['completed_step']),
        actual_time_s=float(frame['time']), tau_s=float(frame['time'])-ref['time'],
        signed_dterror_s=float(clock['signed_dterror_s']), dterror_interval_empty=int(clock['dterror_interval_empty']),
        p_min_Pa=float(p.min()), p_max_Pa=float(p.max()), p_mean_Pa=float(p.mean()), p_RMS_Pa=float(np.sqrt(np.mean(p*p))),
        negative_p_nodes=int(np.count_nonzero(p < 0)),
        native_p_minus_fixedP0_min_Pa=float(excess.min()), native_p_minus_fixedP0_max_Pa=float(excess.max()),
        native_p_minus_fixedP0_mean_Pa=float(excess.mean()), native_p_minus_fixedP0_RMS_Pa=float(np.sqrt(np.mean(excess*excess))),
        effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(effective_norm**2))),
        total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(total_norm**2))),
        effective_zz_mean_Pa=float(kk[:, 2].mean()), total_zz_mean_Pa=float(total[:, 2].mean()),
        velocity_RMS_m_s=float(np.sqrt(np.mean(speed**2))), max_speed_m_s=float(speed.max()),
        min_kappa=float(kap.min()), max_kappa=float(kap.max()), plastic_soil_nodes=int(np.count_nonzero(kap > 0)),
        min_J=float(J.min()), max_J=float(J.max()), min_n=float(n.min()), max_n=float(n.max()),
        min_rho_kg_m3=float(rho.min()), max_rho_kg_m3=float(rho.max()), min_k_m_s=float(k.min()), max_k_m_s=float(k.max()),
        front_x_m=float(pos[:, 0].max()), front_advance_from_PRE_m=float(pos[:, 0].max()-ref['pos'][:, 0].max()),
        front_advance_from_initial_m=float(pos[:, 0].max()-ref['initial'][:, 0].max()), height_max_m=float(pos[:, 2].max()),
        mean_settlement_from_PRE_mm=float(settlement.mean()), min_settlement_from_PRE_mm=float(settlement.min()),
        max_settlement_from_PRE_mm=float(settlement.max()), material_displacement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du, axis=1)))),
        NN_min_over_dp=float(nn.min()), NN_q05_over_dp=float(np.quantile(nn, .05)), NN_median_over_dp=float(np.median(nn)),
        NN_q95_over_dp=float(np.quantile(nn, .95)),
        min_soil_x_m=float(pos[:, 0].min()), min_soil_z_m=float(pos[:, 2].min()),
        negative_x_nodes=int(np.count_nonzero(pos[:, 0] < 0)), negative_z_nodes=int(np.count_nonzero(pos[:, 2] < 0)),
        FS23_nodes=int(np.count_nonzero(fs)), FS23_positive_p_nodes=int(np.count_nonzero(fs & (p > 0))),
        FS23_negative_p_nodes=int(np.count_nonzero(fs & (p < 0))), FS23_zero_p_nodes=int(np.count_nonzero(fs & (p == 0))), **counts)
    for name in ('top', 'bottom'):
        cohort = ref[name]
        for c, axis in enumerate('xyz'): row[name+'_material_d'+axis+'_from_PRE_mm'] = float(1000*du[cohort, c].mean())
        row[name+'_material_settlement_from_PRE_mm'] = float(settlement[cohort].mean())
        row[name+'_material_max_displacement_from_PRE_mm'] = float(1000*np.linalg.norm(du[cohort], axis=1).max())
        row[name+'_material_settlement_from_initial_mm'] = float(-1000*(pos[cohort, 2]-ref['initial'][cohort, 2]).mean())
    values = [('p', p, 'Pa'), ('native_p_minus_fixedP0', excess, 'Pa'), ('speed', speed, 'm/s'),
        ('kappa', kap, '1'), ('J', J, '1'), ('n', n, '1'), ('rho', rho, 'kg/m3'), ('k', k, 'm/s'),
        ('NN_over_dp', nn, '1'), ('effective_trace', kk.sum(axis=1), 'Pa'), ('total_trace', total.sum(axis=1), 'Pa'),
        ('effective_stress_Frobenius', effective_norm, 'Pa'), ('total_stress_Frobenius', total_norm, 'Pa'),
        ('settlement_from_PRE', settlement, 'mm')]
    values += [('SigmaState_kk_component'+str(i), kk[:, i], 'Pa') for i in range(3)]
    values += [('SigmaState_ij_component'+str(i), ij[:, i], 'Pa') for i in range(3)]
    values += [('total_diagonal_component'+str(i), total[:, i], 'Pa') for i in range(3)]
    extrema = []
    for field, val, unit in values:
        for kind, j in (('min', int(val.argmin())), ('max', int(val.argmax()))):
            extrema.append(dict(case=label, part=row['part'], completed_step=row['completed_step'], actual_time_s=row['actual_time_s'],
                tau_s=row['tau_s'], field=field, extreme=kind, value=float(val[j]), unit=unit,
                native_id=int(ids[j]), x_m=float(pos[j, 0]), y_m=float(pos[j, 1]), z_m=float(pos[j, 2])))
    need(all(math.isfinite(v) for v in row.values() if isinstance(v, float)), 'Nonfinite scientific aggregation; no filtering permitted')
    details = dict(ids=np.array(ids), pos=pos, p=p, p0=p0, excess=excess, kappa=kap, J=J, n=n, k=k, rho=rho,
        speed=speed, v=v, kk=kk, ij=ij, total=total, total_norm=total_norm, du=du, nn=nn,
        fixed=np.array(frame['Posd'][~soil]), time_s=row['actual_time_s'], tau_s=row['tau_s'])
    return row, extrema, details



def physical_review(bundles,ref):
    histories,extrema,matched,spatial,tracks=[],[],[],[],[];snapshots={};series={c:[]for c in CASES};tail={};last={c:None for c in CASES}
    focus=(4953,4954,6767,6865,6964,7012,6918,6967)
    for part in range(COUNT):
        data={}
        for label,bundle in zip(CASES,bundles):
            frame=core.read22(bundle,part);row,ev,d=physical_frame(frame,bundle['clocks'][part],label,ref,last[label]);last[label]=d['kappa'].copy();histories.append(row);extrema+=ev;series[label].append(row);data[label]=d
            if part==60:tail[label]=d['pos'].copy()
            for nativeid in focus:
                j=nativeid-2060;tracks.append(dict(case=label,part=part,completed_step=row['completed_step'],actual_time_s=row['actual_time_s'],tau_s=row['tau_s'],native_id=nativeid,x_m=float(d['pos'][j,0]),z_m=float(d['pos'][j,2]),vx_m_s=float(d['v'][j,0]),vz_m_s=float(d['v'][j,2]),p_Pa=float(d['p'][j]),fixed_P0_Pa=float(d['p0'][j]),native_p_minus_fixedP0_Pa=float(d['excess'][j]),J=float(d['J'][j]),n=float(d['n'][j]),k_m_s=float(d['k'][j]),kappa=float(d['kappa'][j]),NN_over_dp=float(d['nn'][j]),effective_trace_Pa=float(d['kk'][j].sum()),total_trace_Pa=float(d['total'][j].sum())))
            if part in SELECTED:
                snapshots[(label,part)]=d
                for j,nativeid in enumerate(d['ids']):
                    spatial.append(dict(case=label,part=part,completed_step=row['completed_step'],actual_time_s=row['actual_time_s'],tau_s=row['tau_s'],native_id=int(nativeid),x_m=float(d['pos'][j,0]),y_m=float(d['pos'][j,1]),z_m=float(d['pos'][j,2]),p_Pa=float(d['p'][j]),fixed_P0_Pa=float(d['p0'][j]),native_p_minus_fixedP0_Pa=float(d['excess'][j]),NN_over_dp=float(d['nn'][j]),kappa=float(d['kappa'][j]),J=float(d['J'][j]),n=float(d['n'][j]),k_m_s=float(d['k'][j]),rho_kg_m3=float(d['rho'][j]),speed_m_s=float(d['speed'][j]),total_stress_Frobenius_Pa=float(d['total_norm'][j]),dx_from_PRE_mm=float(1000*d['du'][j,0]),dy_from_PRE_mm=float(1000*d['du'][j,1]),dz_from_PRE_mm=float(1000*d['du'][j,2]),initial_material_layer=int(ref['layer'][j]),fixed_initial_top_ID=bool(ref['top'][j]),fixed_initial_bottom_ID=bool(ref['bottom'][j])))
        b=data[CASES[2]]
        for control in CASES[:2]:
            a=data[control];need(bits(a['time_s'])==bits(b['time_s'])and np.array_equal(a['ids'],b['ids']),'Same actual time and material IDs required')
            dp=b['p']-a['p'];dx=b['pos']-a['pos'];ds=b['total']-a['total'];di=b['ij']-a['ij']
            q=dict(comparison=CASES[2]+' minus '+control,part=part,completed_step=int(bundles[2]['clocks'][part]['completed_step']),actual_time_s=b['time_s'],tau_s=b['tau_s'],delta_p_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),delta_p_absmax_Pa=float(np.abs(dp).max()),delta_material_XYZ_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(dx*dx,axis=1)))),delta_material_XYZ_absmax_mm=float(1000*np.linalg.norm(dx,axis=1).max()),delta_total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(di*di,axis=1)))),delta_J_RMS=float(np.sqrt(np.mean((b['J']-a['J'])**2))),delta_n_RMS=float(np.sqrt(np.mean((b['n']-a['n'])**2))),delta_kappa_RMS=float(np.sqrt(np.mean((b['kappa']-a['kappa'])**2))))
            for key in ('p_RMS_Pa','p_min_Pa','p_max_Pa','velocity_RMS_m_s','max_speed_m_s','max_kappa','min_J','max_J','top_material_settlement_from_PRE_mm','bottom_material_settlement_from_PRE_mm','front_advance_from_PRE_m','NN_min_over_dp','NN_q05_over_dp','unique_pairs_lt_0p7dp','unique_pairs_lt_0p5dp','unique_pairs_lt_0p3dp'):
                q['delta_'+key]=series[CASES[2]][-1][key]-series[control][-1][key]
            matched.append(q)
    summaries={}
    for label in CASES:
        h=series[label];d=snapshots[(label,90)];move=d['pos']-tail[label];events=[q for q in extrema if q['case']==label and q['field']=='p']
        summaries[label]=dict(final=h[-1],selected_saved_states=[h[i]for i in SELECTED],global_saved_pressure_min=min((q for q in events if q['extreme']=='min'),key=lambda q:q['value']),global_saved_pressure_max=max((q for q in events if q['extreme']=='max'),key=lambda q:q['value']),peak_saved_p_RMS=max(h,key=lambda q:q['p_RMS_Pa']),worst_saved_NN=min(h,key=lambda q:q['NN_min_over_dp']),peak_saved_close_0p5=max(h,key=lambda q:q['unique_pairs_lt_0p5dp']),actual_tail_start_s=h[60]['actual_time_s'],actual_tail_end_s=h[-1]['actual_time_s'],tail_same_material_motion_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(move*move,axis=1)))),tail_same_material_max_motion_mm=float(1000*np.linalg.norm(move,axis=1).max()),tail_front_advance_m=h[-1]['front_x_m']-h[60]['front_x_m'])
    need(len(histories)==273 and len(matched)==182 and len(spatial)==45000 and len(tracks)==2184,'Closed three-case scientific coverage differs')
    return histories,extrema,matched,spatial,tracks,snapshots,summaries

def plots(history, snapshots, prefix):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.lines import Line2D
    colors = ('#2166AC', '#D6604D', '#228833'); styles = ('-', '--', ':')
    series = {label: [q for q in history if q['case'] == label] for label in CASES}
    charts = (
        ('Native p: min / max / RMS [kPa]', ('p_min_Pa', 'p_max_Pa', 'p_RMS_Pa'), .001),
        ('Native p-fixed P0: min / max / RMS [kPa]', ('native_p_minus_fixedP0_min_Pa', 'native_p_minus_fixedP0_max_Pa', 'native_p_minus_fixedP0_RMS_Pa'), .001),
        ('Total / effective stress Frobenius RMS [kPa]', ('total_stress_Frobenius_RMS_Pa', 'effective_stress_Frobenius_RMS_Pa'), .001),
        ('Speed: RMS / maximum [m/s]', ('velocity_RMS_m_s', 'max_speed_m_s'), 1.),
        ('Maximum cumulative kappa', ('max_kappa',), 1.),
        ('J: minimum / maximum', ('min_J', 'max_J'), 1.),
        ('Porosity: minimum / maximum', ('min_n', 'max_n'), 1.),
        ('Hydraulic conductivity: min / max [m/s]', ('min_k_m_s', 'max_k_m_s'), 1.),
        ('Fixed top / bottom / mean settlement from PRE [mm]', ('top_material_settlement_from_PRE_mm', 'bottom_material_settlement_from_PRE_mm', 'mean_settlement_from_PRE_mm'), 1.),
        ('Front advance / maximum settlement from PRE [m]', ('front_advance_from_PRE_m', 'max_settlement_from_PRE_mm'), None),
        ('Nearest neighbor / dp: minimum / q05', ('NN_min_over_dp', 'NN_q05_over_dp'), 1.),
        ('Unique pairs: r < .7 / .5 / .3 dp', ('unique_pairs_lt_0p7dp', 'unique_pairs_lt_0p5dp', 'unique_pairs_lt_0p3dp'), 1.))
    fig, axes = plt.subplots(4, 3, figsize=(16, 15), layout='constrained')
    onset = [series[CASES[0]][i]['tau_s'] for i in (38, 76)]
    for ax, (title, keys, scale) in zip(axes.flat, charts):
        for caseindex, label in enumerate(CASES):
            rows = series[label]
            for j, key in enumerate(keys):
                factor = (.001 if key == 'max_settlement_from_PRE_mm' else 1.) if scale is None else scale
                ax.plot([q['tau_s'] for q in rows], [factor*q[key] for q in rows],
                    color=colors[caseindex], ls=styles[j], lw=1.5)
        for time in onset: ax.axvline(time, color='.65', ls=':', lw=.7)
        ax.set(title=title, xlabel='Actual time since PRE [s]'); ax.grid(alpha=.22)
        ax.tick_params(labelsize=8); ax.set_title(title, fontsize=10)
        if 'Native p' in title: ax.axhline(0, color='.55', lw=.6)
    legend = [Line2D([0], [0], color=c, lw=2, label=label) for c, label in zip(colors, CASES)]
    legend += [Line2D([0], [0], color='.25', ls=s, label=order+' metric in title') for order, s in zip(('1st', '2nd', '3rd'), styles)]
    fig.legend(handles=legend, loc='outside lower center', ncol=3, fontsize=9)
    fig.suptitle('C08: all91 actual matched saves; original / vector RV / radial RV\nNative p-P0 uses a fixed initial reference, not paper-defined plastic excess; changes are not half-step/theory errors', fontsize=12)
    files = [Path(str(prefix)+'_history.png')]; fig.savefig(files[-1], dpi=175); plt.close(fig)
    for part in SELECTED:
        states = [snapshots[(label, part)] for label in CASES]
        pos = np.concatenate([s['pos'] for s in states]); xmin, xmax = float(pos[:, 0].min()), float(pos[:, 0].max())
        zmin, zmax = float(pos[:, 2].min()), float(pos[:, 2].max())
        fullp = np.concatenate([s['p'] for s in states])/1000
        fullnn = np.concatenate([s['nn'] for s in states])
        need(float(fullp.min()) < float(fullp.max()) and float(fullnn.min()) < float(fullnn.max()), 'Constant field requires an explicitly reviewed plotting convention')
        norms = (Normalize(vmin=float(fullp.min()), vmax=float(fullp.max())), Normalize(vmin=float(fullnn.min()), vmax=float(fullnn.max())))
        fig = plt.figure(figsize=(14, 10), layout='constrained')
        grid = fig.add_gridspec(3, 4, width_ratios=(1., .028, 1., .028))
        images = [None, None]
        for i, (label, s) in enumerate(zip(CASES, states)):
            for j, (values, cmap, field) in enumerate(((s['p']/1000, 'coolwarm', 'Native signed pressure'), (s['nn'], 'viridis', 'Nonself nearest neighbor / dp'))):
                ax = fig.add_subplot(grid[i, 2*j])
                ax.scatter(s['fixed'][:, 0], s['fixed'][:, 2], s=3, color='.72', edgecolors='none', rasterized=True)
                images[j] = ax.scatter(s['pos'][:, 0], s['pos'][:, 2], c=values, cmap=cmap, norm=norms[j], s=6, edgecolors='none', rasterized=True)
                ax.set(xlim=(xmin-DP, xmax+DP), ylim=(zmin-DP, zmax+DP), xlabel='Actual x [m]', ylabel='Actual z [m]')
                ax.set_aspect('equal'); ax.set_title(label+' | '+field+'\nP'+str(part)+f", actual t={s['time_s']:.12f}s, tau={s['tau_s']:.12f}s", fontsize=9)
        for j, title in enumerate(('Native p [kPa], full signed linear range', 'Nonself soil NN / dp, full range')):
            cax = fig.add_subplot(grid[:, 2*j+1]); bar = fig.colorbar(images[j], cax=cax); bar.set_label(title, fontsize=9)
        fig.suptitle('All5000 original soil IDs in all three cases; common actual saved time\nNo interpolation, smoothing, pressure clipping or excluded material points', fontsize=11)
        p = Path(str(prefix)+'_spatial_P'+str(part)+'.png'); fig.savefig(p, dpi=180); plt.close(fig); files.append(p)
    return files



def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until passed window/native and independent root offline admission')
    prefix=T/'figures'/TAG;check=L/(TAG+'.check.json');need(not check.exists()and not list(prefix.parent.glob(TAG+'_*')),'Existing complete/partial scientific outputs protected')
    consumed=[];files=[];result=dict(stage=TAG,passed=False,analysis_complete=False,physical_acceptance=False,solver_invocations=0,native_invocations=0,VTK_invocations=0,build_invocations=0,GPU_actions=0,SHA_scans=0)
    try:
        consumed=[stat(Path(__file__)),stat(NOTE),stat(Path(typed.__file__)),stat(Path(core.__file__)),stat(Path(radial.__file__))]
        run,bundles,ref,source,timing,qualification=load_inputs(consumed)
        history,extrema,matched,spatial,tracks,snapshots,summaries=physical_review(bundles,ref)
        need(all(stat(q['path'])==q for q in consumed),'Consumed native/source/reference changed during scientific review')
        for name,rows in (('history',history),('matched',matched),('extrema',extrema),('spatial',spatial),('material_tracks',tracks),('timing',timing)):
            q=Path(str(prefix)+'_'+name+'.csv');write_csv(q,rows);files.append(q)
        files+=plots(history,snapshots,prefix)
        need(all(stat(q['path'])==q for q in consumed),'Consumed source/native changed while writing figures')
        result.update(passed=True,analysis_complete=True,source_run=stat(RUN),native_receipt=stat(NATIVE),reference_scientific_review=stat(OLD_GATE),actual_matched_native_states=91,actual_cases=3,actual_soil_IDs_per_state=5000,typed_arrays=22,history_rows=len(history),matched_rows=len(matched),extrema_rows=len(extrema),spatial_rows=len(spatial),track_rows=len(tracks),selected_parts=list(SELECTED),actual_source_time_s=ref['time'],actual_end_s=float(bundles[2]['clocks'][-1]['time_s']),actual_tau_end_s=float(bundles[2]['clocks'][-1]['time_s'])-ref['time'],fixed_initial_top_IDs=ref['ids'][ref['top']].astype(int).tolist(),fixed_initial_bottom_IDs=ref['ids'][ref['bottom']].astype(int).tolist(),all_actual_clock_matches=True,signed_dterror_preserved=True,source_raw_frames_read=0,sealed_source_cohorts_reused=True,new_radial_qualification=qualification,summaries=summaries,observed_timing=timing,timing_is_controlled_benchmark=False,comparison_is_half_step_or_theory_error=False,native_p_minus_P0_is_fixed_reference_not_paper_plastic_excess=True,NN_thresholds_are_descriptive_not_acceptance_gates=True,pressure_smoothing_is_not_success_criterion=True,all_points_preserved_no_filter_clip_or_fit=True,ij_order='xy,yz,xz',NoPen_same_stage_Darcy_reaction_closed=False,sparse_RV_power_integrated_as_energy=False,full_internal_stage_trace_reconstructed=False,automatic_other_psi_or_next_solver=False,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(q)for q in files])
    except Exception as e:result.update(first_failure=str(e),consumed=consumed,partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
