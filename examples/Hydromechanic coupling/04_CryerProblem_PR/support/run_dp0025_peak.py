import run_cryer_refinement as runner


def main():
    base = {
        "radius": 0.05,
        "q0": 10000.0,
        "e": 2.0e6,
        "nu": 0.3,
        "khyd": 1e-3,
        "pore_dt": 0.1,
        "shepard": 0,
        "shepard_interval": 30,
        "init_mode": "0",
        "drainage_mode": "FreeSurface",
        "damping": 4e-5,
        "visco": 0.1,
        "shift_tfs": 0.0,
    }
    cfg = dict(
        base,
        name="dp0025_freesurface_gpu_peak",
        dp=0.0025,
        load_ramp=0.0,
        drain_start=0.0,
        tl=0.0,
        tout=0.00005,
        time_max=0.0012,
        use_gpu=True,
    )
    runner.RUN_TIMEOUT = 7200.0
    print(runner.run_variant(cfg))


if __name__ == "__main__":
    main()
