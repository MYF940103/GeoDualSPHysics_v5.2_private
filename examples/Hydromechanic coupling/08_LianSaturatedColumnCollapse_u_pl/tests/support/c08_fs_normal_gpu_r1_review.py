"""Offline review of two already completed GPU Debug controls; never invoke any program."""
import argparse, csv, json, math, re, struct
from pathlib import Path

T = Path(__file__).resolve().parents[1]
L, F = T / 'logs', T / 'figures'
TAG = 'c08_fs_normal_gpu_r1'
RUN = L / (TAG + '.run.json')
CPU_RUN = L / 'c08_fs_matrix_cpu_r2.run.json'
CHECK = L / (TAG + '.review.json')
NOTE = T / 'notes' / (TAG + '_review.md')
CSVS = {q: F / (TAG + '_' + q + '.csv') for q in ('control_metrics', 'cpu_gpu_metrics', 'node_differences')}
B = 32 * 2**-23 + 4096 * 2**-52
CONSUMED = []


def need(ok, text):
    if not ok: raise RuntimeError(text)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def bind(entry):
    need(stat(entry['path']) == entry, 'Consumed stat changed: ' + entry['path'])
    CONSUMED.append(entry)
    return Path(entry['path'])


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def verify():
    for entry in CONSUMED: need(stat(entry['path']) == entry, 'Consumed stat changed during review: ' + entry['path'])


def same_path(a, b):
    return Path(a).resolve() == Path(b).resolve()


def f32(value): return struct.unpack('<f', struct.pack('<f', value))[0]
def bits(value): return struct.unpack('<I', struct.pack('<f', value))[0]
def rms(values): return math.sqrt(math.fsum(v*v for v in values) / len(values)) if values else 0.
def absmax(values): return max((abs(v) for v in values), default=0.)
def dot(a, b): return math.fsum(x*y for x, y in zip(a, b))
def surface(node): return int(node['fstype']) in (2, 3)


def table(path, controls=False):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream); names = reader.fieldnames
        need(names and len(names) == len(set(names)), 'Unique CSV columns required')
        result = []
        for item in reader:
            need(None not in item and all(v is not None for v in item.values()), 'Malformed CSV row')
            row = {k: float(v) for k, v in item.items()}
            need(all(math.isfinite(v) for v in row.values()), 'Nonfinite CSV value')
            if controls:
                fields = [q for q in names if q.startswith('field_')]
                need(len(fields) == 1, 'One explicit field column required')
                row['field'] = row.pop(fields[0])
            result.append(row)
    return result


def index(rows, fields):
    result = {}
    for row in rows:
        key = tuple(int(row[q]) for q in fields)
        need(all(row[q] == key[i] for i, q in enumerate(fields)) and key not in result, 'Duplicate/noninteger CSV key')
        result[key] = row
    return result


def items(run):
    value = run['completed']
    result = value if isinstance(value, dict) else {q['label']: q for q in value}
    need(set(result) == {'Raw', 'Normal'} and len(value) == 2, 'Exactly Raw and Normal completed items required')
    return result


def tool_call(entry):
    call = read(bind(entry))
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None,
         'Actual tool exit or owned-handle evidence failed')
    child = call['child']
    need(child['pid'] > 0 and child['creation_filetime_100ns'] > 0 and child['parent_pid'] == call['owner']['pid']
         and same_path(child['exe'], call['program']) and child['argv'] == [call['program'], *call['arguments']],
         'Actual owned tool identity/argv differs')
    bind(call['log'])
    return call


