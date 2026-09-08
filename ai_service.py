from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv()

client = OpenAI()


class LeadAIAnalysis(BaseModel):
    priority: Literal["low", "medium", "high"]
    reason: str
    next_action: str


def analyze_lead(customer: dict, rule_score: int):

    response = client.responses.parse(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "system",
                "content": (
                    "You are a B2B sales qualification assistant. "
                    "Analyze the lead using only the customer data provided. "
                    "Do not invent missing information. "
                    "The rule score was calculated by deterministic business rules. "
                    "Use it as one signal when deciding priority. "
                    "Explain the reason briefly and recommend one concrete next sales action."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Name: {customer['name']}\n"
                    f"Company: {customer['company']}\n"
                    f"Budget: {customer['budget']}\n"
                    f"Interest: {customer['interest']}\n"
                    f"Lead status: {customer['lead_status']}\n"
                    f"Rule score: {rule_score}/100"
                ),
            },
        ],
        text_format=LeadAIAnalysis,
    )

    return response.output_parsed