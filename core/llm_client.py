import os
import json
from openai import OpenAI
from pydantic import ValidationError
from typing import Optional
from dotenv import load_dotenv

from core.schemas import TemplateProfile, DeckSpec

load_dotenv()

# Safely read and strip any accidental smart quotes from the API key
api_key = os.environ.get("OPENAI_API_KEY", "").strip(' \t\n\r"“”\'')
client = OpenAI(api_key=api_key) if api_key else OpenAI()

SYSTEM_PROMPT = """You are an expert PowerPoint deck writer.
You MUST output valid JSON matching the provided JSON schema.
You MUST only use the 'allowed_layout_ids' provided to you.
You MUST only fill fields that exist for the chosen layout.
"""

from core.multi_agent import app, AgentState

def generate_deck(profile: TemplateProfile, prompt: str, slide_count: str, tone: str, template_path: str) -> DeckSpec:
    initial_state = {
        "profile": profile,
        "prompt": prompt,
        "slide_count": slide_count,
        "tone": tone,
        "template_path": template_path,
        "layouts_context": "",
        "planned_outline": "",
        "draft_deck_spec": None,
        "review_feedback": "",
        "review_passed": False,
        "iterations": 0
    }
    
    # Run the langgraph app
    final_state = app.invoke(initial_state)
    
    if final_state["draft_deck_spec"] is None:
        raise ValueError(f"Agent failed to generate valid deck: {final_state.get('review_feedback')}")
        
    return final_state["draft_deck_spec"]

def edit_deck(profile: TemplateProfile, current_deck: DeckSpec, instruction: str, template_path: str) -> DeckSpec:
    # For MVP editing, we can route a specialized edit instruction through the same graph
    # We prefix the prompt with current state.
    edit_prompt = (
        f"CURRENT DECK STATE:\n{current_deck.model_dump_json()}\n\n"
        f"USER EDIT INSTRUCTION:\n{instruction}\n\n"
        f"Please redesign the deck narrative and structure applying these changes."
    )
    
    initial_state = {
        "profile": profile,
        "prompt": edit_prompt,
        "slide_count": str(len(current_deck.slides)),
        "tone": "Keep current tone",
        "template_path": template_path,
        "layouts_context": "",
        "planned_outline": "",
        "draft_deck_spec": None,
        "review_feedback": "",
        "review_passed": False,
        "iterations": 0
    }
    
    final_state = app.invoke(initial_state)
    if final_state["draft_deck_spec"] is None:
        raise ValueError(f"Agent failed to edit valid deck: {final_state.get('review_feedback')}")
        
    return final_state["draft_deck_spec"]
