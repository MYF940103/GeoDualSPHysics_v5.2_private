import argparse
import re
from pathlib import Path


def replace_attr(text, pattern, value):
    text_new, count = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(2)}", text, count=1)
    if count != 1:
        raise RuntimeError(f"Replacement failed for pattern: {pattern}")
    return text_new


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tmax", required=True)
    parser.add_argument("--tout", required=True)
    parser.add_argument("--dtfixed", required=True)
    parser.add_argument("--poresafety", required=True)
    args = parser.parse_args()

    text = Path(args.base).read_text(encoding="utf-8")
    text = replace_attr(text, r'(<PoreDtSafety value=")[^"]+(")', args.poresafety)
    text = replace_attr(text, r'(<parameter key="DtFixed" value=")[^"]+(")', args.dtfixed)
    text = replace_attr(text, r'(<parameter key="TimeMax" value=")[^"]+(")', args.tmax)
    text = replace_attr(text, r'(<parameter key="TimeOut" value=")[^"]+(")', args.tout)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
