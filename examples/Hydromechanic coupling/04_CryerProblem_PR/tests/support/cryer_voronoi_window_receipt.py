"""Seal the actual fixed-clock GPU opening, its fixture and its saved native IDs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cryer_voronoi_window import DLL, DT, OUT, T

LOG = T/"logs/cryer_voronoi_window_open_r1.run.json"


def audit():
    completed = json.loads((OUT/"completed.json").read_text())
    fixture = json.loads((OUT/"fixture.json").read_text())
    assert completed["fixture"] == fixture and completed["closed_pass"] and completed["steps"] == 4160
    hist = pd.read_csv(OUT/"history.csv",float_precision="round_trip")
    cells = pd.read_csv(OUT/"shells.csv",float_precision="round_trip")
    clock = sorted({0,1,2,4,8,16,32,4097,*range(64,4161,64)})
    assert hist.step.tolist() == clock and np.array_equal(hist.time_s, hist.step*DT)
    assert np.array_equal(hist.tau_s, (hist.step-4096)*DT)
    assert len(cells)==len(hist)*20 and np.all(cells.groupby("step")["count"].sum()==37173)
    assert np.isfinite(hist.to_numpy()).all() and np.isfinite(cells.to_numpy()).all()
    frames = []
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as mesh:
        ids, fs, shell = mesh["native_ids"], mesh["native_surface"], mesh["material_shell"]
    for k in (4096,4097,4160):
        with np.load(OUT/f"state_{k}.npz") as frame:
            assert np.array_equal(ids,frame["ids"]) and int(frame["step"])==k
            for name in ("p","previous","u","v","stress","J"):
                assert len(frame[name])==len(ids) and np.all(np.isfinite(frame[name]))
            p, J = frame["p"],frame["J"]
            assert J.min()>1-float(np.float32(.3))
            if k>4096:
                assert np.max(abs(p[fs]))==0
            center = p[shell==1].mean()
            assert abs(center-hist[hist.step==k].center_Pa.item())<1e-9
            frames.append(dict(step=k,time_s=k*DT,tau_s=(k-4096)*DT,center18_Pa=center,
                               J_min=J.min(),J_max=J.max(),p_min_Pa=p.min(),p_max_Pa=p.max(),
                               surface_pressure_absmax_Pa=np.max(abs(p[fs]))))
    support = T/"support"
    tracked = [support/k for k in ("cryer_pair_window.py","cryer_pair_window.cu","cryer_weak_window.cu",
               "cryer_voronoi_window.py","cryer_voronoi_window.cu","build_cryer_voronoi_window.ps1",
               "cryer_voronoi_window_receipt.py")]
    produced = [OUT/k for k in ("fixture.json","completed.json","history.csv","shells.csv",
                "state_4096.npz","state_4097.npz","state_4160.npz")]
    build = DLL.parent
    files = tracked + produced + [DLL,build/"build.json",build/"build.log"]
    sha = {p.relative_to(T).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    warning = [s.strip() for s in (build/"build.log").read_text(encoding="utf-16").splitlines()
               if "warning " in s.lower()]
    with LOG.open("x",encoding="utf8") as out:
        json.dump(dict(steps=4160,closed_steps=4096,open_steps=64,sampled_states=len(hist),
                       material_ids=len(ids),surface_ids=len(fs),source_clock_s=DT,checkpoints=frames,
                       closed_limits=completed["closed_limits"],closed_max=completed["closed_max"],
                       closed_pass=completed["closed_pass"],time_advance_wall_s=completed["wall_seconds"],
                       recorded_utc=datetime.now(timezone.utc).isoformat(),
                       experiment="fixed reference, native mass and AV; changed only hydraulic K and F and their coupled row bound",
                       fixture=fixture,build_warnings=warning,sha256=sha),out,indent=2,allow_nan=False)
        out.write("\n")
    print(json.dumps(frames,indent=2))


if __name__ == "__main__":
    audit()
