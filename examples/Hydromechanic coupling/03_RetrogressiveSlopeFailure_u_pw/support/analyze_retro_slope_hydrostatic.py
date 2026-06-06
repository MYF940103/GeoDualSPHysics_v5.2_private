#!/usr/bin/env python3
import csv
import math
import struct
import sys
from collections import Counter
from pathlib import Path

GAMMA_W = 1000.0 * 9.81
FREE_TYPES = {2, 3}


def _read_line(data, off):
    j = data.find(b"\n", off)
    if j < 0:
        return data[off:].strip(b"\r"), len(data)
    return data[off:j].strip(b"\r"), j + 1


def _skip_newline(data, off):
    if off < len(data) and data[off:off + 2] == b"\r\n":
        return off + 2
    if off < len(data) and data[off:off + 1] in (b"\n", b"\r"):
        return off + 1
    return off


def _unpack_values(data, off, nvals, typ):
    specs = {
        b"unsigned_int": ("I", 4),
        b"int": ("i", 4),
        b"unsigned_short": ("H", 2),
        b"short": ("h", 2),
        b"unsigned_char": ("B", 1),
        b"char": ("b", 1),
        b"float": ("f", 4),
        b"double": ("d", 8),
    }
    if typ not in specs:
        raise ValueError(f"Unsupported VTK binary type: {typ!r}")
    fmt, size = specs[typ]
    raw = data[off:off + nvals * size]
    return struct.unpack(">" + fmt * nvals, raw), off + nvals * size


def read_vtk(path):
    data = Path(path).read_bytes()
    off = 0
    points = None
    arrays = {}
    while off < len(data):
        line, off = _read_line(data, off)
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 3 and parts[0] == b"POINTS":
            npts = int(parts[1])
            vals, off2 = _unpack_values(data, off, npts * 3, parts[2])
            points = [vals[i:i + 3] for i in range(0, len(vals), 3)]
            off = _skip_newline(data, off2)
        elif len(parts) >= 3 and parts[0] == b"FIELD":
            nfields = int(parts[2])
            for _ in range(nfields):
                header, off = _read_line(data, off)
                hp = header.split()
                name = hp[0].decode("ascii")
                ncomp, ntuple, typ = int(hp[1]), int(hp[2]), hp[3]
                vals, off2 = _unpack_values(data, off, ncomp * ntuple, typ)
                arrays[name.lower()] = vals
                off = _skip_newline(data, off2)
    if points is None:
        raise ValueError(f"No POINTS block found in {path}")
    return points, arrays


def _array(arrays, name, default=None):
    return arrays.get(name.lower(), default)


def hydrostatic_errors(points, free_ids, porepress0):
    if not free_ids or porepress0 is None:
        return None
    errs = []
    for i, p in enumerate(points):
        # This is the same nearest free-surface idea used by HydroMechInitMode=FreeSurface
        # in 2D plane strain, where y is ignored.
        nearest = min(free_ids, key=lambda j: (p[0] - points[j][0]) ** 2)
        zwt = points[nearest][2]
        pref = GAMMA_W * max(0.0, zwt - p[2])
        errs.append(float(porepress0[i]) - pref)
    return {
        "rmse": math.sqrt(sum(e * e for e in errs) / len(errs)),
        "mean": sum(errs) / len(errs),
        "max_abs": max(abs(e) for e in errs),
    }


