"""Frozen-cloud Eq23-form reference only; running this file requires prior review.

No solver, native executable, production module, time integration or plotting.
See the same-stem note for pinned inputs, equations and numerical scope.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from datetime import datetime, timezone

STEM = "upl_lian_eq23_reference_r1"
VARIANTS = ("Ci_Eta0", "Cavg_Eta0", "Cavg_Eta2")
EPS = sys.float_info.epsilon
COMPONENTS = ("xx", "yy", "zz", "xy", "xz", "yz")


def fingerprint(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b))


def apply(c, g):
    return tuple(dot(row, g) for row in c)


def pairs(dim):
    return [(a, a) for a in range(dim)] + [(a, b) for a in range(dim) for b in range(a + 1, dim)]


def component_names(dim):
    axes = "xz" if dim == 2 else "xyz"
    return [axes[a] + axes[b] for a, b in pairs(dim)]


def roundoff_bound(count, scale):
    # Fixed before any data execution: gamma_(64N+256) * max(1, scale).
    # Conservative operation-count model, not a formal native-compiler proof.
    neps = (64 * count + 256) * EPS
    return neps / (1.0 - neps) * max(1.0, scale)


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def wendland_fac_2d(h, rr2):
    # Archived GetKernelWendland_Ctes(true,h) and *_Fac expression order.
    bwen = f32(-2.7852 / (h * h * h))
    rad = f32(math.sqrt(f32(rr2)))
    qq = f32(rad / f32(h))
    w = f32(1.0 - f32(0.5 * qq))
    value = f32(bwen * qq)
    for _ in range(3):
        value = f32(value * w)
    return f32(value / rad)


def inverse2(moment):
    a, b = moment[0]
    c, d = moment[1]
    det = a * d - b * c
    if not math.isfinite(det) or det <= 0:
        raise ValueError("Nonpositive/nonfinite frozen 2D correction determinant")
    return ((d / det, -b / det), (-c / det, a / det)), det


def polynomial(dim, name):
    zero = [0.0] * dim
    hess = [[0.0] * dim for _ in range(dim)]
    linear, constant = zero[:], 0.0
    if name == "constant":
        constant = 7.0
    elif name.startswith("affine_") or name.startswith("linear_"):
        suffix = name.split("_", 1)[1]
        if suffix in ("xyz", "mix"):
            constant, linear = 1.0, ([3.0, -2.0] if dim == 2 else [3.0, -2.0, 0.5])
        else:
            linear[("xz" if dim == 2 else "xyz").index(suffix)] = 1.0
    elif name == "quadratic_mix":
        hess = [[2.0, 0.3], [0.3, 4.0]] if dim == 2 else [[2.0, 0.6, -0.4], [0.6, 4.0, 0.8], [-0.4, 0.8, 6.0]]
    elif name == "quadratic_isotropic":
        for a in range(dim):
            hess[a][a] = 2.0
    else:
        suffix = name.split("_", 1)[1]
        axes = "xz" if dim == 2 else "xyz"
        a = axes.index(suffix[0])
        if len(suffix) == 1:
            hess[a][a] = 2.0
        else:
            b = axes.index(suffix[1])
            hess[a][b] = hess[b][a] = 1.0 if dim == 2 else 2.0
    return constant, tuple(linear), hess


def field_names(dim):
    if dim == 2:
        return ("constant", "linear_x", "linear_z", "linear_mix", "quadratic_x", "quadratic_z", "quadratic_xz", "quadratic_mix", "sine", "hydrostatic_head")
    return ("constant", "affine_x", "affine_y", "affine_z", "affine_xyz", "quadratic_x", "quadratic_y", "quadratic_z", "quadratic_xy", "quadratic_xz", "quadratic_yz", "quadratic_mix", "quadratic_isotropic", "smooth_cos_xyz")


def field(dim, name, x):
    if name == "sine":
        sx, sz = (math.sin(math.pi * q) for q in x)
        cx, cz = (math.cos(math.pi * q) for q in x)
        value, cross = sx * sz, math.pi ** 2 * cx * cz
        return value, (math.pi * cx * sz, math.pi * sx * cz), [[-math.pi ** 2 * value, cross], [cross, -math.pi ** 2 * value]]
    if name == "smooth_cos_xyz":
        k = math.pi / 0.12
        co, si = [math.cos(k * q) for q in x], [math.sin(k * q) for q in x]
        value = math.prod(co)
        grad = tuple(-k * si[a] * math.prod(co[b] for b in range(3) if b != a) for a in range(3))
        hess = [[-k * k * value if a == b else k * k * si[a] * si[b] * co[3 - a - b] for b in range(3)] for a in range(3)]
        return value, grad, hess
    if name == "hydrostatic_head":
        pressure = 10000.0 - 9810.0 * x[1]
        return pressure + 9810.0 * x[1], (0.0, 0.0), [[0.0, 0.0], [0.0, 0.0]]
    constant, linear, hess = polynomial(dim, name)
    hx = apply(hess, x)
    return constant + dot(linear, x) + 0.5 * dot(x, hx), tuple(linear[a] + hx[a] for a in range(dim)), hess


def form_operator(dim, edges, ci, variant, eta2):
    """Edges hold r=xj-xi, d=-r, grad_iW=g, V, and real Cavg."""
    count = len(edges)
    bs = [tuple(e["v"] * q for q in apply(ci, e["g"])) for e in edges]
    moment = [[math.fsum(b[a] * e["r"][c] for b, e in zip(bs, edges)) for c in range(dim)] for a in range(dim)]
    ss, ts, coeff = [], [], []
    for a, c in pairs(dim):
        values = []
        for e in edges:
            cs = ci if variant == "Ci_Eta0" else e["avg"]
            eta = eta2 if variant == "Cavg_Eta2" else 0.0
            radial = dot(e["r"], apply(cs, e["g"])) / (e["rr2"] + eta)
            direction = (dim + 2) * e["r"][a] * e["r"][c] / e["rr2"] - float(a == c)
            values.append(e["v"] * direction * radial)
        t = tuple(math.fsum(s * e["r"][a] for s, e in zip(values, edges)) for a in range(dim))
        ss.append(values)
        ts.append(t)
        coeff.append([s - dot(b, t) for s, b in zip(values, bs)])
    first = [[math.fsum(q * e["r"][a] for q, e in zip(row, edges)) for a in range(dim)] for row in coeff]
    response = [[math.fsum(q * e["r"][a] * e["r"][c] * (0.5 if a == c else 1.0) for q, e in zip(row, edges)) for a, c in pairs(dim)] for row in coeff]
    merror = max(abs(moment[a][c] - float(a == c)) for a in range(dim) for c in range(dim))
    mscale = max(math.fsum(abs(b[a] * e["r"][c]) for b, e in zip(bs, edges)) for a in range(dim) for c in range(dim))
    return {"b": bs, "s": ss, "t": ts, "coeff": coeff, "M": moment, "first": first, "response": response, "M_error": merror, "M_bound": roundoff_bound(count, mscale)}


def evaluate(dim, edges, ci, variant, eta2, op, fi, fjs):
    df = [fj - fi for fj in fjs]
    grad = tuple(math.fsum(b[a] * delta for b, delta in zip(op["b"], df)) for a in range(dim))
    raw = [math.fsum(s * delta for s, delta in zip(row, df)) for row in op["s"]]
    defect = [dot(grad, t) for t in op["t"]]
    corrected = [a - b for a, b in zip(raw, defect)]
    action = [math.fsum(q * delta for q, delta in zip(row, df)) for row in op["coeff"]]
    # Independent scalar construction follows the old w/d/lx convention.
    weights = []
    for e in edges:
        cs = ci if variant == "Ci_Eta0" else e["avg"]
        eta = eta2 if variant == "Cavg_Eta2" else 0.0
        weights.append(2.0 * e["v"] * dot(e["d"], apply(cs, e["g"])) / (e["rr2"] + eta))
    lx = tuple(math.fsum(w * e["d"][a] for w, e in zip(weights, edges)) for a in range(dim))
    scalar = -math.fsum(w * delta for w, delta in zip(weights, df)) - dot(grad, lx)
    trace = math.fsum(corrected[:dim])
    field_scale = max([abs(fi)] + [abs(fj) for fj in fjs])
    scale = max([abs(scalar), math.fsum(abs(q) for q in corrected)] + [math.fsum(abs(s * delta) for s, delta in zip(row, df)) for row in op["s"]] + [math.fsum(abs(q) for q in row) * field_scale for row in op["coeff"]])
    bound = roundoff_bound(len(edges), scale)
    return {"raw": raw, "defect": defect, "H": corrected, "grad": grad, "trace": trace, "scalar": scalar, "trace_delta": trace - scalar, "action_delta": max(abs(a - b) for a, b in zip(action, corrected)), "bound": bound}


def make_2d(path, truncated, disorder):
    rows = read_csv(path)
    nodes, by_grid = {}, {}
    for row in rows:
        ident = int(row["id"])
        grid = (ident % 9, ident // 9) if truncated else (int(row["ix"]), int(row["iz"]))
        stored = None if truncated else ((float(row["cxx"]), float(row["cxz"])), (float(row["cxz"]), float(row["czz"])))
        nodes[ident] = {"x": (float(row["x"]), float(row["z"])), "v": float(row["volume"]), "grid": grid, "stored_c": stored}
        by_grid[grid] = ident
    dp, h = (1.0 / 8.0 if truncated else 1.0 / 20.0), 1.8 * (1.0 / 8.0 if truncated else 1.0 / 20.0)
    edge_cache, c_cache = {}, {}

    def edges(ident):
        if ident not in edge_cache:
            node, result = nodes[ident], []
            ix, iz = node["grid"]
            for dz in range(-4, 5):
                for dx in range(-4, 5):
                    other = by_grid.get((ix + dx, iz + dz))
                    if other is None or other == ident:
                        continue
                    d = tuple(node["x"][a] - nodes[other]["x"][a] for a in range(2))
                    rr2 = dot(d, d)
                    if rr2 > 4.0 * h * h:
                        continue
                    fac = wendland_fac_2d(h, rr2)
                    result.append({"j": other, "r": tuple(-q for q in d), "d": d, "g": tuple(fac * q for q in d), "rr2": rr2, "v": nodes[other]["v"], "xj": nodes[other]["x"]})
            edge_cache[ident] = result
        return edge_cache[ident]

    def correction(ident):
        if ident not in c_cache:
            moment = [[math.fsum(e["v"] * e["r"][a] * e["g"][b] for e in edges(ident)) for b in range(2)] for a in range(2)]
            c_cache[ident] = inverse2(moment)
        return c_cache[ident]

    selected = ((4, 4), (0, 4), (0, 0)) if truncated else ((10, 10), (0, 10), (10, 0))
    cloud = "2d_" + ("truncated" if truncated else "full_support") + ("_jitter" if disorder else "_regular")
    receivers = []
    for grid in selected:
        ident = by_grid[grid]
        ci, determinant = correction(ident)
        local = []
        for edge in edges(ident):
            cj, _ = correction(edge["j"])
            local.append(dict(edge, avg=tuple(tuple(0.5 * (ci[a][b] + cj[a][b]) for b in range(2)) for a in range(2))))
        old = nodes[ident]["stored_c"]
        difference = None if old is None else max(abs(ci[a][b] - old[a][b]) for a in range(2) for b in range(2))
        receivers.append({"dim": 2, "cloud": cloud, "id": ident, "x": nodes[ident]["x"], "ci": ci, "edges": local, "eta2": f32((0.1 * h) ** 2), "h": h, "dp": dp, "det": determinant, "stored_C_difference": difference, "old_fields": {}})
    return receivers


def make_3d(paths):
    moments, fields, neighbors = (read_csv(paths[name]) for name in ("moments3d", "fields3d", "neighbors3d"))
    completion = json.loads(paths["completion3d"].read_text(encoding="utf-8-sig"))
    key = lambda row: (row["shape"], row["disorder"], row["receiver_id"])
    by_fields, by_edges = {}, {}
    for row in fields:
        by_fields.setdefault(key(row), {})[(row["method"], row["eta"], row["field"])] = row
    for row in neighbors:
        d = tuple(float(row[q]) for q in ("dx", "dy", "dz"))
        fac = float(row["kernel_fac_float"])
        by_edges.setdefault(key(row), []).append({"r": tuple(-q for q in d), "d": d, "g": tuple(fac * q for q in d), "rr2": float(row["rr2_double"]), "v": completion["uniform_volume_m3"], "avg": tuple(tuple(float(row[f"Cavg{a}{b}"]) for b in range(3)) for a in range(3))})
    receivers = []
    for row in moments:
        if row["eta"] != "0" or row["method"] != "receiverC_star":
            continue
        k = key(row)
        old = by_fields[k]
        position = old[("receiverC_star", "0", "constant")]
        x = tuple(float(position[q]) for q in "xyz")
        local = [dict(e, xj=tuple(x[a] - e["d"][a] for a in range(3))) for e in by_edges[k]]
        receivers.append({"dim": 3, "cloud": "3d_" + k[0] + ("_jitter" if k[1] == "1" else "_regular"), "id": int(k[2]), "x": x, "ci": tuple(tuple(float(row[f"Ci{a}{b}"]) for b in range(3)) for a in range(3)), "edges": local, "eta2": completion["current_Eta2_float"], "h": completion["h_m"], "dp": completion["dp_m"], "det": float(row["receiver_moment_determinant"]), "stored_C_difference": None, "old_fields": old})
    return receivers


def finite_row(row):
    if any(isinstance(value, float) and not math.isfinite(value) for value in row.values()):
        raise ValueError("Nonfinite diagnostic row")


def main():
    script = Path(__file__).resolve()
    tests = script.parent.parent
    repo = tests.parents[3]
    note_path = tests / "notes" / (STEM + ".json")
    note = json.loads(note_path.read_text(encoding="utf-8-sig"))
    if fingerprint(script) != note["evaluator"]:
        raise ValueError("Evaluator differs from reviewed note binding")
    paths = {item["name"]: repo / item["path"] for item in note["inputs"]}
    closure = dict(paths, evaluator=script, note=note_path)
    before = {name: fingerprint(path) for name, path in closure.items()}
    for item in note["inputs"]:
        if before[item["name"]] != {key: item[key] for key in ("bytes", "sha256")}:
            raise ValueError("Pinned input differs: " + item["name"])
    out = tests / "outputs" / STEM
    out.mkdir(exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    result = {"stage": STEM, "status": "failed", "started_utc": started, "diagnostic_only": True, "physical_acceptance": False, "production_call_regression": False, "physical_steps_advanced": 0, "native_or_solver_calls": 0, "public_3D_admitted": False, "P2_accuracy_gate": False, "paper_cubic_replication": False, "paper_3D_literal_replication": False}
    error = None
    try:
        receivers = make_3d(paths)
        for name, truncated, disorder in (("full2d_regular", False, False), ("full2d_jitter", False, True), ("truncated2d_regular", True, False), ("truncated2d_jitter", True, True)):
            receivers.extend(make_2d(paths[name], truncated, disorder))
        field_rows, moment_rows, checks, failures = 0, 0, 0, 0
        fields_header = ["dimension", "cloud", "receiver_id", "variant", "equation_scope", "field", "x", "y", "z", "grad_error", "trace", "independent_scalar", "trace_minus_scalar", "old_scalar_Lstar", "trace_minus_old_scalar", "coefficient_action_error", "roundoff_model_bound", "trace_check", "coefficient_action_check", "null_or_affine_check"] + [prefix + name for prefix in ("raw_", "defect_", "H_", "exact_", "error_") for name in COMPONENTS]
        moments_header = ["dimension", "cloud", "receiver_id", "variant", "equation_scope", "neighbors", "dp", "h", "eta2", "determinant", "recomputed_minus_stored_C_max", "M_minus_I_max", "M_roundoff_model_bound", "M_check", "H_first_moment_max", "basis_order", "M_json", "first_moment_json", "basis_response_json", "basis_minus_I_Frobenius"]
        with (out / "tensor_fields.csv").open("x", newline="", encoding="utf-8") as fs, (out / "tensor_moments.csv").open("x", newline="", encoding="utf-8") as ms:
            fw, mw = csv.DictWriter(fs, fields_header), csv.DictWriter(ms, moments_header)
            fw.writeheader()
            mw.writeheader()
            for receiver in receivers:
                dim, edges, ci = receiver["dim"], receiver["edges"], receiver["ci"]
                for variant in VARIANTS:
                    scope = ("2D_literal_D4_form_Wendland" if variant == "Ci_Eta0" else "2D_D4_modified_comparison_Wendland") if dim == 2 else "3D_conditional_D5_form_Wendland"
                    op = form_operator(dim, edges, ci, variant, receiver["eta2"])
                    base = {"dimension": dim, "cloud": receiver["cloud"], "receiver_id": receiver["id"], "variant": variant, "equation_scope": scope}
                    mcheck = op["M_error"] <= op["M_bound"]
                    checks += 1
                    failures += int(not mcheck)
                    response = op["response"]
                    mrow = dict(base, neighbors=len(edges), dp=receiver["dp"], h=receiver["h"], eta2=receiver["eta2"] if variant == "Cavg_Eta2" else 0.0, determinant=receiver["det"], recomputed_minus_stored_C_max=receiver["stored_C_difference"], M_minus_I_max=op["M_error"], M_roundoff_model_bound=op["M_bound"], M_check=mcheck, H_first_moment_max=max(abs(q) for row in op["first"] for q in row), basis_order=";".join(component_names(dim)), M_json=json.dumps(op["M"], allow_nan=False), first_moment_json=json.dumps(op["first"], allow_nan=False), basis_response_json=json.dumps(response, allow_nan=False), basis_minus_I_Frobenius=math.sqrt(math.fsum((response[a][b] - float(a == b)) ** 2 for a in range(len(response)) for b in range(len(response)))))
                    finite_row(mrow)
                    mw.writerow(mrow)
                    moment_rows += 1
                    for name in field_names(dim):
                        fi, exact_grad, exact_h = field(dim, name, receiver["x"])
                        fjs = [field(dim, name, e["xj"])[0] for e in edges]
                        value = evaluate(dim, edges, ci, variant, receiver["eta2"], op, fi, fjs)
                        tcheck = abs(value["trace_delta"]) <= value["bound"]
                        acheck = value["action_delta"] <= value["bound"]
                        null = name == "constant" or name.startswith(("linear_", "affine_"))
                        ncheck = max(abs(q) for q in value["H"]) <= value["bound"] if null else ""
                        checks += 2 + int(null)
                        failures += int(not tcheck) + int(not acheck) + int(null and not ncheck)
                        old_method, old_eta = (("receiverC_star", "0") if variant == "Ci_Eta0" else ("symC_star", "1" if variant == "Cavg_Eta2" else "0"))
                        old = receiver["old_fields"].get((old_method, old_eta, name))
                        old_scalar = float(old["Lstar"]) if old else None
                        x = receiver["x"]
                        row = dict(base, field=name, x=x[0], y=x[1] if dim == 3 else None, z=x[-1], grad_error=math.sqrt(math.fsum((q - e) ** 2 for q, e in zip(value["grad"], exact_grad))), trace=value["trace"], independent_scalar=value["scalar"], trace_minus_scalar=value["trace_delta"], old_scalar_Lstar=old_scalar, trace_minus_old_scalar=value["trace"] - old_scalar if old else None, coefficient_action_error=value["action_delta"], roundoff_model_bound=value["bound"], trace_check=tcheck, coefficient_action_check=acheck, null_or_affine_check=ncheck)
                        for index, (a, b) in enumerate(pairs(dim)):
                            component = component_names(dim)[index]
                            for prefix, vector in (("raw_", value["raw"]), ("defect_", value["defect"]), ("H_", value["H"])):
                                row[prefix + component] = vector[index]
                            row["exact_" + component] = exact_h[a][b]
                            row["error_" + component] = value["H"][index] - exact_h[a][b]
                        finite_row(row)
                        fw.writerow(row)
                        field_rows += 1
        if len(receivers) != 24 or moment_rows != 72 or field_rows != 864:
            raise ValueError("Frozen bounded coverage differs from the declared 24/72/864")
        result.update(status="completed_arithmetic_review_required", receiver_instances=len(receivers), tensor_moment_rows=moment_rows, tensor_field_rows=field_rows, arithmetic_checks=checks, arithmetic_failures=failures, arithmetic_checks_passed=failures == 0)
    except Exception as exc:
        error = exc
        result["error"] = type(exc).__name__ + ": " + str(exc)
    after = {name: fingerprint(path) for name, path in closure.items()}
    result.update(finished_utc=datetime.now(timezone.utc).isoformat(), input_closure_before=before, input_closure_after=after, input_closure_unchanged=before == after, outputs={path.name: fingerprint(path) for path in out.glob("*.csv")}, note_roundoff_model=note["roundoff_model"])
    if before != after:
        result["status"] = "failed_input_closure_changed"
        error = ValueError("Input/code/note closure changed")
    (out / "completion.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if error:
        raise error
    if not result["arithmetic_checks_passed"]:
        raise ArithmeticError("Predeclared arithmetic checks failed; retained outputs require review")
    print(str(out / "completion.json"))


if __name__ == "__main__":
    main()
