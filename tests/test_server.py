from ask_your_data_mcp.server import (
    Filter,
    _format_unavailable_answer,
    answer_with_bedrock,
    mcp,
)


def test_filter_schema_has_named_fields_and_restricts_operators():
    tool = next(tool for tool in mcp._tool_manager.list_tools() if tool.name == "query")
    schema = tool.parameters["$defs"]["Filter"]

    assert set(schema["properties"]) == {"column", "operator", "value"}
    assert schema["required"] == ["column", "operator", "value"]
    assert schema["properties"]["operator"]["enum"] == [
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
    ]


def test_bedrock_unavailable_response_names_largest_group():
    answer = _format_unavailable_answer(
        {
            "groups": [
                {"category": "Bills", "sum": 1400},
                {"category": "Food", "sum": 3240},
            ]
        }
    )

    assert "Bedrock is unavailable" in answer
    assert "Food has the highest total: 3,240" in answer


def test_answer_tool_uses_basic_summary_without_exposing_bedrock_error(monkeypatch, caplog):
    def unavailable(*_args, **_kwargs):
        raise RuntimeError("AWS account verification pending")

    monkeypatch.setattr("ask_your_data_mcp.server.generate_answer", unavailable)

    answer = answer_with_bedrock(
        "What did I spend?",
        {
            "groups": [
                {"category": "Bills", "sum": 1400},
                {"category": "Food", "sum": 3240},
            ]
        },
    )

    assert "Bedrock is unavailable" in answer
    assert "Food has the highest total: 3,240" in answer
    assert "AWS account verification pending" not in answer
    assert "AWS account verification pending" in caplog.text


def test_answer_tool_prompts_for_query_when_no_results_are_available(monkeypatch):
    monkeypatch.setattr("ask_your_data_mcp.server._last_results", None)

    assert answer_with_bedrock("What did I spend?") == (
        "Run a query first, e.g. sum of amount by category."
    )
