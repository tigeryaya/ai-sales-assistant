import json
import os
import uuid

from dotenv import load_dotenv
from agents import Agent, Runner,function_tool,RunConfig,RunState,ToolExecutionConfig,ToolGuardrailFunctionOutput,SQLiteSession, WebSearchTool
from agents.decorators import tool,tool_input_guardrail
from lead_scoring import calculate_lead_score
from database import (
    get_customer_by_id,
    get_all_customers,
    update_customer_status_in_db,
    save_pending_run,
    get_pending_run,
    get_all_pending_runs,
    delete_pending_run
)
from pydantic import BaseModel


load_dotenv()

SALES_SESSION_DB_PATH = os.getenv(
    "SALES_SESSION_DB_PATH",
    "sales_sessions.db"
)





@tool
def get_customer(
    customer_id: int
) -> str:
    """Get one customer from the CRM by customer ID."""

    customer = get_customer_by_id(customer_id)

    if customer is None:
        return json.dumps({
            "error": "Customer not found"
        })

    return json.dumps(
        customer,
        ensure_ascii=False
    )

@tool
def calculate_customer_score(
    customer_id: int
) -> str:
    """Calculate the deterministic lead score for one customer."""

    customer = get_customer_by_id(customer_id)

    if customer is None:
        return json.dumps({
            "error": "Customer not found"
        })

    score = calculate_lead_score(
        customer["budget"],
        customer["interest"],
        customer["lead_status"]
    )

    return json.dumps({
        "customer_id": customer_id,
        "lead_score": score
    })


@tool
def get_pipeline_snapshot() -> str:
    """Get a read-only snapshot of all CRM customers ranked by lead score."""

    customers = get_all_customers()

    pipeline = []

    for customer in customers:
        score = calculate_lead_score(
            customer["budget"],
            customer["interest"],
            customer["lead_status"]
        )

        pipeline.append({
            "customer_id": customer["id"],
            "name": customer["name"],
            "company": customer["company"],
            "budget": customer["budget"],
            "interest": customer["interest"],
            "lead_status": customer["lead_status"],
            "lead_score": score
        })

    pipeline.sort(
        key=lambda customer: customer["lead_score"],
        reverse=True
    )

    return json.dumps(
        {
            "customer_count": len(pipeline),
            "customers": pipeline
        },
        ensure_ascii=False
    )





@tool_input_guardrail
def protect_closed_status(data):
    args = json.loads(data.context.tool_arguments or "{}")

    new_status = args.get("new_status")

    if new_status in {"won", "lost"}:
        return ToolGuardrailFunctionOutput.reject_content(
            "CRM policy: AI agents are not allowed to set lead_status "
            "to won or lost. These statuses must be closed manually."
        )

    return ToolGuardrailFunctionOutput.allow()



@tool(
    needs_approval=True,
    tool_input_guardrails=[protect_closed_status]
)
def update_customer_status(
    customer_id: int,
    new_status: str
) -> str:
    """Update a customer's CRM status. This action requires human approval."""

    customer = get_customer_by_id(customer_id)

    if customer is None:
        return json.dumps({
            "success": False,
            "error": "customer not found"
        }, ensure_ascii=False)

    old_status = customer["lead_status"]

    updated_customer = update_customer_status_in_db(
        customer_id,
        new_status
    )

    if updated_customer is None:
        return json.dumps({
            "success": False,
            "error": "customer not found"
        }, ensure_ascii=False)

    return json.dumps({
        "success": True,
        "customer_id": customer_id,
        "old_status": old_status,
        "new_status": new_status
    }, ensure_ascii=False)




AGENT_RUN_CONFIG = RunConfig(
    tool_execution=ToolExecutionConfig(
        pre_approval_tool_input_guardrails=True
    )
)

class PipelineLead(BaseModel):
    customer_id: int
    name: str
    company: str
    lead_score: int
    crm_reason: str
    next_action: str


class BuyingSignal(BaseModel):
    company: str
    verified_fact: str
    source: str
    sales_interpretation: str


class DailyPipelineReview(BaseModel):
    top_leads: list[PipelineLead]
    buying_signals: list[BuyingSignal]
    action_items: list[str]
    warnings: list[str]




research_agent = Agent(
    name="Sales Research Agent",
    instructions=(
        "You are a B2B sales research specialist. "
        "Your job is to research public information about companies "
        "and identify recent buying signals that may help a salesperson. "

        "Focus on signals such as funding, hiring, expansion, "
        "new product launches, partnerships, leadership changes, "
        "technology initiatives, and other recent business developments. "

        "Use web search when current external information is needed. "

        "Clearly distinguish verified facts from your interpretation. "
        "Do not invent information. "
        "If reliable current information cannot be found, say so. "

        "You do not modify CRM data. "
        "Return concise findings that another sales agent can use."
    ),
    tools=[
        WebSearchTool()
    ]
)

