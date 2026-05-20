# 🚨 SIREN — Self-Improving Incident Response Engine

> An autonomous AI agent that investigates production incidents, executes remediations with human approval, and gets measurably faster with every incident it resolves.

[![CI](https://github.com/RohanMulay1/siren/actions/workflows/ci.yml/badge.svg)](https://github.com/RohanMulay1/siren/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-red.svg)](https://qdrant.tech)

---

## What Is SIREN?

SIREN is a production-grade AI agent that replaces the "someone wakes up at 3am and stares at dashboards" part of incident response. When an alert fires, SIREN:

1. **Triages** the severity and classifies the incident type
2. **Recalls** similar past incidents from Qdrant vector memory — the more incidents it has seen, the faster it gets
3. **Investigates** root cause using a multi-step tool-use loop (logs → metrics → git blame → database queries)
4. **Plans** a ranked remediation with each action classified as READ / REVERSIBLE / DESTRUCTIVE
5. **Gates** any dangerous action behind a Slack approval button — nothing irreversible happens without a human click
6. **Executes** approved remediations and verifies resolution via live metrics
7. **Learns** — every resolved incident is embedded into Qdrant, measurably reducing MTTR over time

### The Self-Improvement Loop

```
Run 1  (cold, 0 incidents in memory):  MTTR ≈ 9 min  — 6 tool calls to find root cause
Run 5  (5 incidents in memory):        MTTR ≈ 5 min  — Qdrant surfaces 3 similar incidents
Run 10 (10 incidents in memory):       MTTR ≈ 3 min  — 85% match injects the playbook directly
```

The MTTR trend chart in the Streamlit dashboard is the quantified proof.

---

## Architecture

```
Alert Webhook (Prometheus / PagerDuty / CloudWatch / custom)
        │
        ▼
  ┌─────────────┐
  │   INGEST    │  Normalize webhook payload
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │   TRIAGE    │  Llama 3.3 70B → severity (P1–P4), service, confidence
  └──────┬──────┘
         │ P4 or noise → escalate
         ▼
  ┌─────────────────┐
  │  MEMORY RECALL  │  Qdrant cosine search → top-5 similar past incidents
  └──────┬──────────┘
         │
         ▼
  ┌──────────────────────────────────────────┐
  │         INVESTIGATE  (Llama 3.3 70B)     │
  │  Tool-use loop (up to 5 iterations):     │
  │  → fetch_cloudwatch_logs                 │
  │  → query_prometheus                      │
  │  → query_postgres_readonly               │
  │  → inspect_docker_container              │
  │  → git_blame_file                        │
  │  → finish_investigation (confidence≥80%) │
  └──────┬───────────────────────────────────┘
         │
         ▼
  ┌───────────────────┐
  │  REMEDIATION PLAN │  Llama 3.3 70B → ranked action list with rationale
  └──────┬────────────┘
         │
         ▼
  ┌───────────────────────────────────────────────────────┐
  │                  GUARDRAIL GATE                       │
  │  READ       → auto-execute (no approval needed)       │
  │  REVERSIBLE → auto-execute (if confidence ≥ 85%)      │
  │  DESTRUCTIVE→ Slack approval required                 │
  │  Unknown    → default DESTRUCTIVE (safe default)      │
  │  Rate limiter: max 3 destructive actions/hr globally  │
  │  Injection detector: scans all tool output before LLM │
  └──────┬─────────────────────┬─────────────────────────┘
         │ approved            │ needs human
         ▼                     ▼
  ┌─────────────┐    ┌──────────────────────────┐
  │   EXECUTE   │    │  SLACK APPROVAL REQUEST  │
  │  Llama 8B   │    │  Block Kit message with  │
  │  (fast)     │◄───│  [APPROVE] [REJECT]      │
  └──────┬──────┘    │  Graph paused in Redis   │
         │           └──────────────────────────┘
         ▼
  ┌─────────────┐
  │   VERIFY    │  Llama 3.3 70B checks live metrics post-fix
  └──────┬──────┘
         │ resolved
         ▼
  ┌───────────────────────────────────────────┐
  │            POST-MORTEM WRITER             │
  │  Llama 3.3 70B → structured post-mortem  │
  │  Embed incident → upsert to Qdrant        │
  │  MTTR recorded → self-improvement loop   │
  └───────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Groq (Llama 3.3 70B Versatile + Llama 3.1 8B Instant) via OpenAI-compatible API |
| **Workflow** | LangGraph stateful graph + Redis checkpointer (human-in-the-loop pause/resume) |
| **Vector Memory** | Qdrant — incident embeddings, semantic recall, self-improvement |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` (local, no API cost) |
| **API** | FastAPI + Uvicorn |
| **State persistence** | Redis (LangGraph checkpoints + approval correlation) |
| **Structured storage** | PostgreSQL + SQLAlchemy async (incident records, action audit trail) |
| **Human gate** | Slack SDK + Block Kit interactive buttons |
| **Integrations** | AWS CloudWatch, Prometheus, Docker SDK, GitHub API |
| **Guardrails** | Custom Enkrypt-inspired classifier + prompt injection detector + rate limiter |
| **Observability** | LangSmith (agent trace viewer), OpenTelemetry |
| **Dashboard** | Streamlit (live feed, MTTR chart, Qdrant memory visualization) |
| **Infra** | Docker Compose (Redis, Postgres, Qdrant, Prometheus, Grafana) |
| **CI/CD** | GitHub Actions |

---

## Guardrail System

Every action the agent proposes passes through a deterministic safety layer before execution:

```python
# Deterministic — no LLM involved, no hallucination risk
READ:        fetch_cloudwatch_logs, query_prometheus, query_postgres_readonly,
             inspect_docker_container, git_blame_file
             → Auto-executed, zero risk

REVERSIBLE:  restart_docker_container, scale_service, toggle_feature_flag
             → Auto-executed if root cause confidence ≥ 85%

DESTRUCTIVE: flush_redis_cache, drain_lb_node, execute_db_migration
             → Always requires human Slack approval before execution

UNKNOWN:     Any tool not in the registry
             → Default DESTRUCTIVE (safe fail)
```

Additional layers:
- **Prompt injection detector** — scans every tool output with regex patterns before returning to LLM context
- **Rate limiter** — max 3 destructive actions per hour globally (Redis sliding window)
- **Arg-level escalation** — `scale_service(replicas=0)` auto-escalates to DESTRUCTIVE even though the tool is REVERSIBLE

---

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- A [Groq](https://console.groq.com) API key (free)
- Optional: Slack app, AWS IAM user, GitHub token, LangSmith account

### 1. Clone and configure

```bash
git clone https://github.com/RohanMulay1/siren
cd siren
cp .env.example .env
```

Edit `.env` and fill in your keys (minimum: `GROQ_API_KEY`):

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...

GITHUB_TOKEN=ghp_...           # optional — enables git_blame_file tool
LANGSMITH_API_KEY=lsv2_...     # optional — enables agent trace viewer
AWS_ACCESS_KEY_ID=...           # optional — enables CloudWatch log tool
AWS_SECRET_ACCESS_KEY=...
SLACK_BOT_TOKEN=xoxb-...        # optional — enables human approval gate
SLACK_SIGNING_SECRET=...
SLACK_CHANNEL_ID=C...
```

### 2. Start all services

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts: Redis, PostgreSQL, Qdrant, Prometheus, Grafana.

### 3. Seed historical incidents into Qdrant

```bash
pip install -e .
python scripts/seed_qdrant.py
```

Loads 12 synthetic historical incidents (OOM, connection pool, deploy regression, disk saturation) so SIREN shows intelligent recall from the first demo run.

### 4. Start SIREN

```bash
# API server
uvicorn siren.main:app --reload

# Dashboard (separate terminal)
streamlit run dashboard/app.py
```

- API: http://localhost:8000
- Dashboard: http://localhost:8501
- API docs: http://localhost:8000/docs

### 5. Fire the demo incident

```bash
# Fill demo Redis to near-OOM, then fire the alert
python scripts/trigger_demo.py --fill
python scripts/trigger_demo.py --watch
```

Watch the dashboard — SIREN will triage, recall 3 similar OOM incidents from memory, investigate with Groq, propose `flush_redis_cache`, and (if Slack is configured) send you an approval button. After approval, it executes the fix and verifies resolution via Prometheus.

---

## Demo Scenario: Redis OOM

This is the competition demo scenario — reproducible, visual, and exercises every node including the DESTRUCTIVE approval gate.

**What happens:**
1. Alert fires: `payments-api error rate 40%, Redis OOM errors`
2. Triage: P1, payments-api, confidence 0.91
3. Memory recall: finds 3 similar OOM incidents (87%, 74%, 68% match)
4. Investigation (Llama 3.3 70B, ~3 tool calls):
   - `query_prometheus` → error rate 45%, p99 latency 8s
   - `fetch_cloudwatch_logs` → "OOM command not allowed when used memory > maxmemory"
   - `inspect_docker_container redis-demo` → memory 99.8%, restart_count 3
5. Root cause: Redis maxmemory exhausted, confidence 0.94
6. Plan: `[restart_docker_container (REVERSIBLE), flush_redis_cache (DESTRUCTIVE)]`
7. Guardrail: restart auto-executes → flush requires Slack approval
8. Slack: you click APPROVE → agent executes FLUSHDB
9. Verify: `query_prometheus` → error rate 0.2%, latency 120ms ✓
10. Post-mortem written and embedded in Qdrant

**MTTR with 12 seeded incidents in memory: ~3-4 minutes**
**MTTR cold (0 incidents): ~8-9 minutes**

---

## API Reference

```
POST /webhook/alert
  Body: { source, alert_name, severity, service, description, labels, annotations }
  Returns: { incident_id, status, message }

POST /webhook/slack/action
  Slack interactive component payload (button clicks)
  Returns: 200 OK (graph resumes async)

GET /api/incidents
  Returns: list of recent incidents from Postgres

GET /api/incidents/{incident_id}
  Returns: full LangGraph state for this incident

GET /api/incidents/{incident_id}/history
  Returns: step-by-step workflow history

GET /health
  Returns: { status, qdrant_incidents, environment }
```

### Example alert payload

```json
{
  "source": "prometheus",
  "alert_name": "HighErrorRate",
  "severity": "critical",
  "service": "payments-api",
  "description": "payments-api error rate exceeded 40% for 5 minutes. Redis OOM errors observed.",
  "labels": { "env": "production", "region": "us-east-1" }
}
```

---

## Adding a New Tool

1. Create `siren/tools/{tier}/{tool_name}.py`
2. Decorate with `@register_tool("READ" | "REVERSIBLE" | "DESTRUCTIVE")`
3. Implement `NAME`, `DESCRIPTION`, `INPUT_SCHEMA`, and `async execute(**kwargs) -> str`
4. Import it in `siren/tools/__init__.py`
5. Add to `CLASSIFICATION_RULES` in `siren/guardrails/classifier.py`

```python
from ..registry import register_tool

@register_tool("READ")
class CheckRedisMemory:
    NAME = "check_redis_memory"
    DESCRIPTION = "Get Redis memory usage stats. Use during OOM investigations."
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "redis_url": {"type": "string", "description": "Redis connection URL"},
        },
        "required": ["redis_url"],
    }

    @staticmethod
    async def execute(redis_url: str) -> str:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url)
        info = await client.info("memory")
        await client.aclose()
        return f"Used: {info['used_memory_human']}, Peak: {info['used_memory_peak_human']}, Fragmentation: {info['mem_fragmentation_ratio']}"
