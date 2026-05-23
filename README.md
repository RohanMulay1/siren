# SIREN — Self-Improving Incident Response Engine

> Autonomous AI agent that investigates production incidents, executes remediations with Slack-gated human approval, and measurably reduces MTTR with every incident it resolves.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Claude Opus 4.7](https://img.shields.io/badge/Claude-Opus%204.7-orange.svg)](https://anthropic.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-red.svg)](https://qdrant.tech)

**[Live Demo →](https://siren-ruby.vercel.app)** · **[Dashboard →](https://siren-ruby.vercel.app/dashboard)** · **[API Docs →](https://siren-api.onrender.com/docs)**

---

## What SIREN does

When an alert fires, SIREN runs a full investigation-to-resolution loop without waking anyone up:

| Step | What happens |
|------|-------------|
| **Ingest** | Normalizes webhook from any source — Prometheus, CloudWatch, PagerDuty, custom |
| **Triage** | Claude Sonnet classifies severity (P1–P4), service, and confidence in < 2s |
| **Recall** | Qdrant cosine search surfaces the top-5 most similar past incidents |
| **Investigate** | Claude Opus runs a multi-step tool-use loop — logs, metrics, containers, git history |
| **Plan** | Opus ranks a remediation action list, each classified READ / REVERSIBLE / DESTRUCTIVE |
| **Gate** | READ and REVERSIBLE actions auto-execute; DESTRUCTIVE ones pause and send a Slack approval button |
| **Execute** | Approved actions run via Claude Haiku; results feed back into state |
| **Verify** | Sonnet checks live metrics post-fix and confirms resolution |
| **Learn** | Post-mortem is written and embedded into Qdrant — the next similar incident is faster |

### The self-improvement loop

```
Incident #1  (cold):      9.2 min MTTR — 6 tool calls to find root cause
Incident #5  (5 in mem):  5.1 min MTTR — Qdrant surfaces 3 relevant past fixes
Incident #10 (10 in mem): 2.9 min MTTR — 92% match injects the playbook directly
```

−68% MTTR measured over 13 incidents. The dashboard shows the trend.

---

## Architecture

```
Alert Webhook
     │
     ▼
 INGEST ──► TRIAGE ──── low confidence ──────────────────────► ESCALATE
               │
               ▼
         MEMORY RECALL (Qdrant)
               │
               ▼
         INVESTIGATE ◄─── loop until confidence ≥ 0.80 ────────┐
         (Claude Opus)                                           │
               │                                                 │
               ▼                                                 │
         PLAN REMEDIATION                                        │
               │                                                 │
               ▼                                                 │
         GUARDRAIL GATE ──► READ / REVERSIBLE ──► EXECUTE ──────┘
               │                                     │
               ▼                                     │
         DESTRUCTIVE ──► SLACK APPROVAL              │
               │           (graph paused             │
               │            in Redis)                │
               └──────────────────────────────────── ┘
                                                     │
                                                     ▼
                                                  VERIFY
                                                     │
                                                     ▼
                                           WRITE POST-MORTEM
                                           + UPSERT TO QDRANT
```

### Multi-model routing

| Node | Model | Why |
|------|-------|-----|
| Triage | Claude Sonnet 4.6 | Fast structured JSON output, high-volume |
| Memory recall | No LLM (Qdrant) | Deterministic — no hallucination risk |
| Investigate | Claude Opus 4.7 | Max reasoning for root cause analysis |
| Plan remediation | Claude Opus 4.7 | High-stakes ranked planning with past context |
| Execute | Claude Haiku 4.5 | Simple tool dispatch, speed matters |
| Verify | Claude Sonnet 4.6 | Metric interpretation and resolution judgment |
| Post-mortem | Claude Sonnet 4.6 | Structured long-form write, cost-effective |

### Tech stack

| Layer | Technology |
|-------|-----------|
| Core LLMs | Anthropic Claude — Opus 4.7 · Sonnet 4.6 · Haiku 4.5 |
| Workflow | LangGraph stateful graph + Redis checkpointer |
| Vector memory | Qdrant — cosine similarity, payload-indexed |
| Embeddings | fastembed `all-MiniLM-L6-v2` (local ONNX, no API cost) |
| API | FastAPI + Uvicorn |
| Persistence | Redis (checkpoints) + PostgreSQL (audit trail) |
| Human gate | Slack SDK + Block Kit interactive buttons |
| Integrations | AWS CloudWatch · Prometheus · Docker SDK · GitHub API |
| Guardrails | Deterministic classifier + prompt injection detector + rate limiter |
| Observability | LangSmith (trace viewer) + OpenTelemetry |
| Frontend | Next.js 16 App Router (landing + live dashboard) |
| Infra | Docker Compose + Render (API) + Vercel (frontend) |

---

## Guardrail system

Every proposed action passes through a deterministic safety layer before any LLM sees it:

```
READ        → fetch_cloudwatch_logs, query_prometheus, inspect_docker_container,
              query_postgres_readonly, git_blame_file
              Auto-executed immediately, no risk

REVERSIBLE  → restart_docker_container, scale_service, toggle_feature_flag
              Auto-executed when investigation confidence ≥ 85%

DESTRUCTIVE → flush_redis_cache, drain_lb_node, execute_db_migration
              Always pauses graph → sends Slack approval button → resumes on click

UNKNOWN     → any unregistered tool name
              Default DESTRUCTIVE (safe fail)
```

Additional layers:
- **Prompt injection detector** — regex-scans every tool output before it enters LLM context
- **Rate limiter** — max 3 destructive actions per hour (Redis sliding window)
- **Arg-level escalation** — `scale_service(replicas=0)` escalates to DESTRUCTIVE even though `scale_service` is REVERSIBLE

---

## Quick start

### Prerequisites

- Docker Desktop
- Python 3.11+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- Qdrant Cloud account (free tier — [cloud.qdrant.io](https://cloud.qdrant.io))
- Optional: Slack app, AWS IAM credentials, GitHub token

### 1. Clone and configure

```bash
git clone https://github.com/RohanMulay1/siren
cd siren
cp .env.example .env
```

Minimum `.env` to get started:

```env
ANTHROPIC_API_KEY=sk-ant-...

QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=...

DATABASE_URL=postgresql://siren:siren@localhost:5432/siren
REDIS_URL=redis://localhost:6379
```

### 2. Start infrastructure

```bash
docker compose up -d
# Starts: Redis, PostgreSQL, Qdrant (local), Prometheus, Grafana
```

### 3. Seed historical incidents

```bash
pip install -e .
python scripts/seed_qdrant.py
# Loads 20 synthetic incidents so recall works from demo run #1
```

### 4. Start SIREN

```bash
uvicorn siren.main:app --reload       # http://localhost:8000
# API docs: http://localhost:8000/docs
```

### 5. Fire the demo incident

```bash
python scripts/trigger_demo.py
```

Watch SIREN triage a Redis OOM as P1, recall past fixes from memory, investigate with Opus in 3 tool calls, auto-execute the container restart, send a Slack approval button for the cache flush, verify resolution via Prometheus, and write a post-mortem — all in under 4 minutes.

---

## Demo scenario: Redis OOM

The canonical demo exercises every node including the DESTRUCTIVE approval gate.

**What SIREN does:**

1. **Alert** → `payments-api` error rate 40%, Redis OOM errors in logs
2. **Triage** → P1, `payments-api`, confidence 0.94
3. **Recall** → Qdrant returns INC-20260418 (92% match) — same OOM, resolved by FLUSHDB
4. **Investigate** (Claude Opus, 3 tool calls):
   - `query_prometheus` → error_rate=45.2%, p99=8400ms
   - `fetch_cloudwatch_logs` → "OOM command not allowed when used memory > maxmemory" ×847
   - `inspect_docker_container` → mem=99.8%, restart_count=3
5. **Plan** → `[restart_docker_container (REVERSIBLE), flush_redis_cache (DESTRUCTIVE)]`
6. **Gate** → restart auto-executes; flush sends Slack approval button
7. **Slack** → engineer clicks APPROVE → graph resumes from Redis checkpoint
8. **Verify** → `query_prometheus` → error_rate=0.2%, p99=118ms ✓
9. **Post-mortem** → written by Sonnet, embedded in Qdrant
10. **MTTR** → 2.4 min (vs. 9.2 min cold)

---

## API reference

```
POST /webhook/alert
  Ingest an alert from any monitoring source
  Body: { source, alert_name, severity, service, description, labels }
  Returns: { incident_id, status }

POST /webhook/slack/action
  Handle Slack interactive button clicks (APPROVE / REJECT)
  Resumes the paused LangGraph checkpoint

GET  /api/incidents
  List recent incidents with status and MTTR

GET  /api/incidents/{incident_id}
  Full LangGraph state for one incident

GET  /health
  { status, qdrant_incidents, environment }
```

**Example alert payload:**

```json
{
  "source": "prometheus",
  "alert_name": "RedisOOMKiller",
  "severity": "critical",
  "service": "payments-api",
  "description": "OOM killer triggered 3x in 5 minutes. Auth token keys filling maxmemory.",
  "labels": { "env": "production", "region": "us-east-1" }
}
```

---

## Adding a new tool

```python
from ..registry import register_tool

@register_tool("READ")
class CheckRedisMemory:
    NAME = "check_redis_memory"
    DESCRIPTION = "Get Redis memory usage. Use during OOM investigations."
    INPUT_SCHEMA = {
        "type": "object",
        "properties": { "redis_url": {"type": "string"} },
        "required": ["redis_url"]
    }

    @staticmethod
    async def handler(redis_url: str) -> str:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url)
        info = await r.info("memory")
        await r.aclose()
        return f"used={info['used_memory_human']} peak={info['used_memory_peak_human']}"
```

1. Create `siren/tools/{tier}/{tool_name}.py` with the above pattern
2. Import it in `siren/tools/__init__.py`
3. The classifier automatically picks up the tier from the decorator

---

## Slack setup

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App → From scratch**
2. **OAuth & Permissions** → Bot Token Scopes → `chat:write`, `chat:write.public`
3. **Install to Workspace** → copy Bot Token → `SLACK_BOT_TOKEN`
4. **Basic Information** → Signing Secret → `SLACK_SIGNING_SECRET`
5. Right-click your `#incidents` channel → View details → copy Channel ID → `SLACK_CHANNEL_ID`
6. Expose local server: `cloudflared tunnel --url http://localhost:8000`
7. **Interactivity & Shortcuts** → Request URL: `https://your-tunnel/webhook/slack/action`

---

## Project structure

```
siren/
├── siren/
│   ├── agent/
│   │   ├── graph.py              # LangGraph state machine — all nodes + edges
│   │   ├── state.py              # IncidentState TypedDict
│   │   ├── routing.py            # Conditional edge functions
│   │   └── nodes/                # One file per workflow node
│   ├── tools/
│   │   ├── registry.py           # @register_tool decorator + TOOL_REGISTRY
│   │   ├── read/                 # CloudWatch, Prometheus, DB, Docker, GitHub
│   │   ├── reversible/           # Container restart, scale service
│   │   └── destructive/          # Redis flush, ALB drain, DB migration
│   ├── guardrails/
│   │   ├── classifier.py         # Deterministic READ/REVERSIBLE/DESTRUCTIVE lookup
│   │   ├── injection_detector.py # Regex scan on every tool output
│   │   └── rate_limiter.py       # Redis sliding window counter
│   ├── memory/
│   │   ├── qdrant_client.py      # Collection setup + payload indexes
│   │   ├── embedder.py           # fastembed local ONNX inference
│   │   ├── incident_store.py     # recall_similar() + upsert_postmortem()
│   │   └── schemas.py            # IncidentVectorPayload
│   ├── integrations/slack/       # Block Kit messages + approval webhook handler
│   ├── api/routers/              # /webhook/alert, /webhook/slack/action, /incidents
│   ├── db/                       # Postgres models, session, action audit writer
│   └── observability/            # LangSmith + OpenTelemetry
├── frontend/                     # Next.js 16 — landing page + ops dashboard
├── scripts/
│   ├── seed_qdrant.py            # Pre-load 20 synthetic incidents
│   └── trigger_demo.py           # Fire the Redis OOM scenario
├── tests/unit/
└── tests/integration/
```

---

## License

MIT — see [LICENSE](LICENSE). Contributions welcome.
