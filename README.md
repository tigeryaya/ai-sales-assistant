# AI Sales Copilot

[English](./README.md) | [繁體中文](./README.zh-TW.md)

A production-deployed **multi-agent sales operations assistant** that combines structured CRM data, deterministic lead scoring, external company research, AI recommendations, and durable human-in-the-loop workflows.

> **Design goal:** automate where AI adds value, keep deterministic logic where consistency matters, and require human oversight for higher-risk actions.

## Live Demo

- **Frontend:** https://ai-sales-assistant-teal.vercel.app
- **Backend API:** https://ai-sales-assistant-production-6111.up.railway.app
- **Swagger Docs:** https://ai-sales-assistant-production-6111.up.railway.app/docs

> The public deployment runs in **safe demo mode**. Costly AI endpoints are protected, and sensitive CRM write/approval execution is restricted for anonymous visitors.

---

## Why This Project Matters

This project goes beyond a basic chatbot or tool-calling demo. It demonstrates an end-to-end AI application with:

- **Multi-agent orchestration** using the OpenAI Agents SDK
- Structured CRM data + deterministic lead scoring
- External research separated from internal CRM facts
- Tool guardrails for protected actions
- Durable human-in-the-loop approval workflows
- RunState persistence and resume after interruption
- Session-isolated conversation memory
- Cloudflare Turnstile bot protection
- Server-side AI response caching
- Daily app-level AI usage quotas
- Concurrency controls for costly workflows
- Persistent SQLite storage on Railway Volume
- Production deployment on **Vercel + Railway**

---

## Architecture

```text
React / Vercel
      │
      │  Cloudflare Turnstile
      ▼
FastAPI / Railway
      │
      ├── Abuse & Cost Controls
      │     ├── Turnstile verification
      │     ├── Response cache
      │     ├── Daily usage quotas
      │     └── Concurrency locks
      │
      ▼
Sales Manager Agent
      │
      ├── CRM Specialist
      │     ├── Structured CRM data
      │     └── Deterministic lead scoring
      │
      └── Research Specialist
            └── Public company research

Protected CRM write
      ↓
Tool Guardrail
      ↓
Human Approval
      ↓
RunState Persisted / Restored
      ↓
CRM Write

Railway Persistent Volume (/data)
      ├── crm.db
      ├── sales_sessions.db
      └── usage.db
```

**[View Full Architecture →](./docs/architecture.md)**

---

## Core Workflow

### Daily Pipeline Review

The dashboard generates:

- Top leads
- Deterministic lead scores
- CRM-based prioritization reasons
- External buying signals
- Sales interpretations
- Recommended actions
- Reliability warnings
- Agent activity

The Sales Manager orchestrates the workflow rather than handling every task itself.

### CRM Specialist

Works with structured internal CRM fields such as customer, company, budget, interest, lead status, and lead score.

Lead scoring remains deterministic:

```text
CRM Data
   ↓
Deterministic Scoring
   ↓
Prioritized Leads
   ↓
AI Interpretation
```

### Research Specialist

Researches public company signals that may be relevant to sales opportunities.

The system intentionally keeps:

```text
Internal CRM Facts ≠ External Public Research
```

External information can support recommendations, but it is not silently treated as verified CRM data.

---

## Durable Human-in-the-Loop

Protected CRM writes do not execute immediately.

```text
Agent requests CRM change
        ↓
Tool Guardrail
        ↓
Approval Required
        ↓
RunState persisted
        ↓
Pending approval stored
        ↓
Human approves
        ↓
RunState restored
        ↓
Agent resumes
        ↓
CRM write executes
```

The approval state is stored in SQLite instead of existing only in process memory, so pending workflows can survive backend redeployments.

### Public Demo Safety

The public deployment intentionally restricts approval/write execution so anonymous visitors cannot mutate CRM state. The full HITL resume/write flow is available in controlled private/local testing.

---

## Tool Guardrails

Human approval is not the only control layer.

Example policy:

```text
proposal
→ may proceed to human approval

won / lost
→ blocked by tool guardrail before approval
```

This creates two separate safeguards:

```text
Agent Decision
      ↓
Tool Guardrail
      ↓
Human Approval
      ↓
CRM Write
```

---

## Conversation Memory

The application supports SQLite-backed conversation sessions.

Requests include a `session_id`, and separate sessions maintain independent conversation histories.

```text
kevin-session-001
Previous context: Kevin Chen has a budget of 500000

Question: "What is his budget?"
→ 500000
```

