from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield




app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
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

class ApprovalRequest(BaseModel):
    run_id: str

class ResearchTask(BaseModel):
    task: str

class ManagerTask(BaseModel):
    task: str



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
    return await run_sales_agent_task(
        agent_task.task,
        agent_task.session_id
    )


@app.post("/agent/approve")
async def approve_agent(request: ApprovalRequest):

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
async def generate_pipeline_review():

    return await run_daily_pipeline_review()