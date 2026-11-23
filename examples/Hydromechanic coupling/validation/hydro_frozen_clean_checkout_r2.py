"""Verify portable configuration rebuild and Git checkout; no solver, compiler, archiver, or real-index writes."""
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import hydro_frozen_git_rebuild_r2 as rebuild

V=Path(__file__).resolve().parent
PREFIX="examples/Hydromechanic coupling/"
TOOLS="hydro_frozen_maintenance_r2.pathspec"
FORMALS="hydro_frozen_formals_r2.pathspec"
RESULT="hydro_frozen_clean_checkout_r2.json"
GUIDE="hydro_frozen_clean_checkout_r2.md"
SMALL_TOOLS = """
hydro_frozen_xml_r1.py hydro_frozen_xml_templates_r1.json hydro_frozen_xml_review_r1.py
hydro_frozen_xml_review_r1.json hydro_frozen_xml_edits_r1.py hydro_frozen_xml_edits_r1.json
hydro_frozen_entry_stage_r1.py hydro_frozen_entry_apply_r1.py hydro_frozen_entry_review_r1.py
hydro_frozen_entry_edits_r1.py hydro_frozen_entry_manifest_r1.py hydro_frozen_entry_release_r2.json
hydro_frozen_entry_release_r2.md hydro_frozen_runtime_r2.ps1 hydro_frozen_windows_review_r2.json
hydro_frozen_windows_review_r2.py hydro_root_bindings_review_r1.py hydro_root_bindings_review_r1.md
hydro_root_bindings_review_r1.json hydro_frozen_clean_inputs_r2.json hydro_frozen_git_rebuild_r2.py
hydro_frozen_clean_checkout_r2.py hydro_frozen_install_r2.py hydro_frozen_install_r2.json
""".split()


