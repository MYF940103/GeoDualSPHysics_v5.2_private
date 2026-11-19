"""Prepare a consecutive two-frame reader profile and reuse the sealed CPU component build."""
import c08_tpi_eq47_build_r1 as build


def main():
    tests = build.T
    input_file = tests / "outputs/c08_tpi_state_r1_build/shared.inc"
    profile = tests / "outputs/c08_eq47_p3_warm_profile_r1/shared.inc"
    check = build.m.read(tests / "logs/c08_h18_storage_debug2_review_r2.check.json")
    assert check["passed"]
    native = tests / "outputs/c08_h18_storage_debug2_GPU_r1/native_r1"
    assert (native / "typed22.bin").stat().st_size == 12 + 2 * (8 + 6805 * 212)
    source = input_file.read_text(encoding="utf-8")
    for old, new in [("Soil=5000,Samples=301", "Soil=5000,Samples=2"),
                     ("Parts[2]={38,76},Steps[2]={2076001,2152001}",
                      "Parts[2]={0,1},Steps[2]={2000001,2000002}")]:
        assert source.count(old) == 1
        source = source.replace(old, new)
    profile.parent.mkdir()
    profile.write_text(source, encoding="utf-8")
    # The build harness selects only its own input TU and fresh output paths with TAG.
    # Existing native frames, compiler flags, 86 physical objects and seed stay untouched.
    build.TAG = "c08_eq47_p3_warm_r1"
    build.main()


if __name__ == "__main__":
    main()
