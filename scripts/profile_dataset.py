"""Profile local Olist snapshots without third-party dependencies or row samples."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

KEYS = {
    "olist_customers_dataset": ["customer_id"],
    "olist_orders_dataset": ["order_id"],
    "olist_order_items_dataset": ["order_id", "order_item_id"],
    "olist_order_payments_dataset": ["order_id", "payment_sequential"],
    "olist_order_reviews_dataset": ["review_id"],
    "olist_products_dataset": ["product_id"],
    "olist_sellers_dataset": ["seller_id"],
    "product_category_name_translation": ["product_category_name"],
    "olist_geolocation_dataset": [],
}
RELATIONS = [
    ("olist_orders_dataset", "customer_id", "olist_customers_dataset", "customer_id"),
    ("olist_order_items_dataset", "order_id", "olist_orders_dataset", "order_id"),
    ("olist_order_items_dataset", "product_id", "olist_products_dataset", "product_id"),
    ("olist_order_items_dataset", "seller_id", "olist_sellers_dataset", "seller_id"),
    ("olist_order_payments_dataset", "order_id", "olist_orders_dataset", "order_id"),
    ("olist_order_reviews_dataset", "order_id", "olist_orders_dataset", "order_id"),
    (
        "olist_products_dataset",
        "product_category_name",
        "product_category_name_translation",
        "product_category_name",
    ),
]


def profile(directory):
    tables = {}
    values = {}
    for name, keys in KEYS.items():
        path = directory / f"{name}.csv"
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames
            if not columns or len(columns) != len(set(columns)):
                raise ValueError(f"Invalid header: {path.name}")
            nulls = dict.fromkeys(columns, 0)
            seen = set()
            seen_rows = set()
            duplicate_rows = 0
            duplicate_keys = null_keys = count = 0
            tracked = {col for child, col, parent, pcol in RELATIONS if child == name}
            tracked.update(pcol for child, col, parent, pcol in RELATIONS if parent == name)
            values[name] = {col: set() for col in tracked}
            for row in reader:
                count += 1
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"Malformed CSV: {path.name}, record {count}")
                for col in columns:
                    nulls[col] += row[col] == ""
                # Hash canonical parsed field values, including quoted newlines.
                row_hash = hashlib.sha256(
                    json.dumps(
                        [row[col] for col in columns],
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).digest()
                duplicate_rows += row_hash in seen_rows
                seen_rows.add(row_hash)
                if keys:
                    key = tuple(row[col] for col in keys)
                    null_keys += any(value == "" for value in key)
                    duplicate_keys += key in seen
                    seen.add(key)
                for col in tracked:
                    if row[col] != "":
                        values[name][col].add(row[col])
        tables[name] = {
            "sha256": digest,
            "rows": count,
            "columns": columns,
            "empty_fields": nulls,
            "candidate_key": keys,
            "duplicate_key_rows": duplicate_keys if keys else None,
            "empty_key_rows": null_keys if keys else None,
            "exact_duplicate_rows": duplicate_rows,
        }
    relationships = []
    for child, col, parent, pcol in RELATIONS:
        relationships.append(
            {
                "child": f"{child}.{col}",
                "parent": f"{parent}.{pcol}",
                "unmatched_distinct_nonempty_values": len(
                    values[child][col] - values[parent][pcol]
                ),
            }
        )
    return {"tables": tables, "relationships": relationships}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("docs/source-profile.json"))
    args = parser.parse_args()
    result = profile(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for name, table in result["tables"].items():
        print(f"{name}: rows={table['rows']}, duplicate_key_rows={table['duplicate_key_rows']}")
    for relation in result["relationships"]:
        print(
            f"{relation['child']} -> {relation['parent']}: unmatched={relation['unmatched_distinct_nonempty_values']}"
        )


if __name__ == "__main__":
    main()
