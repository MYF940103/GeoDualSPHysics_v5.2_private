"""Future offline RV window91 review only; no solver, native reader or GPU actions."""
import argparse
import csv
import json
import math
import struct
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import c08_h18_rv_implementation_review_r1 as impl

typed, core = impl.typedcore, impl.typedcore.core
T, L = impl.T, impl.L
need, read, stat, bind, entry, owned, same = impl.need, impl.read, impl.stat, impl.bind, impl.entry, impl.owned, impl.same
TAG = 'c08_h18_rv_window_review_r1'
NOTE = T/'notes'/(TAG+'.md')
RUN = L/'c08_h18_rv_window_GPU_r2.run.json'
CONTROL_RUN = L/'c08_h18_as03_n255_r1.run.json'
CONTROL_NATIVE = L/'c08_h18_as03_n255_native_r1.check.json'
BUILD = L/'c08_h18_rv_gpu_Release_r3.build.json'
BASE, END, COUNT, N, DP = 2000000, 2180000, 91, 5000, .04
SELECTED = (38, 76, 90)
CASES = ('Retained original AS03', 'RV alpha0.1')
THRESHOLDS = ((.7, '0p7'), (.5, '0p5'), (.3, '0p3'))


def bits(x): return struct.pack('<d', float(x))


def write_csv(path, rows):
    need(rows, 'No empty scientific table')
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


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


