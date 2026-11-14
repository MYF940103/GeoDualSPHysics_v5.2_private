"""Run exactly one separately admitted bounded storage-observer GPU job; no decoding or next job."""
import argparse
import os
import re
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m

T, L = m.T, m.L
SAN = Path(r'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')


def summary(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    m.need(len(lines) == 2 and lines[0].startswith('#RunName;'), 'One original Run.csv row required')
    keys, values = lines[0][1:].split(';'), lines[1].split(';')
    i = keys.index('Configuration')
    m.need(len(values) == len(keys)+1 and len(set(keys)) == len(keys), 'Only original AS embedded semicolon admitted')
    values = values[:i]+[values[i]+';'+values[i+1]]+values[i+2:]
    d = dict(zip(keys, values))
    pattern = r'(?:^| - )AS_Bui2008\(([^;]+);([^\)]+)\)(?= - |$)'
    hit = re.findall(pattern, d['Configuration'])
    m.need(len(hit) == 1 and d['Configuration'].count(';') == 1 and
           all(m.f32(a) == m.f32(b) for a, b in zip(hit[0], (.3, 2.55))), 'Actual original AS03/n255 configuration differs')
    return d


def run(profile):
    m.need(profile in ('debug2', 'short3'), 'Closed short profiles only')
    tag = 'c08_h18_storage_'+profile+'_GPU_r1'
    prep_path, root_path, run_path = [L/(tag+s) for s in ('.prepare.json', '.root_run_admission.json', '.run.json')]
    m.need(not run_path.exists() and not (L/(tag+'.call.json')).exists() and
           not (L/(tag+'.log')).exists() and not (L/(tag+'.start.json')).exists(), 'Existing job or partial attempt protected')
    p, root = m.read(prep_path), m.read(root_path)
    m.need(p['passed'] and p['prepared_only'] and p['consumed_stats_unchanged'] and p['profile'] == profile and
           root['authorized'] and root['preparation'] == m.stat(prep_path) and root['execution_script'] == m.stat(Path(__file__)),
           'Separately reviewed preparation and exact root run admission required')
    before = [m.stat(prep_path), m.stat(root_path), m.stat(Path(__file__))]
    before += [m.bind(p[k]) for k in ('program', 'source_build', 'source_capture', 'source_archive', 'source_pre_file',
                                    'source_run', 'source_native', 'configuration_xml', 'input_xml', 'native_profile', 'planned_steps')]
    before += [m.bind(q) for q in p['seed']+p['runtime']]
    out = Path(p['output']); m.need(out.is_dir() and not (out/'data').exists() and
                                  not (out/'Run.out').exists() and not (out/'C08StorageTrace.csv').exists(), 'Fresh prepared job only')
    argv = list(p['argv']); program = Path(p['program']['path'])
    m.need(argv[0] == str(program) and argv[-1] == '-nsteps:'+str(p['global_nsteps_limit']), 'Actual global step limit changed')
    tool_argv = argv
    if profile == 'debug2':
        before.append(m.stat(SAN))
        tool_argv = [str(SAN), '--tool', 'memcheck', '--leak-check', 'full', '--target-processes', 'all', '--error-exitcode', '99', *argv]
    m.verify(before)
    owner = dict(pid=os.getpid(), created_epoch=psutil.Process().create_time(), exe=psutil.Process().exe(), argv=psutil.Process().cmdline())
    m.save(L/(tag+'.start.json'), dict(stage=tag+'.start', owner=owner, preparation=m.stat(prep_path), root_admission=m.stat(root_path),
        program=p['program'], source_build=p['source_build'], source_capture=p['source_capture'], source_archive=p['source_archive'],
        source_pre_file=p['source_pre_file'], input_xml=p['input_xml'], planned_steps=p['planned_steps'], argv=tool_argv,
        solver_argv=argv, actual_cwd=p['cwd'], consumed=before, automatic_next_job=False, physical_acceptance=False))
    result = dict(stage=tag, passed=False, solver_completed=False, physical_acceptance=False, native_review_pending=True,
        automatic_next_job=False, profile=profile, program=p['program'], source_build=p['source_build'], source_capture=p['source_capture'],
        source_archive=p['source_archive'], source_pre_file=p['source_pre_file'], source_run=p['source_run'], source_native=p['source_native'],
        runtime=p['runtime'], input_xml=p['input_xml'], seed=p['seed'], planned_steps=p['planned_steps'], native_profile=p['native_profile'],
        preparation=m.stat(prep_path), root_admission=m.stat(root_path), owner=owner, argv=tool_argv, solver_argv=argv,
        actual_source_time_s=p['actual_source_time_s'], planned_actual_end_s=p['planned_actual_end_s'],
        expected_saved_frames=p['expected_saved_frames'], global_nsteps_limit=p['global_nsteps_limit'], new_updates=p['new_updates'],
        fixed_dt_s=.000005, AS_coefficient=.3, AS_exponent=2.55, original_AV=.1, group='psi0', kernel=2, hdp=1.8,
        keep_bed_overlap=False, observer_output_only=True, solver_invocations=1, reader_invocations=0, VTK_invocations=0,
        GenCase_invocations=0, SHA_scans=0, consumed=before, unsaved_failure_time_reconstructed=False)
    try:
        result['actual_call'] = m.invoke(tag, tool_argv, Path(p['cwd']), target=program if profile == 'debug2' else None)
        call = m.read(result['actual_call']['path'])
        result.update(actual_exit=call['actual_target_Win32_exit'] if profile == 'debug2' else call['actual_Win32_exit'],
                      actual_Win32_exit=call['actual_target_Win32_exit'] if profile == 'debug2' else call['actual_Win32_exit'],
                      actual_tool_exit=call['actual_Popen_wait_exit'], ownership_failure=call['ownership_failure'])
        text = (out/'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and
               'certified same-material plastic schema/contract2' in text, 'Original successful completion/schema2 import absent')
        result['solver_completed'] = True  # Later derived checks cannot turn a completed solve into a new run request.
        d = summary(out/'Run.csv')
        m.need(int(d['Steps']) == p['global_nsteps_limit'] and int(d['PartFiles']) == p['expected_saved_frames'] and
               int(d['PartsOut']) == 0 and 'Wendland' in d['Configuration'], 'Actual bounded run summary differs')
        result.update(solver_completed=True, summary=d, actual_steps=int(d['Steps']), saved_frames=int(d['PartFiles']))
        sidecar = out/'C08StorageTrace.csv'; m.need(sidecar.is_file() and sidecar.stat().st_size > 0, 'Genuine observer sidecar absent')
        if profile == 'debug2':
            log = Path(call['log']['path']).read_text(encoding='mbcs', errors='replace')
            m.need('ERROR SUMMARY: 0 errors' in log, 'Actual GPU memcheck zero-error result absent')
            result['memcheck_zero_errors'] = True
        m.verify(before)
        result.update(passed=True, consumed_stats_unchanged=True, observer_sidecar=m.stat(sidecar),
                      Run_out=m.stat(out/'Run.out'), Run_csv=m.stat(out/'Run.csv'), output=str(out))
    except Exception as error:
        result['first_failure'] = str(error)
        cp = L/(tag+'.call.json')
        if cp.exists():
            result['actual_call'] = m.stat(cp); call = m.read(cp)
            result.update(actual_exit=call['actual_target_Win32_exit'] if profile == 'debug2' else call['actual_Win32_exit'],
                actual_Win32_exit=call['actual_target_Win32_exit'] if profile == 'debug2' else call['actual_Win32_exit'],
                actual_tool_exit=call['actual_Popen_wait_exit'], ownership_failure=call['ownership_failure'])
        if (out/'Run.out').exists():
            result['Run_out'] = m.stat(out/'Run.out')
            hit = re.search(r'^Text: (.*)$', (out/'Run.out').read_text(encoding='utf-8-sig', errors='replace'), re.M)
            result['first_engine_exception_text'] = hit[1] if hit else None
    result['last_original_console_line'] = m.base.last_part(out)
    m.save(run_path, result)
    print(tag, 'passed', result['passed'], result.get('first_failure'), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('debug2', 'short3'), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); m.need(args.execution_authorized, 'Independent explicit root run admission required')
    raise SystemExit(run(args.profile))
