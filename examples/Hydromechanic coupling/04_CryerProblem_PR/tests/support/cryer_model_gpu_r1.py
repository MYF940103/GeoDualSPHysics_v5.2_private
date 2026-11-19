"""Two-step GPU regressions of the private single XML model selector."""
import argparse
import csv
import os
from pathlib import Path
import re
import shutil

import cryer_xml_gpu_r1 as previous
from cryer_model_cpu_r1 import verify_native
from cryer_p3_verify_r1 import audit, EXPECTED_TYPES
from cryer_row_gpu_r1 import OUT, LOG, call, identity, load, need, save


TAG = 'cryer_model_gpu_r1'
OLD = previous.TAG
STATIC_REF = TAG + '_static_ref'
PROFILES = {
    'static_ref': (0, None), 'missing': (0, None), 'model0': (0, '0'),
    'legacy1': (1, None), 'model1': (1, '1'),
    'legacy_pair': (2, None), 'model2': (2, '2'),
    'range': (2, '3'), 'mixed': (2, '2'), 'mixed_integrator': (2, '2'),
    'duplicate': (2, '2'), 'hydro_off': (2, '2'), 'misplaced': (2, '2'),
    'restart': (2, '2'), 'stale_env': (2, '2'),
}
REJECT = {
    'range': 'requires 0, 1 or 2', 'mixed': 'cannot be combined',
    'mixed_integrator': 'cannot be combined', 'duplicate': 'Duplicate HydroMechModel',
    'hydro_off': 'requires HydroMech=1', 'misplaced': 'inside special/hydromechanics',
    'restart': 'requires a fresh start', 'stale_env': 'clear the old private environment switches',
}


def bound_file(entry):
    path = Path(entry['path'])
    need(identity(path) == entry, 'Reference differs: '+str(path))
    return path


def prepare_input(profile, tag, model):
    prefix = OLD + ('_controlB' if model == 2 else '_controlA')
    control = load(LOG / (prefix + '.run.json'))
    need(control['passed'], 'Retained reference did not pass')
    src, bi4 = (bound_file(control[key]) for key in ('input_xml', 'input_bi4'))
    data = src.read_bytes()
    pattern = rb'(?m)^([ \t]*)<HydroMechDynamicSeepage value="1"[^\r\n]*?/>[ \t]*(\r?\n)'
    found, = list(re.finditer(pattern, data))
    indent, newline = found.groups()

    def node(key, val):
        return indent + f'<{key} value="{val}" />'.encode('ascii') + newline

    choice = PROFILES[profile][1]
    entry = node('HydroMechModel', choice) if choice is not None else b''
    if profile in ('legacy1', 'legacy_pair', 'mixed'):
        entry = found.group() + entry
    if profile in ('legacy_pair', 'mixed_integrator'):
        entry += node('HydroMechPressureIntegrator', '1')
    if profile == 'duplicate':
        entry += entry
    if profile == 'misplaced':
        need(data.count(b'</soils>') == 1, 'Original soil section')
        data = data.replace(found.group(), b'').replace(b'</soils>', entry + b'</soils>')
    else:
        data = data[:found.start()] + entry + data[found.end():]
    if profile == 'hydro_off':
        need(data.count(b'<HydroMech value="1"') == 1, 'Original coupling switch')
        data = data.replace(b'<HydroMech value="1"', b'<HydroMech value="0"')
    seed = OUT/(tag+'_seed')
    seed.mkdir()
    xml, geom = seed/src.name, seed/bi4.name
    xml.write_bytes(data)
    shutil.copyfile(bi4, geom)
    return xml, geom, control


def review_static(folder, reference, dt):
    fields = verify_native(folder, reference, 0, dt)
    static_schema = {name:typ for name,typ in EXPECTED_TYPES.items()
                     if name != 'PosDiv' and not name.startswith('Poro')}
    need(fields == static_schema, 'Actual static schema')
    need(not list(folder.glob('UplTpi*')), 'Static model emitted TPI outputs')
    return dict(fields=fields, reference=str(reference), matched_ids=37181, saved_times_s=[0., 2*dt],
                matched_native_clocks=['TimeStep','SymplecticDtPre','dterror'])


def review_existing_static(profile):
    tag = TAG+'_'+profile
    record = load(LOG/(tag+'.run.json'))
    need(record['popen_exit']==record['win32_exit']==0 and record['model']==0, 'Closed model zero run')
    check=review_static(OUT/tag, OUT/STATIC_REF, record['dt_s'])
    save(LOG/(tag+'.check.json'), dict(passed=True, offline=True, solver_rerun=False, **check))
    print(profile,'native passed',flush=True)


