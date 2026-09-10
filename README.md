# AI Sales Copilot

[English](./README.md) | [繁體中文](./README.zh-TW.md)

A production-deployed **multi-agent sales operations assistant** that combines CRM data, external company research, lead prioritization, AI recommendations, and durable human approval workflows in a single dashboard.

The project demonstrates how AI agents can assist sales operations while keeping important CRM write actions under **human-in-the-loop control**.

## Live Demo

**Frontend**

https://ai-sales-assistant-teal.vercel.app

**Backend API**

https://ai-sales-assistant-production-6111.up.railway.app

**API Documentation**

https://ai-sales-assistant-production-6111.up.railway.app/docs

---

## Overview

AI Sales Copilot helps a sales team review its pipeline by combining:

- Structured CRM data
- Deterministic lead scoring
- External company research
- Multi-agent orchestration
- AI-generated recommendations
- Human approval for sensitive CRM writes
- Persistent conversation and approval state

Instead of giving an AI agent unrestricted access to modify CRM data, the system separates:

```text
AI reasoning
    ↓
Tool validation
    ↓
Human approval
    ↓
CRM execution
```

This makes the project closer to a real business workflow than a simple chatbot or single tool-calling demo.

---

## Core Features

### 1. Multi-Agent Sales Workflow

The backend uses the **OpenAI Agents SDK** to coordinate multiple AI roles.

Current workflow:

```text
Sales Manager
     │
     ├── CRM Specialist
     │
     └── Research Specialist
     │
     ▼
Daily Pipeline Review
```

### Sales Manager

Acts as the orchestrator.

It combines CRM information and external research into a final sales pipeline review.

### CRM Specialist

Works with structured CRM information such as:

- Customer
- Company
- Budget
- Interest
- Lead status
- Lead score

### Research Specialist

Researches external company signals that may be relevant to sales opportunities.

External information is kept separate from internal CRM facts to reduce the risk of incorrectly treating public information as customer data.

---

## Daily Pipeline Review

The dashboard can generate a daily pipeline review containing:

- Top Leads
- Lead scores
- CRM-based prioritization reasons
- External Buying Signals
- Sales interpretations
- Recommended Actions
- Reliability warnings
- Agent execution status

The current demo baseline includes:

| Customer | Company | Status | Score |
|---|---|---|---:|
| Kevin Chen | NovaTech | qualified | 60 |
| Sarah Lin | Cloudflare | new | 40 |
| Michael Wu | ServiceNow | new | 40 |
| Emily Chen | Snowflake | new | 25 |

**NovaTech is intentionally synthetic demo data.**

The system does not treat online information about companies with the same name as verified information about Kevin Chen's company.

---

## Lead Scoring

Lead scores are calculated from structured CRM data rather than being generated entirely by an LLM.

Inputs include information such as:

- Budget
- Interest level
- Lead status

This creates a clearer separation between deterministic business logic and AI-generated reasoning.

```text
CRM Data
   ↓
Lead Scoring Logic
   ↓
Prioritized Leads
   ↓
AI Interpretation
```

---

## External Buying Signals

The Research Specialist can gather external signals related to real companies in the CRM.

The dashboard separates:

```text
Verified External Fact
        ↓
Sales Interpretation
```

This distinction is intentional.

The AI is allowed to interpret a verified external signal, but the interpretation is not presented as a verified fact.

---

## Recommended Actions

After CRM analysis and external research are complete, the Sales Manager generates prioritized next actions.

Examples may include:

- Follow up with a high-priority lead
- Investigate a buying signal
- Prepare a proposal
- Review a qualified opportunity

The recommendations are advisory.

Sensitive CRM write actions still pass through the approval workflow.

---

## Durable Human-in-the-Loop Approval

One of the main features of this project is a persistent human approval workflow.

When an AI agent requests a protected CRM write:

```text
Agent requests CRM change
        ↓
Tool Guardrail
        ↓
Approval Required
        ↓
RunState persisted
        ↓
Pending Approval shown in dashboard
        ↓
Human clicks Approve
        ↓
RunState restored
        ↓
Agent execution resumes
        ↓
CRM write executes
```

The interrupted run is not stored only in application memory.

Pending approval state is persisted in SQLite, allowing it to survive backend redeployments and process restarts.

---

## Durable RunState

When an agent execution is interrupted for approval, its state is stored so the workflow can continue later.

Production testing confirmed the following sequence:

```text
Create pending approval
        ↓
Railway redeploy
        ↓
Pending approval still exists
        ↓
Restore RunState
        ↓
Approve from Vercel dashboard
        ↓
Resume agent execution
        ↓
CRM record updated
        ↓
Pending approval removed
```

This allows the approval workflow to survive infrastructure restarts instead of losing its state.

---

## Tool Guardrails

CRM-changing tools are protected by tool-level guardrails.

The current demo policy includes behavior such as:

```text
proposal
→ can proceed to human approval

won / lost
→ blocked by the configured guardrail before approval
```

The architecture therefore contains two separate control layers:

```text
Agent Decision
      ↓
Tool Guardrail
      ↓
Human Approval
      ↓
CRM Write
```

The human approval layer is not used as a replacement for tool validation.

Both layers serve different purposes.

---

## Conversation Memory

The application supports persistent agent sessions using SQLite-backed session storage.

Requests can include a `session_id`.

Different sessions maintain independent conversation histories.

