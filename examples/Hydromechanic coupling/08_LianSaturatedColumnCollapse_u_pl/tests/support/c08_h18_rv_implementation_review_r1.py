"""Offline OFF1/Debug2 implementation evidence only; no executable, reader or build calls."""
import argparse
import csv
import json
import math
import re
import struct
import sys
from pathlib import Path
import c08_h18_storage_review_r2 as typedcore

T, L = typedcore.T, typedcore.L
need, read, stat, bind, entry, owned, same = typedcore.need, typedcore.read, typedcore.stat, typedcore.bind, typedcore.entry, typedcore.owned, typedcore.same
TAG = 'c08_h18_rv_implementation_review_r1'
NOTE = T/'notes'/(TAG+'.md')
BASE, SOIL, ACTIVE = 2000000, 5000, 6805
PROFILES = {'off1': (1, 2000001, 'Release'), 'debug2': (2, 2000002, 'Debug')}
RV_FILES = ('C08H18ResidualViscosity.csv', 'C08H18ResidualManufactured.csv', 'C08H18ResidualViscosityPolicy.json')
HEADER = ('record,phase,active,alpha,step_start_global,completed_global,step_start_time_s,force_stage_time_s,save_time_s,operator_dt_s,phase_calls,phase_commits,pre_calls,cor_calls,pre_commits,cor_commits,last_lambda_max_s_1,running_lambda_max_s_1,last_dt_lambda_half,running_dt_lambda_half,validated_soil_nodes,committed,error_bits,invalid_sorted_index,invalid_native_id,cuda_status,'
          'directed_edges,reverse_memberships,max_degree,gamma64,max_condition,max_normal_budget_ratio,max_commit_budget_ratio,work_W_per_m,form_W_per_m,work_defect_prediction_W_per_m,work_certificate_error_W_per_m,work_certificate_budget_W_per_m,work_budget_W_per_m,net_force_norm_N_per_m,net_force_budget_N_per_m,torque_N,torque_defect_prediction_N,torque_certificate_error_N,torque_certificate_budget_N,torque_budget_N,committed_work_W_per_m,committed_work_budget_W_per_m,committed_net_force_norm_N_per_m,committed_net_force_budget_N_per_m,committed_torque_N,committed_torque_budget_N,'
          'running_normal_ratio,running_float_commit_ratio,running_work_certificate_ratio,running_work_budget_ratio,running_net_force_ratio,running_torque_certificate_ratio,running_torque_budget_ratio,running_committed_work_ratio,running_committed_net_force_ratio,running_committed_torque_ratio,max_residual_m_s,residual_budget_m_s,max_force_N_per_m,force_budget_N_per_m').split(',')
MFG_HEADER = ('mode,name,step_start_global,source_time_s,operator_dt_s,directed_edges,reverse_memberships,max_degree,gamma64,max_condition,max_normal_budget_ratio,max_commit_budget_ratio,'
              'work_W_per_m,form_W_per_m,work_defect_prediction_W_per_m,work_certificate_error_W_per_m,work_certificate_budget_W_per_m,work_budget_W_per_m,net_force_norm_N_per_m,net_force_budget_N_per_m,torque_N,torque_defect_prediction_N,torque_certificate_error_N,torque_certificate_budget_N,torque_budget_N,committed_work_W_per_m,committed_work_budget_W_per_m,committed_net_force_norm_N_per_m,committed_net_force_budget_N_per_m,committed_torque_N,committed_torque_budget_N,'
              'max_residual_m_s,residual_budget_m_s,max_force_N_per_m,force_budget_N_per_m,committed,certificates_passed,manufactured_passed,error_bits,cuda_status').split(',')
