"""Strict, particle-ID-aligned comparison of binary legacy VTK snapshots.

Parser provenance: examples/Hydromechanic coupling/05_LianFlexibleStrip2D_PR/
tests/scripts/compare_lian_timestep.py (parse_vtk). This version retains stored
integer/float precision and validates record lengths instead of casting to float.
Requires Python >= 3.9 and NumPy. No simulation or conversion is performed.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np


NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
DTYPES = {
    "float": ">f4", "double": ">f8", "int": ">i4", "integer": ">i4",
    "unsigned_int": ">u4", "uint": ">u4", "short": ">i2",
    "unsigned_short": ">u2", "char": "i1", "uchar": "u1",
    "unsigned_char": "u1",
}


def parse_vtk_bytes(buf, label="<memory>"):
    """Read PartVTK binary POLYDATA, including FIELD/SCALARS/VECTORS."""
    offset = 0

    def line():
        nonlocal offset
        end = buf.find(b"\n", offset)
        if end < 0:
            raise ValueError(f"{label}: incomplete VTK header at byte {offset}")
        result = buf[offset:end].decode("ascii").strip()
        offset = end + 1
        return result

    def skip_separator():
        nonlocal offset
        while offset < len(buf) and buf[offset] in b"\r\n \t":
            offset += 1

    def values(type_name, count):
        nonlocal offset
        if type_name.lower() not in DTYPES:
            raise ValueError(f"{label}: unsupported VTK type {type_name}")
        dtype = np.dtype(DTYPES[type_name.lower()])
        end = offset + count * dtype.itemsize
        if count < 0 or end > len(buf):
            raise ValueError(f"{label}: truncated VTK data at byte {offset}")
        result = np.frombuffer(buf, dtype=dtype, count=count, offset=offset).copy()
        offset = end
        return result

    if not line().lower().startswith("# vtk datafile version"):
        raise ValueError(f"{label}: not a legacy VTK file")
    title = line()
    if line().upper() != "BINARY" or line().upper() != "DATASET POLYDATA":
        raise ValueError(f"{label}: only binary legacy POLYDATA is supported")
    header = line().split()
    if len(header) != 3 or header[0] != "POINTS":
        raise ValueError(f"{label}: expected POINTS")
    count = int(header[1])
    points = values(header[2], count * 3).reshape(count, 3)
    skip_separator()
    header = line().split()
    if len(header) != 3 or header[0] != "VERTICES":
        raise ValueError(f"{label}: expected VERTICES")
    values("int", int(header[2]))
    skip_separator()
    header = line().split()
    if len(header) != 2 or header[0] != "POINT_DATA" or int(header[1]) != count:
        raise ValueError(f"{label}: POINT_DATA count does not match POINTS")
    arrays = {"Pos": points}

    def add(name, data):
        if name in arrays:
            raise ValueError(f"{label}: duplicate field {name}")
        if data.shape[0] != count:
            raise ValueError(f"{label}: {name} tuple count does not match POINTS")
        arrays[name] = data

    while offset < len(buf):
        skip_separator()
        if offset == len(buf):
            break
        header = line().split()
        if not header:
            continue
        kind = header[0]
        if kind == "FIELD":
            for _ in range(int(header[2])):
                skip_separator()
                name, components, tuples, type_name = line().split()
                components, tuples = int(components), int(tuples)
                data = values(type_name, components * tuples).reshape(tuples, components)
                add(name, data[:, 0] if components == 1 else data)
        elif kind == "SCALARS":
            name, type_name = header[1:3]
            components = int(header[3]) if len(header) > 3 else 1
            if not line().startswith("LOOKUP_TABLE"):
                raise ValueError(f"{label}: missing SCALARS lookup table")
            data = values(type_name, count * components).reshape(count, components)
            add(name, data[:, 0] if components == 1 else data)
        elif kind == "VECTORS":
            add(header[1], values(header[2], count * 3).reshape(count, 3))
        else:
            raise ValueError(f"{label}: unsupported VTK record {' '.join(header)}")
    return arrays, title


def parse_vtk(path):
    return parse_vtk_bytes(path.read_bytes(), str(path))


def snapshot_files(directory, pattern):
    indexed = {}
    for path in sorted(directory.glob(pattern)):
        if not path.is_file():
            continue
        match = re.search(r"(?:^|_)(\d+)\.vtk$", path.name, re.IGNORECASE)
        if not match:
            raise ValueError(f"Cannot extract exact PART index: {path}")
        index = int(match.group(1))
        if index in indexed:
            raise ValueError(f"Duplicate PART index {index}: {indexed[index]} and {path}")
        indexed[index] = path
    if not indexed:
        raise ValueError(f"No VTK files matching {pattern!r} in {directory}")
    return indexed


def decimal_resolution(token):
    mantissa, _, exponent = token.lower().partition("e")
    decimals = len(mantissa.partition(".")[2])
    return 10.0 ** (int(exponent or 0) - decimals)


def read_run_log(path):
    """Read physical output times/step counts, never elapsed wall-clock timing."""
    records = {}
    if path is None:
        return records
    pattern = re.compile(r"^\s*Part_?(\d+)\s+(" + NUMBER + r")\s+(\d+)(?:\s|$)")
    for text in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = pattern.match(text)
        if not match:
            continue
        index = int(match[1])
        record = {"time": float(match[2]), "logged_step": int(match[3]),
                  "time_resolution": decimal_resolution(match[2]), "source": str(path)}
        if index in records and records[index] != record:
            raise ValueError(f"Conflicting PART {index} metadata in {path}")
        records[index] = record
    return records


def find_log(directory, explicit):
    if explicit is not None:
        if not explicit.is_file():
            raise ValueError(f"Run log not found: {explicit}")
        return explicit.resolve()
    for parent in (directory, directory.parent):
        path = parent / "Run.out"
        if path.is_file():
            return path.resolve()
    return None


def time_record(index, title, records, initial_time):
    if index in records:
        return records[index]
    match = re.search(r"(?:\bTime(?:Step)?\b|\bt)\s*[:=]\s*(" + NUMBER + r")", title, re.I)
    if match:
        return {"time": float(match[1]), "source": "VTK title",
                "time_resolution": decimal_resolution(match[1])}
    if index == 0 and initial_time is not None:
        return {"time": initial_time, "source": "explicit --initial-time", "time_resolution": 0.0}
    return None


def compare_arrays(left, right, rtol=0.0, atol=0.0, require_bitwise=False):
    """Return structural errors and every common field's ID-aligned metrics."""
    errors, metrics = [], {}
    left_fields, right_fields = set(left), set(right)
    if left_fields != right_fields:
        errors.append({"missing_right_fields": sorted(left_fields - right_fields),
                       "missing_left_fields": sorted(right_fields - left_fields)})
    if "Idp" not in left or "Idp" not in right:
        return errors + ["Both snapshots must contain Idp"], metrics
    orders = []
    for name, arrays in (("left", left), ("right", right)):
        ids = arrays["Idp"]
        if ids.ndim != 1 or not np.issubdtype(ids.dtype, np.integer):
            return errors + [f"{name}: Idp must be a one-dimensional integer field"], metrics
        unique, counts = np.unique(ids, return_counts=True)
        duplicate = unique[counts > 1]
        if duplicate.size:
            return errors + [{"side": name, "duplicate_id_count": int(duplicate.size),
                              "duplicate_id_sample": duplicate[:20].tolist()}], metrics
        orders.append(np.argsort(ids, kind="stable"))
    il, ir = orders
    left_ids, right_ids = left["Idp"][il], right["Idp"][ir]
    if not np.array_equal(left_ids, right_ids):
        missing_right = np.setdiff1d(left_ids, right_ids, assume_unique=True)
        missing_left = np.setdiff1d(right_ids, left_ids, assume_unique=True)
        return errors + [{"missing_right_id_count": int(missing_right.size),
                          "missing_left_id_count": int(missing_left.size),
                          "missing_right_id_sample": missing_right[:20].tolist(),
                          "missing_left_id_sample": missing_left[:20].tolist()}], metrics
    for field in sorted(left_fields & right_fields):
        a, b = left[field], right[field]
        result = {"left_dtype": a.dtype.str, "right_dtype": b.dtype.str,
                  "left_shape": list(a.shape), "right_shape": list(b.shape)}
        metrics[field] = result
        if a.shape != b.shape or not a.shape or a.shape[0] != left_ids.size:
            result.update(passed=False, error="field shape / particle count mismatch")
            continue
        a, b = a[il], b[ir]
        finite_a, finite_b = np.isfinite(a), np.isfinite(b)
        result.update(left_nonfinite=int(np.count_nonzero(~finite_a)),
                      right_nonfinite=int(np.count_nonzero(~finite_b)))
        if not finite_a.all() or not finite_b.all():
            result.update(passed=False, error="nonfinite values; comparison is invalid")
            continue
        same_dtype = a.dtype == b.dtype
        unequal = int(np.count_nonzero(a != b))
        bitwise = bool(same_dtype and a.tobytes() == b.tobytes())
        # float64 represents all supported float32 and uint32 values exactly.
        ref, test = a.astype(np.float64), b.astype(np.float64)
        diff = test - ref
        maxabs = float(np.max(np.abs(diff))) if diff.size else 0.0
        refnorm, diffnorm = float(np.linalg.norm(ref.ravel())), float(np.linalg.norm(diff.ravel()))
        relative_l2 = diffnorm / refnorm if refnorm else (0.0 if not diffnorm else None)
        integral = np.issubdtype(a.dtype, np.integer) or np.issubdtype(b.dtype, np.integer)
        tolerance_ok = (unequal == 0) if integral else bool(np.all(np.abs(diff) <= atol + rtol * np.abs(ref)))
        result.update(same_dtype=same_dtype, scalar_count=int(a.size),
                      unequal_scalar_count=unequal, exact_equal=(unequal == 0),
                      bitwise_equal=bitwise, max_abs=maxabs, absolute_l2=diffnorm,
                      relative_l2=relative_l2, reference_l2=refnorm,
                      within_tolerance=tolerance_ok,
                      stored_epsilon=None if integral else float(np.finfo(a.dtype).eps),
                      passed=bool(same_dtype and tolerance_ok and (bitwise or not require_bitwise)))
    return errors, metrics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="Reference directory containing indexed VTK snapshots")
    parser.add_argument("right", type=Path, help="Candidate directory containing indexed VTK snapshots")
    parser.add_argument("--pattern", default="*.vtk", help="Same glob on both sides (default: *.vtk)")
    parser.add_argument("--left-log", type=Path)
    parser.add_argument("--right-log", type=Path)
    parser.add_argument("--initial-time", type=float, help="Explicit shared time for PART 0 if absent in metadata")
    parser.add_argument("--time-atol", type=float, default=0.0)
    parser.add_argument("--rtol", type=float, default=0.0)
    parser.add_argument("--atol", type=float, default=0.0)
    parser.add_argument("--require-bitwise", action="store_true")
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args(argv)
    if any(not np.isfinite(x) or x < 0 for x in (args.rtol, args.atol, args.time_atol)):
        parser.error("tolerances must be finite and nonnegative")
    if args.initial_time is not None and not np.isfinite(args.initial_time):
        parser.error("initial time must be finite")
    report = {"left": str(args.left.resolve()), "right": str(args.right.resolve()),
              "rtol": args.rtol, "atol": args.atol, "time_atol": args.time_atol,
              "require_bitwise": args.require_bitwise,
              "note": "All fields are compared; integer fields always require exact equality. "
                      "Run.out times have only their printed precision; elapsed timings are ignored.",
              "errors": [], "missing_time_parts": [], "parts": []}
    try:
        left_files = snapshot_files(args.left, args.pattern)
        right_files = snapshot_files(args.right, args.pattern)
        missing_right = sorted(set(left_files) - set(right_files))
        missing_left = sorted(set(right_files) - set(left_files))
        if missing_right or missing_left:
            report["errors"].append({"missing_right_parts": missing_right, "missing_left_parts": missing_left})
        left_log, right_log = find_log(args.left, args.left_log), find_log(args.right, args.right_log)
        report["left_log"], report["right_log"] = str(left_log) if left_log else None, str(right_log) if right_log else None
        left_times, right_times = read_run_log(left_log), read_run_log(right_log)
        for index in sorted(set(left_files) & set(right_files)):
            part = {"index": index, "left_file": str(left_files[index]), "right_file": str(right_files[index])}
            report["parts"].append(part)
            try:
                left, left_title = parse_vtk(left_files[index])
                right, right_title = parse_vtk(right_files[index])
                errors, fields = compare_arrays(left, right, args.rtol, args.atol, args.require_bitwise)
                part.update(errors=errors, fields=fields)
                lt = time_record(index, left_title, left_times, args.initial_time)
                rt = time_record(index, right_title, right_times, args.initial_time)
                part.update(left_time=lt, right_time=rt)
                if lt is None or rt is None:
                    report["missing_time_parts"].append(index)
                    errors.append("Physical output time could not be validated; supply Run.out or --initial-time")
                else:
                    delta = abs(lt["time"] - rt["time"])
                    part["time_abs_difference"] = delta
                    if not np.isfinite(delta) or delta > args.time_atol:
                        errors.append("Physical output times differ")
                    if "logged_step" in lt and "logged_step" in rt and lt["logged_step"] != rt["logged_step"]:
                        errors.append("Logged integration step counts differ")
                part["passed"] = bool(fields and not errors and all(f["passed"] for f in fields.values()))
            except (ValueError, OSError, IndexError, KeyError) as exc:
                part.update(passed=False, errors=[str(exc)], fields={})
    except (ValueError, OSError) as exc:
        report["errors"].append(str(exc))
    report["passed"] = bool(report["parts"] and not report["errors"] and all(p["passed"] for p in report["parts"]))
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {len(report['parts'])} exact-index snapshot pairs")
    for error in report["errors"]:
        print(f"  ERROR: {error}")
    for part in report["parts"]:
        fields = part.get("fields", {})
        unequal = sum(field.get("unequal_scalar_count", 0) for field in fields.values())
        exact = bool(fields) and all(field.get("exact_equal", False) for field in fields.values())
        bitwise = bool(fields) and all(field.get("bitwise_equal", False) for field in fields.values())
        print(f"  PART {part['index']:04d}: passed={part['passed']} exact={exact} bitwise={bitwise} unequal_scalars={unequal}")
        for error in part.get("errors", []):
            print(f"    ERROR: {error}")
        for name, field in fields.items():
            if field.get("unequal_scalar_count", 0) or not field.get("passed", False):
                print(f"    {name}: {json.dumps(field, allow_nan=False)}")
    if report["missing_time_parts"]:
        return 2
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