def build_review(entry):
    build = read(bind(entry))
    need(build['passed'] and build['configuration'] == 'Debug' and build['intervention'] == 'free_surface_normal_taylor_projection'
         and build['actual_typed_exit_code'] == build['actual_Win32_exit'] == 0
         and build['consumed_stats_unchanged'] and not build['public_source_changed'] and not build['physical_acceptance']
         and build['actual_link_objects'] == 113 and build['retained_public_objects'] == 111
         and build['shared_entry_object'] and build['physical_objects_recompiled'] == 1
         and build['compile_invocations'] == 2 and build['link_invocations'] == 2,
         'Closed private GPU Debug113-object build required')
    need(set(build['source_differences']) == {'src/source/JSphCpu.cpp', 'src/source/JSphGpu_ker.cu'}
         and build['exact_inverse_original_bytes'] and build['original_mdbc_include_unchanged'], 'Wrong private intervention')
    for key in ('source_capture', 'source_archive', 'baseline_source_build', 'baseline_source_capture', 'baseline_source_archive',
                'private_gpu_source', 'private_wall_include', 'fixture', 'fixture_object', 'retained_harness',
                'original_gpu_object', 'candidate_object', 'replaced_main'):
        bind(build[key])
    for q in build['runtime'] + build['consumed']: bind(q)
    need(len(build['runtime']) == 7 and len(build['calls']) == 4, 'Seven runtimes/four actual build calls required')
    for q in build['calls']: tool_call(q)
    closures = {}
    for label in ('Raw', 'Normal'):
        bind(build['programs'][label]); values = build['project_objects'][label]
        need(len(values) == 113, 'Actual link must contain113 entries')
        closures[label] = {str(bind(q)) for q in values}
        need(len(closures[label]) == 113 and build['fixture_object']['path'] in closures[label], 'Unique shared-entry closure required')
    need(closures['Raw'] - closures['Normal'] == {build['original_gpu_object']['path']}
         and closures['Normal'] - closures['Raw'] == {build['candidate_object']['path']}, 'Only one GPU physical object may differ')
    return build


