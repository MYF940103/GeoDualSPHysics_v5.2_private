"""Compare the returned P3 pressure and effective stress with explicit A at identical saved clocks."""
import argparse
import json
from pathlib import Path

from cryer_shell_equilibrium import TESTS, Reference, R, T_D, need, reference_fields
import numpy as np
import pandas as pd


def main(review):
    out=review/"physical"
    target=out/"matched_center_diagnosis.csv"
    result_path=out/"matched_center_diagnosis.json"
    need(not target.exists() and not result_path.exists(),"Preserve prior derived review")
    q=json.loads((out/"physical_review.json").read_text(encoding="utf8"))
    need(q["stage"]=="peak" and q["center_material_ids"]==18,"Returned peak review required")
    b=pd.read_csv(out/"native_and_theory.csv",float_precision="round_trip")
    a=pd.read_csv(TESTS/"figures/cryer_shell_equilibrium_r1_history.csv",float_precision="round_trip")
    a=a[a.method=="A_finiteKw"].copy()
    b=b[b.time_s>=T_D].copy()
    need(len(a)==len(b)==513 and np.array_equal(a.time_s,b.time_s)
         and np.array_equal(a.part,b.part),"Matched native clocks and IDs")
    ref=Reference(.3,finite=False)
    ref.cv=ref.H*ref.kappa
    ref.decay=ref.xi**2*ref.cv/R**2
    terms=[reference_fields(ref,t,np.array([.0025])) for t in b.tau_s]
    m0_pressure=np.array([row[0][0] for row in terms])
    need(np.max(abs(m0_pressure-b.M0_r18_Pa))<1e-6,"Independent M0 radial pressure")
    m0_uniform=np.array([row[2] for row in terms])
    b_c=ref.H/ref.K*b.center18_effective_mean_tensile_Pa-b.center18_Pa
    b_dc=b_c-m0_uniform
    b_stress=ref.H/ref.K*b.center18_effective_mean_tensile_Pa-(m0_pressure+m0_uniform)
    need(np.max(abs(b_stress-b_dc-b.native_minus_M0_Pa))<1e-6,"P3 equilibrium/volumetric split")
    matched=pd.DataFrame(dict(part=b.part.values,time_s=b.time_s.values,tau_s=b.tau_s.values,
        legacy_Tv=b.legacy_Tv.values,B_pressure_Pa=b.center18_Pa.values,A_pressure_Pa=a.center_p_Pa.values,
        B_pressure_error_Pa=b.native_minus_M0_Pa.values,A_pressure_error_Pa=a.center_dp_Pa.values,
        B_M0_Pa=m0_pressure,A_finite_Kw_Pa=(a.center_p_Pa-a.center_dp_Pa).values,
        B_dC_Pa=b_dc.values,A_dC_Pa=a.center_dC_Pa.values,B_dH_eps_v_Pa=b_stress.values,
        A_dH_eps_v_Pa=a.center_dvolumetric_stress_term_Pa.values,
        B_total_compression_Pa=b.center18_total_compression_Pa.values,A_total_compression_Pa=a.center_total_compression_Pa.values,
        B_center_Jminus1=b.center18_J_minus_1.values,B_center_shape_change=b.center18_enclosed_volume_change.values))
    matched["BminusA_Pa"]=matched.B_pressure_Pa-matched.A_pressure_Pa
    matched["M0_minus_finiteKw_Pa"]=matched.B_M0_Pa-matched.A_finite_Kw_Pa
    matched["BminusA_pressure_error_Pa"]=matched.B_pressure_error_Pa-matched.A_pressure_error_Pa
    window=matched[matched.legacy_Tv>=.005]
    peak=window.loc[window.B_pressure_Pa.idxmax()]
    need(peak.B_pressure_Pa==q["native_peak_Pa"] and peak.tau_s==q["native_peak_tau_s"],"Independent sampled peak")
    result=dict(reviewer_native_source="Previously reviewed native_and_theory.csv, no BI4 reread",
        material_radius_m=.0025,A_model="explicit u-pl, finite Kw",B_model="P3 Eq40 Rh1, M0",
        matched_post_and_opening_frames=len(matched),Mandel_rows=len(window),
        opening=matched.iloc[0].to_dict(),sampled_B_peak=peak.to_dict(),
        A_same_window_rms_Pa=np.sqrt(np.mean(window.A_pressure_error_Pa**2)),
        B_same_window_rms_Pa=np.sqrt(np.mean(window.B_pressure_error_Pa**2)),
        solver_to_solver_rms_Pa=np.sqrt(np.mean(window.BminusA_Pa**2)))
    matched.to_csv(target,index=False)
    with result_path.open("x",encoding="utf8") as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review",type=Path)
    args=parser.parse_args()
    main(args.review)
