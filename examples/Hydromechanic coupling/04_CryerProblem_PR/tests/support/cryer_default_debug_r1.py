"""Exercise the actual default VS CPU Debug executable on the six-update Cryer input."""
from pathlib import Path
import argparse
import csv
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys

import psutil

TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS.parents[1] / 'validation'))
import hydro_public_xml_r1 as qa


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', choices=['cryer_default_debug_r1', 'cryer_default_debug_r2'])
    tag = parser.parse_args().tag
    folder = TESTS / 'outputs' / tag
    reference = TESTS / 'outputs/hydro_public_xml_r2_cpu_confinement_old'
    program = qa.BIN / 'DualSPHysics5.2CPU_win64_debug.exe'
    receipt = TESTS / 'logs' / (tag + '.check.json')
    if folder.exists() or receipt.exists() or not (reference / 'review.json').is_file():
        raise RuntimeError('Fresh output and completed six-step CPU baseline required')
    seed, dt = qa.prepared('confinement', 'modern', folder)
    argv = [str(program), '-cpu', '-ompthreads:1', '-stable', str(seed), str(folder),
            '-dirdataout', 'data', '-svres', '-nsteps:6']
    with (folder / 'console.log').open('xb') as console:
        child = subprocess.Popen(argv, cwd=program.parent, stdout=console, stderr=subprocess.STDOUT)
        owner = psutil.Process(child.pid)
        start = dict(command=argv, pid=child.pid, creation_time=owner.create_time(),
                     ppid=owner.ppid(), exe=owner.exe(), size=program.stat().st_size,
                     mtime_ns=program.stat().st_mtime_ns)
        qa.write(folder / 'start.json', start)
        rc = child.wait()
        actual = wintypes.DWORD()
        if not ctypes.windll.kernel32.GetExitCodeProcess(wintypes.HANDLE(int(child._handle)), ctypes.byref(actual)):
            raise ctypes.WinError()
    result = dict(start=start, exit=rc, win32_exit=actual.value, reference=str(reference),
                  saved_files=[p.name for p in sorted((folder / 'data').glob('Part_*.bi4'))], passed=False)
    try:
        qa.need(rc == actual.value == 0, 'Unsuccessful original process exit')
        with (folder / 'Run.csv').open(encoding='utf-8-sig', newline='') as stream:
            summary, = csv.DictReader(stream, delimiter=';')
        qa.need(int(summary['Steps']) == 6 and int(summary['PartsOut']) == 0, 'Run.csv differs')
        result.update(native=qa.compare(folder, reference, 2, dt), steps=6, passed=True)
    finally:
        qa.write(receipt, result)
    print(f"{receipt.name}: Win32 exit {actual.value}, {len(result['native'])} exact native pairs")


if __name__ == '__main__':
    main()
