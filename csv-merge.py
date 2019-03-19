"""Merge multiple CSV files into a single CSV file.

Usage: csv-merge <ncols> <in-file-1> <in-file-2> ... <out-file>

Here 'ncols' specifies the no. of columns in the CSV file. The input
CSV files can use any delimiter, the output CSV file will be delimited
with the comma character.
"""

from __future__ import print_function

import sys
import csv


def sniff_delim(filename, ncols):
    for delim in ",;":
        with open(filename) as f:
            reader = csv.reader(f, delimiter=delim)
            row = reader.next()
            if len(row) == ncols:
                break
    else:
        print("csv-merge: unable to determine delimiter")
        sys.exit(1)

    return delim


def read_rows(filename, ncols):
    delim = sniff_delim(filename, ncols)

    with open(filename) as f:
        reader = csv.reader(f, delimiter=delim, quotechar='"')
        rows = list(reader)

    return rows


def csv_merge(ncols, in_filenames, out_filename):
    out_filename = sys.argv[-1]

    with open(out_filename, "w") as outfile:
        writer = csv.writer(outfile, dialect="excel")
        for filename in in_filenames:
            rows = read_rows(filename, ncols)
            writer.writerows(rows)
        

def main():
    if len(sys.argv) < 4:
        print("Usage: csv-merge <ncols> <in-file-1> <in-file-2> ... <out-file>",
              file=sys.stderr)
        sys.exit(1)
    
    ncols = int(sys.argv[1])
    out_filename = sys.argv[-1]
    in_filenames = sys.argv[2:-1]

    csv_merge(ncols, in_filenames, out_filename)


if __name__ == "__main__":
    main()
