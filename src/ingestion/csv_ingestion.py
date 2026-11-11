"""Stream CSV records in bounded batches; inspect without loading a database."""

import argparse
import csv
import json
from pathlib import Path


class CsvStructureError(ValueError):
    """An input violates the CSV structural contract."""

    def __init__(self, message, record_number=None):
        self.record_number = record_number
        super().__init__(message)


def iter_batches(path: Path, batch_size=1000, expected_columns=None):
    if not 1 <= batch_size <= 10000:
        raise ValueError("batch_size must be between 1 and 10000")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream, strict=True)
        columns = reader.fieldnames
        if not columns or any(not col for col in columns) or len(set(columns)) != len(columns):
            raise CsvStructureError("CSV requires a nonempty, unique header")
        if expected_columns is not None and columns != list(expected_columns):
            raise CsvStructureError("CSV header does not match source contract")
        batch = []
        try:
            for record_number, row in enumerate(reader, start=1):
                if None in row or any(value is None for value in row.values()):
                    raise CsvStructureError(
                        f"CSV field count mismatch at record {record_number}", record_number
                    )
                batch.append((record_number, row))
                if len(batch) == batch_size:
                    yield batch
                    batch = []
        except csv.Error:
            raise CsvStructureError(
                f"CSV parse error near physical line {reader.line_num}"
            ) from None
        if batch:
            yield batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    batches = rows = 0
    for batch in iter_batches(args.path, args.batch_size):
        batches += 1
        rows += len(batch)
    print(json.dumps({"rows": rows, "batches": batches, "batch_size": args.batch_size}))


if __name__ == "__main__":
    main()
