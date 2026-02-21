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

def generate_deck(profile: TemplateProfile, prompt: str, slide_count: str, tone: str) -> DeckSpec:
    # Build prompt context
    layouts_summary = []
    for layout in profile.layouts:
        if layout.layout_id in profile.allowed_layout_ids:
            allowed_keys = [p.key for p in layout.placeholders]
            layouts_summary.append(f"- Layout ID: {layout.layout_id}, Name: '{layout.layout_name}', Allowed Fields: {allowed_keys}")
    
    context = (
        f"Template Layouts Context:\n" + "\n".join(layouts_summary) + "\n\n"
        f"User Instructions:\n"
        f"Topic/Outline: {prompt}\n"
        f"Desired Slide Count: {slide_count}\n"
        f"Tone: {tone}\n\n"
        f"Generate the presentation data adhering to the DeckSpec schema."
    )
    
    return _call_llm_with_retries(context)

def edit_deck(profile: TemplateProfile, current_deck: DeckSpec, instruction: str) -> DeckSpec:
    layouts_summary = []
    for layout in profile.layouts:
        if layout.layout_id in profile.allowed_layout_ids:
            allowed_keys = [p.key for p in layout.placeholders]
            layouts_summary.append(f"- Layout ID: {layout.layout_id}, Name: '{layout.layout_name}', Allowed Fields: {allowed_keys}")
    
    context = (
        f"Template Layouts Context:\n" + "\n".join(layouts_summary) + "\n\n"
        f"Current DeckSpec JSON:\n{current_deck.model_dump_json()}\n\n"
        f"User Edit Instruction: {instruction}\n\n"
        f"Apply the edits and return the FULL UPDATED DeckSpec JSON."
    )
    return _call_llm_with_retries(context)

def _call_llm_with_retries(prompt_text: str, max_retries: int = 2) -> DeckSpec:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]
    
    for attempt in range(max_retries + 1):
        try:
            response = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=messages,
                response_format=DeckSpec
            )
            return response.choices[0].message.parsed
        except Exception as e:
            if attempt == max_retries:
                raise ValueError(f"Failed to generate valid DeckSpec after {max_retries} retries: {str(e)}")
            # Append error to messages to context for retry
            messages.append({"role": "assistant", "content": "The generated JSON was invalid."})
            messages.append({"role": "user", "content": f"The JSON generation failed with error: {str(e)}. Please fix the JSON and match the schema exactly."})
