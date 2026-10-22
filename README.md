# Ask Your Data

An Alexa+ track prototype: a Streamable HTTP MCP server that loads CSV text,
filters and aggregates it, and can use Amazon Bedrock to turn query results into
a concise answer suitable for speech.

**Demo video (2:45):** https://youtu.be/7BZU_YJn_fE

## Hackathon scope

- **Primary track:** Alexa+ — self-hosted MCP server implementing MCP spec
  **2025-11-25** over Streamable HTTP (MCP Python SDK 1.30+; the version is
  negotiated during the client handshake).
- **Mini-challenges targeted:** AWS Builder (Amazon Bedrock Converse API
  integration in [`bedrock.py`](src/ask_your_data_mcp/bedrock.py)) and Open
  Source (MIT-licensed public project created during the hackathon window).
- Friction encountered during the build is documented in
  [FRICTION_LOG.md](FRICTION_LOG.md).
- The hackathon's [official resources page](https://amazonappdev2026.devpost.com/resources)
  says Alexa+ projects should use open standards for Agent Skills and Streamable
  HTTP transports. It also describes AWS Builder as an integration of AWS
  services and Open Source as a contribution made during the hackathon window.
- Verify current deadlines, eligibility, and submission requirements on the
  [official Devpost page](https://amazonappdev2026.devpost.com/); those details
  can change.

## Requirements

- Python 3.11+
- AWS credentials configured through the standard AWS credential chain, or a
  short-term Bedrock API key, only when invoking the Bedrock answer tool
- Bedrock model access in the selected AWS region

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
ask-your-data-mcp
```

The MCP server uses Streamable HTTP and listens locally on the MCP SDK's default
address (typically `http://127.0.0.1:8000/mcp`). Keep it bound to localhost
unless you deliberately configure and secure a remote deployment.

## Connect a client

Any MCP client that supports Streamable HTTP can connect to
`http://127.0.0.1:8000/mcp`.

**MCP Inspector** (browse tools and call them by hand):

```bash
npx @modelcontextprotocol/inspector
```

Choose the **Streamable HTTP** transport, enter `http://127.0.0.1:8000/mcp`,
click **Connect**, then open the **Tools** tab.

**VS Code (GitHub Copilot agent mode)** — add `.vscode/mcp.json`:

```json
{
  "servers": {
    "ask-your-data": { "type": "http", "url": "http://127.0.0.1:8000/mcp" }
  }
}
```

Then ask, for example: *"Load data/sample-expenses.csv into ask-your-data and
tell me where most of my money went."* The agent calls `load_dataset`, then
`query` (group by `category`, sum `amount`), then `answer_with_bedrock`.

## Configure Bedrock

Set an AWS region, model ID, and Bedrock credentials before starting the server.
Do not put credentials in this repository.

```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=your-enabled-bedrock-model-id
```

For a quick local test, create a **short-term API key** in the Amazon Bedrock
console under **API keys**. Generate it while the console is set to the same
region as `AWS_REGION`; it expires with your console session (up to 12 hours).
In the same terminal where you will start the server, enter the key without
echoing it or adding it to shell history:

```bash
read -s AWS_BEARER_TOKEN_BEDROCK
export AWS_BEARER_TOKEN_BEDROCK
```

Press Enter after pasting the key. Alternatively, configure AWS credentials
using the standard AWS credential chain (for example, an IAM Identity Center
profile). The model must be available to your account in that region. The
server returns an explicit error if Bedrock configuration is missing or the
AWS call fails; CSV loading and query tools do not require AWS access.

## MCP tools

### `load_dataset`

Pass `csv_text` containing a header and at least one data row, plus an optional
dataset `name`. CSV is limited to 5 MiB and 100,000 data rows. The dataset is
held in memory and is not persisted between server restarts.

### `query`

- `filters`: list of `{ "column", "operator", "value" }` rules. Operators:
  `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, and `contains`.
- `group_by`: optional column name.
- `aggregation`: optional `count`, `sum` (`total`), `avg` (`average` or
  `mean`), `min`, or `max`.
- `column`: required for numeric aggregations; optional for `count`.
- `limit`: maximum returned rows/groups (1–1000).

Numeric-looking values are compared numerically; other values are compared
case-insensitively for relational/equality filters. `contains` is
case-insensitive. Numeric `sum` and `avg` reject nonnumeric values. Numeric
`min` and `max` are returned as JSON numbers; nonnumeric columns retain text
results.

### `summarize`

Returns dataset name, row count, column names, and up to five sample rows.

### `answer_with_bedrock`

Pass a question and optionally query results; if omitted, the most recent
`query` result is used. This tool makes a real Amazon Bedrock `Converse` API
call and therefore requires the AWS configuration above. If Bedrock reports a
configuration or service error, the tool logs the error on the server and
returns a clearly labeled deterministic response from the query results,
naming the group with the largest aggregate when results are grouped. If no
query results are available, it asks you to run a query first.

## Development

```bash
python -m pytest
```

## Current limitations

- One in-memory dataset is shared by all clients connected to this server.
- CSV must be supplied as tool input; no arbitrary local file paths are exposed.
- Bedrock answers need an AWS account with Bedrock inference enabled. The
  hackathon account used for development was blocked by AWS (see
  [FRICTION_LOG.md](FRICTION_LOG.md)), so the demo shows the deterministic
  fallback answer.
- A web-based Alexa+ simulator and richer spreadsheet formats (XLSX, Google
  Sheets, S3) are follow-up work.
