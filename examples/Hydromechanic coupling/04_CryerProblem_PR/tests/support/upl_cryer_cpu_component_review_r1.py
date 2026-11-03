"""Pure offline component review; initialization metadata is parsed, never treated as a particle snapshot."""
import argparse, csv, hashlib, json, math, struct
from pathlib import Path

T = Path(__file__).resolve().parents[1]
BOUND = {}
NAMES = ("constant_p_totalstress0", "affine_XYZ_p_totalstress0", "affine_compression",
         "cyclic_tracefree_shear", "raw_confinement_only", "raw_confinement_cancel")
IDS = (8, 100, 1000, 10000, 20000, 30000, 37179, 37180)
FORMATS = {2:"i", 3:"b", 4:"B", 5:"h", 6:"H", 7:"i", 8:"I", 9:"q", 10:"Q",
           11:"f", 12:"d", 20:"iii", 21:"III", 22:"fff", 23:"ddd"}

def need(ok, why):
    if not ok:
        raise ValueError(why)

def entry(path):
    p = Path(path).resolve()
    with p.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest)

def bind(e):
    need(isinstance(e, dict) and set(("path", "bytes", "sha256")) <= e.keys(), "Malformed Entry")
    key = str(Path(e["path"]).resolve()).casefold()
    actual = BOUND.get(key)
    if actual is None:
        actual = entry(e["path"])
        BOUND[key] = actual
    need(actual["bytes"] == e["bytes"] and actual["sha256"].lower() == e["sha256"].lower(),
         "Changed/conflicting Entry: " + str(e["path"]))
    return Path(actual["path"])

