"""Offline actual-wall review; no solver, input editing or retained-output overwrite."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm

TESTS = Path(__file__).resolve().parents[1]
def entry(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

check = TESTS / "logs/upl_p3_wall_wave_ReleaseCPU_r4.check.json"
sealed = json.loads(check.read_text(encoding="utf-8-sig"))
assert sealed["passed"] and sealed["solver_jobs"] == 4
frozen = {str(Path(v["path"]).resolve()).casefold(): v for v in sealed["files"]}
inputs = [entry(__file__), entry(check)]
out = [TESTS / "figures" / ("upl_p3_wall_r1" + s) for s in (".png", "_history.csv")]
receipt = TESTS / "logs/upl_p3_wall_r1.check.json"
assert not any(p.exists() for p in out + [receipt]), "Retained analysis protected"
A, kappa, B, rho, rhow = 2**-9, 2*np.pi/.125, 2**28, 2048., 1000.
M = 89478488. + 4*134217728./3
cu = np.sqrt((M+B)/rho)
ps, us = B*A/cu, A/(cu*kappa)
D = B*float(np.float32(.0001))/(rhow*9.80665)
a = kappa*ps/(rho*A)
t = D*rhow*kappa*A/ps*a
matrix = np.array([[0,A/us,0,0],[0,0,-a,a],[0,M*kappa*A/ps,0,0],
                   [0,-B*kappa*A/ps,-t,-D*kappa**2+t]])
times = np.arange(257)*2**-23
reference = np.array([(expm(matrix*s)@np.array([0.,1.,0.,0.]))[[3,1,0]] for s in times])
runs = []
for tag in ("c", "h"):
    folder = TESTS / ("outputs/upl_p3_wall_wave_ReleaseCPU_r4_k1_"+tag)
    leaves = ("complete.json","physical.bin","modes.csv","wall_audit.csv","native_ids.csv","fixed_ids.csv")
    for leaf in leaves:
        e = entry(folder/leaf)
        assert e == frozen[e["path"].casefold()], "Frozen wall output changed"
        inputs.append(e)
    d = json.loads((folder/"complete.json").read_text())
    assert d["passed"] and d["actual_end_s"] == 2**-15 and d["samples"] == 257
    ids = list(csv.DictReader((folder/"native_ids.csv").open()))
    assert [int(v["native_id"]) for v in ids] == list(range(256,1280))
    band = np.array([int(v["wall_band"]) for v in ids], dtype=bool)
    assert band.sum() == 256
    path = folder/"physical.bin"
    assert np.fromfile(path,dtype="<u4",count=3).tolist() == [1024,26,257]
    assert path.stat().st_size == 12+257*(1+1024*26)*8
    raw = np.memmap(path,dtype="<f8",mode="r",offset=12,shape=(257,1+1024*26))
    assert np.array_equal(raw[:,0],times)
    state = raw[:,1:].reshape(257,1024,26)
    assert np.isfinite(state).all()
    modes = np.genfromtxt(folder/"modes.csv",delimiter=",",names=True)
    stored = np.column_stack([modes["p_continuum"]/ps,modes["v_continuum"]/A,modes["u_continuum"]/us])
    ref_error = float(np.max(abs(stored-reference)))
    assert ref_error <= 1e-10
    phase = kappa*state[0,:,0]
    errors, near = [], []
    for i in range(257):
        p = state[i,:,6]/ps-reference[i,0]*np.cos(phase)
        v = state[i,:,3:6].copy()/A
        u = (state[i,:,:3]-state[0,:,:3])/us
        v[:,0] -= reference[i,1]*np.sin(phase)
        u[:,0] -= reference[i,2]*np.sin(phase)
        square = np.column_stack([p*p,np.sum(v*v,axis=1),np.sum(u*u,axis=1)])
        errors.append(np.sqrt(square.mean(axis=0)))
        near.append(np.sqrt(square[band].mean(axis=0)))
    assert np.max(errors) <= .01 and np.max(near) <= .01
    endpoint = modes["p_cosine"][-1]/ps/reference[-1,0]-1
    assert abs(endpoint) <= .01
    flux = np.genfromtxt(folder/"wall_audit.csv",delimiter=",",names=True)
    assert len(flux) == 514 and np.array_equal(flux["time_s"],np.repeat(times,2))
    assert np.all(abs(flux["face_qn"]) <= flux["qn_bound"])
    runs.append(dict(state=state,modes=modes,errors=np.array(errors),near=np.array(near),flux=flux,
                     metrics=dict(tag=tag,reference_max_abs=ref_error,endpoint_pressure_relative_error=float(endpoint),
                                  global_max=np.max(errors,axis=0).tolist(),band_max=np.max(near,axis=0).tolist())))
c,h = runs
assert np.array_equal(c["state"][0],h["state"][0])
dp = c["state"][:,:,6]-h["state"][:,:,6]
du = c["state"][:,:,:3]-h["state"][:,:,:3]
dv = c["state"][:,:,3:6]-h["state"][:,:,3:6]
half = dict(p_RMS_Pa=float(np.max(np.sqrt(np.mean(dp*dp,axis=1)))),
            displacement_max_mm=float(1000*np.max(np.linalg.norm(du,axis=2))),
            normalized=[float(np.max(np.sqrt(np.mean(dp*dp,axis=1)))/ps),
                        float(np.max(np.sqrt(np.mean(np.sum(dv*dv,axis=2),axis=1)))/A),
                        float(np.max(np.sqrt(np.mean(np.sum(du*du,axis=2),axis=1)))/us)])
assert half["p_RMS_Pa"]<=5 and half["displacement_max_mm"]<=.005 and max(half["normalized"])<=1e-4
with out[1].open("x",newline="",encoding="utf-8") as stream:
    w=csv.writer(stream)
    w.writerow(["time_s","p_mode_coarse_over_Pstar","p_mode_half_over_Pstar","p_reference_over_Pstar",
                "global_p_RMS_percent","global_v_RMS_percent","global_u_RMS_percent",
                "band_p_RMS_percent","band_v_RMS_percent","band_u_RMS_percent"])
    for i,s in enumerate(times):
        w.writerow([s,c["modes"]["p_cosine"][i]/ps,h["modes"]["p_cosine"][i]/ps,reference[i,0],
                    *(100*h["errors"][i]),*(100*h["near"][i])])
fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
x=times*1e6
axes[0,0].plot(x,reference[:,0],"k--",lw=2,label="Continuum linear reference")
axes[0,0].plot(x,c["modes"]["p_cosine"]/ps,color="#2878b5",label="Actual coarse dt")
axes[0,0].plot(x,h["modes"]["p_cosine"]/ps,"o",markevery=16,ms=3,color="#d65f35",label="Actual half dt")
axes[0,0].set(ylabel="Pressure mode / P*");axes[0,0].legend(fontsize=8)
for j,label in enumerate(("Pressure","Velocity XYZ","Displacement XYZ")):
    axes[0,1].plot(x,100*h["errors"][:,j],label=label)
    axes[1,0].plot(x,100*h["near"][:,j],label=label)
axes[0,1].set(ylabel="Global normalized RMS [%]")
axes[1,0].set(ylabel="Fixed near-wall band normalized RMS [%]")
for ax in (axes[0,1],axes[1,0]):ax.axhline(1,color="k",ls="--",lw=1,label="1% short-wave objective");ax.legend(fontsize=8)
fl=h["flux"]
for plane,label in ((0.,"Left face"),(.0625,"Right face")):
    sel=fl["plane_x"]==plane
    axes[1,1].semilogy(fl["time_s"][sel]*1e6,np.maximum(abs(fl["face_qn"][sel]),1e-18),label=label)
axes[1,1].semilogy(x,fl["qn_bound"][::2],"k--",label="Unchanged face-flux budget")
axes[1,1].set(ylabel="Physical-plane |normal Darcy flux| [m/s]");axes[1,1].legend(fontsize=8)
for ax in axes.flat:ax.set(xlabel="Time [microseconds]");ax.grid(alpha=.25)
fig.suptitle("Private CPU dynamic seepage: two fixed planar FreeSlip walls\nWeak elastic wave, constant k, zero gravity; not general-boundary or full-cycle acceptance")
fig.savefig(out[0],dpi=180);plt.close(fig)
assert all(entry(v["path"])==v for v in inputs), "Analysis inputs changed"
result=dict(passed=True,scope="Independent short-wave actual-wall material-field review",inputs=inputs,
            runs=[r["metrics"] for r in runs],half=half,outputs=[entry(p) for p in out],
            reference="Independently scaled 4x4 matrix exponential; no stored RK4 reference used for field errors",
            physical_acceptance=False,raw_trajectories_cloud_backed=False)
receipt.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ("passed","runs","half")},indent=2))