def bundle(run_entry, build, gpu):
    run = read(bind(run_entry))
    need(run['passed'] and run['physical_acceptance'] is False, 'Passed nonphysical run receipt required')
    sanitizer = bind(run['sanitizer']) if gpu else None
    if 'consumed_stats_unchanged' in run: need(run['consumed_stats_unchanged'], 'Run consumed stats changed')
    for q in run.get('consumed', []): bind(q)
    result = {}
    for label, item in items(run).items():
        program = bind(item['program']); call = tool_call(item['actual_call'])
        need(item['program'] == build['programs'][label], 'Run program differs from actual build')
        donepath = bind(item['completion']); out = donepath.parent
        expected_out = T / 'outputs' / ((TAG if gpu else 'c08_fs_matrix_cpu_r2') + '_' + label.lower())
        need(out == expected_out.resolve(), 'Unexpected retained output directory')
        argv = [str(program), '--expect', label.lower(), '--out', str(out)]
        if gpu:
            need(call['actual_target_Win32_exit'] == 0 and call['actual_target'] is not None, 'Actual GPU target handle/zero exit required')
            target = call['actual_target']
            need(target['pid'] > 0 and target['creation_filetime_100ns'] > 0 and same_path(target['exe'], program)
                 and target['argv'] == argv and target['pid'] != call['child']['pid'], 'Actual GPU target identity/argv differs')
            need(same_path(call['program'], sanitizer) and Path(call['program']).name.lower() == 'compute-sanitizer.exe'
                 and '/CUDA/v11.7/' in Path(call['program']).as_posix(), 'Actual stat-bound CUDA11.7 sanitizer required')
            args = call['arguments']; start = [i for i, q in enumerate(args) if same_path(q, program)]
            need(len(start) == 1 and args[start[0]:] == argv, 'Sanitizer target argv differs')
            prefix = args[:start[0]]
            for key, value in (('--tool', 'memcheck'), ('--leak-check', 'full'), ('--error-exitcode', '99')):
                need(prefix.count(key) == 1 and prefix[prefix.index(key)+1] == value, 'Missing actual sanitizer option: ' + key)
            san = bind(item['memcheck_log'])
            need(prefix.count('--log-file') == 1 and same_path(prefix[prefix.index('--log-file')+1], san)
                 and not same_path(call['log']['path'], san), 'Distinct actual sanitizer and console logs required')
            text = san.read_text(encoding='utf-8-sig')
            errors = re.findall(r'ERROR SUMMARY:\s*([0-9,]+) errors', text)
            leaks = re.findall(r'LEAK SUMMARY:\s*([0-9,]+) bytes leaked in ([0-9,]+) allocations', text)
            need(errors and leaks and all(int(q.replace(',', '')) == 0 for q in errors)
                 and all(int(a.replace(',', '')) == int(b.replace(',', '')) == 0 for a, b in leaks), 'Actual ERROR/leak summaries missing or nonzero')
        else:
            need(same_path(call['program'], program) and call['arguments'] == argv[1:], 'Actual retained CPU argv differs')
        files = {Path(q['path']).name: bind(q) for q in item['files']}
        required = {'controls.csv', 'nodes.csv', 'free_off_rates.bin', 'Run.out'} if gpu else {'controls.csv', 'nodes.csv', 'matrix.csv'}
        need(set(files) == required and len(item['files']) == len(required) and all(q.parent == out for q in files.values()), 'Exact retained output files required')
        done = read(donepath)
        need(done['formula_reference_matched'] and done['expected_reference'] == label.lower()
             and not done['reference_mode_changes_production'] and done['completed_physical_steps'] == 0
             and done['physical_acceptance'] is False, 'Completion formula/zero-step qualification differs')
        if gpu:
            need(done['stage'] == TAG and done['production_GPU_FS_C'] and not done['CPU_FS_C_injected']
                 and done['porosity_feedback_tracking'] and done['input_and_tail_bits_preserved']
                 and done['total_control_rows'] == 1620 and done['node_rows'] == 162
                 and not done['full_basis_computed'] and not done['CPU_GPU_bitwise_equivalence_proven']
                 and not done['coupled_stability_proven'], 'GPU completion scope/tail guards differ')
            log = files['Run.out'].read_text(encoding='utf-8-sig')
            devices = re.findall(r'^device0=(.*?) compute=', log, re.M)
            need(len(devices) == 1 and re.search(r'\bRTX\s*3050\b', devices[0], re.I) and 'A6000' not in devices[0].upper()
                 and 'physical_steps=0' in log and 'expected_reference=' + label.lower() in log, 'Actual Run.out must identify RTX3050 and zero steps')
        nodes = index(table(files['nodes.csv']), ('profile', 'native_id'))
        controls = index(table(files['controls.csv'], True), ('profile', 'field', 'free_on', 'native_id'))
        need(set(nodes) == {(p, i) for p in range(2) for i in range(81)}, 'Complete own162-node grid required')
        expected = {(p, f, on, i) for p in range(2) for f in range(5 if gpu else 3) for on in range(2) for i in range(81)}
        if not gpu: expected |= {(p, 3, 1, i) for p in range(2) for i in range(81)}
        need(set(controls) == expected, 'Complete keyed controls required')
        result[label] = dict(item=item, done=done, files=files, nodes=nodes, controls=controls,
                             device=devices[0] if gpu else None)
    return result