def load_inputs(runpath, nativepath, consumed):
    need(same(runpath, RUN), 'Only the named independently admitted RV window r2 is exposed')
    run, native = read(runpath), read(nativepath)
    need(run['passed'] and run['solver_completed'] and run['profile'] == 'window'
         and run['actual_steps'] == END and run['saved_frames'] == COUNT and run['consumed_stats_unchanged']
         and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == 0
         and run['RV_requested'] is True and run['environment_override'] == {'C08_RV_H18': '1'},
         'Actual owned normal complete window required; failure needs a separate preserved review')
    startpath = Path(str(runpath).removesuffix('.run.json')+'.start.json'); start = read(startpath)
    callentry = entry(run, 'actual_call'); call = read(callentry['path']); owned(call)
    need(call['child'] and call['child']['parent_pid'] == run['owner']['pid']
         and call['owner']['pid'] == run['owner']['pid'] and call['owner']['created_epoch'] == run['owner']['created_epoch']
         and call['child']['argv'] == run['argv'] and same(call['program'], run['program']['path']),
         'Actual original window owner/child/creation/argv/program binding differs')
    need(start['owner'] == run['owner'] and start['argv'] == run['argv'] and start['solver_argv'] == run['solver_argv']
         and start['environment_override'] == run['environment_override'], 'Original start/run owner or environment differs')
    adentry = entry(run, 'root_admission'); ad = read(adentry['path'])
    need(start['root_admission'] == adentry and ad['authorized'] and ad['allowed_job'] == run['stage']
         and ad['profile'] == 'window' and ad['phase'] == 'run' and not ad['automatic_native'] and not ad['automatic_next_job'],
         'Independent named root window admission required')
    for key in ('program', 'source_build', 'source_capture', 'source_archive', 'source_pre_file', 'input_xml', 'planned_steps'):
        need(start[key] == run[key], 'Original start/run input changed: '+key)
    buildentry = entry(run, 'source_build'); build = read(buildentry['path'])
    need(same(buildentry['path'], BUILD) and build['passed'] and build['configuration'] == 'Release'
         and build['consumed_stats_unchanged'] and build['retained_original_objects'] == 112
         and build['private_objects'] == 2 and build['actual_link_objects'] == 114
         and not build['host_object_recompiled'] and build['original_physical_CUDA_objects_retained']
         and build['new_CUDA_flag'] == '--fmad=false' and build['flag_after_inherited_fast_math']
         and not build['numerical_budgets_changed'] and not build['public_source_changed'],
         'Actual r3 new-CUDA-only --fmad=false build required')
    need(build['program'] == run['program'] and build['source_capture'] == run['source_capture']
         and build['source_archive'] == run['source_archive'] and build['private_sources'] == run['private_sources'],
         'Actual frozen private source/program binding differs')
    need(len(build['calls']) == 2, 'Exactly actual new CUDA/link build calls required')
    calls = [read(bind(e)['path']) for e in build['calls']]
    for q in calls: owned(q)
    need(calls[0]['arguments'][-1] == '--fmad=false' and 'nvcc' in Path(calls[0]['program']).name.lower(),
         'Actual NVCC command must retain the final --fmad=false flag')
    adopted = entry(build, 'adopted_host_call'); owned(read(adopted['path']))
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1
         and entry(native, 'source_run') == stat(runpath), 'One independently admitted native receipt bound to this original run required')
    nc_entry = entry(native, 'actual_call'); nc = read(nc_entry['path']); owned(nc)
    doneentry, metaentry = entry(native, 'native_completion'), entry(native, 'metadata')
    done, meta = read(doneentry['path']), read(metaentry['path']); receiver_done(done)
    need(meta['passed'] and meta['stage'] == 'c08_h18_rv_native_r1.metadata' and meta['profile'] == 'window'
         and meta['samples'] == COUNT and meta['original_AV_private_keys_absent_headers'] == COUNT
         and meta['residual_viscosity_proven_by_reader'] is False and meta['RV_program_owner_sidecar_review_required'] is True,
         'Actual new RV-independent array metadata required')
    rb = entry(native, 'reader_build'); reader = read(rb['path'])
    need(reader['passed'] and reader['consumed_stats_unchanged'] and reader['stage'] == 'c08_h18_rv_native_r1.build'
         and reader['actual_link_objects'] == 7 and not reader['JSph_objects_linked']
         and same(nc['program'], entry(reader, 'program')['path']), 'Actual frozen seven-object reader required')
    preentry, planentry = entry(run, 'source_pre_file'), entry(run, 'planned_steps')
    need(same(preentry['path'], T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'), 'Original certified PRE required')
    args = nc['arguments']; nroot = Path(doneentry['path']).parent
    need(len(args) == 8 and args[:3] == ['--receiver', 'window', 'psi0'] and same(args[4], preentry['path'])
         and same(args[3], Path(run['output'])/'data') and same(args[5], planentry['path'])
         and same(args[6], entry(run, 'native_profile')['path']) and same(args[-1], nroot)
         and same(nroot.parent, run['output']), 'Actual unique receiver/DATA/material/plan/PRE/output binding differs')
    original, originalnative = read(CONTROL_RUN), read(CONTROL_NATIVE)
    need(original['passed'] and original['solver_completed'] and original['actual_steps'] == END and original['saved_frames'] == COUNT
         and original['consumed_stats_unchanged'] and originalnative['passed'] and originalnative['consumed_stats_unchanged']
         and originalnative['reader_invocations'] == 1, 'Retained passed original-physics AS03 control required')
    originaldoneentry = entry(originalnative, 'native_completion'); originaldone = read(originaldoneentry['path']); receiver_done(originaldone)
    oldncallentry = entry(originalnative, 'actual_call'); oldncall = read(oldncallentry['path']); owned(oldncall)
    originalcallentry = entry(original, 'actual_call'); owned(read(originalcallentry['path']))
    need(original['source_pre_file'] == preentry and original['source_native'] == run['source_native']
         and original['planned_steps'] == planentry, 'Actual reference PRE/native/scalar plan must be common')
    for key in ('input_xml', 'native_profile'):
        a, b = entry(run, key), entry(original, key)
        need(Path(a['path']).read_bytes() == Path(b['path']).read_bytes(), 'Original generated XML/material physics bytes differ: '+key)
        consumed += [a, b]
    originalroot = Path(originaldoneentry['path']).parent
    originalout = Path(entry(original, 'Run_out')['path']).parent; oldargs = oldncall['arguments']
    need(len(oldargs) == 8 and oldargs[:3] == ['--receiver', 'window', 'psi0']
         and same(oldargs[3], originalout/'data') and same(oldargs[4], preentry['path'])
         and same(oldargs[5], planentry['path']) and same(oldargs[6], original['native_profile']['path'])
         and same(oldargs[-1], originalroot) and same(originalroot.parent, originalout),
         'Retained control native DATA/material/PRE/plan/output binding differs')
    newbundle = typed.typed(nroot, 6805, COUNT, consumed)
    oldbundle = typed.typed(originalroot, 6805, COUNT, consumed)
    need((nroot/'typed22_layout.csv').read_bytes() == (originalroot/'typed22_layout.csv').read_bytes(), 'Actual compared array layouts differ')
    plan = typed.table(planentry['path'])
    need(len(plan) == COUNT and list(plan[0]) == ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s'], 'Original five-column91-frame plan required')
    for i, (a, b, p) in enumerate(zip(newbundle['clocks'], oldbundle['clocks'], plan)):
        completed = END if i == 90 else BASE+1+2000*i
        need(int(a['part']) == int(b['part']) == int(p['part']) == i
             and int(a['completed_step']) == int(b['completed_step']) == int(p['completed_step']) == completed
             and int(a['saved_step']) == int(b['saved_step']) == int(p['saved_step']) == completed-1
             and float(a['dt_s']) == float(b['dt_s']) == float(p['dt_s']) == 5e-6
             and bits(a['time_s']) == bits(b['time_s']) and abs(float(a['time_s'])-float(p['time_s'])) <= 1e-14,
             'Every actual matched time/step/ID record required; no interpolation')
    sourcedoneentry = entry(run, 'source_native'); sourcedone = read(sourcedoneentry['path'])
    need(sourcedone['passed'] and sourcedone['certified_PRE'] and not sourcedone['partial']
         and sourcedone['stage'] == 'c08_h18_wend_native_r1.source' and sourcedone['samples'] == 1001
         and sourcedone['completed_steps'] == BASE and sourcedone['expected_handoff_schema'] == 2
         and sourcedone['same_material_plastic_PRE'] and sourcedone['native_IDs'] == 7060
         and sourcedone['typed_arrays'] == 22 and sourcedone['typed_bytes_per_particle'] == 212,
         'Original full certified source native reference required')
    sourcebundle = typed.typed(Path(sourcedoneentry['path']).parent, 7060, 1001, consumed)
    consumed += [stat(runpath), stat(nativepath), stat(startpath), adentry, callentry, buildentry, adopted,
        entry(build, 'adopted_host_object'), nc_entry, doneentry, metaentry, rb, preentry, planentry,
        stat(CONTROL_RUN), stat(CONTROL_NATIVE), originalcallentry, oldncallentry, originaldoneentry, sourcedoneentry]
    consumed += [bind(q) for q in build['calls']]+[bind(q) for q in build['private_sources'].values()]
    consumed += [entry(run, k) for k in ('program', 'source_capture', 'source_archive', 'Run_out', 'Run_csv')]
    need(run['actual_source_time_s'] == done['source_actual_time_s'] == originaldone['source_actual_time_s'] == sourcedone['actual_end_s'], 'Actual shared PRE reference clock differs')
    timing = observed_timing(run, original, done, originaldone)
    return run, newbundle, oldbundle, sourcebundle, sourcedone, done, timing


def observed_timing(run, original, done, originaldone):
    # Frozen JSphGpuSingle::Run starts TimerSim immediately before the loop;
    # FinishRun passes its elapsed seconds to Run.csv's TSimul field. This
    # timer covers only the receiver loop, not its inherited source step/time.
    rows = []
    for label, actual, native in ((CASES[0], original, originaldone), (CASES[1], run, done)):
        need(actual['passed'] and actual['solver_completed'], 'Observed timing requires an actual passed completed run')
        updates = int(native['new_updates'])
        need(updates == int(actual['actual_steps'])-int(native['source_completed_step']) == 180000,
             'Timing numerator must be180000 new receiver updates, never inherited global steps')
        summary = actual['summary']; loop, total = float(summary['TSimul']), float(summary['TTotal'])
        hardware = summary['Hardware']
        need(math.isfinite(loop) and loop > 0 and math.isfinite(total) and total > 0
             and isinstance(hardware, str) and bool(hardware.strip()), 'Actual positive finite loop/total timers and recorded hardware required')
        rows.append(dict(case=label, new_receiver_updates=updates, TSimul_loop_s=loop, TTotal_program_s=total,
            Hardware=hardware, new_updates_per_TSimul_s=updates/loop,
            controlled_benchmark=False, changed_trajectory_can_change_neighbor_cost=True))
    return rows


def policy_check(policy):
    expected = dict(policy='C08H18ResidualViscosityPolicy', schema=2, phase_policy='ReleaseOnly', active=True,
        alpha=.1, main_columns=66, main_schema='C08H18RV66-r1', manufactured_columns=40,
        kernel='Wendland', kernel_h_sph_float=struct.unpack('<f', struct.pack('<f', .072))[0], dp_m=.04,
        requested_hdp=1.8, operator_dt_s=5e-6, source_schema=2, keep_bed_overlap=False,
        geometry_profile='bedroles', first_stage_global_step=BASE, retired_begin=1805, retired_count=255,
        force_clock='original_TimeStep_both_stages', reaction_closed=False, BI4_metadata=False,
        native_22_schema_changed=False, manufactured_mode_count=3, synthetic_velocity_coordinates='global',
        manufactured_first_force_scratch_only=True, host_gate_before_Ace_commit=True,
        ephemeral_buffers_per_helper=5, neighbor_kernels_per_helper=2, summary_kernels_per_helper=2,
        serial_O_N_summaries=True, reverse_cell_membership_each_positive_neighbor=True,
        per_stage_mechanical_certificates=True, save_rows_are_not_all_stage_trace=True,
        running_ratios_are_per_phase_maxima=True, budget_formed_by_bound_source_not_rebuilt_offline_from_all_neighbors=True,
        LS_regularized=False, wall_bonds=False, full_coupled_stability_claimed=False, physical_acceptance=False)
    need(set(policy) == set(expected), 'Actual frozen40-key RV schema2 policy differs')
    need(all(type(policy[k]) is type(v) and policy[k] == v for k, v in expected.items()), 'Actual typed RV policy differs')


def rv_review(run, bundle, source, consumed):
    sidecar, manufactured, policyentry = (entry(run, k) for k in ('rv_sidecar', 'rv_manufactured', 'rv_policy'))
    out = Path(entry(run, 'Run_out')['path']).parent
    need([Path(q['path']).name for q in (sidecar, manufactured, policyentry)] == list(impl.RV_FILES)
         and all(Path(q['path']).parent == out for q in (sidecar, manufactured, policyentry)), 'Actual RV output paths differ')
    policy_check(read(policyentry['path']))
    rows = impl.table(sidecar['path'], impl.HEADER, impl.INT_MAIN, {'record', 'phase'})
    modes = impl.table(manufactured['path'], impl.MFG_HEADER, impl.INT_MFG, {'name'})
    need(len(rows) == 182 and len(modes) == 3, 'Actual91 saves require182 phase rows plus3 genuine manufactured rows')
    previous = {p: dict(running=[0.]*10, maxlambda=0., maxbound=0.) for p in ('Pre', 'Cor')}
    scalar, step = float(source['actual_end_s']), BASE
    summaries = []
    for part, clock in enumerate(bundle['clocks']):
        completed = int(clock['completed_step'])
        while step < completed:
            before = scalar; scalar += 5e-6; step += 1
        need(abs(float(clock['time_s'])-scalar) <= 1e-14, 'Actual native clock differs from scalar +=dt')
        summary = dict(part=part, completed_step=completed, actual_time_s=float(clock['time_s']), tau_s=float(clock['time_s'])-source['actual_end_s'], calls_per_phase=completed-BASE)
        for phaseindex, phase in enumerate(('Pre', 'Cor')):
            r = rows[2*part+phaseindex]; updates = completed-BASE; prior = previous[phase]
            need(r['record'] == 'save' and r['phase'] == phase and r['active'] == r['committed'] == 1 and bits(r['alpha']) == bits(.1), 'Actual successful active phase row required')
            need(r['step_start_global'] == completed-1 and r['completed_global'] == completed
                 and all(r[k] == updates for k in ('phase_calls', 'phase_commits', 'pre_calls', 'cor_calls', 'pre_commits', 'cor_commits')),
                 'Actual complete phase/commit cumulative counters differ')
            need(r['validated_soil_nodes'] == N and r['error_bits'] == r['cuda_status'] == 0
                 and r['invalid_sorted_index'] == r['invalid_native_id'] == 2**32-1, 'Actual phase validation failed')
            need(bits(r['step_start_time_s']) == bits(before) == bits(r['force_stage_time_s'])
                 and bits(r['save_time_s']) == bits(clock['time_s']) and bits(r['operator_dt_s']) == bits(5e-6),
                 'Actual original source-stage/scalar-save clock differs')
            need(r['last_lambda_max_s_1'] >= 0 and impl.arithmetic_equal(r['last_dt_lambda_half'], 5e-6*r['last_lambda_max_s_1']*.5)
                 and 0 <= r['last_dt_lambda_half'] <= r['running_dt_lambda_half'] <= 1
                 and r['running_lambda_max_s_1'] >= r['last_lambda_max_s_1']
                 and r['running_dt_lambda_half'] >= prior['maxbound'] and r['running_lambda_max_s_1'] >= prior['maxlambda'],
                 'Original isolated bound or actual monotone phase maximum failed')
            values = impl.certificates(r); running = [r[k] for k in impl.RUNNING]
            need(all(0 <= old <= actual <= 1 and (actual >= current or impl.arithmetic_equal(actual, current))
                     for old, actual, current in zip(prior['running'], running, values)), 'Actual long-window running ratio failed/declined')
            if part == 0:
                need(all(impl.arithmetic_equal(a, b) for a, b in zip(running, values)), 'First actual phase has no unobserved prior stage')
            previous[phase] = dict(running=running, maxlambda=r['running_lambda_max_s_1'], maxbound=r['running_dt_lambda_half'])
            for key in ('last_lambda_max_s_1', 'running_lambda_max_s_1', 'last_dt_lambda_half', 'running_dt_lambda_half',
                        'work_W_per_m', 'committed_work_W_per_m', 'form_W_per_m', *impl.RUNNING):
                summary[phase+'_'+key] = r[key]
        summaries.append(summary)
    mfg_results = []
    for mode, name, r in zip((1, 2, 3), ('translation', 'full_affine', 'rigid_rotation'), modes):
        need(r['mode'] == mode and r['name'] == name and r['step_start_global'] == BASE
             and bits(r['source_time_s']) == bits(source['actual_end_s']) and bits(r['operator_dt_s']) == bits(5e-6)
             and r['committed'] == r['error_bits'] == r['cuda_status'] == 0
             and r['certificates_passed'] == r['manufactured_passed'] == 1, 'Actual original first-force scratch-only manufactured mode failed')
        need(all(r[k] == rows[0][k] for k in ('directed_edges', 'reverse_memberships', 'max_degree', 'gamma64', 'max_condition')),
             'Manufactured graph differs from genuine first real Pre graph')
        impl.certificates(r)
        rr, fr = impl.ratio(r['max_residual_m_s'], r['residual_budget_m_s']), impl.ratio(r['max_force_N_per_m'], r['force_budget_N_per_m'])
        need(math.isfinite(rr) and math.isfinite(fr) and rr <= 1 and fr <= 1, 'Original manufactured null budget failed')
        mfg_results.append(dict(mode=mode, name=name, residual_ratio=rr, force_ratio=fr, committed=False))
    need(summaries[-1]['calls_per_phase'] == 180000 and step == END, 'Actual physical phase endpoint count differs')
    consumed += [sidecar, manufactured, policyentry]
    return summaries, dict(schema=2, main_columns=66, actual_saved_phase_rows=182, actual_manufactured_rows=3,
        calls_per_phase=180000, final_phase_maxima=previous, manufactured=mfg_results,
        reported_cumulative_stage_calls=360000, independently_reviewed_saved_stages=182,
        unobserved_internal_maxima_reconstructed=False, all_neighbor_budget_primitives_reconstructed=False,
        sparse_mechanical_work_integrated=False, physical_acceptance=False)


def source_reference(bundle, source):
    initial, pre = core.read22(bundle, 0), core.read22(bundle, 1000)
    allids = np.array(initial['Idp'][:, 0], dtype=np.uint32)
    need(np.array_equal(allids, pre['Idp'][:, 0]) and len(np.unique(allids)) == 7060
         and bits(pre['time']) == bits(source['actual_end_s']), 'Actual certified source ID/endpoint reference differs')
    ids = allids[allids >= 2060]
    need(np.array_equal(ids, np.arange(2060, 7060, dtype=np.uint32)), 'Exactly all5000 true original soil IDs required')
    sourceat = np.searchsorted(allids, ids)
    need(np.array_equal(allids[sourceat], ids), 'Actual source ID mapping failed')
    pos0, pospre = np.array(initial['Posd'][sourceat]), np.array(pre['Posd'][sourceat])
    z, layer = np.unique(pos0[:, 2], return_inverse=True); x = np.unique(pos0[:, 0])
    need(len(z) == 50 and len(x) == 100 and np.all(np.bincount(layer) == 100), 'Actual initial native positions must establish50 layers of100 original IDs')
    need(all(np.array_equal(np.sort(pos0[layer == i, 0]), x) for i in range(50)), 'Actual initial native columns/layers are not the declared grid')
    top, bottom = layer == 49, layer == 0
    need(np.array_equal(initial['PorePress0'][:, 0].view('<u4'), pre['PorePress0'][:, 0].view('<u4')), 'Original fixed source P0 changed')
    receiverids = np.r_[np.arange(1805, dtype=np.uint32), ids]
    receiverat = np.searchsorted(allids, receiverids)
    need(np.array_equal(allids[receiverat], receiverids), 'Actual retained fixed/soil source ID map failed')
    ref = dict(ids=ids, source_indices=sourceat, initial=pos0, pos=pospre,
        p0all=np.array(pre['PorePress0'][receiverat, 0]), pre_kappa=np.array(pre['Kplastic'][sourceat, 0]),
        time=float(pre['time']), layer=layer, top=top, bottom=bottom)
    cohorts = []
    for j, nativeid in enumerate(ids):
        cohorts.append(dict(native_id=int(nativeid), initial_layer=int(layer[j]),
            initial_x_m=float(pos0[j, 0]), initial_y_m=float(pos0[j, 1]), initial_z_m=float(pos0[j, 2]),
            PRE_x_m=float(pospre[j, 0]), PRE_y_m=float(pospre[j, 1]), PRE_z_m=float(pospre[j, 2]),
            fixed_initial_top_ID=bool(top[j]), fixed_initial_bottom_ID=bool(bottom[j]),
            fixed_P0_Pa=float(pre['PorePress0'][sourceat[j], 0]), inherited_PRE_kappa=float(ref['pre_kappa'][j])))
    return ref, cohorts


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


def physical_review(newbundle, oldbundle, ref):
    histories, extrema, matched, spatial, snapshots = [], [], [], [], {}
    last = {c: None for c in CASES}; tailpos = {}; series = {c: [] for c in CASES}
    for part in range(COUNT):
        data = {}
        for label, bundle in zip(CASES, (oldbundle, newbundle)):
            frame = core.read22(bundle, part)
            row, extremes, detail = physical_frame(frame, bundle['clocks'][part], label, ref, last[label])
            last[label] = detail['kappa'].copy(); histories.append(row); series[label].append(row); extrema += extremes; data[label] = detail
            if part == 60: tailpos[label] = detail['pos'].copy()
            if part in SELECTED:
                snapshots[(label, part)] = detail
                for j, nativeid in enumerate(detail['ids']):
                    spatial.append(dict(case=label, part=part, completed_step=row['completed_step'], actual_time_s=row['actual_time_s'], tau_s=row['tau_s'],
                        native_id=int(nativeid), x_m=float(detail['pos'][j, 0]), y_m=float(detail['pos'][j, 1]), z_m=float(detail['pos'][j, 2]),
                        p_Pa=float(detail['p'][j]), fixed_P0_Pa=float(detail['p0'][j]), native_p_minus_fixedP0_Pa=float(detail['excess'][j]),
                        NN_over_dp=float(detail['nn'][j]), kappa=float(detail['kappa'][j]), J=float(detail['J'][j]), n=float(detail['n'][j]),
                        k_m_s=float(detail['k'][j]), speed_m_s=float(detail['speed'][j]), total_stress_Frobenius_Pa=float(detail['total_norm'][j]),
                        dx_from_PRE_mm=float(1000*detail['du'][j, 0]), dy_from_PRE_mm=float(1000*detail['du'][j, 1]), dz_from_PRE_mm=float(1000*detail['du'][j, 2]),
                        initial_material_layer=int(ref['layer'][j]), fixed_initial_top_ID=bool(ref['top'][j]), fixed_initial_bottom_ID=bool(ref['bottom'][j])))
        a, b = data[CASES[0]], data[CASES[1]]
        need(bits(a['time_s']) == bits(b['time_s']) and np.array_equal(a['ids'], b['ids']), 'Actual same-time/material comparison differs')
        pressure = b['p']-a['p']; displacement = b['pos']-a['pos']; dkk, dij = b['total']-a['total'], b['ij']-a['ij']
        q = dict(part=part, completed_step=histories[-1]['completed_step'], actual_time_s=b['time_s'], tau_s=b['tau_s'],
            delta_p_RMS_Pa=float(np.sqrt(np.mean(pressure**2))), delta_p_absmax_Pa=float(np.abs(pressure).max()),
            delta_material_XYZ_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(displacement**2, axis=1)))),
            delta_material_XYZ_absmax_mm=float(1000*np.linalg.norm(displacement, axis=1).max()),
            delta_total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(dkk*dkk, axis=1)+2*np.sum(dij*dij, axis=1)))))
        for key in ('p_RMS_Pa', 'p_min_Pa', 'p_max_Pa', 'velocity_RMS_m_s', 'max_speed_m_s', 'max_kappa', 'min_J', 'max_J',
                    'top_material_settlement_from_PRE_mm', 'bottom_material_settlement_from_PRE_mm', 'front_x_m',
                    'max_settlement_from_PRE_mm', 'NN_min_over_dp', 'NN_nodes_lt_0p7dp', 'NN_nodes_lt_0p5dp', 'NN_nodes_lt_0p3dp',
                    'unique_pairs_lt_0p7dp', 'unique_pairs_lt_0p5dp', 'unique_pairs_lt_0p3dp'):
            q[key+'_RV_minus_original'] = series[CASES[1]][-1][key]-series[CASES[0]][-1][key]
        matched.append(q)
    summaries = {}
    for label in CASES:
        end = snapshots[(label, 90)]; move = end['pos']-tailpos[label]; h = series[label]
        summaries[label] = dict(final=h[-1], selected_saved_states=[h[i] for i in SELECTED],
            actual_tail_start_s=h[60]['actual_time_s'], actual_tail_end_s=h[90]['actual_time_s'],
            tail_same_material_motion_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(move*move, axis=1)))),
            tail_same_material_max_motion_mm=float(1000*np.linalg.norm(move, axis=1).max()),
            tail_front_advance_m=h[-1]['front_x_m']-h[60]['front_x_m'],
            first_observed_pair_lt_0p7dp=next((q for q in h if q['unique_pairs_lt_0p7dp'] > 0), None))
    need(len(histories) == 182 and len(matched) == 91 and len(spatial) == 2*len(SELECTED)*N, 'Complete scientific/material rows differ')
    return histories, extrema, matched, spatial, snapshots, summaries