def summarize_file(path):
    points, arrays = read_vtk(path)
    fstype = _array(arrays, "fstype")
    porepress = _array(arrays, "porepress")
    porepress0 = _array(arrays, "porepress0")
    if fstype is None:
        raise ValueError(f"No FSType array found in {path}")
    counts = Counter(fstype)
    free_ids = [i for i, v in enumerate(fstype) if v in FREE_TYPES]
    free_pw = [float(porepress[i]) for i in free_ids] if porepress is not None else []
    z_free = [points[i][2] for i in free_ids]
    hstats = hydrostatic_errors(points, free_ids, porepress0)
    return {
        "file": Path(path).name,
        "np": len(points),
        "n_fs0": counts.get(0, 0),
        "n_fs1": counts.get(1, 0),
        "n_fs2": counts.get(2, 0),
        "n_fs3": counts.get(3, 0),
        "n_fs4": counts.get(4, 0),
        "n_free": len(free_ids),
        "free_pw_zero": sum(1 for v in free_pw if abs(v) < 1e-5),
        "free_pw_max_abs": max([abs(v) for v in free_pw] or [0.0]),
        "free_z_min": min(z_free) if z_free else 0.0,
        "free_z_max": max(z_free) if z_free else 0.0,
        "hydro_rmse": hstats["rmse"] if hstats else 0.0,
        "hydro_mean": hstats["mean"] if hstats else 0.0,
        "hydro_max_abs": hstats["max_abs"] if hstats else 0.0,
    }


def summarize_outdir(outdir):
    outdir = Path(outdir)
    files = sorted((outdir / "particles").glob("PartFluid_*.vtk"))
    if not files:
        raise FileNotFoundError(f"No PartFluid_*.vtk files found under {outdir / 'particles'}")
    rows = [summarize_file(path) for path in files]
    csv_path = Path("support") / f"{outdir.name}_hydrostatic_summary.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    first, last = rows[0], rows[-1]
    print(f"\n{outdir.name}")
    print(f"  wrote {csv_path}")
    print(f"  first: free={first['n_free']} zero_pw={first['free_pw_zero']} hydro_rmse={first['hydro_rmse']:.6g} Pa max={first['hydro_max_abs']:.6g} Pa")
    print(f"  last : free={last['n_free']} zero_pw={last['free_pw_zero']} hydro_rmse={last['hydro_rmse']:.6g} Pa max={last['hydro_max_abs']:.6g} Pa")
    return outdir, files, rows


def compare_outdirs(left, right):
    left_dir, left_files, _ = left
    right_dir, right_files, _ = right
    by_name = {p.name: p for p in right_files}
    rows = []
    for lp in left_files:
        rp = by_name.get(lp.name)
        if not rp:
            continue
        lpts, la = read_vtk(lp)
        rpts, ra = read_vtk(rp)
        lf, rf = _array(la, "fstype"), _array(ra, "fstype")
        lpw, rpw = _array(la, "porepress"), _array(ra, "porepress")
        lpw0, rpw0 = _array(la, "porepress0"), _array(ra, "porepress0")
        n = min(len(lpts), len(rpts))
        row = {
            "file": lp.name,
            "n": n,
            "fstype_diff": sum(1 for i in range(n) if lf[i] != rf[i]) if lf and rf else 0,
            "porepress_max_abs_diff": max([abs(float(lpw[i]) - float(rpw[i])) for i in range(n)] or [0.0]) if lpw and rpw else 0.0,
            "porepress0_max_abs_diff": max([abs(float(lpw0[i]) - float(rpw0[i])) for i in range(n)] or [0.0]) if lpw0 and rpw0 else 0.0,
        }
        rows.append(row)
    if not rows:
        return
    csv_path = Path("support") / f"{left_dir.name}_vs_{right_dir.name}.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\ncomparison: {left_dir.name} vs {right_dir.name}")
    print(f"  wrote {csv_path}")
    print(f"  max FSType diffs: {max(r['fstype_diff'] for r in rows)}")
    print(f"  max porepress diff: {max(r['porepress_max_abs_diff'] for r in rows):.6g} Pa")
    print(f"  max porepress0 diff: {max(r['porepress0_max_abs_diff'] for r in rows):.6g} Pa")


def main(argv):
    if len(argv) < 2:
        print("Usage: analyze_retro_slope_hydrostatic.py OUTDIR [OUTDIR2]")
        return 1
    summaries = [summarize_outdir(arg) for arg in argv[1:]]
    if len(summaries) >= 2:
        compare_outdirs(summaries[0], summaries[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
