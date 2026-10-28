"""Separate fixed-step pore-diffusion audit; no physical calculation or file overwrite."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from lian_release_r1 import CASE,REPO,native,bound,write_json,utc


def main():
    check=CASE/'tests/logs/lian_hgspr100_r1.check.json'
    out=CASE/'tests/logs/lian_server_return_r1_poredt.check.json'
    assert not out.exists()
    review=json.loads(check.read_text())
    assert review['native_safety_passed'] and review['guard_failure_count']==0
    config=CASE/'CaseLianFlexibleStrip2D_PR_release_Def.xml'
    tree=ET.parse(config)
    hydro={e.tag:float(e.attrib['value']) for e in tree.findall('.//hydromechanics/*')}
    pars={e.attrib['key']:float(e.attrib['value']) for e in tree.findall('.//execution/parameters/parameter')}
    a=native(CASE/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out',0)
    assert a.h.nunique()==1
    # JSphGpu::DtVariable casts stored float material/constants to double.
    f=lambda x:float(np.float32(x))
    h=f(a.h.iloc[0]);n=f(hydro['Porosity']);kw=f(hydro['PoreWaterBulkModulus'])
    rho=f(hydro['PoreWaterRho']);k=f(hydro['HydraulicConductivity']);safety=f(hydro['PoreDtSafety'])
    gravity=tree.find('.//constantsdef/gravity')
    g=float(np.linalg.norm([f(gravity.attrib[v]) for v in ['x','y','z']]))
    ghyd=g if g>0 else 9.80665
    limit=safety*(rho*ghyd/(kw/n))*h*h/k
    fixed=pars['DtFixed']
    result=dict(passed=fixed<=limit,utc=utc(),fixed_dt_s=fixed,pore_diffusion_limit_s=limit,
        fixed_to_pore_limit_ratio=fixed/limit,float_constants=dict(h=h,n=n,Kw=kw,rho=rho,k=k,safety=safety),
        hydraulic_gravity_m_s2=ghyd,
        formula='PoreDtSafety * (rho_w*g/(Kw/n)) * h^2 / k',
        scope='Independent pore-diffusion check, separate from all-sample mechanical natural-step dterror',
        all_saved_h_unchanged=review['guard_failure_count']==0,
        fixed_step_automatic_clipping=False,
        sources=[bound(p) for p in [Path(__file__),check,config,REPO/'src/source/JSphGpu.cpp',
            CASE/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out/data/Part_0000.bi4']],
        note='FixedDt bypasses automatic dtw clipping; this receipt checks its bound independently. No stability proof beyond the implemented bound.')
    write_json(out,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