def run(profile):
    model, _ = PROFILES[profile]
    tag = TAG+'_'+profile
    folder, receipt = OUT/tag, LOG/(tag+'.run.json')
    need(not folder.exists() and not receipt.exists(), 'Existing GPU model short')
    baseline = profile == 'static_ref'
    build = load(LOG/((OLD if baseline else TAG)+'_Release.build.json'))
    need(build['passed'], 'Missing GPU build')
    exe = bound_file(build['program'])
    xml, geom, control = prepare_input(profile, tag, model)
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith('UPL_TPI_')}
    if profile == 'stale_env':
        env['UPL_TPI_GPU_R1'] = 'B'
    argv = [str(exe), '-gpu', '-stable', str(xml.with_suffix('')), str(folder), '-dirdataout', 'data', '-svres', '-nsteps:2']
    if profile == 'restart':
        path = OUT/(OLD+'_controlB')/'data'
        need((path/'Part_0001.bi4').is_file(), 'Real B PART')
        argv.extend(['-partbegin:1', str(path)])
    console = LOG/(tag+'.console.log')
    record = call(argv, exe.parent, env, console)
    record.update(passed=False, profile=profile, program=build['program'], xml=identity(xml), seed=identity(geom))
    try:
        msg = console.read_text(errors='replace')
        rc = record['popen_exit']
        need(rc == record['win32_exit'], 'Win32/child status')
        if profile in REJECT:
            needle = REJECT[profile]
            need(rc != 0 and needle in msg and not any((folder/'data').glob('Part_*.bi4')),
                 'Expected rejection: '+needle)
            record['rejection'] = next(line.strip() for line in msg.splitlines() if needle in line)
        else:
            need(rc == 0 and (baseline or f'HydroMechModel={model}' in msg), 'Run/model log')
            with (folder/'Run.csv').open(encoding='utf-8-sig', newline='') as f:
                summary, = csv.DictReader(f, delimiter=';')
            need(tuple(int(summary[k]) for k in ('Steps','PartFiles','PartsOut','Np')) == (2,2,0,37181),
                 'Wrong actual native schedule')
            if not baseline:
                ref_tag = {0:STATIC_REF, 1:OLD+'_controlA', 2:OLD+'_controlB'}[model]
                reference = OUT/ref_tag
                need(load(LOG/(ref_tag+'.run.json'))['passed'], 'Missing reference run')
                dt = control['dt']
                record.update(model=model, reference=ref_tag, dt_s=dt)
                if model == 0:
                    record['static_native'] = review_static(folder, reference, dt)
                else:
                    record['saves'] = audit(folder/'data', [0,2], dt, reference/'data', exact=True, p3_sidecars=(model == 2))
                    record['fields'] = sorted(EXPECTED_TYPES)
                sidecars = {p.name:identity(p)['sha256'] for p in folder.glob('UplTpi*')}
                expected = {p.name:identity(p)['sha256'] for p in reference.glob('UplTpi*')}
                need(sidecars == expected and bool(sidecars) == (model == 2), 'TPI ledgers')
                record['exact_sidecars'] = sorted(sidecars)
        record['passed'] = True
    finally:
        save(receipt, record)
    print(profile, 'passed', flush=True)


def summary():
    checks = {}
    for profile,(model,_) in PROFILES.items():
        tag = TAG+'_'+profile
        receipt = load(LOG/(tag+'.run.json'))
        if profile in REJECT:
            need(receipt['passed'] and receipt['win32_exit']==receipt['popen_exit']==1
                 and REJECT[profile] in receipt['rejection'], 'Negative check '+profile)
            checks[profile] = dict(exit=1, rejection=receipt['rejection'])
        elif profile != 'static_ref':
            if profile == 'missing':
                need(load(LOG/(tag+'.check.json'))['passed'], 'Offline static native check')
            else:
                need(receipt['passed'], 'Native gate '+profile)
            need(receipt['win32_exit']==receipt['popen_exit']==0, 'Actual completion '+profile)
            fields = verify_native(OUT/tag, OUT/receipt['reference'], model, receipt['dt_s'])
            checks[profile] = dict(exit=0, model=model, saves=2, ids=37181, exact_fields=len(fields),
                                   exact_clock_fields=['TimeStep','SymplecticDtPre','dterror'],
                                   exact_ledgers=len(receipt.get('exact_sidecars', ())))
    save(LOG/(TAG+'.check.json'), dict(passed=True, static_reference=STATIC_REF, profiles=checks))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['build', 'review_missing', 'summary', *PROFILES])
    action = ap.parse_args().action
    if action == 'build':
        previous.TAG = TAG
        previous.build(OUT/(TAG+'_source'))
    elif action == 'review_missing':
        review_existing_static('missing')
    elif action == 'summary':
        summary()
    else:
        run(action)