```

---

## Supported Integrations

| Integration | Tool | What it reads |
|---|---|---|
| AWS CloudWatch | `fetch_cloudwatch_logs` | Application logs, error traces |
| Prometheus | `query_prometheus` | Metrics via PromQL |
| PostgreSQL | `query_postgres_readonly` | DB stats, slow queries, connection counts |
| Docker | `inspect_docker_container` | Container status, OOM kills, restart count |
| GitHub | `git_blame_file` | Recent commits touching a file |
| Docker | `restart_docker_container` | Graceful container restart (REVERSIBLE) |
| Docker Compose | `scale_service` | Replica count change (REVERSIBLE) |
| Redis | `flush_redis_cache` | FLUSHDB on a specific database (DESTRUCTIVE) |
| AWS ALB | `drain_lb_node` | Deregister instance from target group (DESTRUCTIVE) |

---

## Slack Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. **OAuth & Permissions** → Bot Token Scopes → add `chat:write`, `chat:write.public`
3. **Install to Workspace** → copy **Bot User OAuth Token** → `SLACK_BOT_TOKEN`
4. **Basic Information** → **Signing Secret** → `SLACK_SIGNING_SECRET`
5. Right-click your Slack channel → **View channel details** → copy Channel ID → `SLACK_CHANNEL_ID`
6. Type `/invite @SIREN` in that channel
7. Run `ngrok http 8000`, copy the HTTPS URL
8. **Interactivity & Shortcuts** → ON → Request URL: `https://your-ngrok-url/webhook/slack/action`

