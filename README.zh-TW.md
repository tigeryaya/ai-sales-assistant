# AI Sales Copilot

[English](./README.md) | [繁體中文](./README.zh-TW.md)

一套已實際部署的 **Multi-Agent AI Sales Operations Assistant**，整合 CRM 結構化資料、Deterministic Lead Scoring、外部公司研究、AI 銷售建議，以及可持久化的 Human-in-the-Loop 工作流程。

> **設計目標：** AI 用在它有價值的地方、Deterministic Logic 用在需要穩定性的地方，而高風險行為保留 Human Oversight。

## 線上 Demo

- **Frontend:** https://ai-sales-assistant-teal.vercel.app
- **Backend API:** https://ai-sales-assistant-production-6111.up.railway.app
- **Swagger Docs:** https://ai-sales-assistant-production-6111.up.railway.app/docs

> 公開部署使用 **Safe Demo Mode**。高成本 AI endpoint 有額外保護，敏感 CRM 寫入與 Approval Execution 也限制匿名使用者操作。

---

## 這個作品展示什麼

這不只是 Chatbot 或單純 Tool Calling Demo，而是一套完整的 AI Application Workflow：

- 使用 **OpenAI Agents SDK** 建立 Multi-Agent Orchestration
- CRM 結構化資料與 Deterministic Lead Scoring
- External Research 與 Internal CRM Facts 分離
- Tool Guardrails
- Durable Human-in-the-Loop
- RunState Persistence / Restore / Resume
- Session-isolated Conversation Memory
- Cloudflare Turnstile Bot Protection
- Server-side AI Response Cache
- App-level Daily AI Usage Quotas
- Concurrency Controls
- Railway Persistent Volume
- **Vercel + Railway** Production Deployment

---

## 系統架構

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

**[查看 Full Architecture →](./docs/architecture.md)**

---

## 核心流程

### Daily Pipeline Review

Dashboard 可以產生：

- Top Leads
- Deterministic Lead Scores
- CRM-based Prioritization Reasons
- External Buying Signals
- Sales Interpretations
- Recommended Actions
- Reliability Warnings
- Agent Activity

Sales Manager 負責 Orchestration，而不是讓單一 Agent 包辦所有工作。

### CRM Specialist

CRM Specialist 使用 CRM 的結構化欄位，例如 Customer、Company、Budget、Interest、Lead Status 與 Lead Score。

Lead Score 由 deterministic business logic 計算：

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

Research Specialist 研究與 CRM Company 相關的公開資訊與 buying signals。

系統刻意分離：

```text
Internal CRM Facts ≠ External Public Research
```

外部資訊可以支援 AI 判斷，但不會被默認成 CRM 已驗證事實。

---

## Durable Human-in-the-Loop

受保護的 CRM 寫入不會直接執行。

```text
Agent 要求修改 CRM
        ↓
Tool Guardrail
        ↓
Approval Required
        ↓
RunState Persisted
        ↓
Pending Approval 儲存
        ↓
Human Approves
        ↓
RunState Restored
        ↓
Agent Resumes
        ↓
CRM Write
```

Pending Approval 並不是只存在 Python process memory，而是持久化到 SQLite，因此可以跨 Railway Redeploy 保留。

### Public Demo Safety

公開網站刻意限制 Approval / CRM Write Execution，避免匿名使用者直接修改 Demo CRM。完整 HITL Resume / Write 流程保留在 Private / Local Controlled Demo 中展示。

---

## Tool Guardrails

Human Approval 不是唯一的控制層。

```text
proposal
→ 可以進入 Human Approval

won / lost
→ 在 Approval 前由 Tool Guardrail 阻擋
```

因此流程是：

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

系統支援 SQLite-backed Conversation Sessions。

API 可以傳入 `session_id`，不同 session 擁有獨立 conversation history。

```text
kevin-session-001
Previous context: Kevin Chen has a budget of 500000

Question: "What is his budget?"
→ 500000
```

Fresh session 不會自動繼承 Kevin 的 context。

---

## Abuse & Cost Controls

因為作品有公開網址，所以高成本 AI endpoint 不能毫無限制地暴露在網路上。

