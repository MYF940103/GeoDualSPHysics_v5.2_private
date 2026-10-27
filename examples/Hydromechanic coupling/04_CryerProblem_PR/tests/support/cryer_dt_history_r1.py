"""Read-only old-run time-step audit; never changes or restarts a solver."""
import io
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE, TESTS, REPO, READER, bound, write_json


def main():
    target = TESTS/'logs/cryer_dt_history_r1.check.json'
    assert not target.exists(), 'Do not overwrite historical evidence'
    folder = CASE/'CaseCryerProblem_PR_out'
    old = json.loads((TESTS/'logs/cryer_load_audit_r1.json').read_text())
    expected = {e['path']: e['sha256'] for e in old['sources']}
    evidence = [bound(__file__), bound(TESTS/'support/cryer_start_r1.py'), bound(READER)]
    evidence += [bound(folder/'Run.out'), bound(folder/'CaseCryerProblem_PR.xml')]
    records = []
    dtw = None
    for index in [1, 1000]:
        part = folder/'data'/f'Part_{index:04d}.bi4'
        assert bound(part)['sha256'] == expected[str(part)]
        raw = subprocess.check_output([str(READER), str(folder/'data'), str(index)],
                                      creationflags=subprocess.CREATE_NO_WINDOW)
        a = pd.read_csv(io.BytesIO(raw), float_precision='round_trip')
        assert len(a) == 37173 and a.id.nunique() == 37173
        h = float(a.h.iloc[0])
        dtw = float(np.float32(.1))*(1000*9.80665/(float(np.float32(2e8))/float(np.float32(.3))))*h*h/float(np.float32(1e-5))
        t, step = float(a.time_s.iloc[0]), int(a.saved_step.iloc[0])
        reconstructed = 5e-6 + step*dtw
        assert abs(t-reconstructed) < 1e-10
        records.append(dict(part=index, actual_time_s=t, zero_based_saved_step=step,
            average_time_per_step_s=t/(step+1),
            first_5us_then_dtw_reconstruction_s=reconstructed,
            reconstruction_difference_s=t-reconstructed))
        evidence.append(bound(part))
    code = []
    for name in ['JSphCpu.cpp', 'JSphGpu.cpp']:
        path = 'src/source/'+name
        before = subprocess.check_output(['git', 'show', '8af9ed55^:'+path], cwd=REPO).decode('utf8')
        after = subprocess.check_output(['git', 'show', '8af9ed55:'+path], cwd=REPO).decode('utf8')
        old_sequence = 'if(FixedDt)dt=FixedDt->GetDt(TimeStep,dt);\n  dt=min(dt,dtw);'
        new_sequence = 'if(FixedDt)dt=FixedDt->GetDt(TimeStep,dt);\n  else dt=min(dt,dtw);'
        assert old_sequence in before.replace('\r\n', '\n')
        assert new_sequence in after.replace('\r\n', '\n')
        current = (REPO/path).read_text()
        assert new_sequence in current
        code.append(dict(file=path, changed_commit='8af9ed55',
            before='FixedDt was followed by unconditional min(dt,dtw)',
            after='Only variable steps are limited by dtw; fixed steps bypass it',
            current=bound(REPO/path)))
    result = dict(passed=True, scope='Two retained June22 native checkpoints plus Git source history, not a new physical solve',
        declared_fixed_dt_s=5e-6, configured_dtw_s=dtw, actual_checkpoint_reconstruction=records,
        code_history=code, sources=evidence,
        conclusion='The retained run was not a full trajectory of 5us steps; sampled clocks match an initial5us step followed by about2.97877us. A current5us run is not a stress-precision-only A/B control.',
        limits=['Only the two stated native times are reconstructed, not every old saved state.',
            'The conservative dtw limit alone does not prove physical instability or explain the old peak error.',
            'Do not replace actual old times with metadata FixedDt*step.',
            'No source, load, geometry, boundary, material or formal input was changed.'])
    write_json(target, result)
    print(json.dumps({k: result[k] for k in ['passed', 'configured_dtw_s', 'actual_checkpoint_reconstruction']}, indent=2))


if __name__ == '__main__':
    main()