---

## Running Tests

```bash
# Unit tests — no external services required
pytest tests/unit/ -v

# Integration tests — requires compiled LangGraph only
pytest tests/integration/ -v

# Full suite
pytest tests/ -v
```

30 tests, all passing. Unit tests cover guardrail classification, injection detection, and all routing logic. Integration tests verify the full LangGraph workflow compiles and routes correctly.

---

## Project Structure

```
siren/
├── siren/
│   ├── agent/
│   │   ├── graph.py           # LangGraph state machine (10 nodes, conditional edges)
│   │   ├── state.py           # IncidentState TypedDict — source of truth
│   │   ├── routing.py         # Conditional edge functions
│   │   └── nodes/             # One file per workflow node
│   ├── llm/
│   │   ├── client.py          # OpenAI-compatible client (Groq / OpenRouter)
│   │   └── tools.py           # Schema conversion (registry → OpenAI function format)
│   ├── tools/
│   │   ├── registry.py        # @register_tool decorator + TOOL_REGISTRY
│   │   ├── read/              # CloudWatch, Prometheus, DB, Docker inspect, GitHub
│   │   ├── reversible/        # Container restart, scale service
│   │   └── destructive/       # Redis flush, ALB drain
│   ├── guardrails/
│   │   ├── classifier.py      # Deterministic READ/REVERSIBLE/DESTRUCTIVE lookup
│   │   ├── injection_detector.py  # Regex scan on all tool output
│   │   └── rate_limiter.py    # Redis sliding window counter
│   ├── memory/
│   │   ├── qdrant_client.py   # Collection setup + payload indexes
│   │   ├── embedder.py        # sentence-transformers (local)
│   │   ├── incident_store.py  # recall_similar() + upsert_incident()
│   │   └── schemas.py         # IncidentVectorPayload
│   ├── integrations/
│   │   └── slack/             # Block Kit messages + approval webhook handler
│   ├── api/routers/           # FastAPI: /webhook/alert, /webhook/slack/action, /incidents
│   ├── db/                    # Postgres models, session, audit writer
│   └── observability/         # LangSmith + OpenTelemetry setup
├── dashboard/app.py           # Streamlit dashboard
├── scripts/
│   ├── seed_qdrant.py         # Load 12 historical incidents for demo
│   ├── trigger_demo.py        # Fire Redis OOM demo scenario
│   └── setup_slack_app.py     # Verify Slack credentials
├── tests/
│   ├── unit/                  # Guardrails, routing, state (no external deps)
│   └── integration/           # Graph compilation + full routing walkthrough
└── docker/docker-compose.yml  # Redis, Postgres, Qdrant, Prometheus, Grafana
```

---

## Competition Categories

SIREN was built for the AI Agent Awards competition and is nominated under:

| # | Category | Why SIREN qualifies |
|---|---|---|
| 01 | **Best Solo Builder** | Designed, built, and shipped by one person |
| 02 | **Most Innovative Agent** | Self-improving MTTR via Qdrant memory is genuinely novel |
| 03 | **Most Impactful Use Case** | Production downtime costs $5,600/min (Gartner) — quantifiable ROI |
| 06 | **Anthropic SDK Innovation** | Multi-step tool-use loops, structured handoffs, production-grade agent patterns |
| 10 | **Qdrant Vector Database Master** | Semantic incident recall is load-bearing, not decorative RAG |
| 12 | **Enkrypt AI Secure Agent Guardrail** | Tiered action safety + injection detection on a production system |
| 13 | **Best Open Source Contribution** | Plug-and-play tool framework, MIT licensed, free to extend |

---

## License

MIT — contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).