Example:

```text
kevin-session-001

Previous context:
Kevin Chen has a budget of 500000

Question:
"What is his budget?"

→ 500000
```

A new session does not automatically inherit that context:

```text
fresh-session-001

Question:
"What is his budget?"

→ No customer context available
```

This demonstrates session isolation between separate conversations.

---

## Pending Approval Dashboard

The React frontend can directly display pending AI actions.

A pending approval shows information such as:

```text
Customer
Company
Current CRM Status
Requested CRM Status
Tool
Durable RunState
```

The user can approve the action directly from the dashboard.

After approval, the frontend verifies the resulting CRM state and refreshes the pending approval list.

---

## Agent Activity

The dashboard visualizes the current multi-agent workflow.

```text
Sales Manager
     ↓
CRM Specialist
Research Specialist
     ↓
Recommendation
```

Specialists change from `Waiting` to `Completed` after execution.

This makes the internal orchestration easier to understand during a live demo.

---

## Dashboard Navigation

The application uses a single-page React dashboard.

Sidebar sections include:

- Overview
- Pipeline
- AI Review
- Approvals
- Agent Activity

Navigation uses smooth section scrolling without React Router or separate pages.

The project intentionally keeps the frontend simple so the focus remains on the AI workflow and reliability mechanisms.

---

## Architecture

```text
React / Vercel
      ↓
FastAPI / Railway
      ↓
Sales Manager
   ↙          ↘
CRM Specialist   Research Specialist
      ↓
Guardrails + Human Approval
      ↓
Persistent SQLite Storage
```

For the full system architecture, including the durable HITL and RunState resume flow:

**[View Full Architecture →](./docs/architecture.md)**

---

## Tech Stack

### AI / Agent Layer

- OpenAI Agents SDK
- Multi-agent orchestration
- Tool calling
- Tool guardrails
- Human-in-the-loop approval
- RunState persistence
- SQLite-backed conversation sessions

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

### Deployment

- Railway
- Railway Persistent Volume
- Vercel
- GitHub

---

## API Overview

Main endpoints include:

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

Interactive API documentation is available through FastAPI Swagger UI:

https://ai-sales-assistant-production-6111.up.railway.app/docs

---

## Production Persistence

The Railway deployment uses a Persistent Volume.

Production environment paths include:

```text
CRM_DB_PATH=/data/crm.db

SALES_SESSION_DB_PATH=/data/sales_sessions.db
```

Persistent storage is used for:

- CRM records
- Agent conversation sessions
- Pending human approvals
- Interrupted workflow state

Persistence was tested across Railway redeployments.

---

## Reliability Design

This project intentionally avoids giving one AI agent unrestricted control over the entire workflow.

Reliability mechanisms currently include:

- Structured CRM data
- Deterministic lead scoring
- Specialized agent responsibilities
- Separation of CRM facts and external research
- Tool-level guardrails
- Human approval for protected writes
- Persistent approval state
- Agent RunState restoration
- Conversation session isolation
- Synthetic-data protection
- Reliability warnings
- Post-approval CRM verification

The goal is not maximum autonomy.

The goal is to determine:

> **Which tasks should be automated, which actions need deterministic controls, and where a human should remain in the loop?**

---

## Why I Built This

Many AI agent demos stop after:

```text
Prompt
→ Agent
→ Tool Call
→ Answer
```

I wanted to explore what happens after that point.

A business AI system also needs to answer questions such as:

- How should multiple agents divide responsibilities?
- Which logic should remain deterministic?
- How should agents interact with structured business data?
- What happens when an AI wants to modify important data?
- Should every requested tool action be allowed?
- How can a human approve an AI action?
- What happens if the backend restarts while approval is pending?
- How can interrupted AI workflows resume safely?
- How should conversation sessions remain isolated?
- How should internal CRM facts be separated from external research?

AI Sales Copilot was built around these problems.

---

## Production-Tested Workflows

The current deployment has been tested for:

- Frontend-to-backend production integration
- CRM persistence
- Daily pipeline review
- Lead scoring
- Multi-agent orchestration
- CRM specialist execution
- Research specialist execution
- External buying signals
- Recommended actions
- Reliability warnings
- Synthetic company protection
- Tool guardrails
- Human-in-the-loop approval
- Durable pending approvals
- Railway redeployment persistence
- RunState restoration
- Agent resume after approval
- CRM write after approval
- Pending approval cleanup
- Multi-session isolation
- Sidebar section navigation

---

## Current Scope

This project is intentionally focused on completing a reliable end-to-end AI workflow.

The current version does **not** attempt to be a full enterprise CRM platform.

Possible future improvements include:

- Authentication
- Role-based access control
- PostgreSQL
- Real CRM integrations
- Agent observability
- Automated evaluation pipelines
- Model routing based on task complexity
- Scheduled pipeline reviews
- Approval history and audit logs
- Expanded automated testing

These features are intentionally outside the current demo scope.

---

## Project Goal

AI Sales Copilot is designed as a portfolio project demonstrating applied AI system design rather than only prompt engineering.

The project focuses on the intersection of:

```text
AI Agents
+
Business Workflows
+
Structured Data
+
Human Oversight
+
Production Deployment
```

---

## Author

**Tiger Peng**

M.S. Business Analytics  
B.S. Electrical Engineering

Focus areas:

AI Solutions · Technical Product Management · Applied AI · Agent Systems