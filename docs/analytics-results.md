# E-commerce analytics — verified snapshot

[Findings and interpretation](analytics.md) · [Documentation](README.md)

Generated 2026-11-12T03:56:45.188263+00:00; publication `287970dd-9369-4f4b-96db-78bdc9d6c6dd`.

Historical Olist snapshot, not a current trading dashboard. All financial values are BRL unless named USD. Revenue proxy = delivered-order item prices, excluding freight, refunds and fees. Payments are independent tender amounts. SQL runs in one read-only repeatable-read transaction.

Derived aggregate results: attribution to [Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Changes: typed joins, status filters, grouping and calculations. No endorsement implied.

The first/last months are partial snapshot periods. Category/seller order counts are not additive across groups. Repeat-buyer share is snapshot-wide, not cohort retention or customer lifetime value. USD totals are partial coverage only.

## What are the snapshot volume and delivered item value?

[Reproduce this SQL](../sql/analytics/01_overview.sql)

| first_purchase_date | last_purchase_date | orders | items | payment_entries | all_status_item_value_brl | delivered_item_value_brl | freight_brl | payment_value_brl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016-09-04 | 2018-10-17 | 99,441 | 112,650 | 103,886 | 13,591,643.70 | 13,221,498.11 | 2,251,909.54 | 16,008,872.12 |

## How do delivered sales vary by purchase month?

[Reproduce this SQL](../sql/analytics/02_monthly_sales.sql)

| purchase_month | all_status_orders | delivered_item_value_brl | delivered_orders | item_value_per_delivered_order_brl |
| --- | --- | --- | --- | --- |
| 2016-09-01 | 4 | 134.97 | 1 | 134.97 |
| 2016-10-01 | 324 | 40,325.11 | 265 | 152.17 |
| 2016-11-01 | 0 | 0 | 0 | — |
| 2016-12-01 | 1 | 10.90 | 1 | 10.90 |
| 2017-01-01 | 800 | 111,798.36 | 750 | 149.06 |
| 2017-02-01 | 1,780 | 234,223.40 | 1653 | 141.70 |
| 2017-03-01 | 2,682 | 359,198.85 | 2546 | 141.08 |
| 2017-04-01 | 2,404 | 340,669.68 | 2303 | 147.92 |
| 2017-05-01 | 3,700 | 489,338.25 | 3546 | 138.00 |
| 2017-06-01 | 3,245 | 421,923.37 | 3135 | 134.58 |
| 2017-07-01 | 4,026 | 481,604.52 | 3872 | 124.38 |
| 2017-08-01 | 4,331 | 554,699.70 | 4193 | 132.29 |
| 2017-09-01 | 4,285 | 607,399.67 | 4150 | 146.36 |
| 2017-10-01 | 4,631 | 648,247.65 | 4478 | 144.76 |
| 2017-11-01 | 7,544 | 987,765.37 | 7289 | 135.51 |
| 2017-12-01 | 5,673 | 726,033.19 | 5513 | 131.69 |
| 2018-01-01 | 7,269 | 924,645.00 | 7069 | 130.80 |
| 2018-02-01 | 6,728 | 826,437.13 | 6555 | 126.08 |
| 2018-03-01 | 7,211 | 953,356.25 | 7003 | 136.14 |
| 2018-04-01 | 6,939 | 973,534.09 | 6798 | 143.21 |
| 2018-05-01 | 6,873 | 977,544.69 | 6749 | 144.84 |
| 2018-06-01 | 6,167 | 856,077.86 | 6099 | 140.36 |
| 2018-07-01 | 6,292 | 867,953.46 | 6159 | 140.92 |
| 2018-08-01 | 6,512 | 838,576.64 | 6351 | 132.04 |
| 2018-09-01 | 16 | 0 | 0 | — |
| 2018-10-01 | 4 | 0 | 0 | — |

## Which categories contribute the most delivered item value?

[Reproduce this SQL](../sql/analytics/03_top_categories.sql)

| category | delivered_items | delivered_orders | delivered_item_value_brl | share_pct |
| --- | --- | --- | --- | --- |
| health_beauty | 9465 | 8647 | 1,233,131.72 | 9.33 |
| watches_gifts | 5859 | 5495 | 1,166,176.98 | 8.82 |
| bed_bath_table | 10953 | 9272 | 1,023,434.76 | 7.74 |
| sports_leisure | 8431 | 7530 | 954,852.55 | 7.22 |
| computers_accessories | 7644 | 6530 | 888,724.61 | 6.72 |
| furniture_decor | 8160 | 6307 | 711,927.69 | 5.38 |
| housewares | 6795 | 5743 | 615,628.69 | 4.66 |
| cool_stuff | 3718 | 3559 | 610,204.10 | 4.62 |
| auto | 4140 | 3810 | 578,966.65 | 4.38 |
| toys | 4030 | 3804 | 471,286.48 | 3.56 |

## Which buyer states contribute delivered item value?

[Reproduce this SQL](../sql/analytics/04_buyer_states.sql)

| buyer_state | delivered_orders | delivered_item_value_brl |
| --- | --- | --- |
| SP | 40501 | 5,067,633.16 |
| RJ | 12350 | 1,759,651.13 |
| MG | 11354 | 1,552,481.83 |
| RS | 5345 | 728,897.47 |
| PR | 4923 | 666,063.51 |
| SC | 3546 | 507,012.13 |
| BA | 3256 | 493,584.14 |
| DF | 2080 | 296,498.41 |
| GO | 1957 | 282,836.70 |
| ES | 1995 | 268,643.45 |
| PE | 1593 | 251,889.49 |
| CE | 1279 | 219,757.38 |
| PA | 946 | 174,470.59 |
| MT | 886 | 152,191.62 |
| MA | 717 | 117,009.38 |
| MS | 701 | 115,429.97 |
| PB | 517 | 112,586.82 |
| PI | 476 | 84,721.00 |
| RN | 474 | 82,105.66 |
| AL | 397 | 78,855.72 |
| SE | 335 | 56,574.19 |
| TO | 274 | 48,402.51 |
| RO | 243 | 45,682.76 |
| AM | 145 | 22,155.84 |
| AC | 80 | 15,930.97 |
| AP | 67 | 13,374.81 |
| RR | 41 | 7,057.47 |

## How are tender amounts distributed by payment type?

[Reproduce this SQL](../sql/analytics/05_payment_mix.sql)

| payment_type | payment_entries | payment_value_brl | value_share_pct |
| --- | --- | --- | --- |
| credit_card | 76795 | 12,542,084.19 | 78.34 |
| boleto | 19784 | 2,869,361.27 | 17.92 |
| voucher | 5775 | 379,436.87 | 2.37 |
| debit_card | 1529 | 217,989.79 | 1.36 |
| not_defined | 3 | 0.00 | 0.00 |

## What fraction of people have repeat delivered orders?

[Reproduce this SQL](../sql/analytics/06_repeat_buyers.sql)

| delivered_buyers | delivered_orders | repeat_buyers | repeat_buyer_pct |
| --- | --- | --- | --- |
| 93358 | 96,478 | 2801 | 3.00 |

## Which anonymous seller ranks contribute the most sales?

[Reproduce this SQL](../sql/analytics/07_top_sellers.sql)

| seller_rank | seller_state | delivered_items | delivered_orders | delivered_item_value_brl | share_pct |
| --- | --- | --- | --- | --- | --- |
| 1 | SP | 1148 | 1124 | 226,987.93 | 1.72 |
| 2 | BA | 400 | 348 | 217,940.44 | 1.65 |
| 3 | SP | 1949 | 1772 | 196,882.12 | 1.49 |
| 4 | SP | 579 | 578 | 190,917.14 | 1.44 |
| 5 | SP | 1355 | 973 | 186,570.05 | 1.41 |
| 6 | SP | 322 | 319 | 165,981.49 | 1.26 |
| 7 | SP | 1548 | 1311 | 159,816.87 | 1.21 |
| 8 | SP | 1155 | 1145 | 139,658.69 | 1.06 |
| 9 | SP | 1420 | 910 | 138,208.56 | 1.05 |
| 10 | SP | 1472 | 1261 | 131,836.71 | 1.00 |

## How much of the snapshot has stored historical FX coverage?

[Reproduce this SQL](../sql/analytics/08_fx_coverage.sql)

| calendar_days | covered_days | covered_orders | total_orders | order_coverage_pct | covered_item_value_brl | uncovered_item_value_brl | partial_all_status_item_value_usd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 774 | 8 | 3,714 | 99,441 | 3.73 | 465,842.11 | 13,125,801.59 | 144,161.08 |
