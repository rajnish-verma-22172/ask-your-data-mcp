import pytest

from ask_your_data_mcp.engine import parse_csv, query_dataset, summarize_dataset


CSV = """month,category,amount
2026-10,Food,120.50
2026-10,Travel,40
2026-09,Food,80
"""


def test_load_and_summarize_dataset():
    dataset = parse_csv(CSV, "expenses")

    assert summarize_dataset(dataset) == {
        "dataset": "expenses",
        "row_count": 3,
        "columns": ["month", "category", "amount"],
        "sample_rows": [
            {"month": "2026-10", "category": "Food", "amount": "120.50"},
            {"month": "2026-10", "category": "Travel", "amount": "40"},
            {"month": "2026-09", "category": "Food", "amount": "80"},
        ],
    }


def test_filter_and_sum_by_group():
    result = query_dataset(
        parse_csv(CSV),
        filters=[{"column": "month", "operator": "eq", "value": "2026-10"}],
        group_by="category",
        aggregation="sum",
        column="amount",
    )

    assert result["matched_rows"] == 2
    assert result["groups"] == [
        {"category": "Food", "sum": 120.5},
        {"category": "Travel", "sum": 40},
    ]


def test_filter_numeric_values_and_aggregate_average():
    result = query_dataset(
        parse_csv(CSV),
        filters=[{"column": "amount", "operator": "gt", "value": "100"}],
        aggregation="avg",
        column="amount",
    )

    assert result["groups"] == [{"avg": 120.5}]


@pytest.mark.parametrize(
    ("alias", "expected_key", "expected_value"),
    [
        ("average", "avg", 240.5 / 3),
        ("mean", "avg", 240.5 / 3),
        ("total", "sum", 240.5),
    ],
)
def test_aggregation_aliases(alias, expected_key, expected_value):
    result = query_dataset(parse_csv(CSV), aggregation=alias, column="amount")

    assert result["groups"] == [{expected_key: expected_value}]


def test_min_and_max_return_numeric_values_for_numeric_columns():
    dataset = parse_csv("category,amount\nFood,3240\nBills,1400\nTransport,820\n")

    minimum = query_dataset(dataset, aggregation="min", column="amount")
    maximum = query_dataset(dataset, aggregation="max", column="amount")

    assert minimum["groups"] == [{"min": 820}]
    assert maximum["groups"] == [{"max": 3240}]
    assert isinstance(minimum["groups"][0]["min"], int)
    assert isinstance(maximum["groups"][0]["max"], int)


def test_min_and_max_preserve_text_for_non_numeric_columns():
    dataset = parse_csv("category\nFood\nBills\nTransport\n")

    minimum = query_dataset(dataset, aggregation="min", column="category")
    maximum = query_dataset(dataset, aggregation="max", column="category")

    assert minimum["groups"] == [{"min": "Bills"}]
    assert maximum["groups"] == [{"max": "Transport"}]


def test_rejects_invalid_csv_and_unknown_column():
    with pytest.raises(ValueError, match="unique"):
        parse_csv("value,value\n1,2\n")

    with pytest.raises(ValueError, match="Unknown column"):
        query_dataset(parse_csv(CSV), group_by="missing", aggregation="count")


def test_rejects_non_numeric_aggregation():
    with pytest.raises(ValueError, match="non-numeric"):
        query_dataset(
            parse_csv(CSV),
            aggregation="sum",
            column="category",
        )
