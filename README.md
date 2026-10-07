# ModelCoffeeProtocol ☕

A starter coffee purchasing assistant demonstrating **AI agent → MCP client → FastMCP server → FastAPI vendor API**.

The owner asks for replenishment, the agent checks inventory, discovers suppliers, requests quotes, negotiates bean prices and shipping, and presents the terms for review. Suppliers are local simulations; no real vendor is contacted and no order is placed.

```mermaid
flowchart LR
    Owner[Coffee shop owner] --> Agent[Pydantic AI agent]
    Agent --> Client[MCP client]
    Client --> MCP[FastMCP tools :8001/mcp]
    MCP --> API[FastAPI supplier API :8000]
    API --> Vendors[Two simulated roasters]
```

## Run

Requires Python 3.11+. Run all commands from this repository.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -c requirements-lock.txt -e '.[dev]'
cp .env.example .env
```

For the AI chat, put your Anthropic API key in `.env`. `AGENT_MODEL` is configurable using Pydantic AI's provider:model format; configure the corresponding provider credentials when changing it. No model credentials are needed for the API, MCP server or tests. Model calls may incur provider charges.

Start three terminals, activating `.venv` in each:

```sh
# Terminal 1: simulated vendor API
uvicorn modelcoffee.api:app --host 127.0.0.1 --port 8000
# Terminal 2: MCP tool server
python -m modelcoffee.mcp_server
# Terminal 3: conversational AI purchasing assistant
python -m modelcoffee.agent
```

API documentation: http://127.0.0.1:8000/docs

Try:

> Check my beans. If I need more, compare 25 kg from the available roasters. My total budget is $600, delivery must be within four days. Negotiate a lower price and free shipping, then show me the terms.

Conversation history remains in memory during the terminal session. The demo has 12 kg of beans, uses 3 kg/day and has a six-day reorder window (four-day lead time plus two-day buffer). It recommends reordering at or below 18 kg. Roaster A starts at $24/kg plus $18 shipping and can counter at $22/kg with free shipping for orders of at least 25 kg: $550 landed total.

## Tools and endpoints

| MCP tool | REST API | Purpose |
|---|---|---|
| `check_inventory` | `GET /inventory` | Stock, usage and reorder signal |
| `list_vendors` | `GET /vendors` | Discover supplier IDs and lead times |
| `request_quote` | `POST /quotes` | Create a nonbinding quote |
| `negotiate_quote` | `POST /quotes/{id}/counteroffers` | Negotiate price and freight |

FastMCP publishes tool descriptions and schemas. The agent's MCP client discovers them and invokes them; the tool implementation translates arguments into HTTP requests. The REST API validates the supplier bearer credential and inputs. The MCP server holds that credential, not the model.

Prices use integer USD cents. Suppliers enforce price floors and a three-round negotiation limit. There is deliberately no purchasing tool: the agent can propose terms but cannot create a binding purchase.

## Verification

```sh
pytest -q
```

Tests cover authorization failures, invalid quantities and suppliers, reorder math, shipping floors, negotiation limits, and MCP discovery/calls through the real FastAPI handlers. A scripted-model test also checks agent tool discovery and execution. These tests do not establish live model behavior or real vendor integration.

Verified locally: six tests passed, dependency checks passed, and the two-server HTTP demo returned $550 and $575 negotiated quotes. The live provider-backed agent has not been exercised. `requirements-lock.txt` records the tested dependency versions.

## Starter boundaries and next steps

- Quotes and inventory are demo in-memory data; quotes disappear on API restart.
- CLI is the owner interface; no web frontend or scheduled monitoring yet.
- MCP binds to loopback without authentication. The API token is a shared demo credential; this is not multi-user authorization. Do not expose either server publicly as configured.
- Budget and deadline instructions guide the model; there is no executable purchase to authorize. A real ordering implementation needs server-enforced owner policy and explicit approval of exact quote terms.
- Supplier timeouts report an unknown outcome. No automatic mutation retries or idempotency persistence are implemented.
- Add SQLite/Postgres inventory and an auditable negotiation history, inventory updates, scheduled reorder alerts, then a real supplier adapter.
- Add agent evaluations for missing details, budget/deadline adherence, tool selection and dishonest supplier text before expanding autonomy.

## Interview talking points

Explain why MCP wraps business tasks rather than exposing every HTTP endpoint; why credentials stay outside model context; why comparing landed cost matters; and how schema tests differ from agent behavior evaluations.

Built based on the following the documentation [FastMCP client/server interfaces](https://gofastmcp.com/clients/client) and [Pydantic AI MCP integration](https://ai.pydantic.dev/mcp/client/).

## No-key walkthrough

With both servers running, run `python -m modelcoffee.demo` to discover and invoke MCP tools and compare two negotiated quotes. This is a deterministic protocol demonstration, not an AI agent run.
