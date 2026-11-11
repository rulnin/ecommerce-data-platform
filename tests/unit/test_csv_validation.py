import pytest

from src.ingestion.csv_pipeline import CONTRACTS, RejectedRow, encode


def item(price="1.00"):
    row = dict.fromkeys(CONTRACTS["order_items"]["columns"], "value")
    row.update(order_id="order", order_item_id="1", price=price, freight_value="0")
    return row


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1", "private-invalid-value", ""])
def test_amount_rejection_does_not_expose_input(amount):
    with pytest.raises(RejectedRow) as error:
        encode("order_items", 7, item(amount))
    assert error.value.record == 7
    assert error.value.field == "price"
    assert error.value.code == "invalid_nonnegative_amount"
    assert "private-invalid-value" not in str(error.value)


def test_business_key_stays_stable_for_changed_values():
    first = encode("order_items", 1, item("1"))
    changed = encode("order_items", 1, item("2"))
    assert first[0] == changed[0]
    assert first[2] != changed[2]
    row = item()
    row["order_id"] = ""
    with pytest.raises(RejectedRow, match="empty_business_key"):
        encode("order_items", 1, row)


def test_review_versions_preserved_and_hash_ignores_column_order():
    row = dict.fromkeys(CONTRACTS["order_reviews"]["columns"], "value")
    first = encode("order_reviews", 1, row)
    assert first == encode("order_reviews", 2, dict(reversed(list(row.items()))))
    row["review_comment_message"] = "changed"
    assert first[0] != encode("order_reviews", 1, row)[0]
