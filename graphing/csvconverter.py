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




```python
#!/usr/bin/env python3
"""
Combine CSVs and a single Excel sheet in a directory into one output CSV.

Usage:
    python combine_bubbles.py /path/to/directory output.csv

Assumptions & behavior (based on user's spec):
- The directory contains multiple CSV files and exactly one Excel file (.xls or .xlsx).
- Input CSVs have one row per event with columns:
    RUN, EVENT, Estimated Bubble Count, Est Cam 1 Formation, Est Cam 1 Coordinate,
    Est Cam 2 Formation, Est Cam 2 Coordinate, Est Cam 3 Coordinate, PSET, evlivetime
- Excel has rows that may start new events (with RUN and EVENT) or continue the previous event (empty RUN/EVENT).
  Excel columns include actual values for up to 3 bubbles per event (Actual Bubble Count and per-camera Actual Formation/Coordinate),
  plus Estimated Bubble Count (a single value), Est Cam X columns, Source Type, PSET, and Notes.
- Final output should expand events to one row per bubble (if Actual or Estimated counts >1) so each bubble has formation & coordinate fields.
- When actual data exists in Excel, use actual values; otherwise use values from CSVs for estimated fields.
- If Excel rows omit RUN/EVENT, they are continuations of previous event; they supply additional actual bubble rows.
- If actual bubble count is present, we use that to expand into multiple rows using per-bubble fields available across possibly multiple rows.
- For estimated-only events (no actual data), expand using Estimated Bubble Count from CSVs (or Excel if present) and use Est Cam fields.
- If fewer than 3 cameras' data exist for a bubble, leave fields blank.
- Script is defensive about missing columns and tries to match columns case-insensitively.

Outputs a CSV with columns (in order):
RUN, EVENT, Actual Bubble Count, Estimated Bubble Count, Source Type, PSET, evlivetime,
Actual Cam 1 Formation, Actual Cam 1 Coordinate, Est Cam 1 Formation, Est Cam 1 Coordinate,
Actual Cam 2 Formation, Actual Cam 2 Coordinate, Est Cam 2 Formation, Est Cam 2 Coordinate,
Actual Cam 3 Formation, Actual Cam 3 Coordinate, Est Cam 3 Formation, Est Cam 3 Coordinate, Notes
"""

import sys
import os
import glob
import csv
import pandas as pd
from collections import defaultdict

# Helper: case-insensitive column extraction
def col(df, name_variants):
    for n in name_variants:
        if n in df.columns:
            return df[n]
    # try case-insensitive match
    lname = [c.lower() for c in df.columns]
    for n in name_variants:
        if n.lower() in lname:
            return df[df.columns[lname.index(n.lower())]]
    return None

def pick_cell(row, names):
    for n in names:
        if n in row and pd.notna(row[n]):
            return row[n]
    # case-insensitive
    for k,v in row.items():
        for n in names:
            if k.lower() == n.lower() and pd.notna(v):
                return v
    return None

def norm(s):
    return "" if pd.isna(s) else str(s)

def expand_estimated_event(row_csv):
    # returns list of per-bubble dicts for estimated-only event from CSV row
    try:
        est_count = int(float(row_csv.get('Estimated Bubble Count') or row_csv.get('Estimated_Bubble_Count') or 0))
    except Exception:
        est_count = 0
    out = []
    for i in range(est_count if est_count>0 else 1):
        d = {
            'RUN': norm(row_csv.get('RUN') or row_csv.get('Run') or row_csv.get('run')),
            'EVENT': norm(row_csv.get('EVENT') or row_csv.get('Event') or row_csv.get('event')),
            'Actual Bubble Count': '',
            'Estimated Bubble Count': norm(est_count),
            'Source Type': '',
            'PSET': norm(row_csv.get('PSET') or row_csv.get('Pset') or row_csv.get('pset')),
            'evlivetime': norm(row_csv.get('evlivetime') or row_csv.get('evlifetime') or row_csv.get('evliTime')),
            'Actual Cam 1 Formation': '',
            'Actual Cam 1 Coordinate': '',
            'Est Cam 1 Formation': norm(row_csv.get('Est Cam 1 Formation') or row_csv.get('Est Cam 1 Formation'.replace(" ", "_")) or row_csv.get('Est Cam 1 Formation')),
            'Est Cam 1 Coordinate': norm(row_csv.get('Est Cam 1 Coordinate') or row_csv.get('Est Cam 1 Coordinate'.replace(" ", "_"))),
            'Actual Cam 2 Formation': '',
            'Actual Cam 2 Coordinate': '',
            'Est Cam 2 Formation': norm(row_csv.get('Est Cam 2 Formation') or row_csv.get('Est Cam 2 Formation'.replace(" ", "_"))),
            'Est Cam 2 Coordinate': norm(row_csv.get('Est Cam 2 Coordinate') or row_csv.get('Est Cam 2 Coordinate'.replace(" ", "_"))),
            'Actual Cam 3 Formation': '',
            'Actual Cam 3 Coordinate': '',
            'Est Cam 3 Formation': norm(row_csv.get('Est Cam 3 Formation') or row_csv.get('Est Cam 3 Formation'.replace(" ", "_"))),
            'Est Cam 3 Coordinate': norm(row_csv.get('Est Cam 3 Coordinate') or row_csv.get('Est Cam 3 Coordinate'.replace(" ", "_"))),
            'Notes': ''
        }
        out.append(d)
    return out

def main(directory, out_csv):
    # find files
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    excel_files = glob.glob(os.path.join(directory, "*.xls")) + glob.glob(os.path.join(directory, "*.xlsx"))
    if len(excel_files) == 0:
        print("No Excel file found in directory.", file=sys.stderr)
        sys.exit(1)
    if len(excel_files) > 1:
        print("More than one Excel file found. Please keep exactly one.", file=sys.stderr)
        sys.exit(1)
    excel_path = excel_files[0]

    # Read CSV files into dataframe list
    csv_rows = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, dtype=str, keep_default_na=False, na_values=[''])
        except Exception as e:
            print(f"Warning: failed to read CSV '{f}': {e}", file=sys.stderr)
            continue
        for _, r in df.iterrows():
            row = {c: (None if pd.isna(v) or v=="" else v) for c,v in r.items()}
            csv_rows.append(row)

    # Index CSV rows by (RUN, EVENT) for quick lookup using normalized keys
    csv_index = {}
    for r in csv_rows:
        run = (r.get('RUN') or r.get('Run') or r.get('run') or '').strip()
        event = (r.get('EVENT') or r.get('Event') or r.get('event') or '').strip()
        key = (run, event)
        csv_index[key] = r  # last-one-wins if duplicates

    # Read Excel
    try:
        xdf = pd.read_excel(excel_path, dtype=str, keep_default_na=False, na_values=[''])
    except Exception as e:
        print(f"Failed to read Excel file: {e}", file=sys.stderr)
        sys.exit(1)

    # We'll iterate excel rows; track current RUN/EVENT when blank
    results = []
    current_run = None
    current_event = None
    # Helper to extract fields with likely names
    def get_val(row, names):
        v = pick_cell(row, names)
        return None if v is None or v=="" else v

    # Pre-normalize column names for easier access
    xdf.columns = [c.strip() for c in xdf.columns]

    for _, r in xdf.iterrows():
        row = r.to_dict()
        # Determine if this row starts a new event
        run_val = get_val(row, ['RUN', 'Run', 'run'])
        event_val = get_val(row, ['EVENT', 'Event', 'event'])
        if run_val:
            current_run = str(run_val).strip()
        if event_val:
            current_event = str(event_val).strip()

        # If neither run nor event and no actual data -> skip row
        # But per spec continuation rows may have actual formation frames/coords
        # Extract actual bubble count if present
        actual_count_raw = get_val(row, ['Actual Bubble Count', 'Actual_Bubble_Count', 'Actual Bubble Count '])
        est_count_raw = get_val(row, ['Estimated Bubble Count', 'Estimated_Bubble_Count', 'Estimated Bubble Count '])
        source_type = get_val(row, ['Source Type', 'Source_Type', 'Source'])
        pset = get_val(row, ['PSET', 'Pset', 'pset'])
        notes = get_val(row, ['Notes', 'Note'])

        # Per-bubble actual fields may appear in separate rows. We'll collect actual bubble rows by grouping consecutive rows sharing RUN/EVENT (including continuation rows).
        # For each excel row we will create per-bubble records if this row contains actual formation/coordinate data (for any camera),
        # otherwise we'll rely on Actual Bubble Count to create placeholder rows later.
        # Identify actual per-camera fields in this row
        actual_cam_fields = {}
        for cam in (1,2,3):
            af = get_val(row, [f'Actual Cam {cam} Formation', f'Actual Cam {cam} Formation'.replace(" ", "_"), f'Actual Cam {cam} Formation'])
            ac = get_val(row, [f'Actual Cam {cam} Coordinate', f'Actual Cam {cam} Coordinate'.replace(" ", "_")])
            if af or ac:
                actual_cam_fields[cam] = (af or '', ac or '')

        # Identify estimated cam fields in this excel row (may be present)
        est_cam_fields = {}
        for cam in (1,2,3):
            ef = get_val(row, [f'Est Cam {cam} Formation', f'Est Cam {cam} Formation'.replace(" ", "_"), f'Est Cam {cam} Formation'])
            ec = get_val(row, [f'Est Cam {cam} Coordinate', f'Est Cam {cam} Coordinate'.replace(" ", "_")])
            if ef or ec:
                est_cam_fields[cam] = (ef or '', ec or '')

        # If the row contains any actual per-camera data, create a bubble row from it.
        if actual_cam_fields:
            # Build a row with available actual data; actual bubble count may be unspecified per row. We'll leave 'Actual Bubble Count' blank here (handled below).
            out = {
                'RUN': current_run or '',
                'EVENT': current_event or '',
                'Actual Bubble Count': actual_count_raw or '',
                'Estimated Bubble Count': est_count_raw or '',
                'Source Type': source_type or '',
                'PSET': pset or '',
                'evlivetime': '',  # excel may not have evlivetime; CSV does
                'Actual Cam 1 Formation': actual_cam_fields.get(1, ('',''))[0],
                'Actual Cam 1 Coordinate': actual_cam_fields.get(1, ('',''))[1],
                'Est Cam 1 Formation': est_cam_fields.get(1, ('',''))[0] if 1 in est_cam_fields else '',
                'Est Cam 1 Coordinate': est_cam_fields.get(1, ('',''))[1] if 1 in est_cam_fields else '',
                'Actual Cam 2 Formation': actual_cam_fields.get(2, ('',''))[0],
                'Actual Cam 2 Coordinate': actual_cam_fields.get(2, ('',''))[1],
                'Est Cam 2 Formation': est_cam_fields.get(2, ('',''))[0] if 2 in est_cam_fields else '',
                'Est Cam 2 Coordinate': est_cam_fields.get(2, ('',''))[1] if 2 in est_cam_fields else '',
                'Actual Cam 3 Formation': actual_cam_fields.get(3, ('',''))[0],
                'Actual Cam 3 Coordinate': actual_cam_fields.get(3, ('',''))[1],
                'Est Cam 3 Formation': est_cam_fields.get(3, ('',''))[0] if 3 in est_cam_fields else '',
                'Est Cam 3 Coordinate': est_cam_fields.get(3, ('',''))[1] if 3 in est_cam_fields else '',
                'Notes': notes or ''
            }
            results.append(out)
            continue

        # If no per-camera actual data but the row declares an Actual Bubble Count >0, we need to create that many placeholder bubble rows (actual cam fields empty)
        if actual_count_raw:
            try:
                actual_count = int(float(actual_count_raw))
            except Exception:
                actual_count = 0
            for i in range(actual_count if actual_count>0 else 1):
                out = {
                    'RUN': current_run or '',
                    'EVENT': current_event or '',
                    'Actual Bubble Count': str(actual_count),
                    'Estimated Bubble Count': est_count_raw or '',
                    'Source Type': source_type or '',
                    'PSET': pset or '',
                    'evlivetime': '',
                    'Actual Cam 1 Formation': '',
                    'Actual Cam 1 Coordinate': '',
                    'Est Cam 1 Formation': '',
                    'Est Cam 1 Coordinate': '',
                    'Actual Cam 2 Formation': '',
                    'Actual Cam 2 Coordinate': '',
                    'Est Cam 2 Formation': '',
                    'Est Cam 2 Coordinate': '',
                    'Actual Cam 3 Formation': '',
                    'Actual Cam 3 Coordinate': '',
                    'Est Cam 3 Formation': '',
                    'Est Cam 3 Coordinate': '',
                    'Notes': notes or ''
                }
                results.append(out)
            continue

        # If row had no actual info but has RUN/EVENT (start row) possibly with estimated fields, we won't create rows now — rely on CSV fallback later.
        # However, if this row contains estimated cam data and no matching CSV event row exists, we can use it to produce estimated rows.
        if (est_cam_fields or est_count_raw) and (current_run and current_event):
            try:
                est_count = int(float(est_count_raw)) if est_count_raw else 0
            except Exception:
                est_count = 0
            if est_count > 0:
                for i in range(est_count):
                    out = {
                        'RUN': current_run,
                        'EVENT': current_event,
                        'Actual Bubble Count': '',
                        'Estimated Bubble Count': str(est_count),
                        'Source Type': source_type or '',
                        'PSET': pset or '',
                        'evlivetime': '',
                        'Actual Cam 1 Formation': '',
                        'Actual Cam 1 Coordinate': '',
                        'Est Cam 1 Formation': est_cam_fields.get(1, ('',''))[0] if 1 in est_cam_fields else '',
                        'Est Cam 1 Coordinate': est_cam_fields.get(1, ('',''))[1] if 1 in est_cam_fields else '',
                        'Actual Cam 2 Formation': '',
                        'Actual Cam 2 Coordinate': '',
                        'Est Cam 2 Formation': est_cam_fields.get(2, ('',''))[0] if 2 in est_cam_fields else '',
                        'Est Cam 2 Coordinate': est_cam_fields.get(2, ('',''))[1] if 2 in est_cam_fields else '',
                        'Actual Cam 3 Formation': '',
                        'Actual Cam 3 Coordinate': '',
                        'Est Cam 3 Formation': est_cam_fields.get(3, ('',''))[0] if 3 in est_cam_fields else '',
                        'Est Cam 3 Coordinate': est_cam_fields.get(3, ('',''))[1] if 3 in est_cam_fields else '',
                        'Notes': notes or ''
                    }
                    results.append(out)
            # else skip
            continue

        # otherwise skip row (no useful data)
        continue

    # Now, for any CSV-only events that weren't covered by Excel actual rows, produce estimated expansions
    for key, crow in csv_index.items():
        run, event = key
        # Check if Excel produced any rows for this run/event
        produced = any((r['RUN']==run and r['EVENT']==event) for r in results)
        if not produced:
            # Expand estimated from CSV
            est_rows = expand_estimated_event(crow)
            # Fill Source Type and Notes blank, evlivetime may be present in csv rows
            for r in est_rows:
                r['Source Type'] = ''
                r['Notes'] = ''
                # ensure PSET and evlivetime come from CSV row if present
                r['PSET'] = r.get('PSET') or norm(crow.get('PSET') or crow.get('Pset') or crow.get('pset'))
                r['evlivetime'] = r.get('evlivetime') or norm(crow.get('evlivetime') or crow.get('evlifetime') or crow.get('evliTime'))
                results.append(r)

    # Finally, ensure required output columns and write CSV
    out_fields = [
        'RUN', 'EVENT', 'Actual Bubble Count', 'Estimated Bubble Count', 'Source Type', 'PSET', 'evlivetime',
        'Actual Cam 1 Formation', 'Actual Cam 1 Coordinate', 'Est Cam 1 Formation', 'Est Cam 1 Coordinate',
        'Actual Cam 2 Formation', 'Actual Cam 2 Coordinate', 'Est Cam 2 Formation', 'Est Cam 2 Coordinate',
        'Actual Cam 3 Formation', 'Actual Cam 3 Coordinate', 'Est Cam 3 Formation', 'Est Cam 3 Coordinate', 'Notes'
    ]

    # Write out
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in results:
            # ensure all keys exist
            outrow = {k: (row.get(k) or '') for k in out_fields}
            writer.writerow(outrow)

    print(f"Wrote {len(results)} rows to {out_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python combine_bubbles.py /path/to/directory output.csv", file=sys.stderr)
        sys.exit(1)
    directory = sys.argv[1]
    out_csv = sys.argv[2]
    main(directory, out_csv)