INT_MAIN = {'active', 'step_start_global', 'completed_global', 'phase_calls', 'phase_commits', 'pre_calls', 'cor_calls', 'pre_commits', 'cor_commits', 'validated_soil_nodes', 'committed', 'error_bits', 'invalid_sorted_index', 'invalid_native_id', 'cuda_status', 'directed_edges', 'reverse_memberships', 'max_degree'}
INT_MFG = {'mode', 'step_start_global', 'directed_edges', 'reverse_memberships', 'max_degree', 'committed', 'certificates_passed', 'manufactured_passed', 'error_bits', 'cuda_status'}
RUNNING = ('running_normal_ratio', 'running_float_commit_ratio', 'running_work_certificate_ratio', 'running_work_budget_ratio', 'running_net_force_ratio', 'running_torque_certificate_ratio', 'running_torque_budget_ratio', 'running_committed_work_ratio', 'running_committed_net_force_ratio', 'running_committed_torque_ratio')


def bits(x): return struct.pack('<d', float(x))


def ratio(value, budget):
    need(value >= 0 and budget >= 0, 'Nonnegative certificate value/budget required')
    return value/budget if budget else (0. if value == 0 else math.inf)


def arithmetic_equal(a, b):
    # Verification of serialized derived arithmetic only; none of the actual
    # physical/certificate <= budgets below gets this allowance.
    return abs(a-b) <= 8*sys.float_info.epsilon*(abs(a)+abs(b))+8*float.fromhex('0x0.0000000000001p-1022')


def table(path, header, integers, text):
    rows = []
    with Path(path).open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        need(reader.fieldnames == header, 'Exact versioned sidecar header required')
        for raw in reader:
            need(list(raw) == header and None not in raw, 'Sidecar width differs')
            row = {}
            for key in header:
                if key in text:
                    row[key] = raw[key]
                elif key in integers:
                    need(raw[key].isdecimal(), 'Unsigned sidecar field differs: '+key)
                    row[key] = int(raw[key])
                else:
                    row[key] = float(raw[key])
                    need(math.isfinite(row[key]), 'Nonfinite sidecar field: '+key)
            rows.append(row)
    return rows


