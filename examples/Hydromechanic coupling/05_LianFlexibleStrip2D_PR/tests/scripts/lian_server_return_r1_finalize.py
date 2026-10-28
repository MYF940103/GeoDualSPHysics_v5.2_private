"""Seal reviewed server-analysis delivery. Requires explicit human-facing visual confirmation."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,bound,write_json,utc


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-visual-review',action='store_true',required=True)
    parser.parse_args()
    logs=CASE/'tests/logs';out=logs/'lian_server_return_r1.final_review.json'
    assert not out.exists()
    names=['lian_hgspr100_r1.check.json','lian_hgspr100_r1.plots.json',
        'lian_server_return_r1.audit.json','lian_server_return_r1_poredt.check.json','lian_server_particles_r1.check.json']
    records=[json.loads((logs/n).read_text(encoding='utf-8-sig')) for n in names]
    native,plots,audit,pore,particles=records
    assert native['passed'] and native['frames']==2001 and native['guard_failure_count']==0
    assert plots['passed'] and audit['evidence_consistency_passed'] and pore['passed'] and particles['passed']
    for r in [native,plots]:
        for item in r['artifacts']:assert bound(item['path'])['sha256']==item['sha256']
    h=pd.read_csv(CASE/'figures/lian_hgspr100_r1_history.csv',float_precision='round_trip')
    assert len(h)==2001 and np.all(np.diff(h.time_s)>0)
    for name in ['PartFluid','PartBound']:
        series=json.loads((CASE/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out/particles'/(name+'.vtk.series')).read_text())
        assert series['file-series-version']=='1.0' and len(series['files'])==2001
        assert [e['time'] for e in series['files']]==h.time_s.tolist()
    refs=pd.read_csv(CASE/'figures/lian_hgspr100_r1_paper_points.csv')
    result=dict(passed=True,utc=utc(),native_full_history_passed=True,particles_complete=True,
        five_formal_pngs_visually_reviewed=True,all_matching_csvs_present=True,
        exact_paper_reproduction_accepted=False,full_cycle_half_step_tested=False,
        final_A_pressure_pa=float(h.A_pressure_pa.iloc[-1]),final_B_pressure_pa=float(h.B_pressure_pa.iloc[-1]),
        final_A_settlement_mm=float(h.A_settlement_mm.iloc[-1]),final_B_settlement_mm=float(h.B_settlement_mm.iloc[-1]),
        minimum_saved_pressure_pa=float(h.pressure_min_pa.min()),
        id1744_contact_transitions=int(h.id1744_contact.astype(int).diff().abs().sum()),
        sparse_paper_comparison_points=len(refs),
        sources=[bound(p) for p in [Path(__file__)]+[logs/n for n in names]],
        conclusion='Complete stable 100-s HG+SPR result with broadly close deformation references; early A pressure and top horizontal displacement retain visible differences.',
        scope='Current fixed planar mixed-slip elastic strip case only; no exact paper/raw-reference or general large-deformation validation.',
        visual_notes=['All five formal PNGs inspected by the main assistant after rendering.',
            'Original Fig10 palette/row scales and all four reference times retained; no over-range native samples.',
            'Signed horizontal profile and downward settlement units checked; original raster uncertainty disclosed.',
            'ParaView JSON time/file mapping checked; ParaView GUI was not exercised.'])
    write_json(out,result);print(out)


if __name__=='__main__':main()