def adopt(path):
    key = str(Path(path).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(path)
    return BOUND[key]

def readjson(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def owned(e):
    c = readjson(bind(e))
    need(c["direct_native_call"] is True and c["typed_LASTEXITCODE_captured_immediately"] is True
         and c["owned_call_exited"] is True and type(c["exit_code"]) is int
         and c["exit_code"] == 0 and c.get("invocation_failure") is None, "Actual owned typed native exit0 required")
    bind(c["program"]); bind(c["log"])
    return c

class Cursor:
    def __init__(self, data):
        self.data, self.pos = data, 0
    def take(self, n):
        need(isinstance(n, int) and 0 <= n <= len(self.data) - self.pos, "Truncated metadata")
        out = self.data[self.pos:self.pos+n]; self.pos += n
        return out
    def number(self, fmt):
        a = struct.unpack("<" + fmt, self.take(struct.calcsize("<" + fmt)))
        return a[0] if len(a) == 1 else list(a)
    def text(self):
        s = self.take(self.number("I")).decode("utf-8", errors="strict")
        need("\0" not in s, "Embedded NUL in metadata string")
        return s
    def eof(self):
        need(self.pos == len(self.data), "Trailing metadata bytes/append or invalid declared size")

def item(cur, depth=0):
    need(depth <= 3, "Unexpected metadata tree depth")
    base = Cursor(cur.take(cur.number("I")))
    need(base.text() == "\nITEM\n", "Invalid ITEM marker")
    name = base.text()
    need(not name.upper().startswith("PART_"), "Particle PART_* item is forbidden")
    hide, hidevalues = base.number("i"), base.number("i")
    need(hide in (0, 1) and hidevalues in (0, 1), "Invalid serialized bool")
    fmtfloat, fmtdouble = base.text(), base.text()
    narrays, nitems, sizevalues = base.number("I"), base.number("I"), base.number("I")
    base.eof()
    need(narrays == 0 and nitems <= 2, "Any array/payload or unexpected metadata children forbidden")
    values = {}
    if sizevalues:
        block = Cursor(cur.take(sizevalues))
        need(block.text() == "\nVALUES", "Invalid VALUES marker")
        for _ in range(block.number("I")):
            key, typ = block.text(), block.number("i")
            need(key not in values, "Duplicate metadata scalar")
            if typ == 1:
                value = block.text()
            else:
                need(typ in FORMATS, "Unknown metadata scalar type")
                value = block.number(FORMATS[typ])
                if typ == 2:
                    need(value in (0, 1), "Invalid scalar bool")
                for x in value if isinstance(value, list) else (value,):
                    need(math.isfinite(x), "Nonfinite metadata scalar")
            values[key] = value
        block.eof()
    children = [item(cur, depth + 1) for _ in range(nitems)]
    return dict(name=name, arrays=narrays, items=nitems, values_bytes=sizevalues,
                values=values, children=children, hide=hide, hidevalues=hidevalues,
                format_float=fmtfloat, format_double=fmtdouble)

def metadata(path, kind):
    raw = Path(path).read_bytes()
    need(len(raw) >= 64 and raw[60:64] == b"\0\0\0\0", "Only native little-endian64B StHead accepted")
    need(raw[58:60] == b"\n\0" and raw[:58].rstrip(b" ") == ("#FileJBD " + kind).encode("ascii"),
         "Exact JBinaryData metadata title required")
    cur = Cursor(raw[64:]); root = item(cur); cur.eof()
    need(root["name"] == kind, "Wrong metadata root")
    v = root["values"]
    need(all(v.get(k) == val for k, val in dict(CaseNp=37181, CaseNfixed=8,
         CaseNmoving=0, CaseNfloat=0, CaseNfluid=37173).items()), "Metadata native counts differ")
    need(v.get("Data2d") == 0 and v.get("Npiece") == 1, "Metadata dimensionality/piece differs")
    if kind == "JPartDataHead":
        need(root["items"] == 1 and root["children"][0]["name"] == "MkBlocks", "Only MK header subtree allowed")
        mk = root["children"][0]
        need(mk["items"] == 2 and mk["values"] == {"Count":2}, "Exactly2 declared material blocks required")
        blocks = mk["children"]
        need([x["name"] for x in blocks] == ["MkBlock_000", "MkBlock_001"]
             and [x["values"].get("Count") for x in blocks] == [8,37173]
             and all(x["items"] == 0 and set(x["values"]) == {"Type","Mk","MkType","Count"} for x in blocks),
             "Unexpected MK block metadata")
        need(v.get("PeriMode") == 0 and v.get("Gravity") == [0,0,0], "Header periodic/gravity scope differs")
        nodes = [root,mk] + blocks
    else:
        need(kind == "JPartOutBi4" and root["items"] == 0 and v.get("Piece") == 0
             and v.get("Block") == 0 and "Nout" not in v, "PartOut must be initial root only, no excluded PART append")
        nodes = [root]
    return dict(path=str(path), bytes=len(raw), root=kind, strict_EOF=True, arrays=0,
                particle_payload_bytes=0, excluded_particle_payload_count=0,
                tree=[dict(name=x["name"],items=x["items"],arrays=x["arrays"],values_bytes=x["values_bytes"]) for x in nodes])

def csv_check(out):
    tables = []
    for name, count in (("summary.csv",6),("samples.csv",48)):
        p = out / name
        need(len(p.read_text(encoding="utf-8-sig").splitlines()) == count+1, "CSV physical row count differs")
        with p.open(encoding="utf-8-sig",newline="") as f:
            rows = list(csv.DictReader(f))
        need(len(rows) == count, "CSV row coverage differs")
        for row in rows:
            for k,v in row.items():
                if k != "name":
                    need(v is not None and math.isfinite(float(v)), "Nonfinite/missing CSV numeric field")
        tables.append(rows)
    summary, samples = tables
    need({int(r["probe"]) for r in summary} == set(range(6)), "Summary probe set differs")
    maximum = 0.
    for r in summary:
        p = int(r["probe"])
        need(float(r["probe"]) == p and r["name"] == NAMES[p] and int(r["soil_count"]) == 37173
             and sum(int(r["FS"+str(k)]) for k in range(4)) == 37173, "Summary identity/count differs")
        for k in ("C_moment_max_ratio","theta_max_ratio","rate_max_ratio","stress6_max_ratio",
                  "raw_cancel_max_ratio","load_reference_max_ratio"):
            v = float(r[k]); need(0 <= v <= 1, "Original summary ratio exceeded"); maximum=max(maximum,v)
    need({(int(r["probe"]),int(r["id"])) for r in samples} == {(p,i) for p in range(6) for i in IDS},
         "Unique6x8 sample coverage differs")
    for r in samples:
        p,i = int(r["probe"]),int(r["id"])
        need(float(r["probe"]) == p and float(r["id"]) == i and r["name"] == NAMES[p], "Sample identity differs")
        channels = [("theta_s_inv","theta_ref","theta_budget"),("pdot_Pa_s","pdot_ref","pdot_budget")]
        channels += [("R"+s+"_Pa_s","R"+s+"_ref","R"+s+"_budget") for s in ("xx","xy","xz","yy","yz","zz")]
        for a,b,k in channels:
            budget=float(r[k]); need(budget>0,"Missing positive original sample budget")
            ratio=abs(float(r[a])-float(r[b]))/budget
            need(ratio<=1,"Original conditional sample budget exceeded"); maximum=max(maximum,ratio)
        for k in ("C_ratio","raw_force_ratio","load_ref_ratio"):
            ratio=float(r[k]); need(0<=ratio<=1,"Original sample ratio exceeded"); maximum=max(maximum,ratio)
    return maximum

def review(configuration):
    debug = configuration == "DebugCPU"
    tag = "upl_cryer_cpu_component_" + configuration + "_probe_" + ("r1" if debug else "r2")
    source = adopt(T / "logs" / (tag + ".run.json"))
    r = readjson(bind(source))
    if debug:
        need(r["stage"]=="upl_cryer_cpu_component_run_r1" and r["configuration"]=="DebugCPU"
             and r["passed"] is False and r["owned_component_exit0"] is True
             and r["failure_phase"]=="post_call_analysis_failed"
             and r["analysis_failure"]=="Unexpected PART output from non-advancing component"
             and r["component_call_failure"] is None and r["post_binding_failure"] is None
             and r["frozen_build_program_inputs_runtime_unchanged"] is True, "Only the known metadata-classifier postfailure may be adopted")
        call_e, helper_e = r["call"], r["helper"]
        for e in r["inputs"]+r["files"]:
            bind(e)
    else:
        need(r["configuration"]=="ReleaseCPU" and r["stage"]=="upl_cryer_cpu_component_run_r2"
             and r["passed"] is True and r["owned_component_exit0"] is True
             and r["basic_completion_verified"] is True and r["deep_component_review_completed"] is False
             and r["frozen_build_program_inputs_runtime_unchanged"] is True
             and r["component_call_failure"] is None and r["post_binding_failure"] is None,
             "Only sealed successful Release r2 basic call, not a prior deep-QC claim, accepted")
        call_e, helper_e = r["call"], r["helper"]
        for e in r["inputs"]+r["files"]:
            bind(e)
        prior = readjson(bind(r["debug_review"]))
        need(prior["passed"] is True and prior["configuration"]=="DebugCPU"
             and prior["owned_component_exit0"] is True and prior["initialization_metadata_only"] is True,
             "Adopted actual Debug proof required")
    call=owned(call_e); h=readjson(bind(helper_e))
    need(h["passed"] is True and h["stage"]=="upl_cryer_cpu_component_build_r2"
         and h["status"]=="frozen_cryer_CPU_component_linked_not_run" and h["configuration"]==configuration
         and h["kind"]=="component" and h["actual_headers_archived_not_live"] is True
         and h["frozen_build_program_inputs_runtime_unchanged"] is True
         and h["CPU_non_main_objects"]==85 and h["link_object_count"]==86
         and len(h["source_snapshots265"])==265 and len(h["objects"])==85
         and len(h["libraries"])==17 and len(h["runtime"])==4, "Selected sealed r2 helper closure differs")
    for key in ("inputs","author_files","source_snapshots265","actual_project_headers","objects",
                "retained_build_objects86","libraries","tools"):
        for e in h[key]:
            bind(e)
    for key in ("program","source_build","compiler_dependency_record","helper_object",
                "documentation_snapshot","case_readme_snapshot"):
        bind(h[key])
    owned(h["compile_call"]); owned(h["link_call"])
    for pair in h["runtime"]:
        need(pair["original"]["bytes"]==pair["copy"]["bytes"]
             and pair["original"]["sha256"]==pair["copy"]["sha256"],"Recorded runtime identity differs")
        bind(pair["copy"])
    need(call["program"]==h["program"] and call["component_call"] is True
         and call["actual_solver_call"] is False and call["requested_OpenMP_threads"]==1, "Component call attribution differs")
    note_e = next(e for e in h["author_files"] if Path(e["path"]).name=="upl_cryer_cpu_component_r2.json")
    declaration=readjson(bind(note_e))["retained_input_provenance"]
    xml,seed = T.parent / declaration["runtime"], T.parent / declaration["seed"]
    for p,k in ((xml,"runtime"),(seed,"seed")):
        bind(dict(path=str(p),bytes=declaration[k+"_bytes"],sha256=declaration[k+"_sha256"]))
    out=T / "outputs" / tag
    need(call["arguments"]==["--input",str(xml),"--out",str(out)]
         and Path(call["working_directory"]).resolve()==Path(h["program"]["path"]).resolve().parent,
         "Exact retained input/fresh-output argv differs")
    files=[adopt(p) for p in sorted(out.rglob("*")) if p.is_file()]
    need({str(Path(e["path"]).resolve()).casefold() for e in r["files"]}
         == {str(Path(e["path"]).resolve()).casefold() for e in files}, "Sealed output membership changed")
    related=[Path(e["path"]) for e in files if Path(e["path"]).suffix.lower() in (".bi4",".ibi4",".obi4")
             or Path(e["path"]).name.startswith(("Part_","PartOut","PartHead"))]
    need({p.relative_to(out).as_posix() for p in related}=={"data/Part_Head.ibi4","data/PartOut_000.obi4"},
         "Unexpected snapshot/PART/append file")
    parsed=[metadata(out/"data/Part_Head.ibi4","JPartDataHead"),
            metadata(out/"data/PartOut_000.obi4","JPartOutBi4")]
    done_e=adopt(out/"completion.json"); done=readjson(bind(done_e))
    expected=dict(stage="upl_cryer_cpu_component_r2",passed=True,native_count=37173,fixed_dummy_count=8,
        total_native_count=37181,actual_force_calls=6,complete_rate_calls_from_force=6,
        explicit_complete_rate_calls=0,soil_reference_checks=223038,sample_rows=48,summary_rows=6,
        actual_physical_steps=0,actual_time_s=0,feedback_Init_guard_bypassed_by_fixture=True,
        observer_only_initialization_validated=True,feedback_initialization_validated=False,
        public_3D_admitted=False,physical_acceptance=False,whole_object_restored=False,
        declared_input_bytes_restored=True,no_Run_ComputeStep_SaveData_restart=True,
        raw_LoadAce_telemetry_gate_explicitly_accounted=True)
    need(all(done.get(k)==v for k,v in expected.items()),"Original component completion gates differ")
    need((out/"Run.out").is_file(),"Actual initialization log missing")
    maximum=csv_check(out)
    producer_names={"JSph.cpp","JPartDataHead.cpp","JPartOutBi4Save.cpp","JBinaryData.cpp","JBinaryData.h"}
    producers=[e for e in h["source_snapshots265"] if Path(e["path"]).name in producer_names]
    need(len(producers)==5,"Archived metadata producer source closure missing")
    return dict(configuration=configuration,source_run=source,source_call=call_e,
        helper=helper_e,source_build=h["source_build"],program=h["program"],completion=done_e,files=files,
        original_owner_passed=False if debug else None,original_owner_modified=False,
        known_owner_metadata_classification_false_positive=debug,owned_component_exit0=True,
        component_completion_verified=True,summary_rows=6,sample_rows=48,max_checked_ratio=maximum,
        initialization_metadata_only=True,metadata=parsed,metadata_producer_sources=producers,
        no_particle_snapshots_or_exclusions=True,particle_payload_bytes=0,excluded_particle_payload_count=0,
        caller_reconstructed_neighbor_or_device_proof=False,whole_object_restored=False,
        feedback_initialization_validated=False,public_3D_admitted=False,physical_acceptance=False,
        Debug_Release_0ULP_compared=False,solver_trajectory_started=False,programs_executed_by_reviewer=0)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--configuration",choices=("DebugCPU","ReleaseCPU"),default="DebugCPU")
    cfg=ap.parse_args().configuration
    tag="upl_cryer_cpu_component_"+cfg+"_probe_"+("r1" if cfg=="DebugCPU" else "r2")+"_review_r1"
    target=T/"logs"/(tag+".check.json")
    need(not target.exists(),"Fresh review output required; preserve prior checks")
    result=dict(stage="upl_cryer_cpu_component_review_r1",passed=False,configuration=cfg,
                physical_acceptance=False,programs_executed_by_reviewer=0)
    try:
        adopt(Path(__file__)); adopt(T/"notes/upl_cryer_cpu_component_review_r1.json")
        result.update(review(cfg))
        for e in list(BOUND.values()):
            need(entry(e["path"])==e,"Independent final bound-file hash changed")
        result.update(passed=True,inputs=list(BOUND.values()),independent_final_rehash_performed=True,failure=None)
    except Exception as exc:
        result.update(failure=str(exc),inputs=list(BOUND.values()))
    with target.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False); f.write("\n")
    need(result["passed"],"Offline review failed; preserve "+str(target)+": "+str(result.get("failure")))
    print(target)

if __name__=="__main__":
    main()
