"""Compare native device functions in two GPU Release executables without running CUDA."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile


BASE = Path(__file__).resolve().parent
TOOL = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\bin\cuobjdump.exe")
EXE = "DualSPHysics5.2_GEO_win64.exe"
ELF = struct.Struct("<16sHHIQQQIHHHHHH")
SHDR = struct.Struct("<IIQQQQIIQQ")
SYMBOL = struct.Struct("<IBBHQQ")
SALT = re.compile(rb"_INTERNAL_([0-9a-f]{8})_")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def cstring(table, off):
    return table[off:table.index(0, off)].decode("ascii")


def read_elf(path):
    data = path.read_bytes()
    magic, _, machine, _, _, _, soff, flags, _, _, _, ssize, count, names_idx = ELF.unpack_from(data)
    require(magic[:7] == b"\x7fELF\x02\x01\x01" and machine == 190 and ssize == SHDR.size,
            "Expected a little-endian native CUDA ELF64")
    sections = [SHDR.unpack_from(data, soff+i*ssize) for i in range(count)]
    def contents(section):
        offset, size = section[4:6]
        require(offset+size <= len(data), "Section extends beyond image")
        return data[offset:offset+size]
    names = contents(sections[names_idx])
    labels = [cstring(names, s[0]) for s in sections]
    code = {}
    funcs = {}
    for label, sec in zip(labels, sections):
        if sec[2] & 4:  # SHF_EXECINSTR
            require(sec[1] == 1 and label.startswith(".text.") and label not in code, "Unexpected code section")
            code[label] = contents(sec)
    for symtab in sections:
        if symtab[1] != 2:  # SHT_SYMTAB
            continue
        require(symtab[9] == SYMBOL.size, "Unexpected symbol layout")
        strings = contents(sections[symtab[6]])
        for index, info, other, sid, value, size in SYMBOL.iter_unpack(contents(symtab)):
            if info & 15 != 2 or sid >= len(sections):  # Only defined STT_FUNC
                continue
            section = labels[sid]
            offset = value - sections[sid][3]
            require(section in code and 0 <= offset and size > 0 and offset+size <= len(code[section]),
                    "Defined function outside executable section")
            key = (section, cstring(strings,index), offset, size, info, other)
            require(key not in funcs, "Duplicate function identity")
            funcs[key] = memoryview(code[section])[offset:offset+size]
    strtab = sections[labels.index(".strtab")]
    return data, flags, code, funcs, (strtab[4], strtab[5])


def compare_elf(old, new):
    a, flags, code, funcs, strrange = read_elf(old)
    b, flags2, code2, funcs2, strrange2 = read_elf(new)
    require(flags == flags2 and code.keys() == code2.keys() and funcs.keys() == funcs2.keys(), "ELF layout or identity differs")
    require(all(v == code2[k] for k,v in code.items()), "Executable section bytes differ")
    require(all(v == funcs2[k] for k,v in funcs.items()), "Function instruction bytes differ")
    rec = dict(module=old.name, cuda_arch_flags=hex(flags), executable_sections=len(code),
               executable_section_bytes=sum(len(v) for v in code.values()), functions=len(funcs),
               whole_cubin_equal=(a == b))
    if a != b:
        start,size = strrange
        end = start+size
        require(strrange == strrange2 and a[:start] == b[:start] and a[end:] == b[end:], "Difference outside symbol strings")
        oldstr,newstr = a[start:end],b[start:end]
        left,right = SALT.findall(oldstr),SALT.findall(newstr)
        require(len(left) == len(right), "Private identifier count changed")
        changes = Counter((x,y) for x,y in zip(left,right) if x != y)
        require(len(changes) == 1, "Expected a single private salt substitution in this module")
        (x,y), repeats = changes.most_common(1)[0]
        expected = oldstr.replace(b"_INTERNAL_"+x+b"_", b"_INTERNAL_"+y+b"_")
        require(expected == newstr, "String table has other changes")
        rec["strtab_private_id"] = dict(old=x.decode(),new=y.decode(),occurrences=repeats)
    return rec


def extract(exe, directory):
    directory.mkdir()
    cmd = [str(TOOL), "-xelf", "all", str(exe)]
    subprocess.run(cmd, cwd=directory, check=True, capture_output=True,
                   creationflags=subprocess.IDLE_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW)
    files = {}
    for f in directory.glob("*.cubin"):
        m = re.search(r"\.(\d+)\.(sm_\d+)\.cubin$",f.name)
        require(m is not None, f"Unexpected cubin name {f.name}")
        key = int(m[1]), m[2]
        require(key not in files, "Duplicate cubin ordinal/architecture")
        files[key] = f
    require(files, "Executable has no native device code")
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, default=BASE/"old"/EXE)
    parser.add_argument("--new", type=Path, default=BASE/"validated"/EXE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old,new = args.old.resolve(),args.new.resolve()
    with tempfile.TemporaryDirectory() as work:
        old_files = extract(old, Path(work)/"old")
        new_files = extract(new, Path(work)/"new")
        require(old_files.keys() == new_files.keys(), "CUDA architecture or cubin ordinal changed")
        modules = [compare_elf(old_files[k],new_files[k]) for k in sorted(old_files)]
    rec = dict(old=str(old),new=str(new),old_file_bytes=old.stat().st_size,new_file_bytes=new.stat().st_size,
               tool=str(TOOL),architectures=sorted({k[1] for k in old_files}),
               cubins=len(modules),code_sections=sum(m["executable_sections"] for m in modules),
               code_section_bytes=sum(m["executable_section_bytes"] for m in modules),
               defined_function_symbols=sum(m["functions"] for m in modules),
               whole_equal_cubins=sum(m["whole_cubin_equal"] for m in modules),
               native_code_bytes_and_function_identity_equal=True,modules=modules)
    with args.output.open("x",encoding="utf8") as f:
        json.dump(rec,f,indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
