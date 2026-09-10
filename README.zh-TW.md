# AI Sales Copilot

[English](./README.md) | [繁體中文](./README.zh-TW.md)

一套已實際部署的 **Multi-Agent AI Sales Operations Assistant**。

系統整合 CRM 結構化資料、Lead Scoring、外部公司研究、AI 銷售建議，以及可持久化的 Human-in-the-Loop 審批流程，並透過單一 Dashboard 提供操作與展示。

這個專案的重點不只是讓 AI Agent 呼叫工具，而是處理一個更接近實際企業 AI 系統的問題：

> **哪些工作可以交給 AI 自動完成，哪些操作需要程式規則限制，以及哪些重要決策必須保留人工確認？**

## 線上 Demo

**Frontend**

https://ai-sales-assistant-teal.vercel.app

**Backend API**

https://ai-sales-assistant-production-6111.up.railway.app

**API Documentation**

https://ai-sales-assistant-production-6111.up.railway.app/docs

---

## 專案概述

AI Sales Copilot 協助業務團隊整理每日 Sales Pipeline。

系統結合：

- CRM 結構化資料
- Deterministic Lead Scoring
- 外部公司研究
- Multi-Agent 協作
- AI 銷售建議
- Human-in-the-Loop
- Agent RunState persistence
- Conversation Memory
- Production Deployment

系統並不直接讓 AI 擁有無限制修改 CRM 的權限。

重要寫入操作會經過：

```text
AI 判斷
   ↓
Tool Guardrail
   ↓
人工審批
   ↓
CRM 寫入
```

因此這個作品的核心不是「讓 Agent 越自主越好」，而是嘗試建立一個比較可靠、可控、可恢復的 AI 工作流程。

---

## 核心功能

### 1. Multi-Agent Sales Workflow

Backend 使用 **OpenAI Agents SDK** 建立多 Agent 協作流程。

目前包含：

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

擔任 Orchestrator。

負責整合 CRM Specialist 與 Research Specialist 的結果，產生每日 Pipeline Review。

### CRM Specialist

負責處理 CRM 內的結構化資料，例如：

- Customer
- Company
- Budget
- Interest
- Lead Status
- Lead Score

### Research Specialist

負責研究 CRM 公司相關的外部公開訊號，提供 Sales Intelligence。

系統刻意將：

```text
Internal CRM Facts
```

與：

```text
External Research
```

分開處理，避免 AI 將網路上的外部資訊錯誤當成 CRM 內部事實。

---

## Daily Pipeline Review

Dashboard 可以產生每日 Sales Pipeline Review。

內容包含：

- Top Leads
- Lead Score
- CRM-based Reason
- Buying Signals
- Sales Interpretation
- Recommended Actions
- Reliability Warnings
- Agent Activity

目前固定 Demo baseline：

| Customer | Company | Status | Score |
|---|---|---|---:|
| Kevin Chen | NovaTech | qualified | 60 |
| Sarah Lin | Cloudflare | new | 40 |
| Michael Wu | ServiceNow | new | 40 |
| Emily Chen | Snowflake | new | 25 |

其中：

**NovaTech 為刻意建立的 Synthetic Demo Data。**

系統不會因為網路上存在同名 NovaTech 公司，就把那些公開資訊直接當成 Kevin Chen 所屬公司的真實資料。

---

## Lead Scoring

Lead Score 並不是完全交給 LLM 自由判斷。

系統使用 CRM 中的結構化資料執行 scoring logic。

例如：

- Budget
- Interest
- Lead Status

流程：

```text
CRM Data
   ↓
Lead Scoring Logic
   ↓
Prioritized Leads
   ↓
AI Interpretation
```

這樣可以把：

```text
Deterministic Business Logic
```

與：

```text
LLM Reasoning
```

分開。

對需要穩定數值邏輯的部分，不必全部交給 AI 生成。

---

## External Buying Signals

Research Specialist 可以研究真實公司的外部資訊，尋找可能與銷售機會相關的訊號。

Dashboard 刻意分成：

```text
Verified External Fact
        ↓
Sales Interpretation
```

也就是：

**外部事實**與**AI 的商業解讀**不是同一件事。

AI 可以根據已取得的資訊進行銷售判斷，但不會把自己的推論標示成已驗證事實。