def check_native(profile, runpath, nativepath, consumed):
    count, end, configuration = PROFILES[profile]
    run, native = read(runpath), read(nativepath)
    need(run['passed'] and run['solver_completed'] and run['profile'] == profile and run['actual_steps'] == end and run['saved_frames'] == count and run['consumed_stats_unchanged']
         and run['RV_requested'] is (profile == 'debug2') and run['environment_override'] == {'C08_RV_H18': '1' if profile == 'debug2' else None}, 'Actual owned bounded solver result differs')
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1 and entry(native, 'source_run') == stat(runpath), 'One independent native receipt bound to this exact run required')
    actual = entry(run, 'actual_call'); call = read(actual['path']); owned(call)
    need(call['child'] and entry(run, 'program')['path'] in [call['program'], *call['arguments']], 'Actual tool argv must contain the frozen physical program')
    startpath = Path(str(runpath).removesuffix('.run.json')+'.start.json'); start = read(startpath)
    adentry = entry(run, 'root_admission'); admission = read(adentry['path'])
    need(start['owner'] == run['owner'] and start['root_admission'] == adentry and start['argv'] == run['argv'] and start['solver_argv'] == run['solver_argv'] and start['environment_override'] == run['environment_override'], 'Original start/run owner/argv/environment differs')
    need(call['owner']['pid'] == run['owner']['pid'] and call['owner']['created_epoch'] == run['owner']['created_epoch'] and call['child']['parent_pid'] == run['owner']['pid'] and call['child']['argv'] == run['argv'], 'Actual child/owner creation/argv binding differs')
    need(admission['authorized'] and admission['allowed_job'] == run['stage'] and admission['profile'] == profile and admission['phase'] == 'run' and not admission['automatic_native'] and not admission['automatic_next_job'], 'Exact independent root run admission required')
    for key in ('program', 'source_build', 'source_capture', 'source_archive', 'source_pre_file', 'input_xml', 'planned_steps'):
        need(start[key] == run[key], 'Original start/run frozen input binding differs: '+key)
    if profile == 'debug2':
        need(call['actual_target'] and same(call['actual_target']['exe'], run['program']['path']) and call['actual_target_Win32_exit'] == 0, 'Actual Debug solver target handle/exit required')
        need('--tool' in call['arguments'] and call['arguments'][call['arguments'].index('--tool')+1] == 'memcheck' and '--error-exitcode' in call['arguments'] and call['arguments'][call['arguments'].index('--error-exitcode')+1] == '99', 'Actual memcheck invocation required')
        logfile = bind(call['log']); log = Path(logfile['path']).read_text(encoding='utf-8', errors='replace')
        errors = re.findall(r'ERROR SUMMARY: ([0-9,]+) errors', log)
        leaks = re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations', log)
        need(errors and leaks and all(int(x.replace(',', '')) == 0 for x in errors) and all(int(x.replace(',', '')) == int(y.replace(',', '')) == 0 for x, y in leaks), 'Actual zero-error/zero-leak memcheck log required')
        need(run['memcheck_zero_errors_and_leaks'] is True and entry(run, 'memcheck_actual_call') == actual and call['actual_target']['parent_pid'] == call['child']['pid'] and call['actual_target']['argv'] == run['solver_argv'], 'Actual memcheck/target-parent/solver argv differs')
        consumed.append(logfile)
    ncallentry = entry(native, 'actual_call'); ncall = read(ncallentry['path']); owned(ncall)
    doneentry, metaentry = entry(native, 'native_completion'), entry(native, 'metadata')
    done, meta = read(doneentry['path']), read(metaentry['path']); root = Path(doneentry['path']).parent
    need(done['passed'] and done['stage'] == 'c08_h18_wend_native_r1.receiver' and done['samples'] == count and done['completed_steps'] == end and done['typed_arrays'] == 22 and done['typed_bytes_per_particle'] == 212, 'Actual original native profile/core differs')
    for key, value in {'actual_native_IDs_per_frame': ACTIVE, 'actual_fixed_IDs': 1805, 'soil_IDs': SOIL, 'ledger_checks': count*SOIL, 'P0_bits_checks': count*ACTIVE, 'nonempty_signed_intervals': count}.items():
        need(done[key] == value, 'Original complete native coverage differs: '+key)
    need(done['max_scalar_clock_error_s'] <= 1e-14 and done['max_ledger_relative_error'] <= 5e-13 and done['max_signed_dterror_s'] <= 1e-14 and done['FS23_pressure_checks'] > 0, 'Original native safety/clock/ledger/active-FS guard failed')
    need(meta['passed'] and meta['stage'] == 'c08_h18_rv_native_r1.metadata' and meta['profile'] == profile and meta['samples'] == count and meta['backend_argument'] == 'GPU' and meta['original_AV_private_keys_absent_headers'] == count and meta['residual_viscosity_proven_by_reader'] is False and meta['RV_program_owner_sidecar_review_required'] is True and meta['debug_profile_is_Release_bit_truth'] is False, 'RV-independent reader metadata required')
    planentry, preentry = entry(run, 'planned_steps'), entry(run, 'source_pre_file')
    need(same(preentry['path'], T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'), 'Original certified PRE required')
    plan = typedcore.table(planentry['path']); need(len(plan) == count and list(plan[0]) == ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s'], 'Original launch plan schema/count required')
    need([int(p['completed_step']) for p in plan] == list(range(BASE+1, end+1)), 'Only genuine first one/two updates admitted')
    args = ncall['arguments']
    need(len(args) == 8 and args[:3] == ['--receiver', profile, 'psi0'] and same(args[4], preentry['path']) and same(args[5], planentry['path']) and same(args[-1], root), 'Actual native profile/PRE/plan/output binding differs')
    rb = entry(native, 'reader_build'); reader = read(rb['path'])
    need(reader['passed'] and reader['consumed_stats_unchanged'] and reader['stage'] == 'c08_h18_rv_native_r1.build' and reader['actual_link_objects'] == 7 and not reader['JSph_objects_linked'] and same(ncall['program'], entry(reader, 'program')['path']), 'Actual frozen new seven-object reader required')
    buildentry = entry(run, 'source_build'); build = read(buildentry['path'])
    need(build['passed'] and build['configuration'] == configuration and build['consumed_stats_unchanged'] and build['actual_link_objects'] == 114 and build['retained_original_objects'] == 112 and build['private_objects'] == 2, 'Actual private configuration/build required')
    need(entry(build, 'program') == entry(run, 'program') and entry(build, 'source_capture') == entry(run, 'source_capture') and entry(build, 'source_archive') == entry(run, 'source_archive'), 'Actual frozen private source/program binding differs')
    source = entry(run, 'source_native'); sourcedone = read(source['path'])
    need(sourcedone['passed'] and sourcedone['certified_PRE'] and sourcedone['samples'] == 1001 and sourcedone['completed_steps'] == BASE, 'Original full qualified PRE receipt required')
    bundle = typedcore.typed(root, ACTIVE, count, consumed)
    for i, (clock, p) in enumerate(zip(bundle['clocks'], plan)):
        need(int(clock['part']) == int(p['part']) == i and int(clock['completed_step']) == int(p['completed_step']) and int(clock['saved_step']) == int(p['saved_step']) and float(clock['dt_s']) == float(p['dt_s']) == 5e-6 and abs(float(clock['time_s'])-float(p['time_s'])) <= 1e-14, 'Actual native clock/step/launch plan differs')
    need(set(build['private_sources']) == set(run['private_sources']) == {'host', 'CUDA', 'header'} and build['private_sources'] == run['private_sources'], 'Actual private host/CUDA/header source binding differs')
    consumed.extend(bind(q) for q in build['private_sources'].values())
    consumed.extend([stat(runpath), stat(nativepath), stat(startpath), adentry, actual, ncallentry, doneentry, metaentry, planentry, preentry, rb, buildentry, source])
    consumed.extend(entry(run, key) for key in ('program', 'source_capture', 'source_archive', 'input_xml', 'Run_out'))
    return bundle, run, sourcedone


def off_byteproof(bundle, run, consumed):
    output = Path(entry(run, 'Run_out')['path']).parent
    need(run['RV_files_absent'] is True and all(not (output/name).exists() for name in RV_FILES), 'Default-OFF must create no RV CSV/manufactured/policy files')
    receipt = T/'logs/c08_h18_as03_n255_native_r1.check.json'; q = read(receipt)
    need(q['passed'] and q['consumed_stats_unchanged'] and q['reader_invocations'] == 1, 'Passed retained original AS03 native control required')
    doneentry = entry(q, 'native_completion'); done = read(doneentry['path'])
    need(done['passed'] and done['samples'] == 91 and done['completed_steps'] == 2180000, 'Retained genuine91-frame control required')
    control = Path(doneentry['path']).parent
    ref = typedcore.typed(control, ACTIVE, 91, consumed)
    need(bundle['count'] == 1 and bundle['dtype'] == ref['dtype'], 'Genuine one-frame schema required')
    need((bundle['root']/'typed22_layout.csv').read_bytes() == (control/'typed22_layout.csv').read_bytes(), 'Literal original layout bytes differ')
    with (bundle['root']/'typed22.bin').open('rb') as a, (control/'typed22.bin').open('rb') as b:
        need(struct.unpack('<III', a.read(12)) == (ACTIVE, 22, 1) and struct.unpack('<III', b.read(12)) == (ACTIVE, 22, 91), 'Preserve true1/91 native headers')
        n = bundle['dtype'].itemsize
        need(a.read(n) == b.read(n) and not a.read(1), 'First genuine all22-array/time record bytes differ')
    with (bundle['root']/'clocks.csv').open('rb') as a, (control/'clocks.csv').open('rb') as b:
        need(a.readline() == b.readline() and a.readline() == b.readline() and not a.readline(), 'First literal actual signed-clock row/header differs')
    consumed += [stat(receipt), doneentry]
    return dict(compared_records=1, new_header_samples=1, control_header_samples=91, all22_and_actual_time_bytes_equal=True, literal_layout_equal=True, literal_signed_clock_equal=True, headers_rewritten=False, interpolation=False, RV_files_created=False)


def certificates(row):
    edges, reverse, degree = row['directed_edges'], row['reverse_memberships'], row['max_degree']
    need(edges > 0 and edges % 2 == 0 and reverse == edges and 0 < degree < SOIL, 'Actual symmetric neighbor certificate differs')
    ne = 64.*float(SOIL+edges//2+degree+1)*sys.float_info.epsilon
    gamma = ne/(1-ne)
    need(0 < ne < 1 and arithmetic_equal(row['gamma64'], gamma) and row['max_condition'] >= 0, 'Actual graph-derived gamma differs')
    for key in ('max_normal_budget_ratio', 'max_commit_budget_ratio'):
        need(0 <= row[key] <= 1, 'Unchanged node certificate ratio failed: '+key)
    nonnegative = ('form_W_per_m', 'work_certificate_budget_W_per_m', 'work_budget_W_per_m', 'net_force_norm_N_per_m', 'net_force_budget_N_per_m', 'torque_certificate_budget_N', 'torque_budget_N', 'committed_work_budget_W_per_m', 'committed_net_force_norm_N_per_m', 'committed_net_force_budget_N_per_m', 'committed_torque_budget_N', 'max_residual_m_s', 'residual_budget_m_s', 'max_force_N_per_m', 'force_budget_N_per_m')
    need(all(row[key] >= 0 for key in nonnegative), 'Negative original absolute/form/certificate budget')
    work_error = row['work_W_per_m']+2*row['form_W_per_m']-row['work_defect_prediction_W_per_m']
    torque_error = row['torque_N']-row['torque_defect_prediction_N']
    # Large terms can cancel in these derived residuals. Compare GPU-exported
    # and host-recomputed arithmetic on their original operand scale, not on
    # the two small residuals. This never changes an original certificate bound.
    work_export_budget = 8*sys.float_info.epsilon*(abs(row['work_W_per_m'])+2*row['form_W_per_m']+abs(row['work_defect_prediction_W_per_m'])+abs(row['work_certificate_error_W_per_m']))
    torque_export_budget = 8*sys.float_info.epsilon*(abs(row['torque_N'])+abs(row['torque_defect_prediction_N'])+abs(row['torque_certificate_error_N']))
    need(abs(row['work_certificate_error_W_per_m']-work_error) <= work_export_budget
         and abs(row['torque_certificate_error_N']-torque_error) <= torque_export_budget,
         'Independently recomputed defect export arithmetic differs')
    work_ratio = max(ratio(abs(row['work_W_per_m']+2*row['form_W_per_m']), row['work_budget_W_per_m']), ratio(max(0., row['work_W_per_m']), row['work_budget_W_per_m']))
    values = [row['max_normal_budget_ratio'], row['max_commit_budget_ratio'], ratio(abs(row['work_certificate_error_W_per_m']), row['work_certificate_budget_W_per_m']), work_ratio, ratio(row['net_force_norm_N_per_m'], row['net_force_budget_N_per_m']), ratio(abs(row['torque_certificate_error_N']), row['torque_certificate_budget_N']), ratio(abs(row['torque_N']), row['torque_budget_N']), ratio(max(0., row['committed_work_W_per_m']), row['committed_work_budget_W_per_m']), ratio(row['committed_net_force_norm_N_per_m'], row['committed_net_force_budget_N_per_m']), ratio(abs(row['committed_torque_N']), row['committed_torque_budget_N'])]
    need(all(math.isfinite(x) and 0 <= x <= 1 for x in values) and row['work_W_per_m'] <= row['work_budget_W_per_m'], 'Original actual raw/committed work/netforce/torque budget failed')
    return values


def on_debug(bundle, run, sourcedone, consumed):
    sidecar, manufactured, policyentry = (entry(run, key) for key in ('rv_sidecar', 'rv_manufactured', 'rv_policy'))
    output = Path(entry(run, 'Run_out')['path']).parent
    need([Path(q['path']).name for q in (sidecar, manufactured, policyentry)] == list(RV_FILES)
         and all(Path(q['path']).parent == output for q in (sidecar, manufactured, policyentry)), 'Actual three private RV output paths differ')
    policy = read(policyentry['path'])
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
    need(set(policy) == set(expected), 'Actual frozen version2 RV policy key set differs')
    for key, value in expected.items():
        need(type(policy[key]) is type(value) and policy[key] == value, 'Actual typed RV policy differs: '+key)
    rows = table(sidecar['path'], HEADER, INT_MAIN, {'record', 'phase'})
    modes = table(manufactured['path'], MFG_HEADER, INT_MFG, {'name'})
    need(len(rows) == 4 and len(modes) == 3 and len(bundle['clocks']) == 2, 'Actual Debug2 must have four actual phase rows and three manufactured rows')
    previous = {'Pre': dict(running=[0.]*10, maxlambda=0., maxbound=0.), 'Cor': dict(running=[0.]*10, maxlambda=0., maxbound=0.)}
    source_time = float(sourcedone['actual_end_s']); observed = []
    for part in range(2):
        saved_time = source_time+5e-6
        clock = bundle['clocks'][part]
        need(bits(float(clock['time_s'])) == bits(saved_time), 'Actual Debug clock is not scalar PRE+=dt')
        for phaseindex, phase in enumerate(('Pre', 'Cor')):
            row = rows[2*part+phaseindex]; updates = part+1
            need(row['record'] == 'save' and row['phase'] == phase and row['active'] == row['committed'] == 1 and bits(row['alpha']) == bits(.1), 'Only actual successful saved active phase records admitted')
            need(row['step_start_global'] == BASE+part and row['completed_global'] == BASE+updates and row['validated_soil_nodes'] == SOIL, 'Actual stage/global node counters differ')
            need(all(row[key] == updates for key in ('phase_calls', 'phase_commits', 'pre_calls', 'cor_calls', 'pre_commits', 'cor_commits')), 'Actual Pre/Cor call/commit cumulative count differs')
            need(row['error_bits'] == row['cuda_status'] == 0 and row['invalid_sorted_index'] == row['invalid_native_id'] == 2**32-1, 'Actual stage rejected or invalid-node sentinel changed')
            need(all(bits(row[key]) == bits(source_time) for key in ('step_start_time_s', 'force_stage_time_s')) and bits(row['save_time_s']) == bits(saved_time) and bits(row['operator_dt_s']) == bits(5e-6), 'Actual original source clock/dt differs; no half-clock substitution')
            need(row['last_lambda_max_s_1'] >= 0 and arithmetic_equal(row['last_dt_lambda_half'], row['operator_dt_s']*row['last_lambda_max_s_1']*.5) and 0 <= row['last_dt_lambda_half'] <= 1, 'Original isolated necessary damping bound failed')
            values = certificates(row); prior = previous[phase]
            maxlambda, maxbound = max(prior['maxlambda'], row['last_lambda_max_s_1']), max(prior['maxbound'], row['last_dt_lambda_half'])
            need(bits(row['running_lambda_max_s_1']) == bits(maxlambda) and bits(row['running_dt_lambda_half']) == bits(maxbound), 'Actual per-phase running lambda/bound differs')
            actualrunning = [row[key] for key in RUNNING]
            expectedrunning = [max(old, current) for old, current in zip(prior['running'], values)]
            need(all(0 <= actual <= 1 and arithmetic_equal(actual, expected) for actual, expected in zip(actualrunning, expectedrunning)), 'Actual per-phase running ratio maxima differ or failed')
            previous[phase] = dict(running=actualrunning, maxlambda=maxlambda, maxbound=maxbound)
            observed.append(dict(completed=BASE+updates, phase=phase, last_lambda_max_s_1=row['last_lambda_max_s_1'], last_dt_lambda_half=row['last_dt_lambda_half'], running_ratios=dict(zip(RUNNING, actualrunning))))
        source_time = saved_time
    manufactured_results = []
    for mode, name, row in zip((1, 2, 3), ('translation', 'full_affine', 'rigid_rotation'), modes):
        need(row['mode'] == mode and row['name'] == name and row['step_start_global'] == BASE and bits(row['source_time_s']) == bits(sourcedone['actual_end_s']) and bits(row['operator_dt_s']) == bits(5e-6), 'Genuine first-force manufactured mode/clock differs')
        need(row['committed'] == row['error_bits'] == row['cuda_status'] == 0 and row['certificates_passed'] == row['manufactured_passed'] == 1, 'Manufactured scratch-only/error/null certificate failed')
        for key in ('directed_edges', 'reverse_memberships', 'max_degree', 'gamma64', 'max_condition'):
            need(row[key] == rows[0][key], 'Manufactured graph/condition differs from genuine first real Pre graph: '+key)
        values = certificates(row)
        residual_ratio, force_ratio = ratio(row['max_residual_m_s'], row['residual_budget_m_s']), ratio(row['max_force_N_per_m'], row['force_budget_N_per_m'])
        need(math.isfinite(residual_ratio) and math.isfinite(force_ratio) and residual_ratio <= 1 and force_ratio <= 1, 'Original actual manufactured residual/force-null budget failed')
        manufactured_results.append(dict(mode=mode, name=name, residual_ratio=residual_ratio, force_ratio=force_ratio, raw_and_candidate_certificates=dict(zip(RUNNING, values)), committed=False))
    consumed += [sidecar, manufactured, policyentry]
    return dict(actual_native_states=2, actual_stage_rows=4, exact_main_columns=66, policy_schema=2,
        actual_Pre_calls=2, actual_Cor_calls=2, actual_Pre_commits=2, actual_Cor_commits=2,
        all_four_nonaffine_stage_certificates_checked=True, all_Debug_stages_are_observed=True,
        actual_3_manufactured_modes=manufactured_results, actual_phase_results=observed,
        all_manufactured_and_nonaffine_original_budgets_passed=True,
        independently_recomputed=['actual graph count/gamma', 'dt*lambda/2', 'work/torque defect residual arithmetic', 'ratios and complete per-phase Debug running maxima'],
        budgets_formed_by_bound_source=True, all_neighbor_budget_primitives_exported=False,
        independent_normal_or_null_budget_reconstruction_claimed=False,
        physical_acceptance=False, Debug_is_Release_bit_truth=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', choices=tuple(PROFILES), required=True)
    p.add_argument('--run-receipt', type=Path, required=True)
    p.add_argument('--native-receipt', type=Path, required=True)
    p.add_argument('--execution-authorized', action='store_true')
    a = p.parse_args(); need(a.execution_authorized, 'Author-only until root full read and offline admission')
    check = L/('c08_h18_rv_'+a.profile+'_implementation_review_r1.check.json')
    need(not check.exists(), 'Prior complete or failed offline review protected')
    consumed = []; result = dict(stage=TAG, profile=a.profile, passed=False, solver_invocations=0, native_invocations=0, build_invocations=0, GPU_actions=0, SHA_scans=0, physical_acceptance=False)
    try:
        consumed = [stat(Path(__file__)), stat(NOTE), stat(Path(typedcore.__file__)), stat(Path(typedcore.core.__file__))]
        bundle, run, source = check_native(a.profile, a.run_receipt, a.native_receipt, consumed)
        proof = off_byteproof(bundle, run, consumed) if a.profile == 'off1' else on_debug(bundle, run, source, consumed)
        need(all(stat(q['path']) == q for q in consumed), 'A bound consumed artifact changed during offline review')
        result.update(passed=True, source_run=stat(a.run_receipt), native_receipt=stat(a.native_receipt), proof=proof, consumed=consumed, consumed_stats_unchanged=True, Debug_Release_bit_equivalence_claimed=False, manufactured_budget_basis_reconstructed_from_neighbors=False, clumping_repair_or_physical_acceptance_claimed=False)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')


if __name__ == '__main__':
    main()
