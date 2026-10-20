"""CSV loading, filtering, grouping, and aggregation."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_ROWS = 100_000
ALLOWED_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "contains"}
AGGREGATION_ALIASES = {
    "average": "avg",
    "mean": "avg",
    "total": "sum",
}
ALLOWED_AGGREGATIONS = {"count", "sum", "avg", "min", "max", *AGGREGATION_ALIASES}


@dataclass(frozen=True)
class Dataset:
    name: str
    columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def parse_csv(csv_text: str, name: str = "dataset") -> Dataset:
    if not csv_text.strip():
        raise ValueError("CSV content must not be empty.")
    if len(csv_text.encode("utf-8")) > MAX_CSV_BYTES:
        raise ValueError(f"CSV content exceeds the {MAX_CSV_BYTES}-byte limit.")

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("CSV must include a header row.")

    columns = tuple(header.strip() for header in reader.fieldnames)
    if any(not column for column in columns):
        raise ValueError("CSV headers must not be empty.")
    if len(set(columns)) != len(columns):
        raise ValueError("CSV headers must be unique.")

    rows: list[dict[str, str]] = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"CSV row {line_number} has more values than the header.")
        if any(value is None for value in row.values()):
            raise ValueError(f"CSV row {line_number} has fewer values than the header.")
        rows.append(
            {
                columns[index]: (value or "").strip()
                for index, value in enumerate(row.values())
            }
        )
        if len(rows) > MAX_ROWS:
            raise ValueError(f"CSV exceeds the {MAX_ROWS}-row limit.")

    if not rows:
        raise ValueError("CSV must contain at least one data row.")

    return Dataset(name=name.strip() or "dataset", columns=columns, rows=tuple(rows))


def query_dataset(
    dataset: Dataset,
    filters: list[dict[str, str]] | None = None,
    group_by: str | None = None,
    aggregation: str | None = None,
    column: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000.")
    _require_column(dataset, group_by)

    for rule in filters or []:
        filter_column = rule.get("column")
        operator = rule.get("operator")
        if filter_column not in dataset.columns:
            raise ValueError(f"Unknown filter column: {filter_column!r}.")
        if operator not in ALLOWED_OPERATORS:
            raise ValueError(
                f"Unsupported operator {operator!r}; use one of "
                f"{', '.join(sorted(ALLOWED_OPERATORS))}."
            )
        if "value" not in rule:
            raise ValueError("Every filter must include a value.")

    if aggregation is None:
        if column is not None:
            raise ValueError("column can only be used with an aggregation.")
        matched = [
            row
            for row in dataset.rows
            if all(_matches(row[rule["column"]], rule["operator"], rule["value"]) for rule in filters or [])
        ]
        return {
            "dataset": dataset.name,
            "columns": list(dataset.columns),
            "matched_rows": len(matched),
            "rows": matched[:limit],
            "truncated": len(matched) > limit,
        }

    aggregation = AGGREGATION_ALIASES.get(aggregation, aggregation)
    if aggregation not in {"count", "sum", "avg", "min", "max"}:
        raise ValueError(
            f"Unsupported aggregation {aggregation!r}; use one of "
            f"{', '.join(sorted(ALLOWED_AGGREGATIONS))}."
        )
    if aggregation != "count":
        _require_column(dataset, column)
    elif column is not None:
        _require_column(dataset, column)

    matched_rows = [
        row
        for row in dataset.rows
        if all(_matches(row[rule["column"]], rule["operator"], rule["value"]) for rule in filters or [])
    ]
    groups: dict[str | None, list[dict[str, str]]] = defaultdict(list)
    for row in matched_rows:
        key = row[group_by] if group_by else None
        groups[key].append(row)

    results = [
        _aggregate_group(key, rows, aggregation, column, group_by)
        for key, rows in groups.items()
    ]
    results.sort(key=lambda result: str(result.get(group_by or "", "")))
    return {
        "dataset": dataset.name,
        "matched_rows": len(matched_rows),
        "groups": results[:limit],
        "truncated": len(results) > limit,
    }


def summarize_dataset(dataset: Dataset) -> dict[str, Any]:
    return {
        "dataset": dataset.name,
        "row_count": len(dataset.rows),
        "columns": list(dataset.columns),
        "sample_rows": [dict(row) for row in dataset.rows[:5]],
    }


def _aggregate_group(
    key: str | None,
    rows: list[dict[str, str]],
    aggregation: str,
    column: str | None,
    group_by: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if group_by:
        result[group_by] = key
    if aggregation == "count":
        result["count"] = len(rows) if column is None else sum(bool(row[column]) for row in rows)
        return result

    assert column is not None
    values = [row[column] for row in rows if row[column] != ""]
    if aggregation in {"sum", "avg"}:
        numbers = [_as_decimal(value, column) for value in values]
        if not numbers:
            result[aggregation] = None
        elif aggregation == "sum":
            result["sum"] = _format_decimal(sum(numbers, Decimal(0)))
        else:
            result["avg"] = _format_decimal(sum(numbers, Decimal(0)) / len(numbers))
    elif not values:
        result[aggregation] = None
    elif aggregation == "min":
        result["min"] = _format_extreme(min(values, key=_sort_key))
    else:
        result["max"] = _format_extreme(max(values, key=_sort_key))
    return result


def _matches(actual: str, operator: str, expected: str) -> bool:
    if operator == "contains":
        return expected.casefold() in actual.casefold()
    left, right = _try_decimal(actual), _try_decimal(expected)
    if left is not None and right is not None:
        actual_value: Decimal | str = left
        expected_value: Decimal | str = right
    else:
        actual_value = actual.casefold()
        expected_value = expected.casefold()

    if operator == "eq":
        return actual_value == expected_value
    if operator == "ne":
        return actual_value != expected_value
    if operator == "gt":
        return actual_value > expected_value
    if operator == "gte":
        return actual_value >= expected_value
    if operator == "lt":
        return actual_value < expected_value
    return actual_value <= expected_value


def _require_column(dataset: Dataset, column: str | None) -> None:
    if column is not None and column not in dataset.columns:
        raise ValueError(f"Unknown column: {column!r}.")


def _try_decimal(value: str) -> Decimal | None:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _as_decimal(value: str, column: str) -> Decimal:
    number = _try_decimal(value)
    if number is None:
        raise ValueError(
            f"Cannot calculate a numeric aggregation: column {column!r} contains "
            f"non-numeric value {value!r}."
        )
    return number


def _format_decimal(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _sort_key(value: str) -> tuple[int, Decimal | str]:
    number = _try_decimal(value)
    if number is not None:
        return (0, number)
    return (1, value.casefold())


def _format_extreme(value: str) -> int | float | str:
    number = _try_decimal(value)
    return _format_decimal(number) if number is not None else value
