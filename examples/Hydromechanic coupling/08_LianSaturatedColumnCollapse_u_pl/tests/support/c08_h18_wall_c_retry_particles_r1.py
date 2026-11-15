"""Export completed diagnostic once, with separate soil and boundary VTK series."""
import argparse
import json
import re
from pathlib import Path
import c08_h18_wend_matrix_r1 as m
import c08_h18_bedroles_pre_r1 as source

T,L=m.T,m.L
TAG='c08_h18_wall_c_retry_particles_r1'
RUN=L/'c08_h18_wall_c_retry_full3_GPU_r2.run.json'
NATIVE=L/'c08_h18_wall_c_retry_full3_GPU_r2.native_r1.check.json'
CHECK=L/(TAG+'.check.json')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized',action='store_true')
    assert p.parse_args().execution_authorized
    r,n=map(m.read,(RUN,NATIVE))
    assert r['passed'] and r['solver_completed'] and r['actual_exit']==r['actual_Win32_exit']==0
    assert r['saved_frames']==301 and n['passed'] and n['reader_invocations']==1 and n['original_safety_passed']
    out=Path(r['output']);particles=out/'particles'
    assert not CHECK.exists() and not particles.exists(), 'Protect any complete/partial export'
    assert not list(L.glob(TAG+'.Part*.call.json')), 'Existing tool invocation must be reviewed, never repeated'
    build=L/'c08_preload_schema2_Release_r1.build.json';b=m.read(build)
    assert b['passed'] and b['consumed_stats_unchanged']
    tool=m.bind(next(q['destination'] for q in b['runtime'] if Path(q['destination']['path']).name=='PartVTK_win64.exe'))
    seed=m.bind(r['input_xml'])
    before=[m.stat(q) for q in (Path(__file__),RUN,NATIVE,build)]+[tool,seed]
    particles.mkdir();calls=[];files=[]
    for label,kind,count in (('PartFluid','fluid',5000),('PartBound','fixed',1805)):
        argv=[tool['path'],'-dirin',str(out/'data'),'-filexml',seed['path'],'-first:0','-last:300',
              '-savevtk',str(particles/label),'-onlytype:-all,'+kind,source.VARS,'-threads:1']
        calls.append(m.invoke(TAG+'.'+label,argv,m.C))
        for part in range(301):
            f=particles/(label+'_%04d.vtk'%part)
            with f.open('rb') as stream:points=re.search(rb'\bPOINTS\s+(\d+)\s+',stream.read(4096))
            assert points and int(points[1])==count, 'Actual VTK point count differs'
            files.append(m.stat(f))
    assert {p.name for p in particles.iterdir()}=={Path(q['path']).name for q in files}
    assert all(m.stat(q['path'])==q for q in before)
    m.save(CHECK,dict(stage=TAG,passed=True,PartVTK_invocations=2,soil_files=301,boundary_files=301,
        soil_points_per_frame=5000,boundary_points_per_frame=1805,files=files,actual_calls=calls,
        consumed=before,consumed_stats_unchanged=True,positions_are_visualization_float=True,
        quantitative_precision_source='Original double typed22/CSV and native actual clock',
        physical_acceptance=False,solver_invocations=0,native_decodes=0,SHA_scans=0))

if __name__=='__main__':main()