crm_read_agent = Agent(
    name="CRM Read Agent",
    instructions=(
        "You are a read-only CRM specialist for B2B sales operations. "
        "Use the CRM tools to retrieve factual customer information "
        "and calculate deterministic lead scores when relevant. "
        "Never invent customer information. "
        "You are strictly read-only and cannot modify CRM data. "
        "Return concise factual findings that a Sales Manager Agent can use."
    ),
    tools=[
        get_customer,
        calculate_customer_score,
        get_pipeline_snapshot
    ]
)

sales_manager_agent = Agent(
    name="Sales Manager Agent",
    instructions=(
        "You are a B2B Sales Manager Copilot. "
        "Your job is to combine internal CRM information with current external research "
        "and produce practical sales recommendations. "

        "Use the CRM specialist when you need factual customer data, lead status, "
        "budget, interest, or deterministic lead score. "

        "Use the research specialist when you need current public information about "
        "a company, recent business developments, or potential buying signals. "

        "When both internal CRM data and external research are relevant, use both specialists "
        "and combine their findings into one clear recommendation. "

        "Clearly separate known CRM facts, verified external facts, and your interpretation. "
        "Never invent missing CRM data or external facts. "

        "You are read-only. "
        "You do not modify CRM data. "
        "If a CRM change is recommended, explain the recommendation but do not perform the change. "

        "Return concise, practical output for a salesperson, including the reason, "
        "priority, and recommended next action."
    ),
    tools=[
        crm_read_agent.as_tool(
            tool_name="crm_specialist",
            tool_description=(
                "Retrieve read-only CRM customer information and deterministic lead scores."
            ),
        ),
        research_agent.as_tool(
            tool_name="research_specialist",
            tool_description=(
                "Research current public company information and recent B2B buying signals."
            ),
        ),
    ],
)

daily_review_agent = sales_manager_agent.clone(
    name="Daily Pipeline Review Agent",
    instructions=(
        "You are a B2B Sales Manager Copilot generating a structured daily pipeline review. "

        "Always use the CRM specialist to retrieve the full pipeline snapshot and deterministic lead scores. "
        "Rank leads based on the CRM's deterministic scoring logic, not your own intuition. "

        "Use the research specialist only for real public companies when current external buying signals are useful. "
        "Do not research synthetic demo companies such as NovaTech. "
        "Never assume that a public company with the same name is the same CRM account. "

        "Clearly distinguish CRM facts, verified external facts, and sales interpretation. "
        "Do not invent missing CRM or external information. "

        "Return the top sales priorities, relevant buying signals, practical next actions, "
        "and warnings about uncertainty or synthetic data."
    ),
    output_type=DailyPipelineReview
)



sales_agent = Agent(
    name="Sales Assistant Agent",
    instructions=(
    "You are a B2B sales operations agent. "
    "When the user asks about a customer, use the available tools "
    "to retrieve factual CRM data instead of guessing. "
    "Use the lead scoring tool when lead priority is relevant. "
    "Never invent missing customer information. "
    "When the user explicitly requests a CRM status change, call the update_customer_status tool directly. "
    "Do not ask the user for confirmation in natural language before calling the tool. "
    "The application runtime handles human approval for CRM write actions. "
    "Never claim a CRM change succeeded unless the tool actually executed and returned success. "
    "Give a concise assessment and recommend the next sales action."
),
    tools=[
        get_customer,
        calculate_customer_score,
        update_customer_status
    ]
)













async def run_research_agent_task(task: str) -> dict:

    result = await Runner.run(
        research_agent,
        task
    )

    return {
        "result": result.final_output
    }


async def run_sales_manager_task(task: str) -> dict:

    result = await Runner.run(
        sales_manager_agent,
        task
    )

    trace = []

    for item in result.new_items:
        if item.type == "tool_call_item":
            raw = item.raw_item

            if isinstance(raw, dict):
                arguments = raw.get("arguments")
            else:
                arguments = getattr(raw, "arguments", None)

            try:
                arguments = json.loads(arguments) if arguments else {}
            except (json.JSONDecodeError, TypeError):
                pass

            trace.append({
                "type": "specialist_call",
                "specialist": item.tool_name,
                "arguments": arguments
            })

        elif item.type == "tool_call_output_item":
            trace.append({
                "type": "specialist_output",
                "call_id": item.call_id,
                "output": item.output
            })

    return {
        "result": result.final_output,
        "trace": trace
    }