def controls_review(label, data):
    rows, nodes, done = data['controls'], data['nodes'], data['done']
    profiles = {q['profile']: q for q in done['profiles']}
    need(set(profiles) == {0, 1}, 'Exactly two GPU profile completions required')
    witnesses, inner_bits, maxima = [0, 0], [0, 0], {p: dict(reference=0., hydro=0., chain=0.) for p in range(2)}
    offvalues, metrics = [], []
    n0, kw, rho, k0, gz = f32(.35), 1e9, 1000., f32(.0002), f32(-9.81)
    solid = 1-n0; v0 = f32(2072.5*.04*.04)/2072.5
    for (profile, native), node in nodes.items():
        ix, iz = native % 9-4, native//9-4; j = 1+(ix+2*iz)/512 if profile else 1.
        need(node['J'] == j and node['x_m'] == 1+ix*.04+(.04/8 if iz<4 else 0) and node['y_m'] == 0 and node['z_m'] == 1+iz*.04, 'GPU own manufacture differs')
        expected = dict(n=1-solid/j, V_m2=v0*j, rho_exact_kg_m3=rho+(2072.5-rho)/j,
                        k_m_s=k0 if j == 1 else k0*math.exp((j-1)/(solid*2)))
        for key, value in expected.items(): need(abs(node[key]-value) <= B*max(1, abs(value)), 'GPU ledger differs: ' + key)
        need(node['rho_cache_kg_m3'] == f32(expected['rho_exact_kg_m3']), 'GPU uploaded rho cache differs')
    for profile in range(2):
        for field in range(5):
            for native in range(81):
                node = nodes[profile, native]; ix, iz = native%9-4, native//9-4
                p = -4096+rho*gz*(node['z_m']-1) if field == 0 else -16+(ix/8+iz/16 if field == 1 else ix/4+iz/8 if field == 2 else ix/4 if field == 3 else 0)
                a = (0., 0., -gz) if field == 0 else (ix/128+iz/256, 0., ix/256-iz/128) if field == 1 else (0., 0., 0.)
                for on in range(2):
                    row = rows[profile, field, on, native]; limit = row['arithmetic_budget_Pa_s']; actual = row['actual_rate_Pa_s']; ref = row['reference_rate_Pa_s']
                    need(limit > 0 and row['input_quantization_budget_Pa_s'] >= 0 and row['p_Pa'] == f32(p) and row['p_Pa'] < 0
                         and row['actual_bits'] == bits(actual) and row['fstype'] == node['fstype'], 'GPU pressure/bits/label/budget differs')
                    ratio = abs(actual-ref)/limit; need(ratio <= 1, 'GPU actual/reference arithmetic gate failed')
                    maxima[profile]['reference'] = max(maxima[profile]['reference'], ratio)
                    gp = (row['gp_x'], 0., row['gp_z']); lx = (row['Lx_x'], 0., row['Lx_z']); gj = (row['gradJ_x'], 0., row['gradJ_z'])
                    n = (node['normal_x'], node['normal_y'], node['normal_z']); corr = gp
                    raw = bool(on and surface(node) and label == 'Raw')
                    if on and surface(node) and label == 'Normal':
                        nn = dot(n, n); need(nn > 0, 'Invalid GPU FS normal')
                        flux = dot(n, tuple(g+rho*b for g, b in zip(gp, a)))/nn; corr = tuple(g-v*flux for g, v in zip(gp, n))
                    lap = row['LP']+rho*(dot(a, lx)+row['da']) if raw else row['LP']-dot(corr, lx)+rho*row['da']
                    scale = kw/node['n']/(rho*9.80665); dk = node['k_m_s']/(solid*2)
                    chain = dk*dot(gj, tuple(g+rho*b for g, b in zip(corr, a)))
                    need(abs(scale*(node['k_m_s']*lap+chain)-ref) <= limit
                         and abs(scale*(node['k_m_s']*row['lap']+row['chain'])-ref) <= limit,
                         'GPU exported operator terms disagree with intended reference')
                    if not profile: need(row['gradJ_x'] == row['gradJ_z'] == row['chain'] == 0, 'Uniform-J chain is nonzero')
                    if field == 0:
                        nullratio = abs(actual)/(2*limit+row['input_quantization_budget_Pa_s']); need(nullratio <= 1, 'GPU F0 null gate failed')
                        maxima[profile]['hydro'] = max(maxima[profile]['hydro'], nullratio)
                    if field == 4: need(actual == ref == 0, 'GPU constant negative null failed')
                    if field == 2 and on and profile and surface(node):
                        chainratio = abs(scale*row['chain'])/limit; witnesses[profile] += chainratio > 1
                        maxima[profile]['chain'] = max(maxima[profile]['chain'], chainratio)
                offvalues.append(rows[profile, field, 0, native]['actual_rate_Pa_s'])
                if not surface(node):
                    need(rows[profile, field, 0, native]['actual_bits'] == rows[profile, field, 1, native]['actual_bits'], 'GPU interior OFF/ON bits differ'); inner_bits[profile] += 1
            for on in range(2):
                group = [rows[profile, field, on, i] for i in range(81)]
                metrics.append(dict(label=label, profile=profile, field=field, free_on=on, rows=81,
                    rate_RMS_Pa_s=rms([q['actual_rate_Pa_s'] for q in group]), rate_abs_max_Pa_s=absmax([q['actual_rate_Pa_s'] for q in group]),
                    actual_reference_RMS_Pa_s=rms([q['actual_rate_Pa_s']-q['reference_rate_Pa_s'] for q in group]),
                    max_arithmetic_ratio=max(abs(q['actual_rate_Pa_s']-q['reference_rate_Pa_s'])/q['arithmetic_budget_Pa_s'] for q in group)))
        p = profiles[profile]
        need(p['controls'] == 810 and p['negative_projection_checks'] == 5 and p['interior_bits'] == inner_bits[profile]
             and p['nonzero_FS_chain_witnesses'] == witnesses[profile]
             and p['native_FS'] == sum(surface(nodes[profile, i]) for i in range(81))
             and p['native_inner'] == 81-p['native_FS'] and p['native_FS'] > 0 and p['native_inner'] > 0
             and surface(nodes[profile, 76]), 'GPU completion counters differ from exported controls')
    need(witnesses[1] > 0, 'Profile1 lacks a resolved actual FS chain contribution')
    binary = data['files']['free_off_rates.bin'].read_bytes()
    need(binary == struct.pack('<810f', *offvalues), 'Actual OFF binary differs from keyed CSV bits/count')
    return metrics, dict(nonzero_FS_chain_witnesses=witnesses, interior_bit_checks=inner_bits, maxima=maxima)


