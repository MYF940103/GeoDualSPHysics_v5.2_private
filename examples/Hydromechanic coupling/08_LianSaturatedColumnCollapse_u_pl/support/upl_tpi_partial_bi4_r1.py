"""Read one complete, little-endian JPartDataBi4 snapshot without C++ tools.

API: read(path) -> {root, part, arrays, types, file, file_code, byteorder,
strict_EOF}. Metadata nodes have name/values/types; array types give the JBD
type ID, NumPy dtype, count, components, bytes and absolute payload offset.
Arrays retain file order and are read-only views of immutable file bytes.

Narrow format contract: JBinaryData.{h,cpp}, current 64-byte header;
cpp 711-719/739-741 strings, 748-798 typed values, 804-846/892-939 arrays,
853-885/946-983 items, 1124-1149 streaming layout, 1156-1165 header.
JPartDataBi4.cpp 305-318 defines PART identity/count/time metadata.
Only one root + one PART with the current 22 numeric arrays is accepted.
This checks serialization, not solver completion, ownership or physics.
There is deliberately no CLI, writer, decoder process or automatic action.
"""
from pathlib import Path
import os
import re
import struct

import numpy as np


class Bi4FormatError(ValueError):
    """The file is incomplete or outside the supported BI4 contract."""


# JBinaryDataDef::TpData and SizeOfType (JBinaryData.h 72-76; cpp 72-90).
_NUMERIC = {
    2: ("DatBool", "<i4", 1), 3: ("DatChar", "i1", 1),
    4: ("DatUchar", "u1", 1), 5: ("DatShort", "<i2", 1),
    6: ("DatUshort", "<u2", 1), 7: ("DatInt", "<i4", 1),
    8: ("DatUint", "<u4", 1), 9: ("DatLlong", "<i8", 1),
    10: ("DatUllong", "<u8", 1), 11: ("DatFloat", "<f4", 1),
    12: ("DatDouble", "<f8", 1), 20: ("DatInt3", "<i4", 3),
    21: ("DatUint3", "<u4", 3), 22: ("DatFloat3", "<f4", 3),
    23: ("DatDouble3", "<f8", 3),
}


def _need(ok, message):
    if not ok:
        raise Bi4FormatError(message)


class _Cursor:
    def __init__(self, data, start=0, end=None):
        self.data, self.pos = data, start
        self.end = len(data) if end is None else end

    def take(self, n):
        _need(0 <= n <= self.end - self.pos,
              "Truncated payload at byte %d (requested %d)" % (self.pos, n))
        start = self.pos
        self.pos += n
        return memoryview(self.data)[start:self.pos]

    def number(self, fmt):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def uint(self):
        return self.number("<I")

    def integer(self):
        return self.number("<i")

    def boolean(self):
        value = self.integer()
        _need(value in (0, 1), "Noncanonical serialized bool")
        return bool(value)

    def string(self):
        return bytes(self.take(self.uint())).decode("utf-8", "surrogateescape")

    def block(self, n):
        start = self.pos
        self.take(n)
        return _Cursor(self.data, start, self.pos)

    def finish(self, context):
        _need(self.pos == self.end, "%s has unconsumed bytes at %d" % (context, self.pos))


def _name(value):
    _need(bool(value) and "\0" not in value, "Empty or NUL-containing name")
    return value


def _numeric(c, type_id, count):
    _need(type_id in _NUMERIC, "Unsupported numeric type %d" % type_id)
    type_name, dtype, components = _NUMERIC[type_id]
    dtype = np.dtype(dtype)
    size = count * components * dtype.itemsize
    offset = c.pos
    array = np.frombuffer(c.take(size), dtype=dtype, count=count * components)
    if components != 1:
        array = array.reshape(count, components)
    if type_id == 2:
        _need(bool(np.all((array == 0) | (array == 1))), "Noncanonical bool array/value")
    _need(not array.flags.writeable, "Internal immutable-buffer contract failed")
    return array, {"type_id": type_id, "type_name": type_name,
                   "dtype": dtype.str, "count": count, "components": components,
                   "data_bytes": size, "file_offset": offset}


