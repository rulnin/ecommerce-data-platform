import csv
import tempfile
import unittest
from pathlib import Path

from scripts.profile_dataset import KEYS, RELATIONS, profile


class ProfileTests(unittest.TestCase):
    def test_duplicates_empty_fields_and_missing_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, keys in KEYS.items():
                columns = set(keys)
                for child, col, parent, pcol in RELATIONS:
                    if name == child:
                        columns.add(col)
                    if name == parent:
                        columns.add(pcol)
                columns.add("optional")
                with (root / f"{name}.csv").open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=sorted(columns))
                    writer.writeheader()
                    row = dict.fromkeys(columns, "known")
                    row["optional"] = ""
                    if name == "olist_orders_dataset":
                        row["customer_id"] = "missing"
                    writer.writerow(row)
                    writer.writerow(row)
            result = profile(root)
            orders = result["tables"]["olist_orders_dataset"]
            self.assertEqual(orders["rows"], 2)
            self.assertEqual(orders["duplicate_key_rows"], 1)
            self.assertEqual(orders["exact_duplicate_rows"], 1)
            self.assertEqual(orders["empty_fields"]["optional"], 2)
            self.assertEqual(result["relationships"][0]["unmatched_distinct_nonempty_values"], 1)


if __name__ == "__main__":
    unittest.main()