def comparison(gpu, cpu):
    rate_metrics, node_metrics = [], []
    for label in ('Raw', 'Normal'):
        g, c = gpu[label], cpu[label]
        for profile in range(2):
            pairs = [(g['nodes'][profile, i], c['nodes'][profile, i]) for i in range(81)]
            node_metrics.append(dict(label=label, profile=profile, rows=81,
                classification_mismatches=sum(a['fstype'] != b['fstype'] for a, b in pairs),
                max_normal_L2=max(math.sqrt(math.fsum((a[q]-b[q])**2 for q in ('normal_x','normal_y','normal_z'))) for a,b in pairs),
                max_C_component_abs=max(abs(a[q]-b[q]) for a,b in pairs for q in ('Cxx','Cxz','Czx','Czz')),
                max_posdiv_abs=max(abs(a['posdiv']-b['posdiv']) for a,b in pairs)))
            for field in range(3):
                for on in range(2):
                    pairs = [(g['controls'][profile,field,on,i],c['controls'][profile,field,on,i]) for i in range(81)]
                    delta = [a['actual_rate_Pa_s']-b['actual_rate_Pa_s'] for a,b in pairs]
                    rate_metrics.append(dict(label=label,profile=profile,field=field,free_on=on,rows=81,
                        GPU_rate_RMS_Pa_s=rms([a['actual_rate_Pa_s'] for a,b in pairs]),CPU_rate_RMS_Pa_s=rms([b['actual_rate_Pa_s'] for a,b in pairs]),
                        GPU_minus_CPU_RMS_Pa_s=rms(delta),GPU_minus_CPU_abs_max_Pa_s=absmax(delta),
                        classification_mismatches=sum(a['fstype'] != b['fstype'] for a,b in pairs)))
    need(gpu['Raw']['files']['nodes.csv'].read_bytes() == gpu['Normal']['files']['nodes.csv'].read_bytes(), 'GPU Raw/Normal node CSV bytes differ')
    need(gpu['Raw']['files']['free_off_rates.bin'].read_bytes() == gpu['Normal']['files']['free_off_rates.bin'].read_bytes(), 'GPU Raw/Normal OFF bits differ')
    changed, unchanged = 0, 0
    allowed = {'actual_rate_Pa_s','actual_bits','reference_rate_Pa_s','arithmetic_budget_Pa_s',
               'input_quantization_budget_Pa_s','gpcorr_x','gpcorr_z','lap','chain'}
    for key, a in gpu['Raw']['controls'].items():
        b = gpu['Normal']['controls'][key]; profile, field, on, native = key
        if not on or not surface(gpu['Raw']['nodes'][profile,native]):
            need(a == b, 'GPU closure changed OFF/interior actual/reference controls'); unchanged += 1
        else:
            need(all(a[q] == b[q] for q in a.keys()-allowed), 'GPU closure changed shared ON-FS inputs/operator sums')
            if a['actual_bits'] != b['actual_bits']: changed += 1
    need(changed > 0, 'No resolved intended actual GPU ON-FS closure difference')
    return rate_metrics, node_metrics, dict(nodes_byte_exact=True, OFF_binary_byte_exact=True,
        outside_ON_FS_bit_checks=unchanged, changed_ON_FS_rate_rows=changed,
        CPU_GPU_tracking_and_rates_descriptive_only=True)


