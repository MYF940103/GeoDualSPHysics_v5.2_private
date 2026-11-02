"""One sealed GPU gravity pair, read-only inputs, no solver or interpolated time."""
import argparse
import csv
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('neutral_periodic_fields', Path(__file__).with_name('upl_gravity_periodic_compare_r1.py'))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
entry, table, binary, rms_vector, FIELDS = base.entry, base.table, base.binary, base.rms_vector, base.FIELDS
need, verify, read_json, values = base.need, base.verify, base.read_json, base.values
N, S, C, DC, DH, CAD, END, TIMES = base.N, base.S, base.C, base.DC, base.DH, base.CAD, base.END, base.TIMES
A, PSTAR, USTAR, GX, LIMIT, EPS = base.A, base.PSTAR, base.USTAR, base.GX, base.LIMIT, base.EPS
SEED = '364c4421a8b539d0e8e5eb67e00c547657c9c65f48cd7e83168a4ad32cd5a8fa'

def bind(rows):
    return [verify(item) for item in rows]

def owned(item, typed):
    call = read_json(verify(item))
    need(call.get('owned_call_exited') is True and type(call.get('exit_code')) is int and call['exit_code'] == 0, 'Owned actual exit0 required')
    need(not typed or call.get('typed_LASTEXITCODE_captured_immediately') is True, 'New call requires immediate typed exit')
    bind([call['program'], call['log']]); verify(call.get('target_program', call['program'])); return call

