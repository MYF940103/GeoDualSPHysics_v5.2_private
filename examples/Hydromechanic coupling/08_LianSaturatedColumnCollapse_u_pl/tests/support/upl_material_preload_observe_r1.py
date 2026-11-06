"""One closed GPU preload: native material-band observations, no equilibrium gate."""
import json,math,struct
from pathlib import Path
import upl_plastic_periodic_pair_r1 as helpers
from upl_plastic_periodic_pair_r1 import np,plt,SCHEMA,TYPES,need,js,stat,table,write,bound
TAG="upl_material_preload_GPU_r1"
N,SAMPLES,STEPS,DT=7060,257,8192,2.**-18
BANDS=("all","top_2h","bottom_2h","left_2h","right_2h")
COUNTS=(5000,300,300,150,150)

def run():
    tests=Path(__file__).resolve().parents[1];native=tests/"outputs"/(TAG+"_native_r1");old=tests/"outputs/upl_material_gravity_GPU_r1_native_r1"
    prefix=tests/"figures/upl_material_preload_observe_r1"
    paths={k:Path(str(prefix)+s) for k,s in {"history":"_history.csv","late":"_late_quarter.csv","png":".png","check":".check.json"}.items()}
    need(not any(p.exists() for p in paths.values()),"Existing preload observation artifacts protected")
    owner_path=tests/"logs"/(TAG+".run.json");call_path=tests/"logs"/(TAG+"_native_r1.call.json")
    build_path=tests/"logs/upl_material_gravity_Debug_r1.build.json";source_path=tests/"logs/upl_material_gravity_Debug_r1.source.json";reader_build_path=tests/"logs/upl_material_preload_native_r1.build.json"
    consumed=[stat(p) for p in (Path(__file__),tests/"notes/upl_material_preload_observe_r1.json",Path(helpers.__file__),tests/"support/upl_c08_fsmask_r1.py",owner_path,call_path,build_path,source_path,reader_build_path)]
    owner,call,build,reader_build=js(owner_path),js(call_path),js(build_path),js(reader_build_path)
    need(owner["passed"] and owner["actual_exit"]==0 and owner["actual_steps"]==STEPS and owner["saved_frames"]==SAMPLES,"Actual owned preload solver completion required")
    need(call["actual_Popen_wait_exit"]==0 and call["actual_Win32_exit"]==0,"Actual owned reader exits required")
    need(build["passed"] and reader_build["passed"],"Closed solver and reader builds required")
    consumed += [bound(build["source_capture"]),bound(build["program"]),bound(reader_build["source"]),bound(reader_build["source_build"]),bound(reader_build["program"]),bound(call["program"])]
    argv=call["argv"];need(argv[-4:-2]==["--read","GPU"] and Path(argv[-2]).samefile(tests/"outputs"/TAG/"data") and Path(argv[-1]).samefile(native),"Actual reader argv/dataset differs")
    need(Path(call["program"]["path"]).samefile(reader_build["program"]["path"]),"Actual reader program differs from closed build")
    done=js(native/"completion.json")
    expected=dict(stage="upl_material_preload_native_r1",input_run_tag=TAG,backend_argument="GPU",samples=SAMPLES,completed_steps=STEPS,last_saved_step=8191,actual_end_s=.03125,dt_s=DT,total_native_IDs=N,soil_IDs=5000,fixed_IDs=2060,typed_arrays=22,typed_bytes_per_particle=212,soil_ledger_rows=1285000,fixed_marker_rows=529420,soil_cache_float_bits_checks=1285000,free_seepage_metadata_checks=SAMPLES,noninitial_signed_intervals=256,soil_noninitial_kappa_monotonic_checks=1280000)
    need(all(done[k]==v for k,v in expected.items()),"Original completed preload native profile differs")
    for k in ("passed","all22_arrays_finite_and_ID_aligned","actual_scalar_clock_verified","no_exclusions","saved_FS23_soil_pressure_nonpositive","initial_soil_and_fixed_kappa_zero_verified"):need(done[k] is True,"Original native guard not passed: "+k)
    need(done["initial_material_band_counts"]==list(COUNTS) and len(done["saved_FS23_soil_checks_by_part"])==SAMPLES and all(v>0 for v in done["saved_FS23_soil_checks_by_part"]),"Actual material-band or nonempty free-surface coverage differs")
    old_check_path=tests/"logs/upl_material_gravity_GPU_r1_native_r1.check.json";old_check=js(old_check_path)
    need(old_check["passed"] and old_check["original_native_guards_passed"] and old_check["consumed_stats_unchanged"],"Closed retained gravity native control required")
    consumed += [stat(old_check_path),bound(old_check["native_completion"]),bound(old_check["reader_call"])]
    old_done=js(old/"completion.json");old_call=js(old_check["reader_call"]["path"])
    need(old_done["passed"] and old_done["stage"]=="upl_material_gravity_native_r1" and old_done["input_run_tag"]=="upl_material_gravity_GPU_r1" and old_done["samples"]==5 and old_done["completed_steps"]==128 and old_call["actual_Popen_wait_exit"]==0,"Retained five-frame actual decode differs")
    for d in (native,old):
        consumed += [stat(d/leaf) for leaf in ("completion.json","history.csv","clocks.csv","typed22.bin","typed22_layout.csv","native_ids.csv")]
        layout=table(d/"typed22_layout.csv");need(len(layout)==22,"22 actual typed layout rows required")
        for row,(name,kind,nc) in zip(layout,SCHEMA):need((row["array"],row["type"],int(row["components"]),int(row["bytes_per_particle"]))==(name,kind,nc,TYPES[kind].itemsize*nc),"Original typed layout differs")
    record_bytes=8+N*212;payloads=[]
    for d,samples in ((native,SAMPLES),(old,5)):
        need((d/"typed22.bin").stat().st_size==12+samples*record_bytes,"Actual typed file size differs")
        with (d/"typed22.bin").open("rb") as f:
            need(struct.unpack("<III",f.read(12))==(N,22,samples),"Actual sample header differs");payloads.append(f.read(5*record_bytes))
    prefix_exact=payloads[0]==payloads[1];need(prefix_exact,"First five original typed22 payload records differ")
    new_clock_raw=(native/"clocks.csv").read_bytes().splitlines(keepends=True);old_clock_raw=(old/"clocks.csv").read_bytes().splitlines(keepends=True)
    clock_prefix_exact=len(old_clock_raw)==6 and new_clock_raw[:6]==old_clock_raw;need(clock_prefix_exact,"First five raw signed-clock rows/header differ")
    need((native/"native_ids.csv").read_bytes()==(old/"native_ids.csv").read_bytes(),"Original material ID/coordinate map differs")
    clocks=table(native/"clocks.csv");history=table(native/"history.csv");need(len(clocks)==SAMPLES and len(history)==5*SAMPLES,"All257 clocks/1285 native band histories required")
    scalar=0.;times=[]
    for part,c in enumerate(clocks):
        if part:
            for _ in range(32):scalar+=DT
        times.append(float(c["time_s"]))
        need(int(c["part"])==part and int(c["completed_step"])==32*part and int(c["saved_step"])==(32*part-1 if part else 0) and float(c["dt_s"])==DT and struct.pack("<d",times[-1])==struct.pack("<d",scalar),"Actual scalar saved time/step differs")
        if part<5:need(struct.pack("<d",times[-1])==payloads[0][part*record_bytes:part*record_bytes+8],"Actual prefix payload time differs")
    cutoff=.75*times[-1];series=[];by_band={band:[] for band in BANDS}
    for i,h in enumerate(history):
        part,band=divmod(i,5);name=BANDS[band];need(int(h["part"])==part and h["initial_material_band"]==name and int(h["count"])==COUNTS[band] and float(h["time_s"])==times[part],"Native history order/material count/actual time differs")
        r={k:(v if k=="initial_material_band" else int(v) if k in ("part","count") else float(v)) for k,v in h.items()};need(all(math.isfinite(v) for k,v in r.items() if k!="initial_material_band"),"Nonfinite native history")
        r.update(completed_step=32*part,signed_dterror_s=float(clocks[part]["signed_dterror_s"]),mean_velocity_norm_m_s=math.sqrt(sum(r[k]**2 for k in ("mean_vx_m_s","mean_vy_m_s","mean_vz_m_s"))),J_max_abs_departure=max(abs(r["min_J"]-1),abs(r["max_J"]-1)),late_quarter=times[part]>=cutoff)
        previous=by_band[name][-1] if part else None;delta=times[part]-previous["time_s"] if previous else None
        r["backward_interval_s"]=delta if previous else ""
        for axis in ("x","y","z"):r["interval_change_mean_v"+axis+"_over_dt_m_s2"]=(r["mean_v"+axis+"_m_s"]-previous["mean_v"+axis+"_m_s"])/delta if previous else ""
        r["interval_change_mean_velocity_vector_norm_over_dt_m_s2"]=math.sqrt(sum(r["interval_change_mean_v"+axis+"_over_dt_m_s2"]**2 for axis in ("x","y","z"))) if previous else ""
        r["interval_velocity_RMS_slope_m_s2"]=(r["velocity_XYZ_RMS_m_s"]-previous["velocity_XYZ_RMS_m_s"])/delta if previous else ""
        by_band[name].append(r);series.append(r)
    fields={"velocity_XYZ_RMS_m_s":"m/s","mean_velocity_norm_m_s":"m/s","mean_vx_m_s":"m/s","mean_vy_m_s":"m/s","mean_vz_m_s":"m/s","p_mean_Pa":"Pa","p_RMS_Pa":"Pa","sigma_eff_Frobenius_RMS_Pa":"Pa","theta_RMS_s_inv":"1/s","min_J":"1","max_J":"1","J_max_abs_departure":"1","kinetic_J_per_m":"J/m","displacement_RMS_mm":"mm","interval_change_mean_velocity_vector_norm_over_dt_m_s2":"m/s2 interval proxy","interval_velocity_RMS_slope_m_s2":"m/s2 RMS slope"}
    late=[]
    for band,rows in by_band.items():
        selected=[r for r in rows if r["late_quarter"]];need(len(selected)>1,"Late-quarter material history empty")
        for field,unit in fields.items():
            values=[r[field] for r in selected];late.append(dict(initial_material_band=band,count=selected[0]["count"],metric=field,unit=unit,first_part=selected[0]["part"],last_part=selected[-1]["part"],samples=len(selected),first_time_s=selected[0]["time_s"],last_time_s=selected[-1]["time_s"],first=values[0],last=values[-1],change_last_minus_first=values[-1]-values[0],minimum=min(values),maximum=max(values),range=max(values)-min(values)))
    write(paths["history"],series);write(paths["late"],late)
    fig,axes=plt.subplots(2,3,figsize=(14.7,8.7));colors=("#174b7a","#c65d16","#237a45","#8d4c9c","#777323");time=np.array(times)*1000
    panels=(("velocity_XYZ_RMS_m_s","Material velocity: RMS / norm of mean","velocity (m/s)","mean_velocity_norm_m_s"),("p_RMS_Pa","Native pore pressure: RMS / signed mean","pressure (Pa)","p_mean_Pa"),("sigma_eff_Frobenius_RMS_Pa","Native effective stress","Frobenius RMS (Pa)",None),("theta_RMS_s_inv","Native final-stage volumetric rate",r"$\theta$ RMS (s$^{-1}$)",None),("J_max_abs_departure","Native volume-ratio departure",r"maximum $|J-1|$",None),("kinetic_J_per_m","Native mixture kinetic energy","energy per width (J/m)",None))
    for ax,(key,title,ylabel,second) in zip(axes.flat,panels):
        for color,(band,rows) in zip(colors,by_band.items()):
            ax.plot(time,[r[key] for r in rows],color=color,label=band,lw=1.45)
            if second:ax.plot(time,[r[second] for r in rows],color=color,ls="--",lw=.95)
        ax.axvspan(cutoff*1000,times[-1]*1000,color="#888888",alpha=.09);ax.set(title=title,xlabel="actual saved time (ms)",ylabel=ylabel);ax.grid(alpha=.22)
        if second:ax.text(.025,.965,"solid: RMS; dashed: norm of mean" if key.startswith("velocity") else "solid: RMS; dashed: signed mean",transform=ax.transAxes,va="top",fontsize=8)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.944),ncol=5,frameon=False);fig.suptitle("Fixed-gravity / free-seepage preload: observations, no equilibrium verdict",fontsize=14)
    fig.text(.5,.015,"257 raw saved states / five fixed initial-material ID bands (overlapping; energies must not be summed). Shading: last quarter of actual time.\nVelocity finite differences are interval changes of material-band means, not saved force/acceleration or reaction. No fitted theory, new residual tolerance, or equilibrium acceptance.",ha="center",fontsize=8.5);fig.tight_layout(rect=(0,.075,1,.895));fig.savefig(paths["png"],dpi=200);plt.close(fig)
    need(all(stat(e["path"])["bytes"]==e["bytes"] and stat(e["path"])["mtime_ns"]==e["mtime_ns"] for e in consumed),"Consumed receipt/export/helper SMT changed")
    result=dict(stage="upl_material_preload_observe_r1",offline_analysis_completed=True,source_owner_run=stat(owner_path),source_reader_call=stat(call_path),actual_solver_exit=owner["actual_exit"],actual_reader_Popen_exit=call["actual_Popen_wait_exit"],actual_reader_Win32_exit=call["actual_Win32_exit"],actual_frames=SAMPLES,material_band_history_rows=len(series),late_quarter_start_s=cutoff,late_summary_rows=len(late),initial_material_band_counts=dict(zip(BANDS,COUNTS)),original_native_completion=done,first_five_typed22_payload_records_bit_identical=prefix_exact,typed_headers_original_samples=dict(preload=SAMPLES,retained=5),first_five_raw_signed_clock_records_and_header_exact=clock_prefix_exact,retained_control="Same frozen GPU program/physics, upl_material_gravity_GPU_r1, first128 completed updates only",native_history_is_existing_reader_aggregation=True,source_provenance="Closed pre-cosmetic GPU build/source records are bound directly; their archive/base_source/cached_CUDA_origins remain historical. No mutable live source equality or new complete CUDA rebuild is claimed.",finite_difference_qualification="Backward saved-interval change of fixed initial-material-band mean velocity vector; its norm is not RMS particle acceleration. Speed-RMS slope is separately named. First late-window interval may begin just before the late cutoff.",overlapping_band_energy_sum_valid=False,max_velocity_available_in_history=False,late_quarter_is_observation_not_stationarity_test=True,equilibrium_tolerance_applied=False,force_or_reaction_inferred=False,kappa_zero_proves_equilibrium=False,theory_fit=False,physical_acceptance=False,figure_visual_QA_pending=True,consumed_stats=consumed,artifacts=[stat(p) for k,p in paths.items() if k!="check"],SHA_scans=0,solver_decoder_build_Git_actions=0)
    with paths["check"].open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(offline_analysis_completed=True,history_rows=len(series),late_summary_rows=len(late),prefix_payload_exact=prefix_exact,raw_clock_prefix_exact=clock_prefix_exact,physical_acceptance=False)),flush=True)

if __name__=="__main__":run()