def write_csv(path, rows):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized, 'Author-only until root full-read and one offline review authorization')
    need(not CHECK.exists() and all(not q.exists() for q in CSVS.values()), 'Existing review/figure CSV protected')
    CONSUMED.extend(stat(q) for q in (Path(__file__), NOTE))
    try:
        run = read(bind(stat(RUN))); build = build_review(run['build'])
        gpu = bundle(stat(RUN), build, True)
        cpu_run = read(bind(stat(CPU_RUN))); cpu_build = read(bind(cpu_run['build']))
        need(cpu_build['passed'] and cpu_build['configuration'] == 'DebugCPU' and cpu_build['consumed_stats_unchanged'], 'Retained valid CPU r2 build required')
        cpu = bundle(stat(CPU_RUN), cpu_build, False)
        metrics, checks = [], {}
        for label in ('Raw','Normal'):
            rows, checks[label] = controls_review(label,gpu[label]); metrics += rows
        rates, nodes, cross = comparison(gpu,cpu)
        verify()
        for key, rows in (('control_metrics',metrics),('cpu_gpu_metrics',rates),('node_differences',nodes)): write_csv(CSVS[key],rows)
        verify()
        save(CHECK,dict(stage=TAG+'.review',passed=True,build=stat(run['build']['path']),run=stat(RUN),cpu_run=stat(CPU_RUN),cpu_build=cpu_run['build'],
            intervention='free_surface_normal_taylor_projection',actual_hardware={k:v['device'] for k,v in gpu.items()},
            actual_GPU_Debug_target_and_tool_exits_zero=True,memcheck_zero_errors_and_leaks=True,
            GPU_formula_and_saved_guards=checks,cross_GPU_controls=cross,CPU_GPU_node_differences=nodes,CPU_GPU_rate_differences=rates,
            figures=[stat(q) for q in CSVS.values()],source_capture=build['source_capture'],source_archive=build['source_archive'],
            consumed=CONSUMED,consumed_stats_unchanged=True,physical_steps=0,solver_invocations=0,GPU_invocations=0,
            native_decodes=0,BI4_reads=0,SHA_scans=0,CPU_GPU_bitwise_agreement_claimed=False,
            Release_equivalence_claimed=False,unit_or_scientific_acceptance_claimed=False,physical_acceptance=False))
    except Exception as error:
        if not CHECK.exists(): save(CHECK,dict(stage=TAG+'.review',passed=False,first_failure=str(error),consumed=CONSUMED,
            GPU_invocations=0,solver_invocations=0,native_decodes=0,BI4_reads=0,SHA_scans=0,physical_acceptance=False))
        raise


if __name__=='__main__': main()
