"""Prepare a deployable overlay only. Never install it or start a case."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import hydro_frozen_xml_r1 as bridge

SUITE = bridge.SUITE
STAGE = SUITE / "04_CryerProblem_PR/tests/outputs/hfe1"
OVERLAY = STAGE / "overlay"
RUNTIME = "hydro_frozen_runtime_r2.ps1"
ARCHIVES = "hydro_frozen_plan_r2.json"


def package_path(case, archive):
    path = case / archive
    if path.is_file() or Path(archive).name != archive:
        return path
    moved = case / "support/server_packages" / archive
    return moved if moved.is_file() else path


def replace_one(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Original BAT changed at anchor {old!r}")
    return text.replace(old, new)


def read_bat(path):
    return path.read_text(encoding="utf-8")


def bat(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Staged file already exists with a different value: {path}")
        return
    path.write_bytes(content)


def bridge_call(output):
    return ('powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "support\\' + RUNTIME +
            '" -Definition "%name%_Def.xml" -OutFile "' + output + '"\n'
            'if errorlevel 1 goto fail\n')


def simple_bat(original, selfweight):
    src = read_bat(original)
    guard = 'if exist "%dirout%" goto exists'
    src = replace_one(src, 'set diroutdata=', 'if /i "%~1"=="--prepare-only" set "dirout=%name%_prepare"\nset diroutdata=')
    if selfweight:
        src = replace_one(src, 'if not "%~1"=="" if /i not "%~1"=="-solver-only" goto usage',
                          'if not "%~1"=="" if /i not "%~1"=="-solver-only" if /i not "%~1"=="--prepare-only" goto usage')
        src = replace_one(src, '--config "%name%_Def.xml"', '--config "%dirout%\\%name%.xml"')
    else:
        src = src.replace('if not "%~1" == "--unattended" pause',
                          'if not "%~1" == "--unattended" if /i not "%~1" == "--prepare-only" pause')
    # The original existing-output and binary checks must occur before any new directory creation.
    command = '%gencase% "%name%_Def" "%dirout%/%name%" -save:all'
    pos = src.index(command)
    assert src.index(guard) < pos
    src = replace_one(src, command,
                      'mkdir "%dirout%"\nif errorlevel 1 goto fail\n' +
                      bridge_call(r"%dirout%\%name%_Def.xml") +
                      '%gencase% "%dirout%/%name%_Def" "%dirout%/%name%" -save:all')
    src = replace_one(src, "%dualsphysicsgpu% -gpu",
                      'if /i "%~1"=="--prepare-only" exit /b 0\n%dualsphysicsgpu% -gpu')
    return bat(src)


def collapse_bat(original, rev):
    src = read_bat(original)
    src = replace_one(src, 'set "c08postonly=0"', 'set "c08postonly=0"\nset "c08prepare=0"')
    marker = 'for %%A in ("%~3" "%~4") do ('
    src = replace_one(src, marker, marker +
                      '\n    if /i "%%~A" == "--prepare-only" set "c08prepare=1"\n'
                      '    if /i "%%~A" == "--prepare-only" set "c08unattended=1"')
    marker = 'set dirout=%name%_%backend%_out'
    src = replace_one(src, marker, marker+'\nif "%c08prepare%" == "1" set "dirout=%name%_%backend%_prepare"\n'
                      'if "%c08prepare%%c08postonly%" == "11" goto fail')
    src = replace_one(src, r"set template=%CD%\%name%_Def.xml",
                      bridge_call(r"%dirout%\legacy_Def.xml") + r"set template=%CD%\%dirout%\legacy_Def.xml")
    if rev == 3:
        marker = r'"%dirbin%\GenCase_win64.exe" "%name%_Def" '
        src = replace_one(src, marker, 'mkdir "%dirout%"\nif errorlevel 1 goto fail\n' +
                          bridge_call(r"%dirout%\%name%_Def.xml") +
                          r'"%dirbin%\GenCase_win64.exe" "%dirout%\%name%_Def" ')
    marker = r'"%dirbin%\%solver%" %runmode% '
    if src.count(marker) != (2 if rev == 3 else 1):
        raise ValueError("Original solver entry count changed")
    src = src.replace(marker, 'if "%c08prepare%" == "1" exit /b 0\n' + marker)
    return bat(src)


def find_archive(name):
    if "_P3_" in name:
        return "Cryer_TPI_P3_nu030_Windows_RTXA6000_r1.zip", "p3"
    if "u_pl_" in name:
        return "Cryer_upl_nu030_Windows_RTXA6000_r1.zip", "seed"
    if "symc_" in name:
        return "Cryer_symC_nu030_Windows_RTXA6000_r1.zip", "gen"
    if "release_r2" in name:
        return "Cryer_release_r2_Windows_RTXA6000.zip", "gen"
    if "_release_nu" in name:
        return "Cryer_release_nu010_020_045_r1_Windows_RTXA6000.zip", "gen"
    raise ValueError(name)


def cryer_wrapper(name):
    return bat('@echo off\nsetlocal\ncd /d "%~dp0"\n'
               'if not "%~3"=="" exit /b 2\n'
               'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "support\\' +
               RUNTIME + '" -Definition "' + name + '" -Portable -Option1 "opt=%~1" -Option2 "opt=%~2"\n'
               'set "rc=%ERRORLEVEL%"\nif not "%rc%"=="0" if "%~1"=="" pause\nexit /b %rc%\n')


def assemble(source_suite, destination, archive_metadata=None):
    manifest = []
    plans = {}
    hashes = {}
    for name, spec in sorted(bridge.records().items()):
        cid = spec["case"]
        case, = source_suite.glob(cid + "_*")
        archive = (case / name).read_bytes()
        bridge.validate_template(name, archive)
        target = destination / case.name
        support = target / "support"
        public = bridge.modernize(name, archive)
        save(target / name, public)
        save(support / RUNTIME, (bridge.HERE / RUNTIME).read_bytes().replace(b"\r\n",b"\n"))
        special, water = bridge.nodes(bridge.tree(public))
        model, defaults = bridge.mode_values(special, water)
        data = dict(public_sha256=hashlib.sha256(public).hexdigest(), template_sha256=spec["sha256"],
                    editable=cid in ("01", "05"))
        plans.setdefault(case.name, {})[name] = data
        if data["editable"]:
            data.update(model=model, defaults=defaults, legacy_keys=bridge.OLD,
                        material_keys=[n.tag for n in water if isinstance(n.tag,str) and n.tag!=bridge.MODEL],
                        special_keys=[n.tag for n in special if isinstance(n.tag,str) and n.tag not in ("drainage","externalload")])
        if cid != "04":
            save(support / "frozen_xml" / name, archive)
            save(support / "frozen_xml/.gitattributes",b"*_Def.xml -text\n")
        stem = name.removesuffix("_Def.xml")
        original = case / ("x" + stem + "_win64_GPU.bat")
        related = []
        if cid in ("01", "05"):
            save(target / original.name, simple_bat(original, cid == "01"))
            related = [original.name]
        elif cid == "08":
            rev = int(stem[-1])
            helper = f"run_lian_collapse_shared_r{rev}_win64.bat"
            save(support / helper, collapse_bat(case / "support" / helper, rev))
            related = [b.name for b in case.glob("x" + stem + "_win64_*.bat")]
            if not related:
                raise ValueError("Source without root launchers: " + stem)
        else:
            package, mode = find_archive(name)
            archive_entry = package
            if archive_metadata is None:
                archive_file = package_path(case, package)
                archive_entry = archive_file.relative_to(case).as_posix()
                with zipfile.ZipFile(archive_file) as file:
                    if file.read(name) != archive:
                        raise ValueError("Original ZIP definition differs from the registered source: "+name)
                if package not in hashes:
                    with archive_file.open("rb") as stream:
                        hashes[package] = hashlib.file_digest(stream, "sha256").hexdigest()
                    sha = archive_file.with_suffix(".zip.sha256")
                    if sha.exists() and sha.read_text().split()[0].lower() != hashes[package]:
                        raise ValueError("Published package digest mismatch: " + package)
            else:
                record = archive_metadata[package]
                if record["definitions"].get(name) != spec["sha256"]:
                    raise ValueError("Archived definition provenance mismatch: " + name)
                hashes[package] = record["sha256"]
            workspace = {"p3":"cryer_P3_run", "seed":"cryer_upl_run",
                         "gen":"cryer_nu_run" if "_release_nu" in name else "cryer_r2_run" if "_release_r2" in name else "cryer_symc_run"}[mode]
            data.update(archive=archive_entry, mode=mode, archive_sha256=hashes[package], workspace=workspace)
            save(target / original.name, cryer_wrapper(name))
            related = [original.name]
        manifest.append(dict(case=cid, definition=name, launchers=related))
    for case_name, plan in plans.items():
        save(destination / case_name / "support" / ARCHIVES, json.dumps(plan, indent=2).encode("utf8"))
    print(f"Staged {len(manifest)} frozen inputs at {destination}")
    save(destination.parent / (destination.name + "_entries.json"), json.dumps(manifest, indent=2).encode("utf8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OVERLAY)
    destination = parser.parse_args().out.resolve()
    if not destination.is_relative_to((SUITE / "04_CryerProblem_PR/tests/outputs").resolve()):
        raise ValueError("Target must be a separate staging directory under C04/tests/outputs.")
    assemble(SUITE, destination)


if __name__ == "__main__":
    main()

