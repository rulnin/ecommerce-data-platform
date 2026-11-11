# Data provenance and attribution

**Brazilian E-Commerce Public Dataset by Olist**, provided by Olist and published
on [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). The publisher
lists **CC BY-NC-SA 4.0** (checked 2026-11-11). Attribute the dataset, link the license,
identify adaptations, and retain its noncommercial/share-alike terms when reusing
or distributing adapted data. See the [Creative Commons license deed](https://creativecommons.org/licenses/by-nc-sa/4.0/).

Dataset-derived aggregate tables in analytics-results.md and analytics-results.json
are attributed to Olist and distributed under CC BY-NC-SA 4.0. Changes include
string-to-type conversion, status filtering, grouping, calculations and anonymous
seller ranking. Olist does not endorse this project. This notice identifies data
terms; it does not assign a license to unrelated project source code.

Raw CSVs, database dumps and credentials are not included in Git. Download sources
from the publisher and compare the nine SHA-256 hashes in dataset-manifest.json.
The downloader preserves identical files and refuses to overwrite changed ones.
The snapshot is historical/anonymized; it is not current Olist business activity.
The reports contain aggregate results rather than reviews or customer identifiers.

FX comes from the [Frankfurter API](https://frankfurter.dev/) with the fixed ECB
provider. Actual observation date/direction/freshness are retained; provider data
terms remain applicable. See [FX contract and upstream references](fx-contract.md).
This repository does not claim that the data inherits the API implementation's
software license or that sparse cached rates form complete historical coverage.

Inventory and movements are generated synthetic demo data linked to valid public
product IDs. They are not supplied by Olist and are not real commercial stock.
Only public and synthetic sources are used; no employer/company/private datasets
or proprietary SQL assets are part of this portfolio.
