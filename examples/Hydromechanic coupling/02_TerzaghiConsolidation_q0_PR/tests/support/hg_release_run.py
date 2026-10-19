"""Fresh CPU release-integration regression using the real production step.

The retained hg_merge preparation/run machinery is reused without editing it.
SPR and fixed-grid drainage are explicit XML options, not in-memory overrides.
This runner never retries, overwrites an output, or admits another run itself.
"""
import argparse
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
import hg_merge_run as base

original_render = base.render
original_signature = base.signature


def signature(node, omit=False):
    if omit and node.tag == "HydroMechDrainageFixedGrid":
        return None
    return original_signature(node, omit)


def render(text, settings):
    text = original_render(text, settings)
    for key, value, comment in (
        ("SoilBoundaryDerivativeSPR", str(settings["spr"]),
         "Fixed horizontal wall MLS velocity for stress, pore and density derivatives only"),
        ("SoilDampingCoef", settings["damping_text"], "Retained soil damping coefficient"),
    ):
        if f'key="{key}"' not in text:
            match = re.search(r'(?m)^([ \t]*)<parameter key="SoilDamping"', text)
            base.require(match is not None, "Missing standard parameter insertion point")
            text = text[:match.start()] + f'{match[1]}<parameter key="{key}" value="{value}" comment="{comment}" />\n' + text[match.start():]
        else:
            text = base.replace_value(text, f'parameter key="{key}"', value)
    match = re.search(r'(?m)^([ \t]*)<HydroMechDrainageStartTime\s', text)
    base.require(match is not None and "<HydroMechDrainageFixedGrid" not in text,
                 "Expected original drainage event setting")
    line = f'{match[1]}<HydroMechDrainageFixedGrid value="{settings["event_grid"]}" comment="Align an exactly fixed-grid drainage event within time-summation roundoff only" />\n'
    text = text[:match.start()] + line + text[match.start():]
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", required=True)
    p.add_argument("--duration", required=True)
    p.add_argument("--dt", default="0.00001")
    p.add_argument("--output-interval", default="0.001")
    p.add_argument("--xi", type=float, default=.1)
    p.add_argument("--spr", type=int, choices=(0, 1), default=0)
    p.add_argument("--event-grid", type=int, choices=(0, 1), default=0)
    p.add_argument("--damping", choices=("0.02", "0.04"), default="0.02")
    p.add_argument("--binary-label", required=True)
    p.add_argument("--threads", type=int, choices=(1, 4), default=1)
    p.add_argument("--save", type=int, choices=(0, 1), default=0)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = p.parse_args()
    args.engine, args.top_mode, args.exe, args.build_record = "wrapper", 5, None, None
    s = base.settings(args)
    s.update(spr=args.spr, event_grid=args.event_grid, damping_text=args.damping,
             integration_scope="release_same_physics_regression", physical_configuration_overridden=False)
    base.CHANGED_PARAMETERS.update(("SoilBoundaryDerivativeSPR", "SoilDampingCoef", "HydroMechDrainageFixedGrid"))
    base.signature, base.render = signature, render
    base.runtime_inputs(args)
    prefix, prepared = base.prepare(s, not args.dry_run)
    if args.dry_run or args.prepare_only:
        print(base.json.dumps(dict(status="checked_not_run" if args.dry_run else "prepared_not_run",
                                   **prepared), indent=2))
        return 0
    prepared = dict(prepared, inputs=prepared["inputs"] + [base.entry(Path(__file__))])
    return base.run(args, s, prefix, prepared)


if __name__ == "__main__":
    sys.exit(main())
