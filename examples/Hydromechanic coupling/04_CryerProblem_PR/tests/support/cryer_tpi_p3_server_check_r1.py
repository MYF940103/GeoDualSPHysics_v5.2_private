"""Exercise the Windows BAT workflow using a temporary no-physics executable."""
import argparse
import csv
import io
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

import pack_cryer_tpi_p3_r1 as pack


MOCK = r"""
using System;
using System.IO;
class PackageFixture {
  static int Main(string[] a) {
    if(a.Length!=8 || a[0]!="-gpu" || a[1]!="-stable" || a[4]!="-dirdataout" ||
       a[5]!="data" || a[6]!="-svres" || Environment.GetEnvironmentVariable("UPL_TPI_GPU_R1")!="B" ||
       Environment.GetEnvironmentVariable("UPL_TPI_P3_ROWS_R1")!="3" ||
       Environment.GetEnvironmentVariable("UPL_TPI_M0_DT_R1")!="EQ40_RH1" ||
       !File.Exists(a[2]+".xml") || !File.Exists(a[2]+".bi4")) return 13;
    if(Environment.GetEnvironmentVariable("CRYER_MOCK_RESULT")=="fail") return 19;
    int n=int.Parse(a[7].Substring(8)), frames=n==36864?577:265;
    string folder=Path.Combine(a[3],"data"); Directory.CreateDirectory(folder);
    for(int i=0;i<frames;i++) File.WriteAllText(Path.Combine(folder,"Part_"+i.ToString("D4")+".bi4"),"mock");
    File.WriteAllText(Path.Combine(a[3],"Run.csv"),"#Steps;PartFiles;PartsOut;Hardware;PhysicalTime;Np;duplicated;duplicated\n"+
      n+";"+frames+";0;GPU NVIDIA MOCK ONLY;"+(n*Math.Pow(2,-19)).ToString("R",System.Globalization.CultureInfo.InvariantCulture)+";37181;0;0\n");
    File.WriteAllText(Path.Combine(a[3],"Run.out"),"Mock unit test.\nFinished execution (code=0).\n");
    foreach(string f in new string[]{"UplTpiP3GpuR1.policy.json","UplTpiP3DtR1.policy.json","UplTpiP3DtR1.csv",
        "UplTpiP3GpuR1.summary.json","UplTpiP3DtR1.summary.json","UplTpiP3GpuR1.body.csv","UplTpiP3GpuR1.round1.csv",
        "UplTpiP3GpuR1.round2.csv","UplTpiP3GpuR1.round3.csv"})
      File.WriteAllText(Path.Combine(a[3],f),"mock");
    return 0;
  }
}
"""

def check_clock(stage, rows):
    dt=float(pack.DT); drain=float(pack.DRAIN); dense=float(pack.FINE)
    steps, frames, after=pack.PROFILES[stage]
    t=0.0; target=dense
    actual=[(0,t)]
    for step in range(1,steps+1):
        t+=dt
        if t >= target or step == steps:
            actual.append((step,t))
            base,interval=(drain,float(after)) if t>=drain else (0.0,dense)
            n=math.floor((t-base)/interval)
            target=base+n*interval
            while target<=t:
                n+=1; target=base+n*interval
            if t<drain:
                target=min(target,drain)
    assert len(actual)==len(rows)==frames
    assert all((int(row['completed_steps']),float(row['time_s']))==pair for row,pair in zip(rows,actual))