def _values(c):
    values, types = {}, {}
    if c.pos != c.end:
        _need(c.string() == "\nVALUES", "Invalid VALUES marker")
        count = c.uint()
        _need(count <= (c.end - c.pos) // 9, "Impossible value count")
        for _ in range(count):
            name = _name(c.string())
            _need(name not in values, "Duplicate value: " + name)
            type_id = c.integer()
            if type_id == 1:
                value = c.string()
            else:
                array, description = _numeric(c, type_id, 1)
                value = array[0]
            values[name], types[name] = value, type_id
    c.finish("VALUES block")
    return values, types


def _item(c, depth):
    _need(depth <= 1, "Nested PART items are unsupported")
    definition = c.block(c.uint())
    _need(definition.string() == "\nITEM\n", "Invalid ITEM marker")
    name = _name(definition.string())
    hide, hide_values = definition.boolean(), definition.boolean()
    fmt_float, fmt_double = definition.string(), definition.string()
    narrays, nitems, values_size = definition.uint(), definition.uint(), definition.uint()
    definition.finish("ITEM definition")
    _need((depth == 0 and narrays == 0 and nitems == 1) or
          (depth == 1 and narrays == 22 and nitems == 0),
          "Expected root[0 arrays,1 PART] and PART[22 arrays,0 items]")
    values, value_types = _values(c.block(values_size))
    node = {"name": name, "values": values, "types": value_types,
            "hide": hide, "hide_values": hide_values,
            "fmt_float": fmt_float, "fmt_double": fmt_double}
    arrays, types = {}, {}
    for _ in range(narrays):
        definition = c.block(c.uint())
        _need(definition.string() == "\nARRAY", "Invalid ARRAY marker")
        array_name = _name(definition.string())
        _need(array_name not in arrays, "Duplicate array: " + array_name)
        hidden, type_id = definition.boolean(), definition.integer()
        count, payload_size = definition.uint(), definition.uint()
        definition.finish("ARRAY definition")
        _need(type_id in _NUMERIC, "Non-numeric/unknown array type")
        dtype, components = np.dtype(_NUMERIC[type_id][1]), _NUMERIC[type_id][2]
        _need(payload_size == count * dtype.itemsize * components, "Array byte/count mismatch")
        array, description = _numeric(c, type_id, count)
        description["hidden"] = hidden
        arrays[array_name], types[array_name] = array, description
    children = [_item(c, depth + 1) for _ in range(nitems)]
    return node, arrays, types, children


def read(path):
    """Read a single caller-selected, complete BI4; preserve exact payload bits.

    Stability of stat during this read is checked. The caller must independently
    choose an already closed snapshot; stable stat alone is not a completion seal.
    Metadata numeric scalars retain their NumPy width, triples are read-only (3,)
    arrays, and text uses reversible UTF-8 surrogateescape decoding.
    """
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        _need(64 <= before.st_size < 2**32, "Unsupported file size")
        data = stream.read()
        after = os.fstat(stream.fileno())
    current = path.stat()
    identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
    _need(identity(before) == identity(after) == identity(current), "File changed during read")
    _need(len(data) == before.st_size, "Incomplete file read")
    header = data[:64]
    _need(header[:9] == b"#FileJBD " and header[58:60] == b"\n\0", "Invalid file header")
    _need(header[60:] == b"\0\0\0\0", "Only little-endian current header is supported")
    code = header[9:58].rstrip(b" ").decode("ascii", "strict")
    _need(code == "JPartDataBi4", "Not a JPartDataBi4 snapshot")
    cursor = _Cursor(data, 64)
    root, root_arrays, root_types, children = _item(cursor, 0)
    cursor.finish("BI4 file (strict EOF)")
    _need(root["name"] == code, "Root/header identity mismatch")
    part, arrays, types, grandchildren = children[0]
    match = re.fullmatch(r"PART_([0-9]{4,})", part["name"])
    _need(match is not None, "Invalid PART name")
    for key, expected in (("Cpart", 8), ("TimeStep", 12), ("Npok", 8),
                          ("Nout", 8), ("Step", 8)):
        _need(part["types"].get(key) == expected, "Missing/wrong PART metadata: " + key)
    _need(int(match.group(1)) == int(part["values"]["Cpart"]), "PART/Cpart mismatch")
    count = int(part["values"]["Npok"])
    _need(all(entry["count"] == count for entry in types.values()), "PART Npok/array count mismatch")
    id_name = "Idp" if "Idp" in arrays else "Idpd"
    _need(id_name in arrays and types[id_name]["type_id"] == (8 if id_name == "Idp" else 10),
          "Missing/wrong original particle ID array")
    _need(np.unique(arrays[id_name]).size == count, "Duplicate original particle IDs")
    return {"root": root, "part": part, "arrays": arrays, "types": types,
            "file": {"path": str(path), "bytes": before.st_size, "mtime_ns": before.st_mtime_ns},
            "file_code": code, "byteorder": "little", "strict_EOF": True}
