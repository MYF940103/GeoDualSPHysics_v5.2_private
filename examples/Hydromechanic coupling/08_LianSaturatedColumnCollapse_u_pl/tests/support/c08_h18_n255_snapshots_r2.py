"""Correct two derived CSV shear labels; leave native/old analysis untouched."""
import csv, json, zipfile
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_n255_snapshots_r2'


def stat(p):
    p = Path(p).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def main():
    src = T/'figures/c08_h18_n255_full3_review_r1_snapshots.csv'
    dest = T/'figures'/(TAG+'.csv'); check = T/'logs'/(TAG+'.check.json')
    if dest.exists() or check.exists(): raise RuntimeError('Existing correction/partials protected')
    receipt = T/'logs/c08_h18_n255_full3_review_r1.check.json'
    review = json.loads(receipt.read_text(encoding='utf-8'))
    original = next(q for q in review['files'] if Path(q['path']).resolve() == src.resolve())
    if not review['analysis_complete'] or stat(src) != original: raise RuntimeError('Original CSV binding differs')
    archive = T/'outputs/c08_preload_schema2_source_r1/full_source.zip'
    protected = [stat(p) for p in [src, receipt, archive, Path(__file__), T/'notes'/(TAG+'.md')]]
    with zipfile.ZipFile(archive) as z:
        text = z.read('src/source/JSphGpuSingle.cpp').decode('utf-8-sig')
    proof = 'sigmastateij[p]=TDouble3(s.xy,s.yz,s.xz);'
    if text.count(proof) != 1: raise RuntimeError('Frozen native shear-order proof differs')
    with src.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f); names = reader.fieldnames; rows = list(reader)
    if len(rows) != 30000: raise RuntimeError('Six original5000-ID snapshots required')
    a, b = 'effective_and_total_xz_Pa', 'effective_and_total_yz_Pa'
    result = dict(stage=TAG, passed=False, consumed=protected, original_csv_preserved=True,
                  native_order='xy,yz,xz', frozen_export_proof=proof, physical_fields_or_solver_changed=False)
    try:
        with dest.open('x', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=names); writer.writeheader()
            for original_row in rows:
                fixed = dict(original_row); fixed[a], fixed[b] = original_row[b], original_row[a]
                if any(fixed[k] != original_row[k] for k in names if k not in (a, b)):
                    raise RuntimeError('An unrelated derived field changed')
                writer.writerow(fixed)
        with dest.open(newline='', encoding='utf-8') as f:
            fixed_rows = list(csv.DictReader(f))
        for old, new in zip(rows, fixed_rows):
            if new[a] != old[b] or new[b] != old[a] or any(new[k] != old[k] for k in names if k not in (a, b)):
                raise RuntimeError('Written correction differs')
        if len(fixed_rows) != 30000 or any(stat(q['path']) != q for q in protected):
            raise RuntimeError('Correction coverage/input binding changed')
        result.update(passed=True, rows=30000, only_columns_swapped=[a,b], other_field_strings_unchanged=True,
                      corrected_csv=stat(dest), native_decodes=0, solver_invocations=0, SHA_scans=0)
    except Exception as error:
        result.update(first_failure=str(error), partials_preserved=True); raise
    finally:
        with check.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2); f.write('\n')


if __name__ == '__main__': main()