def run_bat(root, stage, flag, rc, fail=False):
    env=os.environ.copy()
    env['CRYER_MOCK_RESULT']='fail' if fail else 'ok'
    bat='x'+pack.stem(stage)+'_win64_GPU.bat'
    call=subprocess.run([os.environ['COMSPEC'],'/d','/c',bat,flag],cwd=root,capture_output=True,env=env)
    assert call.returncode==rc,(bat,rc,call.stdout,call.stderr)
    return call


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--receipt',type=Path)
    args=cli.parse_args()
    if args.receipt and args.receipt.exists():
        raise FileExistsError(args.receipt)
    content=pack.input_files()
    for stage in ('peak','full'):
        rows=list(csv.DictReader(io.StringIO(content[Path('support')/(pack.stem(stage)+'_schedule.csv')].decode())))
        check_clock(stage,rows)
    with tempfile.TemporaryDirectory(prefix='Cryer package unit ') as tmp:
        root=Path(tmp)
        source=root/'mock.cs'; source.write_text(MOCK)
        mock=root/'mock.exe'
        csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        subprocess.run([str(csc),'/nologo','/out:'+str(mock),str(source)],check=True)
        for name in ('ChronoEngine.dll','dsphchrono.dll','DsphConfig.xml','vcomp140.dll'):
            (root/name).write_text('fixture only')
        portable=root/'path with spaces'
        payload=pack.archive_payload(mock,content)
        for relative,data in payload.items():
            pack.write_unique(portable/relative,data)
        for stage in ('peak','full'):
            run_bat(portable,stage,'--check-only',0)
        run_bat(portable,'peak','--not-a-mode',2)
        run_bat(portable,'full','--unattended',1)
        assert not (portable/(pack.stem('full')+'_GPU_out')).exists()
        run_bat(portable,'peak','--unattended',0)
        out=portable/(pack.stem('peak')+'_GPU_out')
        server=json.loads((out/'server_run.json').read_text(encoding='utf-8-sig'))
        assert server['status']=='completed_pending_native_physical_review' and server['steps']==36864
        assert server['hardware']=='GPU NVIDIA MOCK ONLY'
        import cryer_p3_peak_qualify_r1 as reviewer
        # Validate package-to-Run bindings with fixture files only. No BI4 certification.
        with zipfile.ZipFile(root/'unit.zip','x') as z:
            for leaf,data in payload.items():
                z.writestr(leaf.as_posix(),data)
        with zipfile.ZipFile(root/'unit.zip') as z:
            reviewed,_=reviewer.bind(z,out)
            assert reviewed['nu']==.3
            chk=out/(pack.stem('peak')+'.xml')
            previous=chk.read_bytes()
            bad=previous.replace(b'key="DtFixed" value="0.0000019073486328125"',b'key="DtFixed" value="0.000002"')
            assert bad!=previous
            chk.write_bytes(bad)
            try:
                reviewer.bind(z,out)
            except ValueError as e:
                assert 'parameters' in str(e)
            else:
                raise AssertionError('Wrong solver input was accepted')
            chk.write_bytes(previous)
        run_bat(portable,'peak','--unattended',1)
        # Full approval is tested only inside this temporary fixture.
        m=json.loads(payload[pack.MANIFEST])
        evidence=[dict(name=name,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest())
                  for name in ('Run.csv','server_run.json')]
        approval=dict(peak_qualified=True,scheme='B',rounds=3,nu=.30,dt_s=float(pack.DT),
                      native=dict(frames=577,end_s=.0703125,post_open_frames=512),
                      sidecar=dict(pressure_rounds=3,dt_phases=5,rows=577*18*3),
                      physics=dict(sampling=True,amplitude=True,amplitude_vs_A=True,phase=True),
                      peak_server_files=evidence,
                      **{k:m[k] for k in ('package_id','program_sha256','peak_input_sha256')})
        (portable/'support/cryer_tpi_p3_peak_review.json').write_text(json.dumps(approval))
        run_bat(portable,'full','--unattended',1,fail=True)
        fullout=portable/(pack.stem('full')+'_GPU_out')
        failed=json.loads((fullout/'server_run.json').read_text(encoding='utf-8-sig'))
        assert failed['solver_exit']==19 and failed['status']=='solver_failed'
        fullout.rename(root/'preserved mock failure')
        run_bat(portable,'full','--unattended',0)
        assert json.loads((fullout/'server_run.json').read_text(encoding='utf-8-sig'))['part_files']==265
    if args.receipt:
        with args.receipt.open('x',encoding='utf-8') as f:
            json.dump(dict(passed=True,scope='temporary no-physics Windows BAT workflow',
                           physical_solver_calls=0,native_reads=0,qualified_A6000_physics=False,
                           peak_scalar_clocks=577,full_scalar_clocks=265,
                           exercised=['space-containing extraction path','both BAT preflights','invalid arguments',
                               'full blocked before reviewed peak','captured successful mock run',
                               'independent archive/returned XML/input/Run bindings','changed DtFixed rejected',
                               'existing directory protected','nonzero solver exit preserved',
                               'full entry with temporary synthetic receipt'],
                           synthetic_outputs_discarded=True),f,indent=2)
    print('BAT package fixture passed; 577/265 scalar clock profiles checked; zero physical solver calls.')

