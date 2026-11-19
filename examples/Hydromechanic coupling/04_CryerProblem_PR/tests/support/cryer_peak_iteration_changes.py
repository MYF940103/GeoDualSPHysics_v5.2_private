"""Compare actual P3 pressure updates with benchmark errors at shared saved times."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from cryer_p3_verify_r1 import CENTER, TESTS, need


def inspect(folder,review):
    flags=review/"cryer_tpi_p3_peak_review.json"
    if not flags.exists():flags=review/"peak_rejected.json"
    decision=json.loads(flags.read_text())
    need(decision["native"]["frames"]==577 and decision["sidecar"]["pressure_rounds"]==3,
         "Native and method review must be complete")
    frame=pd.read_csv(review/"physical/native_and_theory.csv",float_precision="round_trip")
    body=pd.read_csv(folder/"UplTpiP3GpuR1.body.csv",float_precision="round_trip")
    need(np.array_equal(frame.time_s,body.time_s),"Body time alignment")
    saved=frame[["part","time_s","tau_s","legacy_Tv","center18_Pa","M0_r18_Pa","native_minus_M0_Pa"]].copy()
    prior=None
    for roundno in (1,2,3):
        table=pd.read_csv(folder/f"UplTpiP3GpuR1.round{roundno}.csv",float_precision="round_trip")
        group=table.groupby("part")
        need(len(table)==577*18 and np.array_equal(group.actual_save_time_s.first(),frame.time_s)
             and np.array_equal(table.native_id.to_numpy().reshape(577,18),np.tile(CENTER,(577,1))),
             "Fixed center or step identity")
        q=table.endpoint_q_actual_float_Pa.to_numpy().reshape(577,18)
        p=table.validated_BC_value_float_Pa.to_numpy().reshape(577,18)
        if prior is not None:need(np.array_equal(q,prior),"Next pressure round uses another field")
        diff=p-q
        prefix=f"iteration_{roundno}"
        saved[prefix+"_center_mean_change_Pa"]=np.mean(diff,axis=1)
        saved[prefix+"_center_rms_change_Pa"]=np.sqrt(np.mean(diff**2,axis=1))
        saved[prefix+"_center_max_abs_change_Pa"]=np.max(abs(diff),axis=1)
        if roundno>1:
            bounds=body[f"max_abs_p{roundno}_minus_p{roundno-1}_Pa"]
            need(np.all(saved[prefix+"_center_max_abs_change_Pa"]<=bounds),"Body maximum smaller than center")
            saved[prefix+"_body_max_abs_change_Pa"]=bounds
        prior=p
    need(np.array_equal(np.mean(prior,axis=1),saved.center18_Pa),"Final iteration differs from native")
    data=pd.read_csv(TESTS/"figures/cryer_shell_equilibrium_r1_history.csv",float_precision="round_trip")
    ref=data.loc[data.method=="A_finiteKw",["time_s","center_p_Pa","center_dp_Pa"]]
    saved=saved.merge(ref.rename(columns={"center_p_Pa":"explicit_center_Pa","center_dp_Pa":"explicit_error_Pa"}),
                      on="time_s",how="left",validate="one_to_one")
    window=saved.loc[(saved.legacy_Tv>=.005)&(saved.tau_s<=.0625)]
    need(not window.explicit_error_Pa.isna().any(),"Missing actual explicit A comparison")
    peak=window.loc[window.center18_Pa.idxmax()]
    eps=window.native_minus_M0_Pa.to_numpy();a=window.explicit_error_Pa.to_numpy()
    summary=dict(physical_profile="server peak",frames=len(saved),window=len(window),actual_peak_part=int(peak.part),
                 peak_native_Pa=peak.center18_Pa,peak_same_clock_error_Pa=peak.native_minus_M0_Pa,
                 last_iteration_peak_center_max_Pa=peak.iteration_3_center_max_abs_change_Pa,
                 last_iteration_peak_body_max_Pa=peak.iteration_3_body_max_abs_change_Pa,
                 max_last_iteration_center_in_window_Pa=window.iteration_3_center_max_abs_change_Pa.max(),
                 max_last_iteration_body_in_window_Pa=window.iteration_3_body_max_abs_change_Pa.max(),
                 window_rms_P3_error_M0_Pa=float(np.sqrt(np.mean(eps**2))),
                 window_rms_A_error_finite_Kw_Pa=float(np.sqrt(np.mean(a**2))),
                 window_rms_difference_of_method_specific_errors_Pa=float(np.sqrt(np.mean((eps-a)**2))),
                 peak_A_error_same_clock_Pa=peak.explicit_error_Pa,
                 qualification=bool(decision["peak_qualified"]))
    csvpath=TESTS/"figures/cryer_peak_iteration_changes_r1.csv"
    receipt=TESTS/"logs/cryer_peak_iteration_changes_r1.check.json"
    need(not csvpath.exists() and not receipt.exists(),"Existing review")
    saved.to_csv(csvpath,index=False,float_format="%.17g")
    with receipt.open("x",encoding="utf8") as f:json.dump(summary,f,indent=2,allow_nan=False)


def plot_saved(csvpath, destination):
    """Plot without opening solver files or repeating the native review."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import ScalarFormatter

    data=pd.read_csv(csvpath, float_precision="round_trip")
    window=data.loc[(data.legacy_Tv>=.005) & (data.tau_s<=.0625)]
    need(len(window)==475 and not destination.exists(),"Missing Mandel window or existing figure")
    fig,axes=plt.subplots(3,1,figsize=(9.2,8.6),sharex=True,
                          gridspec_kw={"height_ratios":[1.3,.8,1]},layout="constrained")
    t=window.legacy_Tv
    axes[0].plot(t,window.explicit_error_Pa,color="#ae5827",label="Explicit u-pl minus finite-Kw theory")
    axes[0].plot(t,window.native_minus_M0_Pa,color="#214f86",linestyle="--",label="Three-round TPI minus M0 theory")
    axes[0].set_ylabel("Pressure error (Pa)")
    axes[0].legend(frameon=False)
    axes[1].plot(t,window.native_minus_M0_Pa-window.explicit_error_Pa,color="#35654d")
    axes[1].set_ylabel("TPI error minus\nexplicit error (Pa)")
    axes[2].plot(t,window.iteration_3_body_max_abs_change_Pa,color="#76767e",label="All soil particles")
    axes[2].plot(t,window.iteration_3_center_max_abs_change_Pa,color="#6c4090",label="18 center particles")
    axes[2].set_ylabel("Maximum third-round\nupdate (Pa)")
    axes[2].set_xlabel("Drainage-relative time factor, $T_v$")
    axes[2].legend(frameon=False)
    peak=window.loc[window.center18_Pa.idxmax()]
    for ax in axes:
        ax.axvline(peak.legacy_Tv,color="#666666",lw=.8,ls=":")
        ax.grid(alpha=.20)
        ax.set_xscale("log")
    axes[2].set_xticks([.005,.01,.02,.04,.06])
    axes[2].xaxis.set_major_formatter(ScalarFormatter())
    axes[2].set_xlim(t.min(),t.max())
    axes[0].set_title("Cryer center pressure at matched times  |  ν = 0.30\nDotted line marks the saved TPI peak")
    fig.savefig(destination,dpi=165)
    plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path,nargs="?")
    parser.add_argument("review",type=Path,nargs="?")
    parser.add_argument("--plot",action="store_true",help="Use only the saved comparison CSV")
    args=parser.parse_args()
    figures=TESTS/"figures"
    if args.plot:
        plot_saved(figures/"cryer_peak_iteration_changes_r1.csv",figures/"cryer_peak_iteration_changes_r1.png")
    elif args.output and args.review:
        inspect(args.output,args.review)
    else:
        parser.error("Provide solver output and review paths, or --plot")
