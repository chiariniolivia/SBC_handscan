"""
this one just appends data thats new instead of making a whole new thing
"""



#!/usr/bin/env python3
"""
Take a directory of CSVs (same format as original CSV inputs) and a merged CSV (from previous script),
and produce a new CSV that contains all (RUN, EVENT) pairs present in either source:
- For pairs already present in the merged CSV, keep the merged row as-is.
- For pairs present only in the raw CSV files, add rows with Estimated fields, PSET, evlivetime filled
  from the CSVs, and Actual/Source/Notes fields left blank.

Usage:
    python add_missing_pairs.py /path/to/csv_dir merged.csv output.csv
"""
import sys
import os
import glob
import csv
import argparse
from decimal import Decimal

def norm(val):
    if val is None:
        return ""
    s = str(val).strip()
    try:
        if s != "" and all(ch in "0123456789.-eE" for ch in s):
            if "e" in s.lower() or "." in s:
                d = Decimal(s)
                if d == d.to_integral():
                    s = format(int(d))
                else:
                    s = format(d.normalize())
    except Exception:
        pass
    return s

def read_raw_csvs(dirpath):
    """Read all raw CSVs and return dict keyed by (RUN, EVENT) -> fields from CSVs."""
    files = [p for p in glob.glob(os.path.join(dirpath, "*.csv")) if os.path.isfile(p)]
    data = {}
    for p in files:
        with open(p, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                next(reader)
            except StopIteration:
                continue
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue
                # pad to at least 11 columns (robust to 10 or 11)
                while len(row) < 11:
                    row.append("")
                run = norm(row[0])
                event = norm(row[1])
                key = (run, event)
                data[key] = {
                    "Estimated Bubble Count": row[2],
                    "Est Cam 1 Formation": row[3],
                    "Est Cam 1 Coordinate": row[4],
                    "Est Cam 2 Formation": row[5],
                    "Est Cam 2 Coordinate": row[6],
                    "Est Cam 3 Formation": row[7] if len(row) > 7 else "",
                    "Est Cam 3 Coordinate": row[8] if len(row) > 8 else "",
                    "PSET": row[9] if len(row) > 9 else "",
                    "evlivetime": row[10] if len(row) > 10 else "",
                }
    return data

def read_merged_csv(path):
    """Read merged CSV produced by previous script. Return dict keyed by (RUN, EVENT) -> row (as list)."""
    rows = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            hdr = next(reader)
        except StopIteration:
            return hdr, rows
        header = hdr
        for r in reader:
            if len(r) < 2:
                continue
            run = norm(r[0])
            event = norm(r[1])
            key = (run, event)
            rows[key] = r
    return header, rows

def sort_key(pair):
    run, event = pair
    def to_num(s):
        try:
            return int(s)
        except Exception:
            try:
                return float(s)
            except Exception:
                return s
    return (to_num(run), to_num(event))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_dir", help="Directory with raw CSV files")
    p.add_argument("merged_csv", help="Merged CSV from previous script")
    p.add_argument("out_csv", help="Output CSV path")
    args = p.parse_args()

    if not os.path.isdir(args.csv_dir):
        print("csv_dir not found"); sys.exit(1)
    if not os.path.isfile(args.merged_csv):
        print("merged_csv not found"); sys.exit(1)

    raw = read_raw_csvs(args.csv_dir)
    header, merged = read_merged_csv(args.merged_csv)

    # Ensure we have a header. If not, build expected header same as previous script output:
    if not header:
        header = [
            "RUN","EVENT","Actual Bubble Count","Estimated Bubble Count","Source Type","PSET","evlivetime",
            "Actual Cam 1 Formation","Actual Cam 1 Coordinate","Est Cam 1 Formation","Est Cam 1 Coordinate",
            "Actual Cam 2 Formation","Actual Cam 2 Coordinate","Est Cam 2 Formation","Est Cam 2 Coordinate",
            "Actual Cam 3 Formation","Actual Cam 3 Coordinate","Est Cam 3 Formation","Est Cam 3 Coordinate","Notes"
        ]

    # Combine keys
    all_keys = set(raw.keys()) | set(merged.keys())
    keys = sorted(all_keys, key=sort_key)

    with open(args.out_csv, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for key in keys:
            if key in merged:
                writer.writerow(merged[key])
            else:
                # construct a new row where "Actual..." fields blank, Estimated/PSET/evlivetime from raw
                c = raw[key]
                # Build row according to header positions used earlier:
                row = [
                    key[0],  # RUN
                    key[1],  # EVENT
                    "",  # Actual Bubble Count (blank)
                    c.get("Estimated Bubble Count", ""),  # Estimated Bubble Count
                    "",  # Source Type (blank)
                    c.get("PSET", ""),  # PSET
                    c.get("evlivetime", ""),  # evlivetime
                    "",  # Actual Cam 1 Formation
                    "",  # Actual Cam 1 Coordinate
                    c.get("Est Cam 1 Formation", ""),  # Est Cam 1 Formation
                    c.get("Est Cam 1 Coordinate", ""),  # Est Cam 1 Coordinate
                    "",  # Actual Cam 2 Formation
                    "",  # Actual Cam 2 Coordinate
                    c.get("Est Cam 2 Formation", ""),  # Est Cam 2 Formation
                    c.get("Est Cam 2 Coordinate", ""),  # Est Cam 2 Coordinate
                    "",  # Actual Cam 3 Formation
                    "",  # Actual Cam 3 Coordinate
                    c.get("Est Cam 3 Formation", ""),  # Est Cam 3 Formation (may be blank depending on CSV layout)
                    c.get("Est Cam 3 Coordinate", ""),  # Est Cam 3 Coordinate
                    "",  # Notes
                ]
                # Trim or pad to header length
                if len(row) < len(header):
                    row += [""] * (len(header) - len(row))
                writer.writerow(row[:len(header)])

if __name__ == "__main__":
    main()

