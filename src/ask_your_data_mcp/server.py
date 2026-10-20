"""Streamable HTTP MCP server exposing CSV query and Bedrock tools."""

from __future__ import annotations

import logging
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ask_your_data_mcp.bedrock import answer_with_bedrock as generate_answer
from ask_your_data_mcp.engine import Dataset, parse_csv, query_dataset, summarize_dataset

logger = logging.getLogger(__name__)
mcp = FastMCP("Ask Your Data")
_dataset: Dataset | None = None
_last_results: dict[str, Any] | None = None


class Filter(BaseModel):
    column: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "contains"]
    value: str


def _require_dataset() -> Dataset:
    if _dataset is None:
        raise ValueError("No dataset is loaded. Call load_dataset with CSV content first.")
    return _dataset


@mcp.tool()
def load_dataset(csv_text: str, name: str = "dataset") -> dict[str, Any]:
    """Load CSV text into the current in-memory dataset (maximum 5 MB and 100,000 rows)."""
    global _dataset, _last_results
    dataset = parse_csv(csv_text, name)
    _dataset = dataset
    _last_results = None
    return summarize_dataset(dataset)


@mcp.tool()
def query(
    filters: list[Filter] | None = None,
    group_by: str | None = None,
    aggregation: str | None = None,
    column: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Filter rows and group by column; aggregations: count, sum/total, avg/average/mean, min, or max."""
    global _last_results
    filter_rules = [rule.model_dump() for rule in filters] if filters else None
    results = query_dataset(_require_dataset(), filter_rules, group_by, aggregation, column, limit)
    _last_results = results
    return results


@mcp.tool()
def summarize() -> dict[str, Any]:
    """Describe the currently loaded dataset and show up to five sample rows."""
    return summarize_dataset(_require_dataset())


@mcp.tool()
def answer_with_bedrock(question: str, results: dict[str, Any] | None = None) -> str:
    """Turn query results into a concise spoken-style response using Amazon Bedrock."""
    selected_results = results if results is not None else _last_results
    if selected_results is None:
        return "Run a query first, e.g. sum of amount by category."
    if not question.strip():
        raise ValueError("question must not be empty.")
    try:
        return generate_answer(question, selected_results)
    except RuntimeError as error:
        logger.warning("Bedrock answer generation failed; using query results: %s", error)
        return _format_unavailable_answer(selected_results)


def _format_unavailable_answer(results: dict[str, Any]) -> str:
    groups = results.get("groups")
    if isinstance(groups, list):
        if not groups:
            summary = "The query returned no matching results."
        else:
            metric_labels = {
                "count": "count",
                "sum": "total",
                "avg": "average",
                "min": "minimum",
                "max": "maximum",
            }
            first_group = next((group for group in groups if isinstance(group, dict)), None)
            if first_group is None:
                summary = "The query returned no readable results."
            else:
                metric = next((key for key in metric_labels if key in first_group), None)
                group_key = next(
                    (key for key in first_group if key not in metric_labels),
                    None,
                )
                ranked_groups = [
                    group
                    for group in groups
                    if isinstance(group, dict)
                    and (metric is None or group.get(metric) is not None)
                ]
                if not ranked_groups:
                    summary = "The query returned no matching results."
                elif group_key is None:
                    value = ranked_groups[0].get(metric) if metric else None
                    summary = (
                        f"The query result is {metric_labels[metric]} "
                        f"{_format_answer_value(value)}."
                        if metric and value is not None
                        else "The query returned results."
                    )
                elif metric is None:
                    summary = (
                        f"The query returned results for {len(ranked_groups)} "
                        f"{group_key} groups."
                    )
                else:
                    largest_group = max(
                        ranked_groups,
                        key=lambda group: _answer_sort_key(group[metric]),
                    )
                    summary = (
                        f"{largest_group[group_key]} has the highest "
                        f"{metric_labels[metric]}: "
                        f"{_format_answer_value(largest_group[metric])}."
                    )
    elif isinstance(results.get("rows"), list):
        row_count = results.get("matched_rows", len(results["rows"]))
        summary = (
            "The query returned no matching rows."
            if not row_count
            else f"The query matched {row_count} rows."
        )
    else:
        summary = "I couldn't generate an answer from the query results."
    return f"Bedrock is unavailable; based on the query results, {summary}"


def _answer_sort_key(value: Any) -> tuple[int, float | str]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, float(value))
    return (1, str(value).casefold())


def _format_answer_value(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
