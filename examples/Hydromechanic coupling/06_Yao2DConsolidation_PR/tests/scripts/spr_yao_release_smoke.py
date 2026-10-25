"""Real released GPU program regression; never replace retained Yao trajectories."""
import argparse
import io
import json
import os
import subprocess
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from spr_yao_short import TESTS, CASE, REPO, bound
from spr_yao_review import native
from spr_yao_step_review import exact_fields
from spr_yao_gpu_grid10_run import batch

TAG = 'spr_yao_release_smoke_r1'
REFERENCE = 'spr_yao_gpu_load_raw02_r2'
VARIANTS = ('faces_off', 'faces_on', 'faces_half')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--run', action='store_true')
    args = parser.parse_args()
    state = TESTS/'logs'/(TAG+'.status.json')
    assert not state.exists(), 'Fresh stage only'
    old_path = TESTS/'logs'/(REFERENCE+'.status.json')
    old = json.loads(old_path.read_text())
    assert old['status'] == 'completed_pending_review' and old['raw_program']
    if args.prepare:
        for variant in VARIANTS:
            name = TAG+'_'+variant
            source = TESTS/'configs'/(REFERENCE+'_'+variant+'_Def.xml')
            assert any(x['path'] == str(source) and x['sha256'] == bound(source)['sha256'] for x in old['inputs'])
            xml = TESTS/'configs'/(name+'_Def.xml')
            bat = TESTS/'configs'/('x'+name+'_win64_GPU.bat')
            with xml.open('xb') as stream:
                stream.write(source.read_bytes())
            with bat.open('x', encoding='utf8') as stream:
                stream.write(batch(name, 0, 0, raw=True))
        print('Prepared three real-program XML/BAT pairs; old inputs unchanged')
        return
    exe = REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe'
    meta = TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe'
    record = dict(status='running', owned_sequence_pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat(),
                  reference=REFERENCE, raw_program=True, numerical_equivalence_only=True, physical_acceptance=False,
                  inputs=[bound(__file__), bound(old_path), bound(exe), bound(meta),
                          bound(TESTS/'outputs/read_native_spr_r1/ReadHydroMechPart.exe')], runs=[])
    for variant in VARIANTS:
        name = TAG+'_'+variant
        assert not (TESTS/'outputs'/name).exists() and not (TESTS/'outputs'/(name+'_input')).exists()
        record['inputs'] += [bound(TESTS/'configs'/(name+'_Def.xml')), bound(TESTS/'configs'/('x'+name+'_win64_GPU.bat'))]
    def save():
        tmp = state.with_suffix('.tmp')
        tmp.write_text(json.dumps(record, indent=2), encoding='utf8')
        os.replace(tmp, state)
    save()
    try:
        rows = []
        for variant in VARIANTS:
            previous = next(x for x in old['runs'] if x['variant'] == variant)
            assert previous['exit_code'] == 0 and previous['owned_exited']
            for item in previous['outputs']:
                assert bound(item['path'])['sha256'] == item['sha256'], item['path']
            name = TAG+'_'+variant
            record['stage'] = 'running_'+variant
            log = TESTS/'logs'/(name+'.log')
            with log.open('xb') as stream:
                child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', str(TESTS/'configs'/('x'+name+'_win64_GPU.bat'))],
                                         cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid'] = child.pid
                save()
                code = child.wait()
            entry = dict(variant=variant, exit_code=code, owned_exited=True, log=bound(log))
            record['runs'].append(entry)
            save()
            assert code == 0 and 'Finished execution (code=0)' in log.read_text(errors='replace'), variant
            folder = TESTS/'outputs'/name
            assert len(list((folder/'data').glob('Part_*.bi4'))) == 21
            raw = subprocess.check_output([str(meta), str(folder/'data'), '21'])
            metadata = pd.read_csv(io.BytesIO(raw), float_precision='round_trip')
            dt = 1e-5 if variant == 'faces_half' else 2e-5
            active = metadata[metadata.part.gt(0)]
            assert len(metadata) == 21 and metadata.native_count.eq(21945).all() and metadata.nout.eq(0).all()
            assert active.has_dterror.eq(1).all() and active.dterror_s.between(-1e100, 0).all()
            assert active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all() and dt <= 9.53206462560066e-5
            initial = native(folder, 0)
            core = set(initial.id[np.isclose(initial.z, 10, atol=1e-8) & (abs(initial.x) < 3-1e-8)])
            assert len(initial) == 20301 and initial.id.is_unique and len(core) == 59
            for i in range(21):
                a = native(folder, i)
                b = native(TESTS/'outputs'/(REFERENCE+'_'+variant), i)
                assert exact_fields(a, b), (variant, i, 'Real-program native regression')
                assert np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all()
                assert np.array_equal(a.id, initial.id) and a.load_available.eq(1).all()
                assert a.x.between(-10.0001, 10.0001).all() and a.z.ge(-.0001).all()
                loaded = set(a.id[abs(a.load_az) > 0])
                assert (not loaded if i == 0 else loaded == core)
                t = float(a.time_s.iloc[0])
                q = 5000*min(1, max(0, t-dt)/.1) if i else 0
                force = float(17*a.load_az.sum())
                target = -17*float(np.float32(q/170))*len(loaded)
                assert abs(force-target) < .002
                drained = a.fstype.isin([2, 3]) & ~a.x.between(-3, 3)
                assert a.pressure[drained].eq(0).all()
                rows.append(dict(variant=variant, part=i, actual_time_s=t, all_native_fields_0ulp=True,
                                 pressure_rms_difference_pa=0, material_difference_mm=0,
                                 force_N_m=force, max_pressure_pa=float(a.pressure.max()),
                                 strip_material_settlement_mm=float(((initial.z-a.z)*1000)[initial.id.isin(core)].mean())))
            entry.update(passed=True, actual_time_s=t, native_frames_0ulp=21, mechanical_limit_min_s=float(dt-active.dterror_s.max()),
                         outputs=[bound(p) for base in (folder, TESTS/'outputs'/(name+'_input')) for p in base.rglob('*') if p.is_file()])
            save()
            print(variant, '21 native frames exact; admitted next variant', flush=True)
        csv = TESTS/'figures'/(TAG+'_native.csv')
        pd.DataFrame(rows).to_csv(csv, index=False, mode='x')
        for item in record['inputs']:
            assert bound(item['path'])['sha256'] == item['sha256']
        record.update(status='passed', passed=True, outputs=[bound(csv)], samples_each=21,
                      stage='all_three_real_program_trajectories_0ulp', finished_utc=datetime.now(timezone.utc).isoformat(),
                      limitations=['Ordinary output/stop events can be one dt late; actual times are retained',
                                   'No new independent full-window half-step or theory claim', 'No 10-s solver rerun or formal output relabeling'])
    except Exception as error:
        record.update(status='rejected_or_interrupted', error=repr(error), finished_utc=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