---

## Recommended Actions

當 CRM 分析與外部研究完成後，Sales Manager 會產生下一步建議。

例如：

- 優先聯繫高分 Lead
- 針對 Buying Signal 進一步研究
- 準備 Proposal
- Review Qualified Opportunity

這些 Recommended Actions 屬於 AI 建議。

如果後續涉及敏感 CRM 寫入，仍然必須經過審批流程。

---

## Durable Human-in-the-Loop

這是目前專案最重要的功能之一。

當 AI Agent 想執行受保護的 CRM 寫入時：

```text
Agent 要求修改 CRM
        ↓
Tool Guardrail
        ↓
需要 Human Approval
        ↓
RunState 持久化
        ↓
Dashboard 顯示 Pending Approval
        ↓
Human 點擊 Approve
        ↓
Restore RunState
        ↓
Agent 繼續執行
        ↓
CRM 寫入
```

這裡的關鍵在於：

**Pending Approval 並不是只存在 Python 記憶體裡。**

系統將相關狀態持久化到 SQLite，因此就算 Backend 發生 redeploy 或 process restart，也不會直接失去尚未完成的審批流程。

---

## Durable RunState

當 Agent 因為等待人工確認而被 interrupt 時，系統會保存執行狀態。

Production 已實際測試：

```text
建立 Pending Approval
        ↓
Railway Redeploy
        ↓
Pending Approval 仍存在
        ↓
Restore RunState
        ↓
從 Vercel Dashboard Approve
        ↓
Resume Agent
        ↓
CRM 更新成功
        ↓
Pending Approval 自動移除
```

這表示 AI workflow 不需要假設：

> 「Agent 開始後一定要在同一次 process 裡跑完。」

而是可以：

```text
Pause
→ Persist
→ Restore
→ Resume
```

---

## Tool Guardrails

CRM 修改工具除了 Human Approval 外，還有 Tool Guardrail。

目前 Demo Policy 例如：

```text
proposal
→ 可以通過 Guardrail
→ 進入 Human Approval

won / lost
→ 在 Approval 之前
→ 就會被 Guardrail 阻擋
```

因此目前架構包含兩層不同用途的控制：

```text
Agent Decision
      ↓
Tool Guardrail
      ↓
Human Approval
      ↓
CRM Write
```

Human Approval 並不是拿來取代程式規則。

Guardrail 與 Human Approval 各自負責不同的安全控制。

---

## Conversation Memory

系統支援 SQLite-backed conversation session。

API 可以傳入：

```text
session_id
```

不同 session 擁有獨立 conversation history。

例如：

```text
kevin-session-001
```

之前已討論：

```text
Kevin Chen
Budget = 500000
```

之後同一個 session 問：

```text
What is his budget?
```

系統可以回答：

```text
500000
```

但如果換成：

```text
fresh-session-001
```

直接問：

```text
What is his budget?
```

系統不會自動取得 Kevin 的 context。

這代表不同 session 之間可以維持 conversation isolation。

---

## Pending Approval Dashboard

Frontend 可以直接顯示目前等待人工確認的 AI action。

Approval Card 會呈現例如：

```text
Customer
Company
Current CRM Status
Requested CRM Status
Tool
Durable RunState
```

使用者可以直接從 Dashboard 點擊：

```text
Approve
```

Approve 成功後：

```text
Restore RunState
        ↓
Resume Agent
        ↓
Execute CRM Tool
        ↓
Update CRM
        ↓
Refresh Pending List
```

Frontend 也會再次讀取 CRM 狀態，確認實際更新結果。

---

## Agent Activity

Dashboard 可以顯示 Multi-Agent workflow 的執行狀態。

```text
Sales Manager
     ↓
CRM Specialist
Research Specialist
     ↓
Recommendation
```

Agent 尚未執行時顯示：

```text
Waiting
```

完成後會顯示：

```text
Completed
```

這可以讓使用者與面試官比較直觀地理解系統內部正在發生什麼事情。

---

## Dashboard Navigation

Frontend 使用單頁 React Dashboard。

Sidebar 包含：

- Overview
- Pipeline
- AI Review
- Approvals
- Agent Activity

Sidebar 使用 Smooth Scroll 在同一頁不同 Section 之間導航。

