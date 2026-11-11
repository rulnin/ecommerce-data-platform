"""Obtain the public Olist snapshot; never overwrite differing local CSVs."""

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
NAMES = (
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
)


def extract(archive, destination):
    hashes = {}
    with zipfile.ZipFile(archive) as bundle:
        if len(bundle.namelist()) != len(set(bundle.namelist())):
            raise ValueError("Archive contains duplicate member names")
        if sum(member.file_size for member in bundle.infolist()) > 512 * 1024**2:
            raise ValueError("Archive exceeds expanded size limit")
        # Verify every expected member and existing file before writing anything.
        for name in NAMES:
            with bundle.open(name) as stream:
                hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
            target = destination / name
            if target.exists():
                with target.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != hashes[name]:
                        raise ValueError(f"Existing file differs; preserved: {name}")
        destination.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            target = destination / name
            if not target.exists():
                # Only fixed filenames are extracted; archive paths are never trusted.
                with bundle.open(name) as source, target.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
    return hashes


def download(path):
    with requests.Session() as session:
        session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
            ),
        )
        with session.get(URL, stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            size = 0
            with path.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if size > 256 * 1024**2:
                        raise ValueError("Download exceeds archive size limit")
                    output.write(chunk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a locally downloaded Kaggle ZIP")
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--report", type=Path, default=Path("data/dataset-manifest.json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        archive = args.archive or Path(temporary) / "olist.zip"
        if args.archive is None:
            download(archive)
        hashes = extract(archive, args.output)
        with archive.open("rb") as stream:
            archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "source": URL,
                "archive_sha256": archive_hash,
                "files_sha256": hashes,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Verified {len(hashes)} CSVs; existing identical files preserved")


if __name__ == "__main__":
    main()
