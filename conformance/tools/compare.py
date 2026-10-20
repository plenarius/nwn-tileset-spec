#!/usr/bin/env python3
# CC0 1.0. Compares an implementation's predictions with the routes the
# server walked (conformance/routes). Python 3.8+, standard library only.
#
# Predictions: a directory laid out like conformance/routes/
# (v1/cliff4.0-seed1.json, ...), each file a JSON list with one entry per
# route, in the same order as the recorded file:
#     {"arrived": true, "end": [x, y]}
# "end" is optional. A missing file counts its routes as not predicted.
#
# Usage:
#     python3 conformance/tools/compare.py --predictions DIR [--case ID ...]
#            [--end-tolerance 0.5] [--verbose]
# Exit status 0 when every predicted route agrees on arrival, else 1.

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictions", required=True, help="directory of prediction files")
    ap.add_argument("--case", action="append", help="only this case id (repeatable), e.g. v3/rugged-seed33")
    ap.add_argument("--end-tolerance", type=float, default=0.5, help="metres; end points within this count as close")
    ap.add_argument("--verbose", action="store_true", help="list every disagreeing route")
    args = ap.parse_args()

    with open(os.path.join(CONF, "manifest.json")) as f:
        manifest = json.load(f)

    total = agree = missing = close = with_end = 0
    for case in manifest["cases"]:
        if args.case and case["id"] not in args.case:
            continue
        with open(os.path.join(CONF, case["file"])) as f:
            recorded = json.load(f)
        pred_path = os.path.join(args.predictions, os.path.relpath(case["file"], "routes"))
        if not os.path.exists(pred_path):
            print(f"{case['id']}: no predictions ({len(recorded)} routes)")
            missing += len(recorded)
            total += len(recorded)
            continue
        with open(pred_path) as f:
            predicted = json.load(f)
        c_agree = c_close = c_end = 0
        for i, rec in enumerate(recorded):
            total += 1
            if i >= len(predicted) or "arrived" not in predicted[i]:
                missing += 1
                continue
            p = predicted[i]
            if bool(p["arrived"]) == bool(rec["arrived"]):
                c_agree += 1
            elif args.verbose:
                print(f"  {case['id']} #{i}: {rec['from']} -> {rec['to']}: server "
                      f"{'arrived' if rec['arrived'] else 'stopped'} at {rec['end']}, predicted "
                      f"{'arrived' if p['arrived'] else 'stopped'}"
                      + (f" at {p['end']}" if "end" in p else ""))
            if "end" in p:
                c_end += 1
                d = math.hypot(p["end"][0] - rec["end"][0], p["end"][1] - rec["end"][1])
                if d <= args.end_tolerance:
                    c_close += 1
        agree += c_agree
        close += c_close
        with_end += c_end
        line = f"{case['id']}: arrival agrees on {c_agree}/{len(recorded)}"
        if c_end:
            line += f"; end within {args.end_tolerance} m on {c_close}/{c_end}"
        print(line)

    print(f"total: arrival agrees on {agree}/{total}"
          + (f", {missing} not predicted" if missing else "")
          + (f"; end within {args.end_tolerance} m on {close}/{with_end}" if with_end else ""))
    return 0 if agree == total else 1


if __name__ == "__main__":
    sys.exit(main())
