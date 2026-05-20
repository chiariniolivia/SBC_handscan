# a single argument, which is a directory that will contain csv files and a single excel spreadsheet 

# take in all csv files  
"""
input csv formats:
RUN - EVENT - Estimated Bubble Count - Est Cam 1 Formation - Est Cam 1 Coordinate - Est Cam 2 Formation - Est Cam 2 Coordinate - Est Cam 3 Coordinate - PSET - evlivetime
"""
# all of this data is taken and used for the final output csv, and each row has a new event



# take in excel format
"""
Input excel format
RUN - EVENT - Actual Bubble Count - Estimated Bubble Count - Actual Cam 1 Formation - Actual Cam 1 Coordinate - Actual Cam 2 Formation - Actual Cam 2 Coordinate - Actual Cam 3 Formation - Actual Cam 3 Coordinate - Est Cam 1 Formation - Est Cam 1 Coordinate - Est Cam 2 Formation - Est Cam 2 Coordinate - Est Cam 3 Formation - Est Cam 3 Coordinate -  Source Type - PSET - Notes 

"""
# only the actual values here should be used in the final output, as well as the source type and notes
## an important note, in this excel sheet not every row is a new event. if a row is a continuation of a previous row, it will have no event or run entry but will have actual formation frames and coordinates 
## this should be continued in the final output, so if a run event pair has an actual bubble count or estimated bubble count of 3, it should take up 3 rows so each bubble can have its formation frame and coordinates in each camera.


# combine data into an output csv
"""

final output csv format:

RUN - EVENT - Actual Bubble Count - Estimated Bubble Count - Source Type - PSET - evlivetime - Actual Cam 1 Formation - Actual Cam 1 Coordinate - Est Cam 1 Formation - Est Cam 1 Coordinate - Actual Cam 2 Formation - Actual Cam 2 Coordinate - Est Cam 2 Formation - Est Cam 2 Coordinate - Actual Cam 3 Formation - Actual Cam 3 Coordinate - Est Cam 3 Formation - Est Cam 3 Coordinate - Notes
"""
#!/usr/bin/env python3
import sys
import os
import glob
import csv
import argparse
from decimal import Decimal
try:
    import pandas as pd
except ImportError:
    print("Install: pip install pandas openpyxl")
    sys.exit(1)

def norm(val):
    if pd.isna(val):
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

def clean(v):
    if v is None:
        return ""
    try:
        import math
        if isinstance(v, float) and math.isnan(v):
            return ""
    except Exception:
        pass
    s = str(v)
    if s.strip().lower() in ("nan", "none", "nan.0"):
        return ""
    return s

def read_all_csvs(dirpath):
    csv_files = [p for p in glob.glob(os.path.join(dirpath, "*.csv")) if os.path.isfile(p)]
    data = {}
    for path in csv_files:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                hdr = next(reader)
            except StopIteration:
                continue
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue
                # pad to at least 11 columns (indices 0..10)
                while len(row) < 11:
                    row.append("")
                run = norm(row[0])
                event = norm(row[1])
                key = (run, event)
                # Explicit mapping assuming CSV actually has 11 columns
                data[key] = {
                    "Estimated Bubble Count": row[2],
                    "Est Cam 1 Formation": row[3],
                    "Est Cam 1 Coordinate": row[4],
                    "Est Cam 2 Formation": row[5],
                    "Est Cam 2 Coordinate": row[6],
                    "Est Cam 3 Formation": row[7],
                    "Est Cam 3 Coordinate": row[8],
                    "PSET": row[9],
                    "evlivetime": row[10],
                }
    return data

