import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from turnstile import verify_turnstile
from ai_service import analyze_lead
from lead_scoring import calculate_lead_score
from agent_service import (
    run_sales_agent_task,
    approve_pending_run,
    run_research_agent_task,
    run_sales_manager_task,
    run_daily_pipeline_review,
    list_pending_approvals
)
from database import (
    init_db,
    create_customer as create_customer_in_db,
    get_all_customers,
    get_customer_by_id,
    update_customer_status_in_db
)

from usage_guard import (
    init_usage_db,
    daily_review_lock,
    get_cached_daily_review,
    save_daily_review_cache,
    reserve_daily_generation,
    get_daily_usage,
    DAILY_REVIEW_LIMIT,
    agent_task_lock,
    reserve_agent_task,
    get_agent_task_usage,
    AGENT_TASK_DAILY_LIMIT
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_usage_db()
    yield


PUBLIC_DEMO_MODE = (
    os.getenv("PUBLIC_DEMO_MODE", "true").lower()
    == "true"
)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://ai-sales-assistant-teal.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class CustomerCreate(BaseModel):
    name: str
    company: str
    email: str
    budget: int
    interest: str

class CustomerStatusUpdate(BaseModel):
    lead_status: Literal[
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost"
    ]
class AgentTask(BaseModel):
    session_id: str
    task: str
    turnstile_token: str

class ApprovalRequest(BaseModel):
    run_id: str

class ResearchTask(BaseModel):
    task: str

class ManagerTask(BaseModel):
    task: str

class AgentApproveRequest(BaseModel):
    run_id: str

class PipelineReviewRequest(BaseModel):
    turnstile_token: str | None = None

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/customers")
def get_customers():
    return get_all_customers()


@app.post("/customers")
def create_customer(customer: CustomerCreate):

    customer_id = create_customer_in_db(
        customer.name,
        customer.company,
        customer.email,
        customer.budget,
        customer.interest
    )

    new_customer = {
        "id": customer_id,
        "name": customer.name,
        "company": customer.company,
        "email": customer.email,
        "budget": customer.budget,
        "interest": customer.interest,
        "lead_status": "new"
    }

    return new_customer


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):

    customer = get_customer_by_id(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer

@app.patch("/customers/{customer_id}")
def update_customer_status(
    customer_id: int,
    update: CustomerStatusUpdate
):

    customer = update_customer_status_in_db(
        customer_id,
        update.lead_status
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer

@app.get("/customers/{customer_id}/score")
def get_customer_score(customer_id: int):

    customer = get_customer_by_id(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    score = calculate_lead_score(
        customer["budget"],
        customer["interest"],
        customer["lead_status"]
    )

    return {
        "customer_id": customer_id,
        "name": customer["name"],
        "lead_score": score
    }

@app.get("/customers/{customer_id}/ai-analysis")
def get_customer_ai_analysis(customer_id: int):

    customer = get_customer_by_id(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    rule_score = calculate_lead_score(
        customer["budget"],
        customer["interest"],
        customer["lead_status"]
    )

    analysis = analyze_lead(
        customer,
        rule_score
    )

    return {
        "customer_id": customer_id,
        "name": customer["name"],
        "rule_score": rule_score,
        "ai_analysis": analysis.model_dump()
    }

@app.post("/agent/run")
async def run_agent(agent_task: AgentTask):

    turnstile_valid = await verify_turnstile(
        agent_task.turnstile_token
    )

    if not turnstile_valid:
        raise HTTPException(
            status_code=403,
            detail="Turnstile verification failed."
        )

    async with agent_task_lock:

        allowed, usage_count = reserve_agent_task()

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Daily Agent Task limit reached. "
                    "Please try again tomorrow."
                )
            )

        result = await run_sales_agent_task(
            agent_task.task,
            agent_task.session_id
        )

        return {
            **result,
            "protection": {
                "turnstile_verified": True,
                "daily_agent_task_count": usage_count,
                "daily_agent_task_limit": AGENT_TASK_DAILY_LIMIT
            }
        }

@app.post("/agent/approve")
async def agent_approve(request: AgentApproveRequest):

    if PUBLIC_DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail=(
                "Approval execution is disabled in public demo mode. "
                "Human-in-the-loop approval is available in the private demo."
            )
        )

    result = await approve_pending_run(
        request.run_id
    )

    return result


@app.get("/agent/pending")
async def get_pending_approvals():
    return await list_pending_approvals()



@app.post("/research/run")
async def run_research(request: ResearchTask):

    return await run_research_agent_task(
        request.task
    )


@app.post("/manager/run")
async def run_manager(request: ManagerTask):

    return await run_sales_manager_task(
        request.task
    )


@app.post("/pipeline/review")
async def pipeline_review(
    request: PipelineReviewRequest | None = None
):

    # 1. Cached responses are cheap.
    #    If cache exists, return it immediately.
    cached_review = get_cached_daily_review()

    if cached_review is not None:
        current_usage = get_daily_usage()

        return {
            **cached_review,
            "protection": {
                "cached": True,
                "turnstile_verified": False,
                "daily_generation_count": current_usage,
                "daily_generation_limit": DAILY_REVIEW_LIMIT
            }
        }

    # 2. No cache = this request may trigger an expensive AI run.
    #    Verify Turnstile before touching quota or OpenAI.
    turnstile_token = (
        request.turnstile_token
        if request is not None
        else ""
    )

    turnstile_valid = await verify_turnstile(
        turnstile_token
    )

    if not turnstile_valid:
        raise HTTPException(
            status_code=403,
            detail="Turnstile verification failed."
        )

    # 3. Only one expensive generation at a time.
    async with daily_review_lock:

        # Another request may have generated a review
        # while this request was waiting.
        cached_review = get_cached_daily_review()

        if cached_review is not None:
            current_usage = get_daily_usage()

            return {
                **cached_review,
                "protection": {
                    "cached": True,
                    "turnstile_verified": True,
                    "daily_generation_count": current_usage,
                    "daily_generation_limit": DAILY_REVIEW_LIMIT
                }
            }

        # 4. Reserve one generation slot.
        allowed, generation_count = reserve_daily_generation()

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Daily AI generation limit reached. "
                    "Please try again tomorrow."
                )
            )

        # 5. Only now do we spend AI/API resources.
        result = await run_daily_pipeline_review()

        # 6. Cache successful result.
        save_daily_review_cache(result)

        return {
            **result,
            "protection": {
                "cached": False,
                "turnstile_verified": True,
                "daily_generation_count": generation_count,
                "daily_generation_limit": DAILY_REVIEW_LIMIT
            }
        }