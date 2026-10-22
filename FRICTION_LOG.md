# Friction log

Friction encountered while building Ask Your Data for the Build, Ship, Shape:
Amazon Developer Hackathon (Alexa+ track, AWS Builder and Open Source mini
challenges), October 2026.

| # | Area | Severity |
|---|---|---|
| F1 | Amazon Bedrock: Converse call rejected on a new account | Critical (blocker) |
| F2 | Service Quotas: every Bedrock quota is 0, no self-serve fix | High |
| F3 | AWS Support: case not picked up within the hackathon window | High |
| F4 | MCP: confirming spec 2025-11-25 compliance | Low |
| F5 | Alexa+: no way to test a self-hosted MCP server against Alexa+ | Medium |

---

## F1: Bedrock Converse call rejected on a new account

- **Task attempted:** Generate a short spoken-style answer from query results
  with the Amazon Bedrock Converse API (`answer_with_bedrock` tool).
- **Steps taken:** Configured `AWS_REGION=eu-north-1`, `BEDROCK_MODEL_ID` and
  Bedrock credentials as documented in the README, started the MCP server and
  called `answer_with_bedrock`, which calls `bedrock-runtime` `converse()`
  through boto3.
- **Expected:** A text response from the model.
- **Actual:** `ValidationException: Operation not allowed`.
- **Severity:** Critical. It blocked every Bedrock call for the rest of the
  hackathon.
- **Workaround:** The tool logs the error on the server and returns a clearly
  labelled deterministic answer computed from the query results (for example,
  the group with the largest total), so users still get a useful spoken
  answer. Also opened an AWS Support case (F3).
- **Actionable suggestion:** Return a specific error for account-level
  restrictions, for example "This account is not yet enabled for on-demand
  inference", with a link explaining how to get access. A generic
  `ValidationException` sends developers off debugging their request payload.

## F2: Every Bedrock quota is 0, with no self-serve fix

- **Task attempted:** Find out why Bedrock calls were rejected.
- **Steps taken:** Opened Service Quotas, then Amazon Bedrock, in
  eu-north-1 and us-east-1, and filtered on "tokens per minute".
- **Expected:** Applied values matching the AWS defaults (for example
  5,000,000 tokens/min for cross-region Claude Haiku 4.5).
- **Actual:** An applied account-level value of **0** for all 79
  tokens-per-minute quotas. Many on-demand quotas are marked "Not adjustable",
  so no increase request can be filed from the console. Nothing explains why.
- **Severity:** High.
- **Workaround:** None in the console. Opened a support case.
- **Actionable suggestion:** Show *why* a quota is 0 (for example, "new account
  under review") directly in Service Quotas and in the Bedrock console, and
  offer a request path even for non-adjustable quotas.

## F3: Support case not picked up within the hackathon window

- **Task attempted:** Get Bedrock unblocked before the submission deadline.
- **Steps taken:** Opened case 179252085100017, "Amazon Bedrock blocked on new
  account: ValidationException Operation not allowed (eu-north-1)", on Basic
  Support.
- **Expected:** Triage within about a day.
- **Actual:** Still "Unassigned" roughly 24 hours later, with no ETA shown.
- **Severity:** High for a time-boxed event.
- **Workaround:** Submitted with the deterministic fallback path. The Bedrock
  integration code is complete and documented.
- **Actionable suggestion:** Offer a fast-track lane (or pre-approval) for
  accounts registered to an AWS-sponsored hackathon, or publish an "account
  readiness check" participants can run before the event starts.

## F4: Confirming MCP spec 2025-11-25 compliance

- **Task attempted:** Make sure the server meets the Alexa+ track rule
  "MCP spec 2025-11-25 or later over Streamable HTTP".
- **Steps taken:** Read the MCP Python SDK docs and release notes, then
  inspected `mcp.types.LATEST_PROTOCOL_VERSION` and ran a real client
  handshake against the server.
- **Expected:** A clear statement of which SDK release implements spec
  2025-11-25.
- **Actual:** Had to verify empirically. SDK 1.30.0 negotiates `2025-11-25`.
- **Severity:** Low.
- **Workaround:** Pinned `mcp>=1.30.0` in `pyproject.toml`.
- **Actionable suggestion:** Publish a spec-version-to-SDK compatibility table
  for Alexa+ builders, plus a small conformance checker that reports the
  negotiated protocol version and transport.

## F5: No way to test a self-hosted MCP server against Alexa+

- **Task attempted:** Try the server end to end with Alexa+.
- **Steps taken:** Read the hackathon resources page and the linked MCP
  documentation.
- **Expected:** A developer sandbox or simulator where a self-hosted
  Streamable HTTP MCP URL can be connected to Alexa+.
- **Actual:** The resources describe building an MCP server or simulating
  Alexa+ in your own web app, but there is no self-serve way to point Alexa+
  at a self-hosted MCP endpoint.
- **Severity:** Medium. The voice experience can't be verified on the target
  platform.
- **Workaround:** Tested with generic MCP clients (MCP Inspector and an
  MCP-capable IDE agent).
- **Actionable suggestion:** An Alexa+ developer simulator that accepts a
  Streamable HTTP MCP URL and shows what Alexa+ would say for each tool
  result.