def read_single_excel(dirpath):
    files = glob.glob(os.path.join(dirpath, "*.xls")) + glob.glob(os.path.join(dirpath, "*.xlsx"))
    if not files:
        raise FileNotFoundError("No Excel file found")
    excel_path = files[0]
    df = pd.read_excel(excel_path, header=None, skiprows=2, engine="openpyxl")
    expected = 19
    if df.shape[1] < expected:
        for i in range(df.shape[1], expected):
            df[i] = ""
    df = df.iloc[:, :expected]
    cols = [
        "RUN","EVENT","Actual Bubble Count","Estimated Bubble Count (excel)",
        "Actual Cam 1 Formation","Actual Cam 1 Coordinate",
        "Actual Cam 2 Formation","Actual Cam 2 Coordinate",
        "Actual Cam 3 Formation","Actual Cam 3 Coordinate",
        "Est Cam 1 Formation (excel)","Est Cam 1 Coordinate (excel)",
        "Est Cam 2 Formation (excel)","Est Cam 2 Coordinate (excel)",
        "Est Cam 3 Formation (excel)","Est Cam 3 Coordinate (excel)",
        "Source Type","PSET (excel)","Notes"
    ]
    df.columns = cols
    df["RUN"] = df["RUN"].ffill()
    df["EVENT"] = df["EVENT"].ffill()
    data = {}
    for _, r in df.iterrows():
        run = norm(r["RUN"])
        event = norm(r["EVENT"])
        if run == "" or event == "":
            continue
        key = (run, event)
        data[key] = {
            "Actual Bubble Count": r["Actual Bubble Count"],
            "Actual Cam 1 Formation": r["Actual Cam 1 Formation"],
            "Actual Cam 1 Coordinate": r["Actual Cam 1 Coordinate"],
            "Actual Cam 2 Formation": r["Actual Cam 2 Formation"],
            "Actual Cam 2 Coordinate": r["Actual Cam 2 Coordinate"],
            "Actual Cam 3 Formation": r["Actual Cam 3 Formation"],
            "Actual Cam 3 Coordinate": r["Actual Cam 3 Coordinate"],
            "Source Type": r["Source Type"],
            "PSET (excel)": r["PSET (excel)"],
            "Notes": r["Notes"],
        }
    return data

def merge_and_write(csv_data, excel_data, out_path):
    header = [
        "RUN","EVENT","Actual Bubble Count","Estimated Bubble Count","Source Type","PSET","evlivetime",
        "Actual Cam 1 Formation","Actual Cam 1 Coordinate","Est Cam 1 Formation","Est Cam 1 Coordinate",
        "Actual Cam 2 Formation","Actual Cam 2 Coordinate","Est Cam 2 Formation","Est Cam 2 Coordinate",
        "Actual Cam 3 Formation","Actual Cam 3 Coordinate","Est Cam 3 Formation","Est Cam 3 Coordinate","Notes"
    ]
    keys = sorted(k for k in csv_data.keys() if k in excel_data)
    with open(out_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for key in keys:
            run, event = key
            c = csv_data[key]
            e = excel_data[key]
            pset_candidate = clean(c.get("PSET", ""))
            if pset_candidate == "":
                pset_candidate = clean(e.get("PSET (excel)", ""))
            row = [
                run,
                event,
                clean(e.get("Actual Bubble Count", "")),
                clean(c.get("Estimated Bubble Count", "")),
                clean(e.get("Source Type", "")),
                pset_candidate,
                clean(c.get("evlivetime", "")),
                clean(e.get("Actual Cam 1 Formation", "")),
                clean(e.get("Actual Cam 1 Coordinate", "")),
                clean(c.get("Est Cam 1 Formation", "")),
                clean(c.get("Est Cam 1 Coordinate", "")),
                clean(e.get("Actual Cam 2 Formation", "")),
                clean(e.get("Actual Cam 2 Coordinate", "")),
                clean(c.get("Est Cam 2 Formation", "")),
                clean(c.get("Est Cam 2 Coordinate", "")),
                clean(e.get("Actual Cam 3 Formation", "")),
                clean(e.get("Actual Cam 3 Coordinate", "")),
                clean(c.get("Est Cam 3 Formation", "")),
                clean(c.get("Est Cam 3 Coordinate", "")),
                clean(e.get("Notes", "")),
            ]
            writer.writerow(row[:len(header)])
    return len(keys)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("dir")
    p.add_argument("out")
    args = p.parse_args()
    if not os.path.isdir(args.dir):
        print("Directory not found")
        sys.exit(1)
    csv_data = read_all_csvs(args.dir)
    excel_data = read_single_excel(args.dir)
    matched = merge_and_write(csv_data, excel_data, args.out)
    print(f"Merged {matched} rows to {args.out}")

if __name__ == "__main__":
    main()

