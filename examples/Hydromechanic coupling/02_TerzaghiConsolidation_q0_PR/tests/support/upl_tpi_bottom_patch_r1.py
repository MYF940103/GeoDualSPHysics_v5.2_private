"""Replay the vertical momentum stress row beside the C02 fixed bed on saved geometry."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from upl_tpi_partial_bi4_r1 import read

TEST = Path(__file__).resolve().parents[1]
DATA = TEST / "outputs/upl_tpi_p3_B10us_full2tv_GPU_r1/data"
FIG = TEST / "figures"
TAG = "upl_tpi_bottom_patch_r1"
Q0 = 10000.
PERIOD = .1


def require(value, message):
    if not value:
        raise ValueError(message)


def ordered(frame):
    arrays = frame["arrays"]
    order = np.argsort(arrays["Idp"])
    require(np.array_equal(arrays["Idp"][order], np.arange(1040)), "Material IDs changed")
    return {name: arrays[name][order] for name in ("Posd", "PoroVolumeRatio", "PorePress", "SigmaState_kk",
            "SigmaState_ij", "HydroMechLoadAce")}


def dx_periodic(x):
    return x - PERIOD*np.rint(x/PERIOD)


class Bed:
    def __init__(self, initial):
        a = ordered(initial)
        meta = initial["root"]["values"]
        self.x, self.z = a["Posd"][:,0], a["Posd"][:,2]
        self.h = float(meta["H"])
        self.v0 = float(meta["MassFluid"]) / float(meta["Rhop0"])
        self.rho0 = float(meta["Rhop0"])
        require(meta["CaseNfixed"] == 40 and meta["CaseNfluid"] == 1000 and abs(self.h - .018) < 1e-8,
                "Wrong bed or smoothing length")
        # Reference material identities. Include 8 bottom layers and one interior control layer.
        layer = np.rint(self.z/.01-.5).astype(int)
        self.recv = np.concatenate([np.flatnonzero(layer == i) for i in (*range(8), 49)])
        require(len(self.recv) == 90 and np.array_equal(np.sort(np.unique(layer[:40])), [-4,-3,-2,-1]),
                "Unexpected material layout")
        d2 = dx_periodic(self.x[:40,None]-self.x[None,40:])**2 + (self.z[:40,None]+self.z[None,40:])**2
        self.partner = 40 + np.argmin(d2, axis=1)
        require(len(np.unique(self.partner)) == 40 and np.max(np.min(d2, axis=1)) < 1e-23,
                "No unique original reflection across z=0")
        # Fixed superset by material ID; actual support is tested independently per frame.
        dx = dx_periodic(self.x[self.recv,None] - self.x)
        dz = self.z[self.recv,None] - self.z
        self.row, self.nb = np.nonzero(dx*dx+dz*dz < (.049)**2)
        self.i = self.recv[self.row]

    def evaluate(self, x, z, J, pressure, effective, shear, mode):
        if mode == "mirror":
            x, z = x.copy(), z.copy()
            x[:40], z[:40] = x[self.partner], -z[self.partner]
        if mode == "fixed_volume":
            J = J.copy()
            J[:40] = 1.
        # All pairs initially outside .049 must remain outside 2H in both geometries.
        max_shift = np.max(np.hypot(dx_periodic(x - self.x), z - self.z))
        require(.049 - 2*max_shift > 2*self.h, "Neighbour candidate list cannot cover full kernel support")
        i, j = self.i, self.nb
        dx, dz = dx_periodic(x[i]-x[j]), z[i]-z[j]
        r = np.hypot(dx,dz)
        # Wendland 2D derivative (decimal coefficients used in FunSphKernel.h).
        # Difference from CUDA: binary64 coordinates and sum, independent material-order traversal.
        fac = -2.7852 / self.h**4 * np.maximum(1.-.5*r/self.h, 0.)**3
        rho = 1000. + (self.rho0-1000.) / J[i]
        gx, gz = self.v0*J[j]*fac*dx/rho, self.v0*J[j]*fac*dz/rho
        def layers(v):
            return np.bincount(self.row, weights=v, minlength=len(self.recv)).reshape(9,10).mean(axis=1)
        # Constant prestress is a manufactured patch on each real geometry, including ramp states.
        # The linear coefficient isolates the difference term of the symmetric stress gradient.
        c = layers(-2*Q0*gz)
        m = layers(-rho*gz*dz)
        f = layers((effective[i]+effective[j])*gz+(shear[i]+shear[j])*gx)
        p = layers(-(pressure[i]+pressure[j])*gz)
        return c, m, f, p


def main():
    history = pd.read_csv(TEST.parent/"figures/upl_tpi_p3_full_diagnostic_r1/history.csv",float_precision="round_trip")
    require(len(history) == 1653 and history.stress_guard_failed.sum()==225, "Wrong sealed full history")
    case = Bed(read(DATA/"Part_0000.bi4"))
    dst = [FIG/(TAG+".csv"), FIG/(TAG+"_patch.csv"), FIG/(TAG+".png"), TEST/"logs"/(TAG+".check.json")]
    require(not any(p.exists() for p in dst), "Use retained outputs; this review does not overwrite them")
    rows = []
    for h in history.itertuples():
        frame = read(DATA/f"Part_{h.part:04d}.bi4")
        require(float(frame["part"]["values"]["TimeStep"]) == h.time_s, "Save clock differs")
        a = ordered(frame)
        x,z = a["Posd"][:,0],a["Posd"][:,2]
        J, p = a["PoroVolumeRatio"], a["PorePress"].astype(float)
        s = a["SigmaState_kk"][:,2]
        # The momentum kernel converts double constitutive state to float, then sums in double.
        eff = s.astype(np.float32).astype(float)
        sxz = a["SigmaState_ij"][:,2].astype(np.float32).astype(float)
        idx = case.recv[:10]
        row = dict(part=h.part, time_s=h.time_s, guard_applies=h.stress_guard_applies,
                   failed=h.stress_guard_failed, pressure_error_Pa=p[idx].mean()-h.ref_bottom_pressure_Pa,
                   total_stress_error_Pa=(s[idx]-p[idx]).mean()+Q0,
                   applied_zmax_abs_m_s2=float(np.abs(a["HydroMechLoadAce"][idx,2]).max()))
        require(row["applied_zmax_abs_m_s2"]==0., "Unexpected direct external load at bottom")
        for mode in ("native","mirror","fixed_volume"):
            const,linear,e,pw=case.evaluate(x,z,J,p,eff,sxz,mode)
            for key,num in (("const_bottom_m_s2",const[0]),("const_interior_m_s2",const[-1]),
                            ("linear_bottom",linear[0]),("linear_interior",linear[-1]),
                            ("effective_bottom_m_s2",e[0]),("pressure_bottom_m_s2",pw[0]),
                            ("actual_stress_bottom_m_s2",e[0]+pw[0])):
                row[f"{mode}_{key}"]=float(num)
        if h.stress_guard_failed:
            require(h.worst_layer == 0 and abs(abs(row["total_stress_error_Pa"])-h.max_layer_stress_error_Pa)<1e-7,
                    "Bottom material stress differs from independently accepted saved-state review")
        rows.append(row)
    table=pd.DataFrame(rows)
    bad=table[table.failed]
    require(len(bad)==225 and bad.iloc[-1].part==1652,"Guard review differs")
    # Uniform affine compression. Exact constant stress gives no force; interior first moment
    # quantifies the kernel's discretization on the finite lattice without any wall.
    fixture=[]
    for stretch in (1.,.999,.9963,.995):
        z=case.z.copy(); z[40:]*=stretch
        j=np.full_like(z,stretch)
        zeros=np.zeros_like(z)
        for mode in ("native","mirror","fixed_volume"):
            c,m,_,_=case.evaluate(case.x,z,j,zeros,zeros,zeros,mode)
            fixture.append(dict(stretch=stretch,mode=mode,bottom_constant_m_s2=c[0],interior_constant_m_s2=c[-1],
                                bottom_linear_moment=m[0],interior_linear_moment=m[-1]))
            if mode=="mirror":
                require(abs(c[0])<2e-9 and abs(m[0]-m[-1])<1e-11, "Mirrored affine patch failed")
    patch=pd.DataFrame(fixture)
    table.to_csv(dst[0],index=False);patch.to_csv(dst[1],index=False)
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout="constrained")
    late=table[table.time_s>=.1]
    for mode,lab in (("native","Saved geometry and J"),("mirror","Reflect wall quadrature locations"),("fixed_volume","Set wall quadrature J=1")):
        axes[0,0].plot(late.time_s,late[f"{mode}_const_bottom_m_s2"],label=lab)
        axes[0,1].plot(late.time_s,late[f"{mode}_actual_stress_bottom_m_s2"],label=lab)
        subset=patch[(patch["mode"]==mode)]
        axes[1,1].plot(subset.stretch,subset.bottom_constant_m_s2,"o-",label=lab)
    axes[0,0].set_title("Uniform -10 kPa on saved geometry")
    axes[0,1].set_title("Recorded pressure and effective stress")
    axes[1,0].plot(late.time_s,late.total_stress_error_Pa,label="Bottom total stress error")
    axes[1,0].plot(late.time_s,late.pressure_error_Pa,label="Bottom pressure error")
    axes[1,0].axhline(-100,color="k",linestyle="--",label="Lower total-stress limit")
    axes[1,1].set_title("Manufactured affine compression")
    for ax in axes.flat: ax.grid(alpha=.25)
    for ax in axes[0]: ax.set(xlabel="Time (s)",ylabel="Vertical acceleration (m/s²)")
    axes[1,0].set(xlabel="Time (s)",ylabel="Error (Pa)",ylim=(-135,135),title="Errors against original reference, ±135 Pa detail")
    axes[1,1].set(xlabel="Vertical stretch",ylabel="Vertical acceleration (m/s²)")
    axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=8)
    fig.savefig(dst[2],dpi=165);plt.close(fig)
    summary=dict(frames=len(table),failed_frames=len(bad),first_failed=bad.iloc[0].to_dict(),
                 final=table.iloc[-1].to_dict(), failed_window_max_abs_pressure_error_Pa=float(bad.pressure_error_Pa.abs().max()),
                 failed_window_minmax_const_m_s2={m:[float(bad[m+"_const_bottom_m_s2"].min()),
                                                     float(bad[m+"_const_bottom_m_s2"].max())] for m in ("native","mirror","fixed_volume")},
                 manufactured=fixture,physical_acceptance=False,solver_launches=0,
                 scope="Frozen vertical stress-divergence row; cold virtual wall replays exclude dynamics, stage velocity, HG and viscosity.")
    dst[3].write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__=="__main__":main()