A fresh session does not automatically inherit that context.

---

## Abuse & Cost Controls

Because the demo is publicly accessible, expensive AI endpoints include multiple protection layers.

### Cloudflare Turnstile

The frontend obtains a Turnstile token and FastAPI performs server-side verification before expensive AI work is allowed.

### Response Cache

Daily pipeline reviews are cached for a configurable period. Repeated requests during the cache window return the stored result instead of launching another multi-agent run.

### Daily AI Quotas

Configurable app-level counters include:

```text
DAILY_REVIEW_LIMIT
AGENT_TASK_DAILY_LIMIT
```

When a limit is reached, the API returns HTTP `429` instead of spending additional model resources.

### Concurrency Controls

Async locks prevent bursts of simultaneous requests from launching duplicate expensive workflows in the same process.

### Persistent Protection State

Quota and cache state are stored in:

```text
/data/usage.db
```

so protection state survives Railway redeployments.

---

## Production Persistence

Railway mounts a Persistent Volume at:

```text
/data
```

The application stores:

```text
/data/crm.db
/data/sales_sessions.db
/data/usage.db
```

These databases persist CRM records, pending approvals, interrupted RunState data, conversation sessions, usage counters, and cached review responses.

---

## Synthetic Demo Data

The demo includes synthetic CRM records.

**NovaTech is intentionally synthetic demo data.**

The system avoids treating public information about a real company with the same name as verified information about the synthetic CRM account.

---

## Tech Stack

### AI / Agent Layer

- OpenAI Agents SDK
- Multi-agent orchestration
- Tool calling
- Tool guardrails
- Human-in-the-loop approval
- RunState persistence
- Web research tools
- SQLite-backed agent sessions

### Backend

- Python
- FastAPI
- Pydantic
- SQLite
- Uvicorn

### Frontend

- React
- JavaScript
- Vite
- Fetch API
- Cloudflare Turnstile

### Deployment

- Vercel
- Railway
- Railway Persistent Volume
- GitHub

---

## API Overview

```text
GET  /health

GET  /customers
POST /customers
GET  /customers/{id}
PUT  /customers/{id}

POST /pipeline/review

POST /agent/run
GET  /agent/pending
POST /agent/approve
```

Interactive API documentation:

https://ai-sales-assistant-production-6111.up.railway.app/docs

---

## Local Development

### Backend

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### Environment Variables

Backend secrets belong in local `.env` or deployment variables and must not be committed.

```text
OPENAI_API_KEY
PUBLIC_DEMO_MODE
TURNSTILE_ENABLED
TURNSTILE_SECRET_KEY
DAILY_REVIEW_LIMIT
DAILY_REVIEW_CACHE_SECONDS
AGENT_TASK_DAILY_LIMIT
DATA_DIR
```

Frontend build-time variables:

```text
VITE_API_BASE_URL
VITE_TURNSTILE_SITE_KEY
```

---

## Reliability Design

Current reliability mechanisms include:

- Deterministic lead scoring
- Agent responsibility separation
- CRM / external research separation
- Tool guardrails
- Human approval for protected writes
- Durable pending state
- RunState restoration
- Session isolation
- Synthetic-data protection
- Post-approval CRM verification
- Persistent storage
- Turnstile verification
- Server-side response caching
- Daily usage quotas
- Concurrency controls
- Public demo restrictions

> **The goal is controlled automation, not maximum autonomy.**

---

## Current Scope

This project is intentionally focused on a reliable, explainable, end-to-end AI workflow rather than a full enterprise CRM platform.

Potential future extensions:

- Authentication and role-based access control
- PostgreSQL
- Real CRM integrations
- Agent observability
- Automated evaluation pipelines
- Model routing by task complexity
- Scheduled pipeline reviews
- Approval history / audit logs
- Broader automated testing

---

## Why I Built This

Many AI agent demos stop at:

```text
Prompt
→ Agent
→ Tool Call
→ Answer
```

This project explores what comes next:

- How should multiple agents divide responsibilities?
- Which decisions should remain deterministic?
- How should agents work with structured business data?
- What happens when AI wants to modify important data?
- How should interrupted workflows resume?
- How should separate conversations remain isolated?
- How do you expose an AI demo publicly without leaving expensive endpoints unprotected?

---

## Author

**Tiger Peng**

M.S. Business Analytics  
B.S. Electrical Engineering

**AI Solutions · Technical Product Management · Applied AI · Agent Systems**