async def run_sales_agent_task(
    task: str,
    session_id: str
) -> dict:

    
    session = SQLiteSession(
    session_id,
    SALES_SESSION_DB_PATH
      )


    result = await Runner.run(
        sales_agent,
        task,
        session=session,
        run_config=AGENT_RUN_CONFIG
    )

    trace = []

    for item in result.new_items:

        if item.type == "tool_call_item":
            raw = item.raw_item

            if isinstance(raw, dict):
                arguments = raw.get("arguments")
            else:
                arguments = getattr(raw, "arguments", None)

            try:
                arguments = json.loads(arguments) if arguments else {}
            except (json.JSONDecodeError, TypeError):
                pass

            trace.append({
                "type": "tool_call",
                "tool": item.tool_name,
                "call_id": item.call_id,
                "arguments": arguments
            })

        elif item.type == "tool_call_output_item":
            trace.append({
                "type": "tool_output",
                "call_id": item.call_id,
                "output": item.output
            })

    if result.interruptions:
        run_id = str(uuid.uuid4())
        state = result.to_state()

        state_json = state.to_string()

        save_pending_run(
            run_id,
            session_id,
            state_json
        )

       

        interruption = result.interruptions[0]

        arguments = interruption.arguments

        try:
            arguments = json.loads(arguments) if arguments else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "status": "approval_required",
            "run_id": run_id,
            "approval": {
                "tool": interruption.name,
                "arguments": arguments
            },
            "trace": trace
        }

    return {
        "result": result.final_output,
        "trace": trace
    }


async def run_daily_pipeline_review() -> dict:

    task = (
        "Generate today's Daily Pipeline Review for the entire CRM. "
        "Use the CRM specialist to retrieve the full pipeline snapshot "
        "and deterministic lead scores. "

        "Identify the top 3 sales priorities based on CRM scoring. "

        "Use the research specialist to research current public buying signals "
        "for relevant real public companies among the priority leads. "

        "NovaTech is synthetic demo CRM data. "
        "Do not research NovaTech or associate it with any real company found online. "

        "Clearly separate CRM facts, verified external facts, "
        "sales interpretation, recommended next actions, and warnings."
    )

    result = await Runner.run(
        daily_review_agent,
        task
    )

    review = result.final_output_as(
        DailyPipelineReview,
        raise_if_incorrect_type=True
    )

    trace = []

    for item in result.new_items:
        if item.type == "tool_call_item":
            trace.append({
                "type": "specialist_call",
                "specialist": item.tool_name
            })

    return {
        "review": review.model_dump(),
        "trace": trace
    }




async def list_pending_approvals() -> dict:

    pending_runs = get_all_pending_runs()

    items = []

    for pending in pending_runs:

        state = await RunState.from_string(
            sales_agent,
            pending["state_json"]
        )

        interruptions = state.get_interruptions()

        approvals = []

        for interruption in interruptions:

            arguments = interruption.arguments

            try:
                arguments = json.loads(arguments) if arguments else {}
            except (json.JSONDecodeError, TypeError):
                pass

            customer_info = None

            if isinstance(arguments, dict):

                customer_id = arguments.get("customer_id")

                if customer_id is not None:

                    customer = get_customer_by_id(customer_id)

                    if customer is not None:
                        customer_info = {
                            "customer_id": customer["id"],
                            "name": customer["name"],
                            "company": customer["company"],
                            "current_status": customer["lead_status"]
                        }

            approvals.append({
                "tool": interruption.name,
                "arguments": arguments,
                "customer": customer_info
            })

        if approvals:
            items.append({
                "run_id": pending["run_id"],
                "session_id": pending["session_id"],
                "created_at": pending["created_at"],
                "approvals": approvals
            })

    return {
        "count": len(items),
        "pending_runs": items
    }




async def approve_pending_run(run_id: str) -> dict:

    pending = get_pending_run(run_id)

    if pending is None:
        return {
            "status": "error",
            "message": "Pending run not found"
        }

    session_id = pending["session_id"]

    state = await RunState.from_string(
        sales_agent,
        pending["state_json"]
    )

    session = SQLiteSession(
    session_id,
    SALES_SESSION_DB_PATH
    )

    interruptions = state.get_interruptions()

    if not interruptions:
        return {
            "status": "error",
            "message": "No pending approval found"
        }

    for interruption in interruptions:
        state.approve(interruption)

    result = await Runner.run(
        sales_agent,
        state,
        session=session,
        run_config=AGENT_RUN_CONFIG
    )

    delete_pending_run(run_id)



    return {
        "status": "completed",
        "result": result.final_output
    }