目前沒有使用 React Router，也沒有將 Dashboard 拆成多頁。

這是刻意的設計選擇，因為目前作品重點是 AI workflow，而不是建立複雜 frontend routing architecture。

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

完整架構、Durable HITL 與 RunState Resume 流程：

**[查看完整系統架構 →](./docs/architecture.md)**

---

## Tech Stack

### AI / Agent

- OpenAI Agents SDK
- Multi-Agent Orchestration
- Tool Calling
- Tool Guardrails
- Human-in-the-Loop
- RunState Persistence
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

### Deployment

- Railway
- Railway Persistent Volume
- Vercel
- GitHub

---

## API Overview

目前主要 Endpoint：

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

FastAPI Swagger：

https://ai-sales-assistant-production-6111.up.railway.app/docs

---

## Production Persistence

Railway Backend 已掛載 Persistent Volume。

Production environment path：

```text
CRM_DB_PATH=/data/crm.db

SALES_SESSION_DB_PATH=/data/sales_sessions.db
```

Persistent Storage 用於：

- CRM records
- Agent conversation sessions
- Pending approvals
- Interrupted workflow state

Production 已實際測試 Railway Redeploy 後資料仍然存在。

---

## Reliability Design

這個專案刻意不讓單一 Agent 擁有整個系統的無限制控制權。

目前包含的 Reliability Design：

- Structured CRM Data
- Deterministic Lead Scoring
- Agent Responsibility Separation
- CRM / External Research Separation
- Tool Guardrails
- Human Approval
- Durable Pending State
- RunState Restoration
- Session Isolation
- Synthetic Data Protection
- Reliability Warnings
- Post-Approval CRM Verification

這套系統的目標不是追求：

```text
Maximum Autonomy
```

而是回答：

> **哪些任務適合自動化？哪些操作應該使用 deterministic controls？哪些重要行為仍然需要 Human-in-the-Loop？**

---

## 為什麼做這個專案

很多 AI Agent Demo 的流程停在：

```text
Prompt
→ Agent
→ Tool
→ Answer
```

但真正進到商業系統後，還會出現很多其他問題：

- 多個 Agent 應該如何分工？
- 哪些邏輯應該由程式決定，而不是 LLM？
- Agent 怎麼使用結構化 CRM Data？
- AI 想修改重要資料時怎麼辦？
- 每個 Tool Call 都應該被允許嗎？
- 如何加入 Human Approval？
- Backend restart 後 Pending Approval 怎麼辦？
- 被 interrupt 的 Agent 如何恢復？
- 不同 Conversation 怎麼避免 context 混在一起？
- Internal CRM Facts 與 External Research 如何分離？

AI Sales Copilot 就是針對這些問題建立的作品。

---

## Production-Tested Workflows

目前 Production 已測試：

- Frontend / Backend integration
- CRM persistence
- Daily Pipeline Review
- Lead Scoring
- Multi-Agent Orchestration
- CRM Specialist
- Research Specialist
- Buying Signals
- Recommended Actions
- Reliability Warnings
- Synthetic Company Protection
- Tool Guardrails
- Human-in-the-Loop Approval
- Durable Pending Approval
- Railway Redeploy Persistence
- RunState Restoration
- Agent Resume
- CRM Write after Approval
- Pending Approval Cleanup
- Multi-Session Isolation
- Sidebar Section Navigation

---

## 目前 Scope

這個專案目前的重點是：

**完成一條可靠、可展示、可以實際部署的 end-to-end AI workflow。**

它目前並不是完整 Enterprise CRM Platform。

後續可擴充：

- Authentication
- Role-Based Access Control
- PostgreSQL
- Real CRM Integration
- Agent Observability
- Automated Evaluation Pipeline
- Model Routing
- Scheduled Pipeline Review
- Approval History / Audit Log
- Expanded Automated Testing

這些目前刻意沒有繼續加入，以避免 Demo Scope 無限制膨脹。

---

## Project Goal

AI Sales Copilot 是一個 Applied AI System Design Portfolio Project。

重點不是只有 Prompt Engineering，而是整合：

```text
AI Agents
+
Business Workflow
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

Focus Areas：

AI Solutions · Technical Product Management · Applied AI · Agent Systems