"""Apply Eq.47 to retained cold frozen rows. Do not advance the collapse or change source data."""
import csv
from decimal import Decimal, localcontext
import json
from pathlib import Path
import numpy as np

TESTS = Path(__file__).resolve().parents[1]
DT = 5e-6
BETA = .04
OUT = TESTS/'logs/c08_tpi_eq47_state_r1.check.json'
TABLE = TESTS/'figures/c08_tpi_eq47_state_r1.csv'


def raw_pressure(pn, palpha, q, diagonal, residual, beta, drained):
    if drained:
        return np.float32(0)
    capacity = beta/DT if pn < 0 else 0.
    if not (np.isfinite(diagonal) and diagonal > 0 and np.isfinite(residual)):
        raise ValueError('Invalid active row')
    return np.float32(q + (residual+capacity*(palpha-q))/(diagonal+capacity))


def exact(pn, palpha, q, diagonal, residual):
    d=Decimal.from_float
    with localcontext() as ctx:
        ctx.prec=90
        c=d(BETA)/d(DT) if pn<0 else Decimal(0)
        # Independent numerator form of Eq.47.
        return np.float32(float((d(q)*d(diagonal)+d(residual)+c*d(palpha))/(d(diagonal)+c)))


def rms(a):
    return float(np.sqrt(np.mean(np.square(a))))


def measure(rows, part):
    bodies=[r for r in rows if int(r['part'])==part]
    assert sorted(int(r['native_id']) for r in bodies)==list(range(2060,7060))
    def column(k):
        return np.array([float(r[k]) for r in bodies])
    p=column('p_actual_Pa'); p0=column('P0_Pa')
    S=column('S_LP_1_per_m_s'); residual=column('Rgamma_Pa_per_m_s')
    fs=np.isin(column('FS'),[2,3]); drained=column('true_Dirichlet')!=0
    active=(p<0)&~drained
    assert active.any() and not drained.any()
    outputs=[]
    for beta in (0., BETA):
        raw=np.array([raw_pressure(n,n,n,s,r,beta,bool(bc)) for n,s,r,bc in zip(p,S,residual,drained)])
        final=np.where(fs&(raw>0),np.float32(0),raw)
        outputs.append((raw,final))
    (raw0,final0),(raw4,final4)=outputs
    original=column('p_conditional_raw_Pa').astype(np.float32)
    assert raw0.tobytes()==original.tobytes()
    reference=np.array([exact(n,n,n,s,r) for n,s,r in zip(p,S,residual)])
    assert raw4.tobytes()==reference.tobytes()
    assert final4[~active].tobytes()==final0[~active].tobytes()
    assert (final4[fs]<=0).all() and final4[raw4<0].tobytes()==raw4[raw4<0].tobytes()
    inc0=raw0[active].astype(np.float64)-p[active]
    inc4=raw4[active].astype(np.float64)-p[active]
    ratio=S[active]/(S[active]+BETA/DT)
    return dict(part=part,time_s=float(bodies[0]['time_s']),soil=len(p),old_total_negative=int(active.sum()),
                old_excess_negative=int(((p-p0)<0).sum()),
                different_total_excess_sign_masks=int((active!=((p-p0)<0)).sum()),
                beta0_positive_to_negative=int(((p>=0)&(raw0<0)).sum()),
                beta0_negative_to_nonnegative=int((active&(raw0>=0)).sum()),
                S_active_min=float(S[active].min()),S_active_max=float(S[active].max()),
                capacity_over_dt_1_per_m_s=BETA/DT,
                raw_increment_ratio_median=float(np.median(ratio)),raw_increment_ratio_max=float(np.max(ratio)),
                rms_raw_increment_active_beta0_Pa=rms(inc0),rms_raw_increment_active_beta004_Pa=rms(inc4),
                beta004_active_float_increment_rounded_to_zero=int((inc4==0).sum()),
                beta004_active_negative_survivors=int((active&(final4<0)).sum()),
                free_surface_positive_caps_beta0=int((fs&(raw0>0)).sum()),
                free_surface_positive_caps_beta004=int((fs&(raw4>0)).sum()),
                true_dirichlet_rows=int(drained.sum()))


def main():
    if OUT.exists() or TABLE.exists():
        raise FileExistsError('Retain the existing review')
    receipt=json.loads((TESTS/'logs/c08_tpi_state_review_r1.check.json').read_text(encoding='utf-8-sig'))
    assert receipt['passed'] and receipt['soil_rows']==20000
    binding=next(f for f in receipt['consumed'] if Path(f['path']).name=='soil.csv')
    source=Path(binding['path']); st=source.stat()
    assert st.st_size==binding['bytes'] and st.st_mtime_ns==binding['mtime_ns']
    with source.open(newline='',encoding='utf-8-sig') as f:
        rows=[r for r in csv.DictReader(f) if r['leg']=='baseline']
    assert len(rows)==10000
    # Actual C08 rows have no true Dirichlet receivers. Exercise all three old p signs
    # in a separate constrained fixture, deliberately with invalid/unused spatial terms.
    for pn in (-5.,-0.,5.):
        for beta in (0.,BETA):
            assert raw_pressure(pn,99.,-75.,np.nan,np.nan,beta,True)==0.
    stats=[measure(rows,part) for part in (38,76)]
    with TABLE.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
    with OUT.open('x',encoding='utf-8') as f:
        json.dump(dict(passed=True,source=binding,results=stats,drained_synthetic_checks=6,
                       independently_checked_raw_floats=10000,retained_beta0_matched_raw_floats=10000,
                       cold_hypothesis='q = pAlpha = p_n; no previous-step history in these frozen states',
                       physical_steps=0,HG_enabled=False,trajectory_validated=False,
                       coupled_force_feedback_measured=False),f,indent=2,allow_nan=False)
    print(json.dumps(stats,indent=2))


if __name__=='__main__':
    main()

