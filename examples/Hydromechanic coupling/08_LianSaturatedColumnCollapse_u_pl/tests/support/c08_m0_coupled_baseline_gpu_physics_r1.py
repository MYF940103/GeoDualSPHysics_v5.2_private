"""Compare released TPI native states to retained finite-Kw C08 and the sampled Fig. 14 outline."""
import csv
import json
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from c08_m0_coupled_baseline_gpu_review_r1 import load,T,TAG,mature
from c08_m0_coupled_deformed_r1 import SEED


def analyse(label,folder,release,source):
    rows=[];chosen=None;pressure_samples=[];initial=source["Posd"][2060:]
    dt=(initial[:,2]>initial[:,2].max()-.020);db=(initial[:,2]<initial[:,2].min()+.020)
    for file in sorted((folder/"data").glob("Part_????.bi4")):
        m,a,_=load(file,label!="finite Kw")
        if not m["GravityPreloadPhase"]:continue
        tau=m["TimeStep"]-release
        if tau>.300006:break
        if tau<.00999:continue
        s=a["Idp"]>=2060;pos=a["Posd"][s];p=a["PorePress"][s].astype(float)
        k=a["Kplastic"][s];vel=a["Vel"][s];stress=a["SigmaState_kk"][s];sxz=a["SigmaState_ij"][s,2]
        fs=np.isin(a["FSType"][s],[2,3])
        # NN is defined between distinct native material IDs in the x-z physical plane.
        nn=cKDTree(pos[:,[0,2]]).query(pos[:,[0,2]],k=2)[0][:,1]/.04
        rows.append(dict(method=label,part=int(file.stem[-4:]),absolute_time_s=m["TimeStep"],actual_tau_s=tau,
            front_m=pos[:,0].max(),p_min_Pa=p.min(),p_max_Pa=p.max(),p_rms_Pa=np.sqrt(np.mean(p*p)),
            negative_material=int((p<0).sum()),negative_surface=int(np.sum((p<0)&fs)),
            negative_interior=int(np.sum((p<0)&~fs)),kappamax=k.max(),plastic_material=int((k>0).sum()),
            kappa_p99=np.quantile(k,.99),p01_Pa=np.quantile(p,.01),p99_Pa=np.quantile(p,.99),
            contact_cluster_ids=int((nn<.7).sum()),
            nn_min_dp=nn.min(),nn_p01_dp=np.quantile(nn,.01),nn_p99_dp=np.quantile(nn,.99),nn_max_dp=nn.max(),
            surface_nn_p99_dp=np.quantile(nn[fs],.99),max_speed_m_s=np.linalg.norm(vel,axis=1).max(),
            stresszz_total_rms_Pa=np.sqrt(np.mean((stress[:,2]-p)**2)),
            effective_shear_xz_rms_Pa=np.sqrt(np.mean(sxz**2)),effective_shear_xz_maxabs_Pa=np.max(np.abs(sxz)),
            Jmin=a["PoroVolumeRatio"][s].min(),Jmax=a["PoroVolumeRatio"][s].max(),
            k_min_m_s=a["PoroHydraulicConductivity"][s].min(),k_max_m_s=a["PoroHydraulicConductivity"][s].max(),
            top_settlement_mm=(initial[dt,2]-pos[dt,2]).mean()*1000,
            bed_settlement_mm=(initial[db,2]-pos[db,2]).mean()*1000))
        if abs(tau-.3)<1e-5:chosen=(pos,p,k,sxz)
        pressure_samples.append(p)
    assert len(rows)==30 and chosen is not None
    sampled=np.asarray(pressure_samples);inc=np.diff(sampled,axis=0)
    second=np.diff(inc,axis=0)
    variation=np.abs(inc).sum(axis=0)
    excess_variation=variation-np.abs(sampled[-1]-sampled[0])
    reversal=np.count_nonzero(inc[:-1]*inc[1:]<0,axis=0)
    roughness=dict(all_particle_sampled_second_difference_RMS_Pa=float(np.sqrt(np.mean(second**2))),
        particle_nonmonotone_pressure_travel_mean_Pa=float(np.mean(excess_variation)),
        particle_nonmonotone_pressure_travel_p99_Pa=float(np.quantile(excess_variation,.99)),
        particle_increment_direction_reversals_mean=float(np.mean(reversal)),
        native_sample_interval_s=.01,samples=30)
    return rows,chosen,roughness