### Cloudflare Turnstile

Frontend 取得 Turnstile token，FastAPI backend 執行 server-side verification，驗證成功後才允許進入昂貴 AI workflow。

### Response Cache

Daily Pipeline Review 支援 server-side cache。在 cache window 內重複請求時，直接回傳已產生結果，不會重新跑一次 multi-agent workflow。

### Daily AI Quotas

Backend 維護 app-level daily counters：

```text
DAILY_REVIEW_LIMIT
AGENT_TASK_DAILY_LIMIT
```

Quota 用完後，API 回傳 HTTP `429`，避免繼續消耗 model resources。

### Concurrency Controls

Async lock 避免短時間大量 simultaneous requests 同時啟動重複的昂貴 AI workflow。

### Persistent Usage State

Quota / Cache 狀態持久化於：

```text
/data/usage.db
```

所以 Railway redeploy 後 protection state 仍可以保留。

---

## Production Persistence

Railway Persistent Volume 掛載於：

```text
/data
```

目前 production 使用：

```text
/data/crm.db
/data/sales_sessions.db
/data/usage.db
```

分別保存 CRM Records、Pending Approval State、Interrupted RunState、Conversation Sessions、Daily AI Usage Counters 與 Cached Review Responses。

---

## Synthetic Demo Data

Demo CRM 中包含 synthetic records。

**NovaTech 是刻意建立的 Synthetic Demo Data。**

系統不會因為網路上存在同名公司，就把相關外部公開資訊直接當成 Demo CRM 中 Kevin Chen 所屬公司的真實資料。

---

## Tech Stack

### AI / Agent Layer

- OpenAI Agents SDK
- Multi-Agent Orchestration
- Tool Calling
- Tool Guardrails
- Human-in-the-Loop
- RunState Persistence
- Web Research Tools
- SQLite-backed Conversation Sessions

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

Swagger：

https://ai-sales-assistant-production-6111.up.railway.app/docs

---

## Local Development

### Backend

```bash
python -m venv .venv
```

Windows：

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

Backend secrets 應放在本機 `.env` 或 deployment environment variables，不應 commit 到 Git。

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

Frontend build-time variables：

```text
VITE_API_BASE_URL
VITE_TURNSTILE_SITE_KEY
```

---

## Reliability Design

目前 reliability mechanisms 包含：

- Deterministic Lead Scoring
- Agent Responsibility Separation
- CRM / External Research Separation
- Tool Guardrails
- Human Approval
- Durable Pending State
- RunState Restoration
- Session Isolation
- Synthetic Data Protection
- Post-Approval CRM Verification
- Persistent Storage
- Turnstile Verification
- Server-side Response Cache
- Daily Usage Quotas
- Concurrency Controls
- Public Demo Restrictions

> **設計目標是 Controlled Automation，而不是 Maximum Autonomy。**

---

## 目前 Scope

目前重點是建立一條可靠、可解釋、可實際部署的 end-to-end AI workflow，而不是完整 Enterprise CRM Platform。

後續可以擴充：

- Authentication / Role-Based Access Control
- PostgreSQL
- Real CRM Integration
- Agent Observability
- Automated Evaluation Pipeline
- Model Routing
- Scheduled Pipeline Review
- Approval History / Audit Log
- Expanded Automated Testing

---

## 為什麼做這個專案

很多 AI Agent Demo 停在：

```text
Prompt
→ Agent
→ Tool Call
→ Answer
```

但進到實際 Business System 後，還要處理：

- Multi-Agent 怎麼分工？
- 哪些 decision 應該保持 deterministic？
- Agent 怎麼使用 Structured Business Data？
- AI 想修改重要資料時怎麼辦？
- Interrupted Workflow 如何 Resume？
- 不同 Conversation 怎麼維持 Session Isolation？
- 公開 AI Demo 時，怎麼避免昂貴 endpoint 被濫用？

---

## Author

**Tiger Peng**

M.S. Business Analytics  
B.S. Electrical Engineering

**AI Solutions · Technical Product Management · Applied AI · Agent Systems**