def closure(check, current):
    helper = read_json(verify(check['helper'])); program = verify(helper['program'])
    bind(helper['author_files']+helper['tools']+helper['libraries']+[helper['compile_call'],helper['link_call']])
    bind(helper.get('transitive_author_include_files',[]))
    for item in helper['runtime']: bind([item['original'],item['copy']])
    if current:
        build = read_json(verify(check['source_build'])); frozen = read_json(verify(build['source_freeze']))
        need(helper['status'] == 'actual_authoritative_GPU_objects_helper_linked_not_run' and helper['configuration'] == build['configuration'] == 'Release' and build['status'] == 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' and helper['source_build'] == check['source_build'] and helper['link_object_count'] == 111 and helper['exact_link_closure_verified'] is True and len(build['objects']) == 110 and len(frozen['source']) == 265 and len(frozen['targets']) == 2 and frozen['other_source_count'] == 263, 'Current265/2/263 and110+1 closure required')
        bind(frozen['source']+frozen['canonical_GPU_six_and_CPU_two']+build['objects']+[build['project_call'],build['isolated_GPU_program'],helper['helper_object']])
        for item in frozen['current_source_snapshot']: bind([item['original'],item['snapshot']])
        verify(build['default_CPU_Debug_build'])
    return program

def proof(folder, check_path, kind, model, dt):
    verify(entry(check_path)); check = read_json(check_path); gravity = kind != 'g0'; current = kind == 'gpu'
    need(check.get('passed') is True and check.get('physical_acceptance') is False, 'Bounded passed single check required')
    exports = set(bind(check['files'])); required = ['completion.json','physical.bin','history.csv','native_ids.csv','last_poro.csv']+(['frame.bin'] if gravity else [])
    need(all(folder/name in exports for name in required) and verify(check['completion']) == folder/'completion.json', 'Supplied review exports not bound')
    program = closure(check,current); reader = owned(check['reader_call'] if kind == 'cpu' else check['call'], gravity); argv = reader['arguments']; window = 'coarse' if dt == DC else 'half'
    if current:
        need(len(argv) == 6 and argv[:3] == ['--read',model,window], 'New GPU reader/model/window mismatch'); data, xml, target = map(Path,argv[3:])
    elif kind == 'cpu':
        need(model == 'variable' and len(argv) == 5 and argv[:2] == ['--read',window], 'Only retained nong0 CPU variable reader exists'); data, xml, target = map(Path,argv[2:])
    else:
        need(len(argv) == 7 and argv[:3] == ['--read',model,'GPU'] and float(argv[4]) == dt, 'Retained GPU g0 reader mismatch'); data, xml, target = Path(argv[3]),Path(argv[5]),Path(argv[6])
    need(target.resolve() == folder and verify(reader.get('target_program',reader['program'])) == program, 'Reader target/program mismatch')
    run = read_json(verify(check['source_run'])); solver = owned(run['call'],gravity); args = solver.get('target_arguments',solver['arguments'])
    need(verify(solver.get('target_program',solver['program'])) == program and str(data.parent) in args and str(xml.with_suffix('')) in args, 'Actual solver/program/input/output mismatch')
    need(args[:3] == ['--solver',model,window] if current else args[:2] == ['--solver',window] if kind == 'cpu' else args[0] == '--solver-'+model, 'Actual solver entry mismatch')
    need(current or run.get('owned_solver_exit0') is True, 'Historical completed solver proof required')
    raw = set(bind(run['files'])); parts = {data/f'Part_{p:04}.bi4' for p in range(S)}
    need(set(data.glob('Part_*.bi4')) == parts and parts <= raw, 'All257 original raw PARTs must be bound')
    live,last = entry(data.parent/'live_final.csv'),entry(folder/'last_poro.csv'); need(verify(live) in raw and live['bytes'] == last['bytes'] and live['sha256'] == last['sha256'], 'Live/native final J/n/theta bytes differ')
    actual_e = check['actual_complete'] if kind == 'cpu' else run['actual_completion']; actual = read_json(verify(actual_e))
    need(verify(actual_e) in raw and actual.get('passed') is True and actual.get('actual_production_Run') is True and actual.get('private_feedback') is True and actual.get('private_complete_dynamic_rate') is True and actual.get('physical_fields_rewritten_by_fixture') is False and actual.get('predictor_histories_released') is True and actual['dt_s'] == dt and actual['completed_steps'] == round(END/dt), 'Actual complete private Run required')
    if gravity: need(actual.get('gravity_x_m_s2') == GX and actual.get('public_master') is False, 'Private true gravity/public OFF required')
    else: need(actual.get('model') == model and actual.get('public_GPU_dynamic_mode') is False, 'Retained private g0 model required')
    if kind == 'cpu': seed = read_json(verify(check['preflight']))['inputs']
    elif current: seed = run['inputs']
    else: seed = [run['selected_input']['xml'],run['selected_input']['bi4']]
    need(xml.resolve() in bind(seed) and any(item['bytes'] == 23948 and item['sha256'].lower() == SEED for item in seed), 'Exact XML/initial BI4 not bound')
    for record in (check,run):
        for key in ('source_build','helper','input','preflight'):
            if record.get(key): verify(record[key])  # Historical source inventories/Git refs are not mutable current inputs.
    return read_json(folder/'completion.json'), not gravity

def load(folder, check, kind, model, dt):
    folder = folder.resolve(); done, old_exit_format = proof(folder,check,kind,model,dt); gravity = kind != 'g0'
    need(done.get('passed') is True and done.get('native_count') == N and done.get('fixed_count') == 0 and done.get('samples') == S and done.get('common_columns') == C and done.get('dt_s') == dt and done.get('cadence_s') == CAD and done.get('actual_end_s') == END, 'Single schema/clock mismatch')
    need(done.get('backend') == {'gpu':'GPU_private','cpu':'CPU_private','g0':'GPU'}[kind] and done.get('native_J_arrays') == 3 and done.get('public_dynamic_metadata') is False, 'Honest private3J/backend attribution required')
    need(done.get('V_rho_k_derived_not_native') is True if gravity else done.get('GPU_V_rho_k_derived_not_native_arrays') is True, 'GPU/CPU private V/rho/k must be derived,not native')
    need(done.get('private_Ck') == (base.CK if model == 'variable' else 0) if gravity else done.get('model') == model and (model == 'constant' or done.get('conductivity_Ck') == base.CK), 'Declared constant/smooth law mismatch')
    lab = binary(folder/'physical.bin'); q = binary(folder/'frame.bin') if gravity else lab
    if gravity:
        expected = lab.copy(); expected[:,:,0] -= (.5*GX*TIMES*TIMES)[:,None]; expected[:,:,3] -= (GX*TIMES)[:,None]; expected[:,:,25] -= (.5*GX*TIMES*TIMES)[:,None]
        need(np.array_equal(expected.view(np.uint64),q.view(np.uint64)), 'Frame must change exactly x/vx/ux by declared transform')
    ids, history = table(folder/'native_ids.csv'),table(folder/'history.csv'); x0 = np.column_stack([values(ids,k) for k in ('x0','y0','z0')]); step = np.rint(TIMES/dt).astype(np.int64)-1; step[0] = 0
    need(len(ids) == N and len(history) == S and np.array_equal(values(ids,'row'),np.arange(N)) and np.array_equal(values(ids,'id'),np.arange(N)) and np.array_equal(x0.view(np.uint64),lab[0,:,:3].copy().view(np.uint64)), 'Native512 ID/material alignment differs')
    need(np.array_equal(values(history,'part'),np.arange(S)) and np.array_equal(values(history,'time_s'),TIMES) and np.array_equal(values(history,'saved_step'),step) and np.array_equal(values(history,'dt_s'),np.full(S,dt)) and (values(history,'signed_dterror_s' if gravity else 'dterror_s') <= 1e-14).all(), 'Actual clock/Step/lockedDt/signed safety differs')
    j,n = q[:,:,8],q[:,:,29]; rn=1-(1-base.N0)/j; rv=base.V0*j; rr=base.RHOW+(base.RHO0-base.RHOW)/j; rk=base.K0*np.exp((j-1)/((1-base.N0)*base.CK)) if model == 'variable' else np.full_like(j,base.K0)
    ledger=np.stack([np.abs(n-rn)/rn,np.abs(q[:,:,30]-rv)/rv,np.abs(q[:,:,31]-rr)/rr,np.abs(q[:,:,32]-rk)/rk]); consistency=float(np.abs(q[:,:,25:28]-(q[:,:,:3]-x0)).max())
    need((j>1-base.N0).all() and (np.abs(j-1)<=1e-4).all() and (n>0).all() and (n<1).all() and np.isfinite(ledger).all() and (ledger<=5e-13).all() and (np.abs((1-n)*j-(1-base.N0))<=5e-13).all() and consistency<=16*EPS, 'Original independent ledger/domain/material-u failed')
    need((q[:,:,7]==0).all() and (q[:,:,16]==0).all() and (q[:,:,21:24]==0).all() and (q[:,:,24]>=700).all() and (q[:,:,24]<=3000).all() and np.array_equal(q[:,:,28],(q[:,:,6].astype(np.float32)-q[:,:,7].astype(np.float32)).astype(np.float32).astype(float)), 'Original p0/plastic/load/passive rho/excess safety failed')
    trace=q[:,:,10]+q[:,:,13]+q[:,:,15]; dev=((q[:,:,[10,13,15]]-trace[:,:,None]/3)**2).sum(2)+2*(q[:,:,[11,12,14]]**2).sum(2)
    energy=(rv*(.5*rr*(q[:,:,3:6]**2).sum(2)+dev/(4*base.SHEAR)+trace**2/(18*base.BULK)+n*q[:,:,6]**2/(2*base.KW))).sum(1); ratio=energy/energy[0]
    cu=np.sqrt((base.BULK+4*base.SHEAR/3+base.KW/rn)/rr)*dt/base.H; diffusion=base.KW/rn*rk/(base.RHOW*9.80665)*dt/base.H**2; margin=rr*(base.KW/rn)/(base.BULK+4*base.SHEAR/3+base.KW/rn)-base.RHOW
    need(energy[0]>0 and np.isfinite(ratio).all() and (ratio<=1.1).all() and (cu<=.01).all() and (diffusion<=.01).all() and (margin>64*EPS*np.maximum(rr,base.RHOW)).all(), 'Original saved energy/necessary-step/RH screens failed')
    return {'q':q,'lab':lab,'x0':x0,'ledger':float(ledger.max()),'energy':float(ratio.max()),'legacy_call_has_no_immediate_typed_flag':old_exit_format}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--pair',required=True,choices=['half','frame_c','frame_h','cross_c','cross_h']); parser.add_argument('--model',required=True,choices=['constant','variable'])
    for name in ('a','b','a-check','b-check','out'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--figure',action='store_true'); args=parser.parse_args(); need(not args.pair.startswith('cross') or args.model == 'variable','No retained nong0 constant CPU trajectory exists')
    prefix=args.out.resolve(); fp=ROOT/'figures'/prefix.name; paths={'check':Path(str(prefix)+'.check.json'),'history':Path(str(fp)+'.csv'),'fields':Path(str(fp)+'_fields.csv'),'figure':Path(str(fp)+'.png')}
    need(prefix.parent == ROOT/'logs' and fp.parent.is_dir() and not any(path.exists() for path in paths.values()), 'Fresh shallow log/figure paths required')
    bind([entry(__file__),entry(ROOT/'notes'/'upl_gpu_gravity_periodic_pair_r1.json'),entry(spec.origin),entry(ROOT/'notes'/'upl_gravity_periodic_compare_r1.json'),entry(ROOT/'notes'/'upl_gravity_periodic_admission_r1.json')])
    da=DC if args.pair in ('half','frame_c','cross_c') else DH; db=DH if args.pair == 'half' else da; right_kind='gpu' if args.pair == 'half' else 'cpu' if args.pair.startswith('cross') else 'g0'
    left=load(args.a,args.a_check,'gpu',args.model,da); right=load(args.b,args.b_check,right_kind,args.model,db); x,y=left['q'],right['q']; delta=x-y; raw_delta=left['lab']-right['lab']
    need(np.array_equal(left['x0'].view(np.uint64),right['x0'].view(np.uint64)) and np.array_equal(x[0].view(np.uint64),y[0].view(np.uint64)), 'Original strict common initial33/material-ID bits gate failed')
    prms=np.sqrt((delta[:,:,6]**2).mean(1)); vrms=rms_vector(delta[:,:,3:6]); urms=rms_vector(delta[:,:,25:28]); umax=1000*np.linalg.norm(delta[:,:,25:28],axis=2).max(1); consistency=float(np.abs(delta[:,:,25:28]-delta[:,:,:3]).max())
    gates={'pressure_RMS_5Pa':bool((prms<=5).all()),'material_u_max_0p005mm':bool((umax<=.005).all()),'pressure_normalized_1e4':bool((prms/PSTAR<=LIMIT).all()),'velocity_normalized_1e4':bool((vrms/A<=LIMIT).all()),'material_u_normalized_1e4':bool((urms/USTAR<=LIMIT).all()),'fixed_p0_plastic_load_legacyrho_bits_exact':bool(np.array_equal(x[:,:,base.EXACT].copy().view(np.uint64),y[:,:,base.EXACT].copy().view(np.uint64))),'position_u_difference_consistent':bool(consistency<=32*EPS)}
    body=None; missing=None; doubled=None
    if right_kind == 'g0':
        dv=left['lab'][:,:,3:6]-right['lab'][:,:,3:6]; expected=np.zeros((S,1,3)); expected[:,0,0]=GX*TIMES; body=rms_vector(dv-expected)/A
        missing=float(np.sqrt((dv[-1]**2).sum(1).mean())/(A*LIMIT)); doubled=float(np.sqrt(((dv[-1]-2*expected[-1])**2).sum(1).mean())/(A*LIMIT)); gates.update(body_gravity_native_XYZ_RMS_1e4=bool((body<=LIMIT).all()),missing_g_formula_negative_gt100=bool(missing>100),doubled_g_formula_negative_gt100=bool(doubled>100))
    frms=np.sqrt((delta*delta).mean(1)); fmax=np.abs(delta).max(1); fmean=delta.mean(1); bits=(x.view(np.uint64)!=y.view(np.uint64)).sum(1); rawbits=(left['lab'].view(np.uint64)!=right['lab'].view(np.uint64)).sum(1)
    with paths['fields'].open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['part','time_s','column','field','frame_RMS_difference','frame_maximum_absolute_difference','frame_mean_signed_difference','frame_binary64_mismatch_nodes','inertial_RMS_difference','inertial_maximum_absolute_difference','inertial_binary64_mismatch_nodes','interpretation'])
        rawrms=np.sqrt((raw_delta*raw_delta).mean(1)); rawmax=np.abs(raw_delta).max(1)
        for p,t in enumerate(TIMES):
            for c,name in enumerate(FIELDS): writer.writerow([p,t,c,name,frms[p,c],fmax[p,c],fmean[p,c],int(bits[p,c]),rawrms[p,c],rawmax[p,c],int(rawbits[p,c]),'strict_bit_gate' if c in base.EXACT else 'descriptive_not_independent_field_accuracy_gate'])
    with paths['history'].open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['part','time_s','pressure_RMS_Pa','velocity_XYZ_RMS_m_s','material_u_XYZ_RMS_m','material_u_max_mm','pressure_RMS_over_Pstar','velocity_RMS_over_A','u_RMS_over_Ustar','body_gravity_XYZ_RMS_over_A'])
        for p,t in enumerate(TIMES): writer.writerow([p,t,prms[p],vrms[p],urms[p],umax[p],prms[p]/PSTAR,vrms[p]/A,urms[p]/USTAR,'' if body is None else body[p]])
    if args.figure:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(3,1,figsize=(7,7),sharex=True)
        for ax,data,label in zip(axes,[prms/PSTAR,vrms/A,urms/USTAR],['Pressure / Pstar [ppm]','Velocity / A [ppm]','Material u / Ustar [ppm]']): ax.plot(TIMES*1e6,data*1e6,label=args.model+' '+args.pair); ax.set_ylabel(label); ax.grid(alpha=.25); ax.legend(loc='best')
        axes[0].set_title('Private GPU gravity: bounded pair; prior limit 100 ppm (not axis-forced)'); axes[-1].set_xlabel('Actual saved time [microseconds]'); fig.tight_layout(); fig.savefig(paths['figure'],dpi=170); plt.close(fig)
    for item in base.BOUND.values(): need(entry(item['path']) == item,'Bound input/source changed during offline analysis')
    result={'passed':bool(all(gates.values())),'stage':'upl_gpu_gravity_periodic_pair_r1','pair':args.pair,'model':args.model,'samples':S,'native_ids':N,'columns':C,'comparison_coordinate':'declared accelerating frame; inertial33 differences also reported','gates':gates,'max_pressure_RMS_Pa':float(prms.max()),'max_velocity_RMS_over_A':float((vrms/A).max()),'max_material_u_RMS_over_Ustar':float((urms/USTAR).max()),'max_material_u_mm':float(umax.max()),'max_body_gravity_XYZ_RMS_over_A':None if body is None else float(body.max()),'missing_g_formula_final_over_original_budget':missing,'doubled_g_formula_final_over_original_budget':doubled,'position_u_difference_consistency_m':consistency,'single_independent_checks':[{k:z[k] for k in ('ledger','energy','legacy_call_has_no_immediate_typed_flag')} for z in (left,right)],'initial_33_bits_exact':True,'all_33_raw_bitwise_equal':bool((rawbits==0).all()),'all_33_field_accuracy_acceptance_claimed':False,'negative_controls_are_formula_only_not_faulty_solver_runs':True,'source_and_raw_hashes_before_after':True,'saved_flux_or_force_stage_independently_observed':False,'inputs':list(base.BOUND.values()),'files':[entry(paths[k]) for k in ('history','fields')]+([entry(paths['figure'])] if args.figure else []),'public_gravity_accepted':False,'wall_gravity_accepted':False,'physical_acceptance':False}
    with paths['check'].open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError,KeyError,OSError) as failure: print('Offline pair rejected: '+str(failure),file=sys.stderr); raise SystemExit(1)