def plots(history, snapshots, prefix):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.lines import Line2D
    colors = ('#2166AC', '#D6604D'); styles = ('-', '--', ':')
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
    fig.legend(handles=legend, loc='outside lower center', ncol=5, fontsize=9)
    fig.suptitle('C08: all91 actual matched saves; RV versus retained original\nNative p-P0 uses a fixed initial reference, not paper-defined plastic excess; changes are not half-step/theory errors', fontsize=12)
    files = [Path(str(prefix)+'_history.png')]; fig.savefig(files[-1], dpi=175); plt.close(fig)
    for part in SELECTED:
        states = [snapshots[(label, part)] for label in CASES]
        pos = np.concatenate([s['pos'] for s in states]); xmin, xmax = float(pos[:, 0].min()), float(pos[:, 0].max())
        zmin, zmax = float(pos[:, 2].min()), float(pos[:, 2].max())
        fullp = np.concatenate([s['p'] for s in states])/1000
        fullnn = np.concatenate([s['nn'] for s in states])
        need(float(fullp.min()) < float(fullp.max()) and float(fullnn.min()) < float(fullnn.max()), 'Constant field requires an explicitly reviewed plotting convention')
        norms = (Normalize(vmin=float(fullp.min()), vmax=float(fullp.max())), Normalize(vmin=float(fullnn.min()), vmax=float(fullnn.max())))
        fig = plt.figure(figsize=(14, 7), layout='constrained')
        grid = fig.add_gridspec(2, 4, width_ratios=(1., .028, 1., .028))
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
        fig.suptitle('All5000 original soil IDs in both cases; common actual saved time\nNo interpolation, smoothing, pressure clipping or excluded material points', fontsize=11)
        p = Path(str(prefix)+'_spatial_P'+str(part)+'.png'); fig.savefig(p, dpi=180); plt.close(fig); files.append(p)
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-receipt', type=Path, required=True)
    p.add_argument('--native-receipt', type=Path, required=True)
    p.add_argument('--execution-authorized', action='store_true')
    a = p.parse_args(); need(a.execution_authorized, 'Author-only until completed run, unique native and independent root offline admission')
    check = L/(TAG+'.check.json'); prefix = T/'figures'/TAG
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')), 'Existing complete/failed/partial derived evidence protected')
    consumed = []; files = []; result = dict(stage=TAG, passed=False, analysis_complete=False, physical_acceptance=False,
        solver_invocations=0, native_invocations=0, VTK_invocations=0, build_invocations=0, GPU_actions=0, SHA_scans=0)
    try:
        consumed = [stat(Path(__file__)), stat(NOTE), stat(Path(impl.__file__)), stat(impl.NOTE),
            stat(Path(typed.__file__)), stat(Path(core.__file__))]
        run, newbundle, oldbundle, sourcebundle, sourcedone, done, timing = load_inputs(a.run_receipt, a.native_receipt, consumed)
        rvrows, rv = rv_review(run, newbundle, sourcedone, consumed)
        reference, cohorts = source_reference(sourcebundle, sourcedone)
        history, extrema, matched, spatial, snapshots, summaries = physical_review(newbundle, oldbundle, reference)
        need(all(stat(q['path']) == q for q in consumed), 'Consumed original/new/reference input changed during offline review')
        for name, rows in (('history', history), ('matched', matched), ('extrema', extrema), ('source_cohorts', cohorts), ('rv_summary', rvrows), ('spatial', spatial), ('timing', timing)):
            path = Path(str(prefix)+'_'+name+'.csv'); write_csv(path, rows); files.append(path)
        files += plots(history, snapshots, prefix)
        need(all(stat(q['path']) == q for q in consumed), 'Consumed input changed while writing figures')
        result.update(passed=True, analysis_complete=True, source_run=stat(a.run_receipt), native_receipt=stat(a.native_receipt),
            reference_run=stat(CONTROL_RUN), reference_native=stat(CONTROL_NATIVE), reference_source=entry(run, 'source_native'),
            actual_matched_native_states=91, actual_soil_IDs=5000, typed_arrays=22, source_frames_read=[0, 1000],
            actual_initial_material_layers=50, actual_IDs_per_initial_layer=100, fixed_initial_top_IDs=reference['ids'][reference['top']].astype(int).tolist(),
            fixed_initial_bottom_IDs=reference['ids'][reference['bottom']].astype(int).tolist(),
            history_rows=len(history), matched_rows=len(matched), extrema_rows=len(extrema), spatial_rows=len(spatial),
            actual_source_time_s=reference['time'], actual_end_s=float(newbundle['clocks'][-1]['time_s']),
            actual_tau_end_s=float(newbundle['clocks'][-1]['time_s'])-reference['time'],
            all_actual_clock_matches=True, signed_dterror_values_preserved=True,
            Release_r3_new_CUDA_flag='--fmad=false', new_Release_r3_OFF_native_byteproof_claimed=False,
            RV_review=rv, summaries=summaries, selected_parts=list(SELECTED),
            observed_timing=dict(rows=timing, timing_CSV=str(Path(str(prefix)+'_timing.csv')),
                RV_over_original_new_updates_per_second=timing[1]['new_updates_per_TSimul_s']/timing[0]['new_updates_per_TSimul_s'],
                RV_over_original_loop_seconds=timing[1]['TSimul_loop_s']/timing[0]['TSimul_loop_s'],
                controlled_benchmark=False, actual_new_updates_each=180000,
                different_operator_trajectory_can_change_neighbor_cost=True, inherited_global_steps_or_absolute_physical_time_used_as_rate_numerator=False),
            comparison_is_half_step_or_theory_error=False, native_p_minus_P0_is_fixed_reference_not_paper_plastic_excess=True,
            NN_thresholds_are_descriptive_not_acceptance_gates=True,
            all5000_NN_and_unique_pair_counts_computed_per_state=True,
            storage_is_fluid_mass_claimed=False, sparse_RV_power_integrated_as_energy=False,
            full360000_stage_trace_reconstructed=False, first_force_state_inferred_from_first_native_save=False,
            automatic_other_psi_or_next_solver=False, visual_QA_pending=True,
            consumed=consumed, consumed_stats_unchanged=True, files=[stat(q) for q in files])
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__':
    main()