def main():
    stage=TAG+"_w30";gate=json.loads((T/"logs"/(stage+".check.json")).read_text())
    summary=T/"logs"/(stage+".physical.json");tab=T/"figures"/(stage+"_physical.csv")
    contour=T/"figures"/(stage+"_upper_envelope.csv");field_csv=T/"figures"/(stage+"_fields.csv")
    plot=T/"figures"/(stage+"_fields.png");timeplot=T/"figures"/(stage+"_history.png")
    assert all(not p.exists() for p in (summary,tab,contour,field_csv,plot,timeplot))
    source_meta,source,_=load(mature.hold.PRE,False)
    paper=list(csv.DictReader((T/"figures/upl_c08_lian14_outline_r1_outline.csv").open()))
    outline=np.array([(float(r["x_m"]),float(r["z_m"])) for r in paper if float(r["requested_tau_s"])==.3])
    pfront=float(outline[:,0].max());names=["finite Kw","TPI β=0","TPI β=0.04"]
    folders=[SEED,T/"outputs"/(stage+"_b0"),T/"outputs"/(stage+"_b004")]
    clocks=[source_meta["TimeStep"],gate["release"],gate["release"]]
    groups=[analyse(n,f,clock,source) for n,f,clock in zip(names,folders,clocks)]
    tables=[r for js,_,_ in groups for r in js]
    # Original branch saved the post-schedule +1 step; compare actual tau and retain both clocks.
    for i in range(30):
        tau=groups[1][0][i]["actual_tau_s"]
        assert abs(tau-groups[2][0][i]["actual_tau_s"])<1e-14 and abs(tau-groups[0][0][i]["actual_tau_s"])<5.1e-6
    with tab.open("x",newline="",encoding="utf-8") as fo:
        w=csv.DictWriter(fo,fieldnames=list(tables[0]));w.writeheader();w.writerows(tables)
    fig,axs=plt.subplots(2,2,figsize=(10.5,7.0),layout="constrained")
    for j,((records,_,_),name) in enumerate(zip(groups,names)):
        for ax,key,title,factor in zip(axs.flat,("p_min_Pa","contact_cluster_ids","front_m","top_settlement_mm"),
                          ("Minimum pore pressure (kPa)","Particles with nearest spacing <0.7 dp","Front position (m)","Top material settlement (mm)"),(.001,1.,1.,1.)):
            ax.plot([r["actual_tau_s"] for r in records],[factor*r[key] for r in records],label=name,
                    color=("0.15","tab:blue","tab:orange")[j],linestyle=("--","-","-.")[j],
                    marker=("o","s","^")[j],markersize=4,markerfacecolor="none",markevery=(j,4))
            ax.set_ylabel(title);ax.set_xlabel("Time after wall removal (s)");ax.grid(alpha=.2)
    axs.flat[2].scatter([.3],[pfront],marker="x",color="black",label="Lian Fig. 14")
    axs.flat[2].legend();fig.savefig(timeplot,dpi=160);plt.close(fig)
    fig,axs=plt.subplots(2,3,figsize=(12,5),sharex=True,sharey=True,layout="constrained")
    lo=min(p.min() for _,(_,p,k,_),_ in groups)/1e3;hi=max(p.max() for _,(_,p,k,_),_ in groups)/1e3
    khi=max(k.max() for _,(_,p,k,_),_ in groups)
    with field_csv.open("x",newline="",encoding="utf-8") as fo:
        w=csv.writer(fo);w.writerow(["method","actual_tau_s","material_id","x_m","z_m","pore_pressure_Pa","kappa","effective_shear_xz_Pa"])
        for name,(records,(pos,p,k,sxz),_) in zip(names,groups):
            w.writerows((name,records[-1]["actual_tau_s"],2060+i,xy[0],xy[2],q,value,tau)
                        for i,(xy,q,value,tau) in enumerate(zip(pos,p,k,sxz)))
    pnorm=TwoSlopeNorm(vmin=lo,vcenter=0.,vmax=hi);knorm=Normalize(vmin=0.,vmax=khi)
    for col,((records,(pos,p,k,sxz),_),name) in enumerate(zip(groups,names)):
        for row,values,norm,cmap in ((0,p/1e3,pnorm,"coolwarm"),(1,k,knorm,"viridis")):
            ax=axs[row,col];sc=ax.scatter(pos[:,0],pos[:,2],c=values,s=1.6,lw=0,norm=norm,cmap=cmap)
            ax.scatter(outline[:,0],outline[:,1],s=1,c="black",linewidths=0)
            ax.set_aspect("equal");ax.set_xlabel("x (m)")
            if col==0:ax.set_ylabel("z (m)")
            if row==0:ax.set_title(name)
            if col==2:fig.colorbar(sc,ax=axs[row,:],shrink=.72,label="Pore pressure (kPa)" if row==0 else "Plastic history κ")
    fig.suptitle("C08 ψ=0°, 0.3 s after wall removal. Black: digitized boundary pixels in Lian Fig. 14")
    fig.savefig(plot,dpi=175);plt.close(fig)
    final=[dict(method=r["method"],tau_s=r["actual_tau_s"],front_m=r["front_m"],front_minus_paper_m=r["front_m"]-pfront,
          min_p_Pa=r["p_min_Pa"],near_IDs=r["contact_cluster_ids"],nn_min_dp=r["nn_min_dp"],kappa_max=r["kappamax"]) for js,_,_ in groups for r in js[-1:]]
    # Unsmooth, fixed 1-dp horizontal bins; the raster extent and centre envelope are different representations.
    dp=.04
    px=np.floor(outline[:,0]/dp).astype(int);paper_bins=np.unique(px);env=[];envelope_metrics={}
    for name,(_, (pos,_,_,_),_) in zip(names,groups):
        ix=np.floor(pos[:,0]/dp).astype(int);diffs=[]
        for b in paper_bins:
            paper_z=outline[px==b,1].max();nodes=pos[ix==b,2]
            if not nodes.size:continue
            z=nodes.max();delta=z-paper_z;diffs.append(delta)
            env.append(dict(method=name,x_left_m=float(b*dp),x_right_m=float((b+1)*dp),soil_count=int(nodes.size),
                      max_material_center_z_m=float(z),max_reference_edge_pixel_z_m=float(paper_z),signed_delta_m=float(delta)))
        envelope_metrics[name]=dict(overlap_bins=len(diffs),total_paper_bins=len(paper_bins),
            signed_mean_m=float(np.mean(diffs)),rms_m=float(np.sqrt(np.mean(np.square(diffs)))),bin_width_m=dp)
    with contour.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(env[0]));w.writeheader();w.writerows(env)
    pairs=[]
    for left,right in ((0,1),(1,2),(0,2)):
        pos0,p0,k0,s0=groups[left][1]
        pos1,p1,k1,s1=groups[right][1]
        shift=np.linalg.norm(pos1-pos0,axis=1)*1000
        pairs.append(dict(reference=names[left],candidate=names[right],matched_soil_ids=len(p0),
            actual_tau_offset_s=groups[right][0][-1]["actual_tau_s"]-groups[left][0][-1]["actual_tau_s"],
            pressure_difference_rms_Pa=np.sqrt(np.mean((p1-p0)**2)),
            pressure_difference_max_abs_Pa=np.max(np.abs(p1-p0)),
            common_negative_ids=np.count_nonzero((p0<0)&(p1<0)),
            reference_only_negative_ids=np.count_nonzero((p0<0)&(p1>=0)),
            candidate_only_negative_ids=np.count_nonzero((p0>=0)&(p1<0)),
            position_difference_rms_mm=np.sqrt(np.mean(shift**2)),position_difference_max_mm=shift.max(),
            plastic_history_difference_rms=np.sqrt(np.mean((k1.astype(float)-k0.astype(float))**2)),
            effective_shear_xz_difference_rms_Pa=np.sqrt(np.mean((s1-s0)**2))))
    summary.write_text(json.dumps(dict(paper_coloured_extent_m=pfront,raster_allowance_m=.03615819209039548,
         particle_centre_offset_scale_m=.02,fields="Raw values, matched ranges across all three methods",
         initial_conditions="Both M0 trajectories held the finite-Kw PRE with closed wall for 1 ms after a cold pressure-history switch; finite-Kw released at its original source endpoint.",
         pressure_history_observed_at_0p01_s={name:g[2] for name,g in zip(names,groups)},
         upper_envelope_in_common_native_raster_bins=envelope_metrics,
         finite_Kw_time_offset_s=float(groups[0][0][-1]["actual_tau_s"]-groups[1][0][-1]["actual_tau_s"]),
         paired_endpoint=pairs,final=final),indent=2,default=lambda v:v.item()))
    print(summary.read_text())


if __name__=="__main__":
    main()
