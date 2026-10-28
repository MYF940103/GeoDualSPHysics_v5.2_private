"""Corrected CLI-only entry; adopts sealed r1 field/build and retains failed r1."""
import argparse
import json
import subprocess
import time
import cryer_radial_force_r1 as core
from cryer_load_pair_r1 import TESTS,bound,write_json

core.TAG='cryer_radial_force_r2'
core.OUT=TESTS/'outputs/cryer_radial_force_r2_observation'


def run():
    runtime=TESTS/'logs'/(core.TAG+'.run.json')
    assert not runtime.exists() and not core.OUT.exists()
    failed=TESTS/'logs/cryer_radial_force_r1.run.json'
    old=json.loads(failed.read_text()); assert old['exit_code']==1 and old['owned_exited']
    assert 'Parameter "-omp:8" unrecognised' in (TESTS/'logs/cryer_radial_force_r1.stdout.log').read_text()
    assert not (TESTS/'outputs/cryer_radial_force_r1_observation').exists()
    prepared=json.loads(core.PREP.read_text());build=json.loads(core.BUILD.read_text(encoding='utf-8-sig'))
    for entry in prepared['inputs']+build['inputs']+build['runtime']:
        assert bound(entry['path'])['sha256'].lower()==entry['sha256'].lower(),entry['path']
    exe=TESTS/'outputs/cryer_radial_force_r1_dbg/cryer_radial_force_r1.exe'
    command=[str(exe),str(core.DATA),'-cpu','-ompthreads:8',str(core.FOLDER/'cryer_preload_peak_r1'),str(core.OUT),'-dirdataout','data']
    start=time.perf_counter()
    with (TESTS/'logs'/(core.TAG+'.stdout.log')).open('xb') as output:
        process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
        record=dict(status='nonintegrating_observer_running',owned_pid=process.pid,command=command,
            program=bound(exe),prepared=bound(core.PREP),build=bound(core.BUILD),driver=bound(__file__),
            adopted_failed_cli_receipt=bound(failed),physical_solver=False)
        write_json(runtime,record);code=process.wait()
    record.update(status='observer_exited',exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start)
    write_json(runtime,record)
    assert code==0,'Inspect retained r2 evidence; do not restart it'
    core.review()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--review',action='store_true')
    args=p.parse_args()
    if args.run:run()
    elif args.review:core.review()
    else:p.print_help()
