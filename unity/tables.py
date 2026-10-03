#!/usr/bin/env python3
"""The game tables of Saint Seiya Rebirth (`config/config.fassets`: one TextAsset per table).

Each table is a TSV with three header rows: value types (STR, INT, UINT, FLOAT, DOUBLE, STRARR,
INTARR, STRARR2, INTARR2, FLOATARR, DOUBLEARR, VECTOR...), Chinese column names, English keys;
then one row per record. Arrays use `+` between items and `|` between rows of a 2D array.

usage: tables.py TXT_DIR OUT_DIR        every TABLE.txt -> OUT_DIR/TABLE.json (list of records)
                                        and OUT_DIR/_columns.json ({table: [[key, chinese, type]]})
"""
import json
import os
import sys

INT_TYPES = {'INT', 'UINT', 'LONG'}
FLOAT_TYPES = {'FLOAT', 'DOUBLE'}


def convert_value(value, kind):
    """One cell by its declared type; unknown types stay strings."""
    if value == '':
        if kind in INT_TYPES | FLOAT_TYPES:
            return None
        return [] if kind.endswith('ARR') or kind.endswith('ARR2') else ''
    if kind in INT_TYPES:
        try:
            return int(value)
        except ValueError:
            return value
    if kind in FLOAT_TYPES:
        try:
            return float(value)
        except ValueError:
            return value
    if kind.endswith('ARR2'):
        base = kind[:-4]
        return [[convert_value(v, base) for v in row.split('+')] for row in value.split('|')]
    if kind.endswith('ARR'):
        base = kind[:-3]
        return [convert_value(v, base) for v in value.split('+')]
    return value


def parse_table(text):
    """-> (columns [[key, chinese, type]], records [dict])."""
    lines = [line.rstrip('\r\n') for line in text.split('\n')]
    while lines and lines[-1] == '':
        lines.pop()
    if len(lines) < 3:
        return [], []
    types = lines[0].split('\t')
    chinese = lines[1].split('\t')
    keys = lines[2].split('\t')
    width = len(keys)
    columns = [[keys[i], chinese[i] if i < len(chinese) else '', types[i] if i < len(types) else 'STR']
               for i in range(width) if keys[i] != '']
    records = []
    for line in lines[3:]:
        if line == '' or line.startswith('//'):
            continue
        cells = line.split('\t')
        rec = {}
        for i in range(width):
            if keys[i] == '':
                continue
            kind = types[i] if i < len(types) else 'STR'
            rec[keys[i]] = convert_value(cells[i] if i < len(cells) else '', kind)
        records.append(rec)
    return columns, records


def convert_dir(txt_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    all_columns = {}
    n = 0
    for name in sorted(os.listdir(txt_dir)):
        if not name.endswith('.txt'):
            continue
        with open(os.path.join(txt_dir, name), encoding='utf-8', errors='replace') as f:
            text = f.read()
        if '\t' not in text.split('\n', 1)[0]:
            continue  # not a table (LanguagePackage, help texts...)
        columns, records = parse_table(text)
        if not columns:
            continue
        table = name[:-4]
        all_columns[table] = columns
        with open(os.path.join(out_dir, table + '.json'), 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=0)
        n += 1
    with open(os.path.join(out_dir, '_columns.json'), 'w', encoding='utf-8') as f:
        json.dump(all_columns, f, ensure_ascii=False, indent=1)
    return n


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    n = convert_dir(argv[0], argv[1])
    print(f'{n} tables -> {argv[1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
