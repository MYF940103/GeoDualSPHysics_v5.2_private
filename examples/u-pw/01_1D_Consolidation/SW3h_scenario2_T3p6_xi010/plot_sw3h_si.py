#!/usr/bin/env python3
"""Generate Supporting-Information-style SVG plots for SW-3h results.
No third-party dependencies are required.
"""
import csv, math, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Case1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_out" / "data"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)
FRAME_CSV = ROOT / "sw3h_frame_metrics.csv"

E = 2e6
NU = 0.3
KPERM = 1e-3
RHOW = 1000.0
G = 9.81
K = E/(3*(1-2*NU))
GMOD = E/(2*(1+NU))
CV = (K + 4*GMOD/3) * KPERM / (RHOW * G)

TARGET_TIMES = [0.0, 0.1, 0.5, 1.0, 2.0, 3.6]
COLORS = ["#111111", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#d62728", "#8c564b"]

def rows_from_csv(path):
    with path.open(newline='', errors='ignore') as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ';' if sample.count(';') >= sample.count(',') else ','
        return list(csv.DictReader(f, delimiter=delim))

def val(row, name, default=0.0):
    if name in row and row[name] != '':
        return float(row[name])
    for k, v in row.items():
        if k.split('[')[0].strip() == name and v != '':
            return float(v)
    return default

def is_fluid(row):
    return str(row.get('Type','')).strip().lower() in ('3','fluid')

def load_profile(frame):
    rows = [r for r in rows_from_csv(DATA / f"PartCsv_{frame:04d}.csv") if is_fluid(r)]
    zvals = [val(r, 'Pos.z') for r in rows]
    zmin, zmax = min(zvals), max(zvals)
    H = zmax - zmin
    bins = defaultdict(list)
    for r in rows:
        z = val(r, 'Pos.z')
        eta = (z - zmin)/H if H > 0 else 0
        b = int(round(eta * 99))
        p = val(r, 'PorePress')
        ex = val(r, 'ExcessPorePress')
        bins[b].append((z, p, ex))
    prof = []
    for b in sorted(bins):
        arr = bins[b]
        prof.append((sum(a[0] for a in arr)/len(arr), sum(a[1] for a in arr)/len(arr), sum(a[2] for a in arr)/len(arr)))
    return prof, zmin, zmax

frames = rows_from_csv(FRAME_CSV)
frame_by_time = {round(float(r['time']), 6): int(r['frame']) for r in frames}
avail_times = [float(r['time']) for r in frames]
def nearest_frame(t):
    tt = min(avail_times, key=lambda x: abs(x-t))
    return int(frame_by_time[round(tt,6)]), tt

initial_profile, z0min, z0max = load_profile(0)
H0 = z0max - z0min

def tv(t):
    return CV * t / (H0*H0)

# Basic SVG plotter.
def svg_line_plot(path, title, xlabel, ylabel, series, xlim=None, ylim=None, width=920, height=640):
    ml, mr, mt, mb = 95, 210, 58, 78
    pw, ph = width-ml-mr, height-mt-mb
    allx = [x for s in series for x,y in s['data']]
    ally = [y for s in series for x,y in s['data']]
    xmin, xmax = xlim if xlim else (min(allx), max(allx))
    ymin, ymax = ylim if ylim else (min(ally), max(ally))
    if ymax == ymin: ymax = ymin + 1
    pad = 0.04*(ymax-ymin)
    ymin -= pad; ymax += pad
    def sx(x): return ml + (x-xmin)/(xmax-xmin)*pw if xmax != xmin else ml
    def sy(y): return mt + (ymax-y)/(ymax-ymin)*ph
    def fmt(v):
        if abs(v) >= 1e4 or (abs(v) < 1e-2 and v != 0): return f"{v:.1e}"
        return f"{v:.3g}"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial" font-size="20">{title}</text>']
    # grid and axes
    for i in range(6):
        x = xmin + (xmax-xmin)*i/5
        px = sx(x)
        parts.append(f'<line x1="{px:.1f}" y1="{mt}" x2="{px:.1f}" y2="{mt+ph}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{px:.1f}" y="{mt+ph+24}" text-anchor="middle" font-family="Arial" font-size="12">{fmt(x)}</text>')
    for i in range(6):
        y = ymin + (ymax-ymin)*i/5
        py = sy(y)
        parts.append(f'<line x1="{ml}" y1="{py:.1f}" x2="{ml+pw}" y2="{py:.1f}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{ml-10}" y="{py+4:.1f}" text-anchor="end" font-family="Arial" font-size="12">{fmt(y)}</text>')
    parts.append(f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="none" stroke="black"/>')
    parts.append(f'<text x="{ml+pw/2}" y="{height-24}" text-anchor="middle" font-family="Arial" font-size="15">{xlabel}</text>')
    parts.append(f'<text x="24" y="{mt+ph/2}" transform="rotate(-90 24 {mt+ph/2})" text-anchor="middle" font-family="Arial" font-size="15">{ylabel}</text>')
    # lines
    for s in series:
        pts = ' '.join(f'{sx(x):.2f},{sy(y):.2f}' for x,y in s['data'])
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" stroke-width="2.2"/>')
    # legend
    lx, ly = ml + pw + 24, mt + 18
    for i, s in enumerate(series):
        y = ly + i*24
        parts.append(f'<line x1="{lx}" y1="{y}" x2="{lx+26}" y2="{y}" stroke="{s["color"]}" stroke-width="3"/>')
        parts.append(f'<text x="{lx+34}" y="{y+5}" font-family="Arial" font-size="13">{s["label"]}</text>')
    parts.append('</svg>')
    path.write_text('\n'.join(parts), encoding='utf-8')

# Profile plots.
p_series, ex_series = [], []
for idx, t in enumerate(TARGET_TIMES):
    frame, actual_t = nearest_frame(t)
    prof, zmin, zmax = load_profile(frame)
    label = f't={actual_t:g}s, Tv={tv(actual_t):.3f}'
    color = COLORS[idx % len(COLORS)]
    p_series.append({'label': label, 'color': color, 'data': [(p, z) for z,p,ex in prof]})
    ex_series.append({'label': label, 'color': color, 'data': [(ex, z) for z,p,ex in prof]})
svg_line_plot(FIGDIR/'sw3h_porepress_profiles.svg', 'SW-3h Scenario 2: Pore pressure profiles', 'PorePress [Pa]', 'z [m]', p_series)
svg_line_plot(FIGDIR/'sw3h_excess_profiles.svg', 'SW-3h Scenario 2: Excess pore pressure profiles', 'ExcessPorePress [Pa]', 'z [m]', ex_series)

# Time plots.
metrics = [{k: float(v) if k not in ('frame','n') else int(v) for k,v in r.items()} for r in rows_from_csv(FRAME_CSV)]
time = [m['time'] for m in metrics]
bottom_series = [
    {'label':'bottom PorePress', 'color':'#1f77b4', 'data':[(m['time'], m['bottom_Excess_mean'] + m['hydrostatic_max']) for m in metrics]},
    {'label':'bottom hydrostatic', 'color':'#111111', 'data':[(m['time'], m['hydrostatic_max']) for m in metrics]},
]
svg_line_plot(FIGDIR/'sw3h_bottom_porepress_time.svg', 'SW-3h Scenario 2: bottom pore pressure relaxation', 'time [s]', 'pressure [Pa]', bottom_series, xlim=(0, max(time)))
ex_time_series = [
    {'label':'Excess max', 'color':'#d62728', 'data':[(m['time'], m['Excess_max']) for m in metrics]},
    {'label':'Excess mean', 'color':'#2ca02c', 'data':[(m['time'], m['Excess_mean']) for m in metrics]},
    {'label':'bottom excess', 'color':'#1f77b4', 'data':[(m['time'], m['bottom_Excess_mean']) for m in metrics]},
]
svg_line_plot(FIGDIR/'sw3h_excess_time.svg', 'SW-3h Scenario 2: excess pore pressure decay', 'time [s]', 'ExcessPorePress [Pa]', ex_time_series, xlim=(0, max(time)))
print(f'Wrote figures to {FIGDIR}')