def command(cwd,*args,data=None):
    p=subprocess.run([*args],cwd=cwd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(str(args)+"\n"+(p.stdout+p.stderr).decode(errors="replace"))
    return p.stdout


def git(cwd,*args,data=None):
    return command(cwd,"git",*args,data=data)


def nul(items):
    return b"".join(s.encode("utf8")+b"\0" for s in sorted(set(items)))


def checkout(repo, paths):
    git(repo,"checkout-index","--force","--stdin","-z",data=nul(paths))


def index(repo,paths):
    git(repo,"--literal-pathspecs","add","--force","--pathspec-from-file=-","--pathspec-file-nul",data=nul(paths))


def temp_repo(root, foreign_objects, tree, autocrlf):
    root.mkdir()
    git(root,"init","-q")
    (root/".git/objects/info/alternates").write_bytes((foreign_objects.resolve().as_posix()+"\n").encode("utf8"))
    git(root,"config","core.autocrlf",autocrlf)
    git(root,"config","core.compression","0")
    git(root,"config","gc.auto","0")
    git(root,"read-tree",tree)


def main():
    repo=Path(git(V,"rev-parse","--show-toplevel").decode().strip()).resolve()
    objects=Path(git(V,"rev-parse","--path-format=absolute","--git-path","objects").decode().strip())
    proof=json.loads(rebuild.SOURCE.read_text());ref=proof["git_baseline"]
    report=json.loads(rebuild.REVIEW.read_text())
    files={PREFIX+x["path"]:x for x in report["entries"]}
    formals=sorted(files)
    prescription=sorted(PREFIX+"validation/"+f for f in SMALL_TOOLS+[RESULT,GUIDE,TOOLS,FORMALS])
    # Bound and future deployment paths are separated to avoid staging old root files before installation.
    (V/TOOLS).write_bytes(nul(prescription))
    (V/FORMALS).write_bytes(nul(formals))
    new_tools=[p for p in prescription if p.rsplit("/",1)[1] not in (RESULT,GUIDE)]
    baseline_paths=set(git(repo,"ls-tree","-r","--name-only","-z",ref,"--","examples/Hydromechanic coupling").decode().strip("\0").split("\0"))
    fold=collections.Counter()
    for p,rec in files.items():
        if rec["previous"] is not None:
            _,e=rebuild.original_bytes(git(repo,"cat-file","blob",ref+":"+p),rec["previous"],p)
            fold[e]+=1
    attrs=set()
    for test in set(formals+new_tools):
        for d in Path(test).parents:
            f=(d/".gitattributes").as_posix()
            if git(repo,"ls-tree",ref,"--",f).strip():attrs.add(f)
    unchanged=[]
    for item in report["staged_normal_entry"]["rows"]:
        if item["case"]=="08":
            unchanged.append(PREFIX+"08_LianSaturatedColumnCollapse_u_pl/"+item["launcher"])
    tracked_old=[p for p,r in files.items() if r["previous"] is not None]
    examples=PREFIX+"validation/"
    trial_results=[]
    with tempfile.TemporaryDirectory(prefix="hydro_git_") as temp:
        fixture=Path(temp)/"first"
        temp_repo(fixture,objects,ref,"true")
        checkout(fixture,attrs|set(unchanged+tracked_old))
        for p in new_tools:
            dst=fixture/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/p,dst)
        index(fixture,new_tools)
        # Explicitly obtain the same prospective settings through Git's smudge conversion.
        checkout(fixture,new_tools)
        def run(root,script,*args):
            return command(root,sys.executable,"-B",str(root/(examples+script)),*args).decode(errors="replace").strip()
        assert not (fixture/(PREFIX+"04_CryerProblem_PR/tests/outputs/hfe1")).exists()
        rebuilt=run(fixture,"hydro_frozen_git_rebuild_r2.py")
        before=run(fixture,"hydro_frozen_entry_apply_r1.py")
        applied=run(fixture,"hydro_frozen_entry_apply_r1.py","--apply")
        assert "59 of 59" in applied
        index(fixture,formals)
        prospect=git(fixture,"write-tree").strip().decode()
        # Every necessary final file is now part of the temporary Git tree, including ignored templates.
        for mode in ("true","false"):
            other=Path(temp)/("after_"+mode)
            temp_repo(other,fixture/".git/objects",prospect,mode)
            checkout(other,attrs|set(unchanged+new_tools+formals))
            review=run(other,"hydro_frozen_entry_apply_r1.py")
            assert "already match" in review
            assert not list((other/(PREFIX+"04_CryerProblem_PR")).glob("*.zip"))
            assert not (other/(PREFIX+"04_CryerProblem_PR/tests/outputs")).exists()
            recreated=run(other,"hydro_frozen_git_rebuild_r2.py")
            proof_only=run(other,"hydro_frozen_entry_apply_r1.py","--apply")
            assert "No files written" in proof_only
            trial_results.append(dict(core_autocrlf=mode,clean_index_tree=prospect,verification=review,
                rebuild_ok="Verified 59 files, 492206 bytes" in recreated,hfe1_needed_on_entry=False,
                solver_calls=0,external_zip_files=0))
        assert all(t["rebuild_ok"] for t in trial_results)
    dependencies={}
    for cid,paths in proof["external_runtime_paths"].items():
        dependencies[cid]=[dict(path=p,local_bytes=(repo/p).stat().st_size if (repo/p).is_file() else None,
                                tracked_at_baseline=p in baseline_paths) for p in paths]
    out=dict(git_baseline=ref,previous_35_byte_sources=dict(fold),root_pathspec_count=len(files),
             maintenance_pathspec_count=len(prescription),new_tool_inputs_tested_through_temp_index=len(new_tools),
             clean_checkout_verification=trial_results,preinstall_dryrun=before,preinstall_install_test=applied,
             baseline_formals_tracked=len(tracked_old),unchanged_C08_launchers=len(set(unchanged)),
             local_runtime_inventory=dependencies,portable_manifest_bytes=sum(r["bytes"] for r in proof["archives"].values()),
             git_index_changed=False,formal_root_writes=0,builds=0,solver_calls=0,new_zip_archives=0)
    (V/RESULT).write_text(json.dumps(out,indent=2),encoding="utf8")
    print("Verified small-file production checkout on both EOL settings, with no packaged applications or prior staging.")
    print("Runtime entries by case:",{k:len(v) for k,v in dependencies.items()})


if __name__=="__main__":
    main()

